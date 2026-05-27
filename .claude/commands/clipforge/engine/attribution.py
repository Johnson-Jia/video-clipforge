"""归因引擎 — 强归因（规则命中分析）+ 弱归因（根因判定 + Delta 产出）。

架构哲学对齐：
- P3（事故复盘）：弱归因产出 Delta，实现「失败 → 归因 → 收紧规则」闭环
- P8（渐进严谨）：证据驱动置信度，而非硬编码常量
- Delta Rule API 完整调用：归因不再只返回 dict，而是直接产出增量规则变更
"""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from engine.lib.rule_parser import load_all_rules, RULES_DIR
from engine.lib.models import Rule, Severity, RuleClass
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
