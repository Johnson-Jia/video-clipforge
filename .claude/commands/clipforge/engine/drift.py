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
    """
    if not best_slot:
        return {"drift": False, "best_slot": None, "note": "无 best_slot"}
    recent_ratio = _bucket_ratio(recent, best_slot)
    baseline_ratio = _bucket_ratio(all_projects, best_slot)
    drift = recent_ratio < baseline_ratio * 0.5 and recent_ratio < 0.20
    n = _count_with_hour(recent)
    return {
        "best_slot": best_slot,
        "drift": drift,
        "recent_ratio": round(recent_ratio, 3),
        "baseline_ratio": round(baseline_ratio, 3),
        "recent_n": n,
        "advice": (f"近{n}条 {best_slot} 占比 {recent_ratio:.0%}（全期 {baseline_ratio:.0%}），"
                   f"建议下个发布窗口调 {best_slot}") if drift else None,
    }
