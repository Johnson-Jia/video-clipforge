"""运行时可观测性 — 从已有 trace/delta/hit_counts 聚合指标并生成健康报告。

数据源全部已存在（无新存储）：
- traces/{project}/trace.json — 门禁结果、soft_score
- deltas/*.yaml — Delta 状态
- hit_counts.json — 规则命中计数
"""
from __future__ import annotations
import argparse
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from collections import Counter

sys.path.insert(0, str(Path(__file__).parent.parent))
from engine.trace import query_traces, TRACES_DIR
from engine.lib.delta import load_deltas, DELTAS_DIR
from engine.lib.rule_parser import load_all_rules, get_persistent_hit_counts, RULES_DIR
from engine.lib.models import GateType, RuleClass, Severity

# SAFETY 级 gate — 违反即安全事故
SAFETY_GATES = {
    "no_forbidden_speech",
    "no_url_in_output",
    "no_real_person_name",
    "no_school_name",
    "no_app_name",
    "no_competitor_attack",
    "no_search_cta",
}


def collect_metrics(
    traces_dir: Path | None = None,
    deltas_dir: Path | None = None,
    rules_dir: Path | None = None,
) -> dict:
    """从已有数据聚合运行指标。"""
    traces_dir = traces_dir or TRACES_DIR
    deltas_dir = deltas_dir or DELTAS_DIR
    rules_dir = rules_dir or RULES_DIR

    traces = query_traces(traces_dir=traces_dir, last=9999)
    total_traces = len(traces)

    # ── 门禁通过率 ──
    hard_passed_count = sum(
        1 for t in traces
        if (t.get("result") or {}).get("gate_report") and (t.get("result") or {}).get("gate_report").get("hard_passed") is True
    )
    gate_pass_rate = hard_passed_count / max(total_traces, 1)

    # ── 各 GateType 违规率 ──
    gate_violation_counts: Counter = Counter()
    for t in traces:
        gate = (t.get("result") or {}).get("gate_report") or {}
        for v in gate.get("hard_violations", []):
            rule_id = v.get("rule_id", "")
            if rule_id.startswith("gate:"):
                gate_name = rule_id[5:]
                gate_violation_counts[gate_name] += 1
    per_gate_violation_rate = {
        name: count / max(total_traces, 1)
        for name, count in gate_violation_counts.items()
    }

    # ── soft_score 分布 ──
    soft_scores = [
        ((t.get("result") or {}).get("gate_report") or {}).get("soft_score", 0.0)
        for t in traces
        if ((t.get("result") or {}).get("gate_report") or {}).get("soft_score") is not None
    ]
    avg_soft_score = sum(soft_scores) / max(len(soft_scores), 1)

    # ── Delta 流水线健康 ──
    deltas = load_deltas(deltas_dir)
    total_deltas = len(deltas)
    now = datetime.now(timezone.utc)

    delta_categories = {"pending": 0, "auto_activated": 0, "promoted": 0, "expired": 0}
    for d in deltas:
        inner = d.get("delta", d)
        op = inner.get("operation", "")
        confidence = inner.get("confidence", 0)
        needs_review = d.get("requires_human_review", inner.get("requires_human_review", True))

        if op == "EXPIRED":
            delta_categories["expired"] += 1
        elif needs_review:
            delta_categories["pending"] += 1
        elif confidence >= 0.85:
            delta_categories["promoted"] += 1
        elif confidence >= 0.70:
            # 检查 7 天观察期
            created = inner.get("created_at", "")
            age_ok = False
            if created:
                try:
                    created_dt = datetime.fromisoformat(created)
                    if (now - created_dt).days >= 7:
                        age_ok = True
                except (ValueError, TypeError):
                    pass
            if age_ok:
                delta_categories["auto_activated"] += 1
            else:
                delta_categories["pending"] += 1  # 还在观察期

    attribution_auto_rate = delta_categories["auto_activated"] / max(
        delta_categories["auto_activated"] + delta_categories["pending"], 1
    )

    # ── 规则有效性 ──
    rules = load_all_rules(rules_dir)
    hit_counts = get_persistent_hit_counts()
    zero_hit_rules: list[str] = []
    rule_hit_summary = {
        "total": len(rules),
        "hit": 0,
        "zero_hit": 0,
    }
    for r in rules:
        hc = hit_counts.get(r.id, 0)
        if hc == 0:
            zero_hit_rules.append(r.id)
        else:
            rule_hit_summary["hit"] += 1
    rule_hit_summary["zero_hit"] = len(zero_hit_rules)

    return {
        "gate_pass_rate": round(gate_pass_rate, 3),
        "hard_passed_count": hard_passed_count,
        "total_traces": total_traces,
        "per_gate_violation_rate": {k: round(v, 3) for k, v in sorted(per_gate_violation_rate.items())},
        "avg_soft_score": round(avg_soft_score, 3),
        "attribution_auto_rate": round(attribution_auto_rate, 3),
        "delta_pipeline": delta_categories,
        "total_deltas": total_deltas,
        "rule_hit_summary": rule_hit_summary,
        "zero_hit_rules": zero_hit_rules,
    }


