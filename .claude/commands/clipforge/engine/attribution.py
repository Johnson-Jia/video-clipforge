"""归因引擎 — 强归因（规则命中分析）+ 弱归因（根因判定 + Delta 产出）+ 播放数据归因。

架构哲学对齐：
- P3（事故复盘）：弱归因产出 Delta，实现「失败 → 归因 → 收紧规则」闭环
- P8（渐进严谨）：证据驱动置信度，而非硬编码常量
- Delta Rule API 完整调用：归因不再只返回 dict，而是直接产出增量规则变更
- 数据驱动归因：从播放数据（播放量、5s 完播率、分享率）反推失败根因
"""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from engine.lib.rule_parser import load_all_rules, RULES_DIR
from engine.lib.models import Rule, Severity, RuleClass, Platform, PerformanceRecord
from engine.lib.delta import create_delta, save_delta


def _evidence_confidence(violation: dict, trace: dict | None = None) -> float:
    """证据驱动置信度：基于语义级信号动态计算。

    信号来源（按权重递减）：
    1. trace 中是否存在规则触碰记录（constraint_hits）→ 直接证据
    2. violation 是否匹配已有规则的 detection.keywords → 模式匹配证据
    3. trace gate_report 中 hard_violations 的数量 → 上下文证据
    4. violation 详情中是否包含具体关键词（绕过/跳过/无法）→ 行为证据
    """
    signals = 0.25  # 基础置信度（低起点，证据积累才提升）

    # 信号 1：trace 中有规则触碰记录（最高权重）
    if trace:
        exec_data = trace.get("execution", {})
        steps = exec_data.get("steps", [])
        for step in steps:
            hits = step.get("constraint_hits", [])
            if hits:
                signals += 0.25
                break

        # 信号 3：gate_report 中 hard_violations 数量提供上下文
        gate = trace.get("result", {}).get("gate_report", {})
        violations = gate.get("hard_violations", [])
        if len(violations) >= 1:
            signals += 0.10
        if len(violations) >= 2:
            signals += 0.05

        # path_switches 说明 Agent 曾尝试规避
        switches = exec_data.get("path_switches", [])
        if switches:
            signals += 0.10

    # 信号 2：violation 详情匹配具体行为关键词
    details = violation.get("details", violation.get("rule_pattern", ""))
    behavior_keywords = ["绕过", "跳过", "忽略", "遗漏", "缺失", "失败", "异常"]
    matched_behaviors = sum(1 for kw in behavior_keywords if kw in details)
    if matched_behaviors >= 1:
        signals += 0.10
    if matched_behaviors >= 2:
        signals += 0.05

    return min(signals, 0.95)


def strong_attribution(violation: dict, rules: list[Rule]) -> dict:
    """强归因：检查已有规则是否覆盖此违规。确定性推理，可全自动执行。"""
    violation_pattern = violation.get("details", violation.get("rule_pattern", ""))

    for rule in rules:
        if violation.get("rule_id", "").endswith(rule.id):
            return {
                "layer": "STRONG",
                "root_cause": "rule_hit",
                "matched_rule": rule.id,
                "action": "OPTIMIZE_DETECTION",
                "requires_human_review": False,
                "confidence": 1.0,
            }

        from engine.lib.positive_rewrite import rewrite_rule
        guardrail = rewrite_rule(rule)["guardrail"]
        if guardrail and any(kw in violation_pattern for kw in rule.detection.keywords):
            return {
                "layer": "STRONG",
                "root_cause": "rule_hit",
                "matched_rule": rule.id,
                "action": "STRENGTHEN_RULE",
                "requires_human_review": False,
                "confidence": 1.0,
            }

    return {
        "layer": "STRONG",
        "root_cause": "no_rule_match",
        "matched_rule": None,
        "action": "PASS_TO_WEAK",
        "requires_human_review": False,
    }


def weak_attribution(
    violation: dict,
    trace: dict | None = None,
    produce_delta: bool = True,
) -> dict:
    """弱归因：根因判定 + Delta 产出。

    证据驱动置信度 + rule_missing 时自动调用 create_delta。
    """
    violation_pattern = violation.get("details", violation.get("rule_pattern", ""))
    confidence = _evidence_confidence(violation, trace)

    if "绕过" in violation_pattern or "跳过" in violation_pattern:
        root = "behavior_violation"
    elif "无法" in violation_pattern or "不支持" in violation_pattern:
        root = "capability_gap"
    else:
        root = "rule_missing"

    action = None
    candidate = None
    delta_path = None

    if root == "rule_missing":
        action = "NEW_RULE"
        candidate = {
            "id": f"R-AUTO-{violation.get('rule_id', 'UNK')}",
            "type": "FORBIDDEN_ACTION",
            "pattern": violation_pattern[:200],
            "positive": f"确保{violation_pattern[:80]}的正确处理",
            "severity": "SOFT",
            "class": "EXPERIENTIAL",
            "scope": "SKILL",
        }
        if produce_delta:
            delta = create_delta(
                operation="ADDED",
                source="weak_attribution",
                confidence=confidence,
                target_rule_id=candidate["id"],
                new_rule_raw=candidate,
                reason=f"归因发现规则缺失: {violation_pattern[:100]}",
            )
            delta_path = save_delta(delta)

    elif root == "behavior_violation":
        action = "STRENGTHEN_INJECTION"

    return {
        "layer": "WEAK",
        "root_cause": root,
        "confidence": round(confidence, 3),
        "evidence": [t for t in [violation_pattern] if t],
        "action": action,
        "candidate_rule": candidate,
        "delta_path": str(delta_path) if delta_path else None,
        "requires_human_review": confidence < 0.55,
    }


