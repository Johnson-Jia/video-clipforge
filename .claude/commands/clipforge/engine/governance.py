"""规则库治理 — 冲突检测、冗余合并、膨胀检查。"""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path
from collections import Counter

sys.path.insert(0, str(Path(__file__).parent.parent))
from engine.lib.rule_parser import load_all_rules, RULES_DIR
from engine.lib.models import Rule, Scope


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


def get_stats(rules: list[Rule]) -> dict:
    return {
        "total": len(rules),
        "by_severity": dict(Counter(r.severity.value for r in rules)),
        "by_class": dict(Counter(r.rule_class.value for r in rules)),
        "by_scope": dict(Counter(r.scope.value for r in rules)),
        "zero_hit": [r.id for r in rules if r.hit_count == 0],
    }


def main():
    parser = argparse.ArgumentParser(description="ClipForge 规则治理")
    parser.add_argument("command", choices=["check", "stats"])
    parser.add_argument("--rules-dir", default=None)
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
    elif args.command == "stats":
        print(json.dumps(get_stats(rules), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
