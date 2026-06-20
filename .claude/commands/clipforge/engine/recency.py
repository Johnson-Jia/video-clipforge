"""数据时效加权 — auto_evolve 统计给近期数据更高权重。

校准偏向近期表现：近 7 天数据权重 1.0，逐步衰减（旧数据不归零，保留样本）。
让自进化反映最新趋势，而非被远古数据拖累。

设计：纯函数，仅依赖标准库，便于单测。
"""
from __future__ import annotations

import statistics
from datetime import date


def recency_weight(age_days: int) -> float:
    """数据年龄（天）→ 权重。近期高，旧衰减但不归零（保留样本）。"""
    if age_days <= 7:
        return 1.0
    if age_days <= 14:
        return 0.7
    if age_days <= 30:
        return 0.4
    return 0.1


def weighted_mean(values, weights) -> float:
    """加权平均；权重和为 0 时降级简单均值；空返回 0。"""
    if not values:
        return 0.0
    sw = sum(weights)
    if sw <= 0:
        return statistics.mean(values)
    return sum(v * w for v, w in zip(values, weights)) / sw


def project_data_weight(snapshots, today: str) -> float:
    """从 snapshots 算项目数据权重（最新 source_date 距 today 的天数 → 权重）。

    无 snapshots / 解析失败 → 1.0（不惩罚无历史数据的项目）。
    """
    if not snapshots:
        return 1.0
    dates = [s.get("source_date") for s in snapshots
             if isinstance(s, dict) and s.get("source_date")]
    if not dates:
        return 1.0
    latest = max(dates)
    try:
        d0 = date.fromisoformat(str(today)[:10])
        d1 = date.fromisoformat(str(latest)[:10])
        age = (d0 - d1).days
        return recency_weight(age)
    except Exception:
        return 1.0