def analyze_trace(trace_file: Path, rules_dir: Path | None = None) -> dict:
    rules_dir = rules_dir or RULES_DIR
    rules = load_all_rules(rules_dir)

    with open(trace_file, "r", encoding="utf-8") as f:
        content = f.read()
    try:
        traces = json.loads(content)
        if not isinstance(traces, list):
            traces = [traces]
    except json.JSONDecodeError:
        return {"error": f"无法解析 trace 文件: {trace_file}"}

    results: list[dict] = []
    for trace in traces:
        gate = trace.get("result", {}).get("gate_report", {})
        if gate and not gate.get("hard_passed", True):
            for v in gate.get("hard_violations", []):
                strong = strong_attribution(v, rules)
                if strong["root_cause"] == "no_rule_match":
                    weak = weak_attribution(v, trace)
                    results.append({"trace_id": trace.get("id"), "attribution": weak})
                else:
                    results.append({"trace_id": trace.get("id"), "attribution": strong})

    return {"total_traces": len(traces), "attributions": results}


# ── 播放数据归因 ──────────────────────────────────────────────────────────────
# 数据来源：2026-05-27 三平台分析
# - 抖音：5s 完播率 ≥44% → 36K 播放，<38% → 3.1K
# - 视频号：分享率 4-5% → 高增长
# - 小红书：收藏 > 1.5x 点赞 → 高价值

_DOUYIN_THRESHOLDS = {
    "5s_completion_low": 0.38,
    "5s_completion_high": 0.44,
    "completion_rate_sweet_low": 0.03,
    "completion_rate_sweet_high": 0.05,
    "plays_low": 3000,
    "plays_high": 10000,
}

_WECHAT_THRESHOLDS = {
    "share_rate_low": 0.02,
    "share_rate_high": 0.04,
}

_XHS_THRESHOLDS = {
    "save_to_like_ratio_high": 1.5,
}


def _classify_hook_type(hook_text: str) -> str:
    """分类 hook 文本模式。"""
    if not hook_text:
        return "empty"
    for kw in ("你知道吗", "有没有想过", "猜猜", "你知道"):
        if kw in hook_text[:10]:
            return "question_interactive"
    for kw in ("不用", "却能", "居然", "竟然", "不需要"):
        if kw in hook_text:
            return "contrarian_conflict"
    for kw in ("涨星最快", "N 个项目", "天涨近", "千星", "万星", "单日涨", "最高涨星"):
        if kw in hook_text:
            return "number_anchor"
    if any(hook_text.startswith(w) for w in ("这个", "今天", "注意")):
        return "signal_attention"
    return "direct_narrative"


