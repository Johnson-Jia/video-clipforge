"""成功分析引擎 — 高分案例采集、经验模式提炼、约束放宽提案。

架构哲学对齐：
- P4（成功进化）：Gate 验证后才 save_pattern，确保模式质量
- P5（偏好模型）：提炼的决策点存为 Preference（带 weight），而非泛泛描述
- 从 trace execution.steps 提取真实决策点，替代 generic "执行路径高效"
- 平台区分成功阈值：抖音看 5s 完播率、视频号看分享率、小红书看收藏率
- 从播放数据自动提取高分模式（auto_extract_from_performance）
"""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from engine.trace import query_traces, query_traces_with_performance, TRACES_DIR
from engine.lib.delta import create_delta, save_delta, DELTAS_DIR
from engine.lib.rule_parser import load_all_rules, RULES_DIR
from engine.lib.models import Severity, Platform, PerformanceRecord


PATTERNS_DIR = Path(__file__).parent.parent / "patterns"
DEFAULT_THRESHOLD = 0.85


def find_high_score_traces(traces_dir: Path | None = None, threshold: float = DEFAULT_THRESHOLD) -> list[dict]:
    all_traces = query_traces(traces_dir=traces_dir, last=500)
    high_score: list[dict] = []
    for t in all_traces:
        gate = t.get("result", {}).get("gate_report", {})
        if gate and gate.get("hard_passed") is True:
            score = gate.get("soft_score", 0.0)
            if score >= threshold:
                high_score.append(t)
    return high_score


def extract_decision_points(traces: list[dict]) -> list[dict]:
    """从 trace execution.steps 提取真实决策点。"""
    points: list[dict] = []
    for t in traces:
        steps = t.get("execution", {}).get("steps", [])
        for step in steps:
            decision = step.get("decision", "")
            chosen = step.get("chosen", "")
            reason = step.get("reason", "")
            if decision and chosen:
                points.append({
                    "skill_id": t.get("skill_id"),
                    "decision": decision,
                    "chosen": chosen,
                    "reason": reason,
                })
    return points


def gate_validate_pattern(
    pattern: dict,
    min_confidence: float = 0.60,
    rules_dir: Path | None = None,
) -> dict:
    """Gate 验证：模式必须满足最低质量门槛才能入库。

    P7 双闭环制衡：经验模式入库前，必须通过硬门禁校验——
    如果模式文本本身包含违禁内容，负向闭环有权否决。

    检查项：
    - evidence.sample_size >= 3
    - evidence.confidence >= min_confidence
    - as_preference.text 非空且有实质内容（非 generic 描述）
    - 模式文本不包含 HARD 规则的违禁关键词（P7 否决权）
    """
    evidence = pattern.get("evidence", {})
    issues: list[str] = []

    if evidence.get("sample_size", 0) < 3:
        issues.append("sample_size < 3")
    if evidence.get("confidence", 0) < min_confidence:
        issues.append(f"confidence {evidence.get('confidence', 0):.2f} < {min_confidence}")

    pref_text = pattern.get("as_preference", {}).get("text", "")
    generic_phrases = ["执行路径高效", "可直接复用", "表现良好"]
    if not pref_text or any(p in pref_text for p in generic_phrases):
        issues.append(f"偏好描述过于泛化: {pref_text[:50]}")

    # P7 负向闭环否决权：检查模式文本是否包含 HARD 规则的违禁关键词
    pref_text_lower = pref_text.lower()
    rules = load_all_rules(rules_dir or RULES_DIR)
    for r in rules:
        if r.severity != Severity.HARD:
            continue
        for kw in r.detection.keywords:
            if kw.lower() in pref_text_lower:
                issues.append(f"P7 否决: 偏好包含硬门禁关键词 '{kw}'（规则 {r.id}）")

    return {"valid": len(issues) == 0, "issues": issues}


