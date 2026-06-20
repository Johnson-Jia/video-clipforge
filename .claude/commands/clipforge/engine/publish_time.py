"""发布时间段分析 — 纯函数模块。

从 published_at 提取小时/星期，按时段分桶，多平台聚合首发放时间。
供 auto_evolve Phase 2 调用，分析「发布时段/星期」对播放的影响（运营决策维度）。

设计：纯函数，仅依赖标准库，便于单测。parse_*_date（保时分）在 collect_performance，
本模块只做提取/分桶/聚合——职责分离。
"""
from __future__ import annotations

import re
from collections import defaultdict
from datetime import datetime
from statistics import mean

WEEKDAYS_ZH = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]

# 时段桶顺序（对齐短视频流量曲线），供分析层稳定遍历
BUCKET_ORDER = ["early_morning", "midday", "afternoon", "evening", "late_night"]

# published_at 中的小时：匹配 "YYYY-MM-DD HH" 或 "YYYY-MM-DDTHH"
_HOUR_RE = re.compile(r"(\d{4})-\d{2}-\d{2}[ T](\d{2})")

# published_at 中的日期
_DATE_RE = re.compile(r"(\d{4})-(\d{2})-(\d{2})")


def extract_hour(published_at: str | None) -> int | None:
    """从 published_at 提取小时；无时分返回 None。

    >>> extract_hour("2026-05-29 12:40")
    12
    >>> extract_hour("2026-05-29")
    """
    if not published_at:
        return None
    m = _HOUR_RE.search(str(published_at))
    return int(m.group(2)) if m else None


def hour_to_bucket(hour: int) -> str:
    """小时 → 时段桶（5 桶）。

    early_morning 6-10 | midday 11-14 | afternoon 15-18 | evening 19-23 | late_night 0-5
    """
    if 6 <= hour <= 10:
        return "early_morning"
    if 11 <= hour <= 14:
        return "midday"
    if 15 <= hour <= 18:
        return "afternoon"
    if 19 <= hour <= 23:
        return "evening"
    return "late_night"  # 0-5


def weekday_of(published_at: str | None) -> str:
    """从 published_at 推星期（中文）；解析失败返回 '未知'。"""
    if not published_at:
        return "未知"
    m = _DATE_RE.search(str(published_at))
    if not m:
        return "未知"
    try:
        d = datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        return WEEKDAYS_ZH[d.weekday()]
    except ValueError:
        return "未知"


def aggregate_publish_time(plats: dict) -> dict:
    """多平台聚合：取首发放时间（跨平台最早含时分的小时）。

    - publish_hour：所有含时分平台里最早的小时；全无时分则 None
    - publish_weekday：任一平台日期即可推（视频号只有日期也覆盖）

    plats = {"douyin": {"published_at": "..."}, ...}
    """
    hours: list[int] = []
    weekday = "未知"
    for pdata in plats.values():
        if not isinstance(pdata, dict):
            continue
        ts = pdata.get("published_at")
        if not ts:
            continue
        h = extract_hour(ts)
        if h is not None:
            hours.append(h)
        if weekday == "未知":
            weekday = weekday_of(ts)
    return {
        "publish_hour": min(hours) if hours else None,
        "publish_weekday": weekday,
    }


def analyze_publish_time(projects: list[dict]) -> dict:
    """发布时段 + 星期维度分析（reach_composite 受众广度信号）。

    projects: [{"publish_hour": int|None, "publish_weekday": str, "reach_composite": float}, ...]
    返回 hour_bucket/weekday 分组（N<3 桶省略避免幸存者偏差）+ best_hour_bucket + coverage。

    运营决策维度：关联非因果，只供发布时机参考，不生成内容 pattern/Delta。
    """
    hour_groups: dict[str, list[float]] = defaultdict(list)
    for p in projects:
        h = p.get("publish_hour")
        if h is None:
            continue
        hour_groups[hour_to_bucket(h)].append(p.get("reach_composite", 0.0))

    hour_analysis: dict = {}
    for bucket in BUCKET_ORDER:
        reachs = hour_groups.get(bucket, [])
        if len(reachs) >= 3:
            hour_analysis[bucket] = {"count": len(reachs), "avg_reach": round(mean(reachs), 3)}

    weekday_groups: dict[str, list[float]] = defaultdict(list)
    for p in projects:
        wd = p.get("publish_weekday")
        if not wd or wd == "未知":
            continue
        weekday_groups[wd].append(p.get("reach_composite", 0.0))

    weekday_analysis: dict = {}
    for wd, reachs in weekday_groups.items():
        if len(reachs) >= 3:
            weekday_analysis[wd] = {"count": len(reachs), "avg_reach": round(mean(reachs), 3)}

    best_hour = max(hour_analysis, key=lambda b: hour_analysis[b]["avg_reach"]) if hour_analysis else None
    n_with_hour = sum(len(v) for v in hour_groups.values())

    return {
        "hour_bucket": hour_analysis,
        "weekday": weekday_analysis,
        "best_hour_bucket": best_hour,
        "coverage_hour": f"{n_with_hour}/{len(projects)}",
        "note": "关联非因果；N<3 桶已省略" if hour_analysis else "样本不足（含时分的发布记录少）",
    }


