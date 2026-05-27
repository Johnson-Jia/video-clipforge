"""归因引擎 — 强归因（规则命中分析）+ 弱归因（根因判定）。"""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from engine.lib.rule_parser import load_all_rules, RULES_DIR
from engine.lib.models import Rule, Severity, RuleClass


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


def weak_attribution(violation: dict, trace: dict | None = None) -> dict:
    """弱归因：根因判定。因果推断，需置信度和人工兜底。"""
    violation_pattern = violation.get("details", violation.get("rule_pattern", ""))

    if "绕过" in violation_pattern or "跳过" in violation_pattern:
        root = "behavior_violation"
        confidence = 0.75
    elif "无法" in violation_pattern or "不支持" in violation_pattern:
        root = "capability_gap"
        confidence = 0.65
    else:
        root = "rule_missing"
        confidence = 0.70

    action = None
    candidate = None
    if root == "rule_missing":
        action = "NEW_RULE"
        candidate = {
            "id": f"R-AUTO-{violation.get('rule_id', 'UNK')}",
            "type": "FORBIDDEN_ACTION",
            "pattern": violation_pattern[:100],
            "severity": "SOFT",
            "class": "EXPERIENTIAL",
            "scope": "SKILL",
        }
    elif root == "behavior_violation":
        action = "STRENGTHEN_INJECTION"

    return {
        "layer": "WEAK",
        "root_cause": root,
        "confidence": confidence,
        "evidence": [violation_pattern],
        "action": action,
        "candidate_rule": candidate,
        "requires_human_review": confidence < 0.7,
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
    args = parser.parse_args()

    result = analyze_trace(Path(args.trace_file), Path(args.rules_dir) if args.rules_dir else None)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