def extract_patterns(high_score_traces: list[dict], min_samples: int = 3) -> list[dict]:
    if len(high_score_traces) < min_samples:
        return []

    skill_groups: dict[str, list[dict]] = {}
    for t in high_score_traces:
        sid = t.get("skill_id", "unknown")
        skill_groups.setdefault(sid, []).append(t)

    decision_points = extract_decision_points(high_score_traces)

    patterns: list[dict] = []
    for sid, traces in skill_groups.items():
        if len(traces) < min_samples:
            continue
        avg_score = sum(
            t.get("result", {}).get("gate_report", {}).get("soft_score", 0) for t in traces
        ) / len(traces)
        confidence = min(0.5 + len(traces) * 0.1, 0.95)

        # 从决策点构建偏好文本
        sid_decisions = [d for d in decision_points if d["skill_id"] == sid]
        if sid_decisions:
            top_decision = sid_decisions[0]
            pref_text = f"{sid}: {top_decision['decision']}时选择{top_decision['chosen']}" + (
                f"（{top_decision['reason']}）" if top_decision.get("reason") else ""
            )
        else:
            pref_text = f"Skill {sid} 连续 {len(traces)} 次高分通过，路径稳定可复用"

        # 从决策点数量推断 weight
        weight = "HIGH" if len(sid_decisions) >= 3 else "MEDIUM"

        pattern = {
            "id": f"P-{sid}",
            "skill_scope": sid,
            "description": f"Skill {sid} 连续 {len(traces)} 次高分通过，avg_score={avg_score:.3f}",
            "evidence": {
                "sample_size": len(traces),
                "avg_soft_score": round(avg_score, 3),
                "decision_points": len(sid_decisions),
                "confidence": round(confidence, 3),
            },
            "as_preference": {
                "text": pref_text,
                "weight": weight,
                "source_pattern": f"P-{sid}",
            },
        }
        patterns.append(pattern)
    return patterns


def save_pattern(pattern: dict, patterns_dir: Path | None = None) -> Path:
    patterns_dir = patterns_dir or PATTERNS_DIR
    patterns_dir.mkdir(parents=True, exist_ok=True)
    filepath = patterns_dir / f"{pattern['id']}.yaml"

    import yaml
    with open(filepath, "w", encoding="utf-8") as f:
        yaml.dump(pattern, f, allow_unicode=True, default_flow_style=False)
    return filepath


# ── 平台区分成功判定 ──────────────────────────────────────────────────────────

PLATFORM_THRESHOLDS = {
    Platform.DOUYIN.value: {
        "key_metric": "completion_5s_rate",
        "high_threshold": 0.44,
        "medium_threshold": 0.38,
    },
    Platform.WECHAT_VIDEO.value: {
        "key_metric": "share_rate",
        "high_threshold": 0.04,
        "medium_threshold": 0.02,
    },
    Platform.XIAOHONGSHU.value: {
        "key_metric": "save_to_like_ratio",
        "high_threshold": 1.5,
        "medium_threshold": 1.0,
    },
    Platform.BILIBILI.value: {
        "key_metric": "interaction_rate",
        "high_threshold": 0.05,
        "medium_threshold": 0.02,
    },
}


def _is_platform_success(performance: dict) -> bool:
    """按平台特定指标判断是否为成功案例。"""
    platform = performance.get("platform", "")
    thresholds = PLATFORM_THRESHOLDS.get(platform)
    if not thresholds:
        return performance.get("plays", 0) > 0

    metric = thresholds["key_metric"]
    if metric == "save_to_like_ratio":
        like_rate = performance.get("like_rate", 0)
        save_rate = performance.get("save_rate", 0)
        if like_rate > 0:
            value = save_rate / like_rate
        else:
            value = 0
    else:
        value = performance.get(metric, 0)

    return value >= thresholds["high_threshold"]


def _platform_success_score(performance: dict) -> float:
    """计算平台特定的成功分数（0-1）。"""
    platform = performance.get("platform", "")
    thresholds = PLATFORM_THRESHOLDS.get(platform)
    if not thresholds:
        plays = performance.get("plays", 0)
        return min(plays / 50000, 1.0)

    metric = thresholds["key_metric"]
    if metric == "save_to_like_ratio":
        like_rate = performance.get("like_rate", 0)
        save_rate = performance.get("save_rate", 0)
        value = save_rate / like_rate if like_rate > 0 else 0
    else:
        value = performance.get(metric, 0)

    high = thresholds["high_threshold"]
    medium = thresholds["medium_threshold"]
    if value >= high:
        return min(0.8 + (value - high) / high * 0.2, 1.0)
    elif value >= medium:
        return 0.5 + (value - medium) / (high - medium) * 0.3
    return max(0.0, value / medium * 0.5)