def build_publish_advice(analysis: dict, market_avg: float) -> dict:
    """从分析结果生成发布时机建议（供 publish_timing_advice.json）。

    confidence：best 桶 avg_reach 高于大盘 + 样本充足才 high/medium，否则 low。
    运营决策——供 evolve-daily 汇报参考，不注入创作流程。
    """
    best = analysis.get("best_hour_bucket")
    hour_bucket = analysis.get("hour_bucket", {})
    if not best or best not in hour_bucket:
        return {
            "best_hour_bucket": None,
            "confidence": "low",
            "evidence": hour_bucket,
            "note": "样本不足，暂无发布时段建议",
        }
    best_reach = hour_bucket[best]["avg_reach"]
    n = hour_bucket[best]["count"]
    if best_reach > market_avg and n >= 5:
        confidence = "high"
    elif best_reach > market_avg and n >= 3:
        confidence = "medium"
    else:
        confidence = "low"
    return {
        "best_hour_bucket": best,
        "best_avg_reach": best_reach,
        "market_avg_reach": round(market_avg, 3),
        "confidence": confidence,
        "evidence": hour_bucket,
        "coverage_hour": analysis.get("coverage_hour"),
        "note": f"建议在 {best} 时段发布（关联非因果，基于 {analysis.get('coverage_hour')} 含时分记录）",
    }


# 桶中文（publish_note 显示用）
BUCKET_ZH = {
    "early_morning": "早间 6-10 点",
    "midday": "午间 11-14 点",
    "afternoon": "下午 15-18 点",
    "evening": "晚间 19-23 点（黄金时段）",
    "late_night": "深夜 0-5 点",
}


def render_publish_note(advice: dict | None) -> str:
    """从 advice 渲染 publish_note.md 内容（交付物发布时机提示）。

    纯函数：advice dict → markdown 字符串。confidence=low 或无 best → 样本不足提示。
    运营决策维度，关联非因果，不进创作 pattern。
    """
    if not advice or not advice.get("best_hour_bucket"):
        return (
            "# 发布时机建议\n\n"
            "⚠️ 当前发布时段数据样本不足，暂无统计建议。\n\n"
            "建议参考你历史发布效果最好的时段，或先在早间/晚间黄金时段发布。\n"
            "> 数据积累后 auto_evolve 会自动生成建议（publish_timing_advice.json）\n"
        )
    best = advice["best_hour_bucket"]
    confidence = advice.get("confidence", "low")
    best_zh = BUCKET_ZH.get(best, best)
    coverage = advice.get("coverage_hour", "?")
    best_reach = advice.get("best_avg_reach", 0)
    market = advice.get("market_avg_reach", 0)
    emoji = "⭐" if confidence == "high" else ("💡" if confidence == "medium" else "⚠️")
    return (
        f"# 发布时机建议\n\n"
        f"{emoji} 建议在 **{best_zh}** 发布（置信度：{confidence}）\n\n"
        f"- 该时段受众广度 {best_reach:.2f}，高于大盘均值 {market:.2f}\n"
        f"- 基于 {coverage} 条含时分的发布记录（视频号无时分，4/5 平台覆盖）\n\n"
        f"> ⚠️ 关联非因果：时段效果可能与内容质量/发布习惯混淆，结合自身作息参考。\n"
    )