def generate_health_report(
    traces_dir: Path | None = None,
    deltas_dir: Path | None = None,
    rules_dir: Path | None = None,
) -> dict:
    """聚合指标 + 告警评估。"""
    metrics = collect_metrics(traces_dir, deltas_dir, rules_dir)
    alerts: list[dict] = []

    # CRITICAL: SAFETY gate 违规率 > 10%
    for gate_name, rate in metrics["per_gate_violation_rate"].items():
        if gate_name in SAFETY_GATES and rate > 0.10:
            alerts.append({
                "level": "CRITICAL",
                "metric": f"safety_gate_violation:{gate_name}",
                "value": round(rate, 3),
                "threshold": 0.10,
                "message": f"SAFETY gate '{gate_name}' 违规率 {rate:.1%} > 10%",
            })

    # WARNING: 归因自动率 < 50%
    if metrics["attribution_auto_rate"] < 0.50 and metrics["total_deltas"] > 0:
        alerts.append({
            "level": "WARNING",
            "metric": "attribution_auto_rate",
            "value": metrics["attribution_auto_rate"],
            "threshold": 0.50,
            "message": f"归因自动率 {metrics['attribution_auto_rate']:.1%} < 50%，过多 Delta 需人工审核",
        })

    # WARNING: 待审核 Delta > 20
    pending = metrics["delta_pipeline"].get("pending", 0)
    if pending > 20:
        alerts.append({
            "level": "WARNING",
            "metric": "pending_deltas",
            "value": pending,
            "threshold": 20,
            "message": f"待审核 Delta {pending} 条 > 20，归因积压",
        })

    # INFO: 零命中规则
    for rule_id in metrics["zero_hit_rules"]:
        alerts.append({
            "level": "INFO",
            "metric": "zero_hit_rule",
            "value": 0,
            "threshold": 1,
            "message": f"规则 {rule_id} 零命中（候选废弃）",
        })

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "metrics": metrics,
        "alerts": alerts,
        "summary": {
            "gate_pass_rate": metrics["gate_pass_rate"],
            "attribution_auto_rate": metrics["attribution_auto_rate"],
            "total_traces": metrics["total_traces"],
            "total_deltas": metrics["total_deltas"],
        },
    }


def main():
    parser = argparse.ArgumentParser(description="ClipForge 可观测性引擎")
    parser.add_argument("command", choices=["report", "metrics"])
    parser.add_argument("--traces-dir", default=None)
    parser.add_argument("--deltas-dir", default=None)
    parser.add_argument("--rules-dir", default=None)
    args = parser.parse_args()

    traces_dir = Path(args.traces_dir) if args.traces_dir else None
    deltas_dir = Path(args.deltas_dir) if args.deltas_dir else None
    rules_dir = Path(args.rules_dir) if args.rules_dir else None

    if args.command == "metrics":
        result = collect_metrics(traces_dir, deltas_dir, rules_dir)
    else:
        result = generate_health_report(traces_dir, deltas_dir, rules_dir)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