def find_high_performance_traces(
    traces_dir: Path | None = None,
    min_plays: int = 10000,
) -> list[dict]:
    """从带播放数据的 trace 中找出高播放量案例。"""
    perf_traces = query_traces_with_performance(traces_dir=traces_dir, last=500)
    high_perf: list[dict] = []
    for t in perf_traces:
        perf = t.get("performance", {})
        if not perf:
            continue
        if perf.get("plays", 0) >= min_plays or _is_platform_success(perf):
            high_perf.append(t)
    return high_perf


def auto_extract_from_performance(
    performance_data: list[dict],
    min_samples: int = 3,
) -> list[dict]:
    """从原始播放数据（非 trace 格式）自动提取高分模式。

    Args:
        performance_data: [{platform, plays, completion_5s_rate, title, hook_type, ...}]
        min_samples: 最小样本数

    Returns:
        提炼出的 pattern 列表
    """
    if len(performance_data) < min_samples:
        return []

    # 按 hook_type 分组
    hook_groups: dict[str, list[dict]] = {}
    for pd in performance_data:
        ht = pd.get("hook_type", "unknown")
        hook_groups.setdefault(ht, []).append(pd)

    patterns: list[dict] = []
    for ht, group in hook_groups.items():
        if len(group) < min_samples:
            continue

        avg_plays = sum(p.get("plays", 0) for p in group) / len(group)
        avg_5s = sum(p.get("completion_5s_rate", 0) for p in group) / len(group)
        avg_comp = sum(p.get("completion_rate", 0) for p in group) / len(group)

        # 只提炼高于基线的模式
        if avg_plays < 5000:
            continue

        confidence = min(0.5 + len(group) * 0.1, 0.95)
        weight = "HIGH" if avg_plays > 30000 else "MEDIUM" if avg_plays > 10000 else "LOW"

        # 构建偏好文本
        pref_text = f"hook 使用 {ht} 模式（{len(group)} 条数据，平均 {avg_plays:.0f} 播放，5s 完播率 {avg_5s:.1%}）"

        pattern = {
            "id": f"P-hook-{ht}",
            "skill_scope": "stage3-scenes",
            "description": f"Hook {ht} 模式：{len(group)} 条视频，avg_plays={avg_plays:.0f}",
            "evidence": {
                "sample_size": len(group),
                "avg_plays": round(avg_plays),
                "avg_completion_5s_rate": round(avg_5s, 3),
                "avg_completion_rate": round(avg_comp, 3),
                "confidence": round(confidence, 3),
                "platform": group[0].get("platform", "unknown"),
            },
            "as_preference": {
                "text": pref_text,
                "weight": weight,
                "source_pattern": f"P-hook-{ht}",
            },
        }
        # Gate 验证
        check = gate_validate_pattern(pattern)
        if check["valid"]:
            patterns.append(pattern)

    return patterns


def main():
    parser = argparse.ArgumentParser(description="ClipForge 成功分析引擎")
    parser.add_argument("--traces-dir", default=None)
    parser.add_argument("--min-score", type=float, default=DEFAULT_THRESHOLD)
    parser.add_argument("--min-samples", type=int, default=3)
    parser.add_argument("--save", action="store_true", help="保存提炼的模式")
    args = parser.parse_args()

    traces_dir = Path(args.traces_dir) if args.traces_dir else None
    high_score = find_high_score_traces(traces_dir, args.min_score)
    patterns = extract_patterns(high_score, args.min_samples)

    # Gate 验证过滤
    validated = []
    rejected = []
    for p in patterns:
        check = gate_validate_pattern(p)
        if check["valid"]:
            validated.append(p)
        else:
            rejected.append({"pattern_id": p["id"], "issues": check["issues"]})

    output = {
        "high_score_count": len(high_score),
        "patterns_found": len(patterns),
        "patterns_validated": len(validated),
        "patterns_rejected": len(rejected),
        "rejected_details": rejected,
        "patterns": validated,
    }

    if args.save and validated:
        for p in validated:
            path = save_pattern(p)
            output["saved"] = output.get("saved", [])
            output["saved"].append(str(path))

    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
