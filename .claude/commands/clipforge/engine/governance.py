"""规则库治理 — 冲突检测、冗余合并、膨胀检查 + Delta 产出。

架构哲学对齐：
- P3（事故复盘）：冲突/冗余发现产出 Delta，实现治理闭环
- P8（渐进严谨）：Delta 审批前 shadow_validate，确保变更安全
- P7（守卫共识）：治理结果通过 Delta 机制统一流转
"""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path
from collections import Counter

sys.path.insert(0, str(Path(__file__).parent.parent))
from engine.lib.rule_parser import load_all_rules, RULES_DIR
from engine.lib.models import Rule
from engine.lib.delta import create_delta, save_delta, shadow_validate, load_deltas
from engine.trace import query_traces


def detect_conflicts(rules: list[Rule]) -> list[dict]:
    by_id: dict[str, list[Rule]] = {}
    for r in rules:
        by_id.setdefault(r.id, []).append(r)

    conflicts: list[dict] = []
    for rid, rlist in by_id.items():
        if len(rlist) > 1:
            conflicts.append({
                "type": "duplicate_id",
                "rule_id": rid,
                "count": len(rlist),
                "files": [r.source for r in rlist],
            })

    keyword_map: dict[str, list[Rule]] = {}
    for r in rules:
        for kw in r.detection.keywords:
            keyword_map.setdefault(kw, []).append(r)
    for kw, rlist in keyword_map.items():
        if len(rlist) > 1:
            conflicts.append({
                "type": "keyword_overlap",
                "keyword": kw,
                "rules": [r.id for r in rlist],
            })

    return conflicts


def detect_redundancy(rules: list[Rule]) -> list[dict]:
    patterns: dict[str, list[Rule]] = {}
    for r in rules:
        key = r.pattern.lower().strip()
        patterns.setdefault(key, []).append(r)

    redundant: list[dict] = []
    for key, rlist in patterns.items():
        if len(rlist) > 1:
            redundant.append({
                "pattern": key,
                "rule_ids": [r.id for r in rlist],
                "suggestion": f"合并为单条规则，保留 {rlist[0].id}",
            })
    return redundant


def check_bloat(rules: list[Rule], max_per_scene: int = 100, max_total: int = 300) -> list[dict]:
    alerts: list[dict] = []
    scope_counts: dict[str, int] = Counter()
    for r in rules:
        key = r.scene or r.skill or r.scope.value
        scope_counts[key] = scope_counts.get(key, 0) + 1

    for scope_name, count in scope_counts.items():
        if count > max_per_scene:
            alerts.append({
                "type": "scope_bloat",
                "scope": scope_name,
                "count": count,
                "max": max_per_scene,
                "suggestion": "触发瘦身，考虑淘汰命中率 0 的 EXPERIENTIAL 规则",
            })

    if len(rules) > max_total:
        alerts.append({
            "type": "total_bloat",
            "count": len(rules),
            "max": max_total,
        })
    return alerts


def produce_deltas_for_findings(
    findings: dict,
    rules: list[Rule],
    traces: list[dict] | None = None,
    dry_run: bool = True,
) -> list[dict]:
    """治理发现产出 Delta，并通过 shadow_validate 检验安全性。"""
    deltas: list[dict] = []

    # 冗余规则 → DEPRECATED Delta
    for red in findings.get("redundancy", []):
        rule_ids = red.get("rule_ids", [])
        for i, rid in enumerate(rule_ids[1:], 1):
            delta = create_delta(
                operation="DEPRECATED",
                source="governance.redundancy",
                confidence=0.80,
                target_rule_id=rid,
                superseded_by=rule_ids[0],
                reason=f"冗余合并: pattern '{red['pattern'][:50]}' 与 {rule_ids[0]} 重复",
            )
            # shadow 验证
            shadow = shadow_validate(delta, rules, traces or [])
            delta["_shadow"] = shadow
            deltas.append(delta)

    # 膨胀警报中的零命中率规则 → DEPRECATED Delta
    # 注意：hit_count 仅存在于进程内存（不写回 YAML），每次运行归零。
    # 因此"零命中"= "本次运行中未被 inject"≠"历史上从未命中"。
    # 这是有意设计：YAML 是人类维护的规则定义，不应被程序自动修改。
    for alert in findings.get("bloat", []):
        if alert.get("type") == "scope_bloat":
            zero_hit = [r for r in rules
                        if (r.scene or r.skill or r.scope.value) == alert["scope"]
                        and r.hit_count == 0
                        and r.rule_class.value == "EXPERIENTIAL"]
            for r in zero_hit:
                delta = create_delta(
                    operation="DEPRECATED",
                    source="governance.bloat",
                    confidence=0.70,
                    target_rule_id=r.id,
                    reason=f"scope 膨胀瘦身: {alert['scope']} 超过 {alert['max']} 条，淘汰零命中 EXPERIENTIAL 规则",
                )
                shadow = shadow_validate(delta, rules, traces or [])
                delta["_shadow"] = shadow
                deltas.append(delta)

    if not dry_run:
        for d in deltas:
            save_delta(d)

    return deltas


def get_stats(rules: list[Rule]) -> dict:
    """规则统计。hit_count 仅反映本次进程内的 inject 记录，不跨进程持久化。"""
    return {
        "total": len(rules),
        "by_severity": dict(Counter(r.severity.value for r in rules)),
        "by_class": dict(Counter(r.rule_class.value for r in rules)),
        "by_scope": dict(Counter(r.scope.value for r in rules)),
        "zero_hit": [r.id for r in rules if r.hit_count == 0],
        "note": "hit_count 仅反映本次运行，不跨进程持久化",
    }


def main():
    parser = argparse.ArgumentParser(description="ClipForge 规则治理")
    parser.add_argument("command", choices=["check", "stats", "remediate"])
    parser.add_argument("--rules-dir", default=None)
    parser.add_argument("--dry-run", action="store_true", default=True, help="只产出 Delta 不保存")
    parser.add_argument("--apply", action="store_true", help="保存 Delta 文件")
    args = parser.parse_args()

    rules_dir = Path(args.rules_dir) if args.rules_dir else RULES_DIR
    rules = load_all_rules(rules_dir)

    if args.command == "check":
        conflicts = detect_conflicts(rules)
        redundancy = detect_redundancy(rules)
        bloat = check_bloat(rules)
        result = {"conflicts": len(conflicts), "redundant": len(redundancy), "bloat_alerts": len(bloat),
                  "details": {"conflicts": conflicts, "redundancy": redundancy, "bloat": bloat}}
        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif args.command == "remediate":
        conflicts = detect_conflicts(rules)
        redundancy = detect_redundancy(rules)
        bloat = check_bloat(rules)
        findings = {"conflicts": conflicts, "redundancy": redundancy, "bloat": bloat}

        traces = query_traces(last=50)
        deltas = produce_deltas_for_findings(
            findings, rules, traces,
            dry_run=not args.apply,
        )
        result = {
            "findings": {
                "conflicts": len(conflicts),
                "redundant": len(redundancy),
                "bloat_alerts": len(bloat),
            },
            "deltas_produced": len(deltas),
            "deltas_applied": len(deltas) if args.apply else 0,
            "deltas": deltas,
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif args.command == "stats":
        print(json.dumps(get_stats(rules), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
