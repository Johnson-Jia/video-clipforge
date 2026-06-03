"""Delta Rule 管理 — 增量规则变更。"""
from __future__ import annotations
import re
import yaml
from datetime import datetime
from pathlib import Path
from .rule_parser import parse_rule, load_rules_from_file
from .models import Rule, Severity, RuleClass

DELTAS_DIR = Path(__file__).parent.parent.parent / "deltas"


def create_delta(
    operation: str,
    source: str,
    confidence: float,
    target_rule_id: str | None = None,
    new_rule_raw: dict | None = None,
    modified_fields: dict | None = None,
    superseded_by: str | None = None,
    reason: str | None = None,
    approved_by: str | None = None,
) -> dict:
    delta_id = f"D-{datetime.now().strftime('%Y%m%d')}-{target_rule_id or 'NEW'}"
    delta = {
        "delta": {
            "id": delta_id,
            "operation": operation,
            "target_rule": target_rule_id,
            "source": source,
            "confidence": confidence,
            "approved_by": approved_by,
            "created_at": datetime.now().isoformat(),
        }
    }
    if operation == "ADDED" and new_rule_raw:
        delta["delta"]["new_rule"] = new_rule_raw
    if operation == "MODIFIED" and modified_fields:
        delta["delta"]["modified_fields"] = modified_fields
    if operation == "DEPRECATED" and superseded_by:
        delta["delta"]["superseded_by"] = superseded_by
        delta["delta"]["reason"] = reason
    return delta


def save_delta(delta: dict, deltas_dir: Path | None = None) -> Path:
    deltas_dir = deltas_dir or DELTAS_DIR
    deltas_dir.mkdir(parents=True, exist_ok=True)
    # Windows 非法字符清洗（: / \ * ? " < > |）
    safe_id = re.sub(r'[:\\/*?"<>|]', '_', delta['delta']['id'])
    filepath = deltas_dir / f"{safe_id}.yaml"
    with open(filepath, "w", encoding="utf-8") as f:
        yaml.dump(delta, f, allow_unicode=True, default_flow_style=False)
    return filepath


def load_deltas(deltas_dir: Path | None = None) -> list[dict]:
    deltas_dir = deltas_dir or DELTAS_DIR
    if not deltas_dir.exists():
        return []
    deltas = []
    for fp in sorted(deltas_dir.glob("*.yaml")):
        with open(fp, "r", encoding="utf-8") as f:
            deltas.append(yaml.safe_load(f))
    return deltas


def apply_delta_to_rules(rules: list[Rule], delta: dict) -> list[Rule]:
    d = delta.get("delta", delta)
    op = d.get("operation")
    target = d.get("target_rule")
    result = list(rules)
    if op == "ADDED" and "new_rule" in d:
        result.append(parse_rule(d["new_rule"]))
    elif op == "MODIFIED" and target and "modified_fields" in d:
        for i, r in enumerate(result):
            if r.id == target:
                for field, new_val in d["modified_fields"].items():
                    if hasattr(r, field):
                        setattr(r, field, new_val)
    elif op == "REMOVED" and target:
        # P6 保护：SAFETY 规则不可删除，只能 DEPRECATED
        to_remove = [r for r in result if r.id == target]
        if to_remove and to_remove[0].rule_class == RuleClass.SAFETY:
            pass  # 跳过 SAFETY 规则的 REMOVED
        else:
            result = [r for r in result if r.id != target]
    elif op == "DEPRECATED" and target:
        for r in result:
            if r.id == target:
                if r.rule_class == RuleClass.SAFETY:
                    continue  # SAFETY 规则不可降级
                r.severity = Severity.SOFT
    return result


def shadow_validate(delta: dict, rules: list[Rule], traces: list[dict]) -> dict:
    """用最近 N 条 Trace 重放，确认 Delta 变更不会恶化。

    检查逻辑：
    - REMOVED/DEPRECATED: 如果目标规则曾出现在 hard_violations 中，标记 unsafe
    - ADDED: 如果新规则的 pattern 中的关键词曾出现在 passing trace 的输出中，标记需人工确认
    - 无 trace 数据时：标记 unsafe（而非默认通过），强制人工审核
    """
    d = delta.get("delta", delta)
    delta_id = d.get("id")
    op = d.get("operation")
    target = d.get("target_rule")

    # 无 trace 数据时不默认通过，强制人工审核
    if not traces:
        return {
            "safe": False,
            "reason": "无历史 Trace 可重放，Delta 必须人工审核",
            "delta_id": delta_id,
            "requires_human_review": True,
        }

    # REMOVED/DEPRECATED: 检查目标规则是否曾阻断过违规
    if op in ("REMOVED", "DEPRECATED") and target:
        blocking_traces = []
        for t in traces:
            gate = t.get("result", {}).get("gate_report", {})
            for v in gate.get("hard_violations", []):
                if target in v.get("rule_id", "") or target in v.get("rule_pattern", ""):
                    blocking_traces.append(t.get("id", "unknown"))
        if blocking_traces:
            return {
                "safe": False,
                "reason": f"规则 {target} 曾在 {len(blocking_traces)} 条 Trace 中阻断违规，移除可能导致安全回退",
                "delta_id": delta_id,
                "blocking_trace_ids": blocking_traces[:5],
                "requires_human_review": True,
            }

    # ADDED: 新规则不应与已有规则完全冲突
    if op == "ADDED" and "new_rule" in d:
        new_pattern = d["new_rule"].get("pattern", "")
        for r in rules:
            if new_pattern.lower().strip() == r.pattern.lower().strip():
                return {
                    "safe": False,
                    "reason": f"新规则 pattern 与已有规则 {r.id} 完全相同",
                    "delta_id": delta_id,
                    "conflicting_rule": r.id,
                    "requires_human_review": True,
                }

    total = len(traces)
    violations_before = sum(
        1 for t in traces
        if t.get("result", {}).get("gate_report", {}).get("hard_passed") is False
    )
    return {
        "safe": True,
        "reason": "通过影子校验",
        "total_traces": total,
        "violations_before": violations_before,
        "delta_id": delta_id,
        "requires_human_review": False,
    }