def performance_attribution(
    performance: dict,
    narration_file: Path | None = None,
    produce_delta: bool = True,
) -> dict:
    """从播放数据反推失败根因。

    Args:
        performance: 播放数据 {platform, plays, completion_rate, completion_5s_rate, ...}
        narration_file: narration_segments.json 路径（可选，用于 hook 文本分析）
        produce_delta: 是否产出 Delta 规则建议

    Returns:
        归因结果，包含 root_cause、evidence、delta_path 等
    """
    platform = performance.get("platform", "")
    causes: list[dict] = []
    evidence: list[str] = []
    delta_path = None

    # ── 抖音归因 ──
    if platform == Platform.DOUYIN.value or platform == "douyin":
        plays = performance.get("plays", 0)
        c5s = performance.get("completion_5s_rate", 0)
        comp = performance.get("completion_rate", 0)

        # 信号 1：5s 完播率低
        if c5s > 0 and c5s < _DOUYIN_THRESHOLDS["5s_completion_low"]:
            causes.append({"cause": "low_5s_completion", "severity": "HIGH",
                           "detail": f"5s 完播率 {c5s:.1%} < {_DOUYIN_THRESHOLDS['5s_completion_low']:.0%}，平均仅 3,102 播放"})
            evidence.append(f"5s 完播率 {c5s:.1%}（阈值 ≥44% 对应 36K 播放）")

        # 信号 2：完播率不在甜蜜区
        if comp > 0 and (comp < _DOUYIN_THRESHOLDS["completion_rate_sweet_low"] or
                         comp > _DOUYIN_THRESHOLDS["completion_rate_sweet_high"] * 2):
            causes.append({"cause": "completion_out_of_sweet_spot", "severity": "MEDIUM",
                           "detail": f"完播率 {comp:.1%}，甜蜜区 3-5%（平均 29,871 播放）"})
            evidence.append(f"完播率 {comp:.1%}（甜蜜区 3-5%）")

        # 信号 3：播放量低
        if 0 < plays < _DOUYIN_THRESHOLDS["plays_low"]:
            causes.append({"cause": "low_plays", "severity": "HIGH",
                           "detail": f"播放量 {plays} < {_DOUYIN_THRESHOLDS['plays_low']}（基线）"})
            evidence.append(f"播放量 {plays}")

    # ── 视频号归因 ──
    elif platform in (Platform.WECHAT_VIDEO.value, "wechat_video"):
        share_rate = performance.get("share_rate", 0)
        if share_rate > 0 and share_rate < _WECHAT_THRESHOLDS["share_rate_low"]:
            causes.append({"cause": "low_share_rate", "severity": "HIGH",
                           "detail": f"分享率 {share_rate:.1%} < {_WECHAT_THRESHOLDS['share_rate_low']:.0%}，视频号增长靠分享驱动"})
            evidence.append(f"分享率 {share_rate:.1%}（阈值 ≥4%）")

    # ── 小红书归因 ──
    elif platform in (Platform.XIAOHONGSHU.value, "xiaohongshu"):
        save_rate = performance.get("save_rate", 0)
        like_rate = performance.get("like_rate", 0)
        if like_rate > 0 and save_rate / like_rate < _XHS_THRESHOLDS["save_to_like_ratio_high"]:
            causes.append({"cause": "low_save_to_like", "severity": "MEDIUM",
                           "detail": f"收藏/点赞比 {save_rate/like_rate:.1f} < {_XHS_THRESHOLDS['save_to_like_ratio_high']}，小红书收藏驱动"})
            evidence.append(f"收藏/点赞比 {save_rate/like_rate:.1f}")

    # ── Hook 文本分析（如果提供了 narration 文件）──
    hook_type = ""
    if narration_file and narration_file.exists():
        try:
            data = json.loads(narration_file.read_text(encoding="utf-8"))
            segments = data.get("segments", [])
            if segments:
                hook_text = segments[0].get("narration_segment", "")
                hook_type = _classify_hook_type(hook_text)
                if hook_type == "question_interactive":
                    causes.append({"cause": "weak_hook_pattern", "severity": "HIGH",
                                   "detail": f"hook 使用疑问/互动模式（平均 1,195 播放，最低）"})
                    evidence.append(f"hook 模式: {hook_type}, 文本: '{hook_text[:30]}'")
                elif hook_type == "direct_narrative":
                    causes.append({"cause": "generic_hook", "severity": "MEDIUM",
                                   "detail": f"hook 使用直接叙述模式（平均 5,363 播放，基线）"})
                    evidence.append(f"hook 模式: {hook_type}")
        except (json.JSONDecodeError, UnicodeDecodeError):
            pass

    # ── 综合判定 ──
    if not causes:
        return {
            "layer": "PERFORMANCE",
            "root_cause": "no_performance_issue",
            "confidence": 0.0,
            "evidence": [],
            "action": None,
            "causes": [],
            "requires_human_review": False,
        }

    primary = causes[0]
    confidence = min(0.4 + len(causes) * 0.15, 0.90)

    # 产出 Delta（针对可修复的根因）
    action = None
    candidate = None
    if primary["cause"] in ("weak_hook_pattern", "low_5s_completion") and produce_delta:
        action = "STRENGTHEN_RULE"
        candidate = {
            "id": f"R-PERF-{platform}-{primary['cause'][:20]}",
            "type": "FORBIDDEN_ACTION",
            "pattern": primary["detail"],
            "positive": "使用反直觉/冲突模式或数字锚定模式作为 hook（数据来源：抖音 58 条分析）",
            "severity": "HARD",
            "class": "EXPERIENTIAL",
            "scope": "SKILL",
        }
        delta = create_delta(
            operation="ADDED",
            source="performance_attribution",
            confidence=confidence,
            target_rule_id=candidate["id"],
            new_rule_raw=candidate,
            reason=f"播放数据归因: {primary['detail'][:80]}",
        )
        delta_path = save_delta(delta)

    return {
        "layer": "PERFORMANCE",
        "root_cause": primary["cause"],
        "confidence": round(confidence, 3),
        "evidence": evidence,
        "action": action,
        "causes": causes,
        "hook_type": hook_type,
        "candidate_rule": candidate,
        "delta_path": str(delta_path) if delta_path else None,
        "requires_human_review": confidence < 0.55,
    }


def main():
    parser = argparse.ArgumentParser(description="ClipForge 归因引擎")
    parser.add_argument("--trace-file", required=True)
    parser.add_argument("--rules-dir", default=None)
    parser.add_argument("--no-delta", action="store_true", help="不产出 Delta 文件")
    args = parser.parse_args()

    result = analyze_trace(
        Path(args.trace_file),
        Path(args.rules_dir) if args.rules_dir else None,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
