"""执行漂移诊断纯函数 — 近期执行 vs 全期基线的偏离。

两类信号：
  - timing drift：近期 best_slot 发布占比 vs 全期（运营执行层，路由到 publish_note）
  - c5s trend：真 5s 完播月度趋势（内容开头吸引力，路由到 report）

纯函数、纯读：不写状态、不碰 score/pattern/cron。依据 auto_evolve 数据校准阈值。
"""
from __future__ import annotations

import re
import statistics
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path

from engine.publish_time import hour_to_bucket


def proj_date(proj: Path) -> str | None:
    """从项目目录路径提取 YYYY-MM-DD（workspace/YYYY/MM/DD/name 约定）。"""
    m = re.search(r"(20\d{2})[\\/](\d{2})[\\/](\d{2})", str(proj))
    return f"{m.group(1)}-{m.group(2)}-{m.group(3)}" if m else None


def within_days(pub_date: str | None, ref: date, n: int) -> bool:
    """pub_date 是否在 ref 当天往前 n 天内（闭区间，含 ref）。"""
    if not pub_date:
        return False
    try:
        d = datetime.strptime(pub_date, "%Y-%m-%d").date()
    except ValueError:
        return False
    return 0 <= (ref - d).days <= n


def _bucket_ratio(projects: list[dict], bucket: str) -> float:
    """projects 中 publish_hour 落入 bucket 的占比（无 publish_hour 的不计入分母）。"""
    items = [p for p in projects if p.get("publish_hour") is not None]
    if not items:
        return 0.0
    in_bucket = sum(1 for p in items if hour_to_bucket(p["publish_hour"]) == bucket)
    return in_bucket / len(items)


def _count_with_hour(projects: list[dict]) -> int:
    return sum(1 for p in projects if p.get("publish_hour") is not None)


def diagnose_timing_drift(recent: list[dict], all_projects: list[dict],
                          best_slot: str | None) -> dict:
    """近期 best_slot 发布占比 vs 全期。

    判定：recent_ratio < baseline_ratio × 0.5 且 recent_ratio < 0.20 → drift=True。
    依据：evening 全期 16%、7月 0%（recent=0 < 16%×0.5=8% 且 <20%）。
    最小样本保护：含时分记录 <3 → drift=False（空 recent / 全无 publish_hour 不误报）。
    注：baseline_ratio 基于 all_projects（含 recent），运营级粗筛；recent 占全期比例小时影响有限。
    """
    if not best_slot:
        return {"drift": False, "best_slot": None, "recent_ratio": 0.0,
                "baseline_ratio": 0.0, "recent_n": 0, "advice": None, "note": "无 best_slot"}
    n = _count_with_hour(recent)
    baseline_ratio = _bucket_ratio(all_projects, best_slot)
    if n < 3:
        return {"drift": False, "best_slot": best_slot, "recent_ratio": 0.0,
                "baseline_ratio": round(baseline_ratio, 3), "recent_n": n,
                "advice": None, "note": "近期样本不足（含时分记录少）"}
    recent_ratio = _bucket_ratio(recent, best_slot)
    drift = recent_ratio < baseline_ratio * 0.5 and recent_ratio < 0.20
    return {
        "best_slot": best_slot, "drift": drift,
        "recent_ratio": round(recent_ratio, 3),
        "baseline_ratio": round(baseline_ratio, 3),
        "recent_n": n,
        "advice": (f"近{n}条 {best_slot} 占比 {recent_ratio:.0%}（全期 {baseline_ratio:.0%}），"
                   f"建议下个发布窗口调 {best_slot}") if drift else None,
    }


def compute_c5s_trend(projects: list[dict]) -> dict:
    """真 5s 完播（c5s_real）月度趋势，近月 vs 上月。

    判定：月降幅 > 15% → flag=True。依据：0.43→0.32（-25%）。
    projects: [{"c5s_real": float|None, "pub_date": "YYYY-MM-DD"}, ...]
    """
    by_month: dict[str, list[float]] = defaultdict(list)
    for p in projects:
        c = p.get("c5s_real")
        d = p.get("pub_date") or ""
        if c is not None and d.startswith("20"):
            by_month[d[:7]].append(c)
    months = sorted(by_month)
    if len(months) < 2:
        return {"trend": "insufficient", "months": len(months),
                "flag": False, "advice": None}
    cur = statistics.median(by_month[months[-1]])
    prev = statistics.median(by_month[months[-2]])
    drop = (prev - cur) / prev if prev else 0.0
    flag = drop > 0.15
    return {
        "current_month": months[-1],
        "previous_month": months[-2],
        "current": round(cur, 3),
        "previous": round(prev, 3),
        "drop": round(drop, 3),
        "flag": flag,
        "advice": (f"5s完播 {prev:.2f}→{cur:.2f}（-{drop:.0%}），开头吸引力退化，"
                   f"检查 hook 文案/封面") if flag else None,
    }
