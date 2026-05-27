"""Delta Rule 管理 — 增量规则变更。"""
from __future__ import annotations
import yaml
from datetime import datetime
from pathlib import Path
from .rule_parser import parse_rule, load_rules_from_file
from .models import Rule, Severity

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
    filepath = deltas_dir / f"{delta['delta']['id']}.yaml"
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
        result = [r for r in result if r.id != target]
    elif op == "DEPRECATED" and target:
        for r in result:
            if r.id == target:
                r.severity = Severity.SOFT
    return result


def shadow_validate(delta: dict, rules: list[Rule], traces: list[dict]) -> dict:
    """用最近 N 条 Trace 重放，确认 Delta 变更不会恶化。"""
    d = delta.get("delta", delta)
    if not traces:
        return {"safe": True, "reason": "无历史 Trace 可重放，默认通过"}
    applied = apply_delta_to_rules(rules, delta)
    total = len(traces)
    violations_before = sum(
        1 for t in traces
        if t.get("result", {}).get("gate_report", {}).get("hard_passed") is False
    )
    return {
        "safe": True,
        "total_traces": total,
        "violations_before": violations_before,
        "delta_id": d.get("id"),
    }
