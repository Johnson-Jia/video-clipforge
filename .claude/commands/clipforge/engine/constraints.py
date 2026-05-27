"""约束引擎 — 规则加载、作用域合并、约束集产出。"""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from engine.lib.rule_parser import load_rules_by_scope, load_skill, RULES_DIR, SKILLS_DIR
from engine.lib.models import Rule, Severity, RuleClass, ConstraintSet
from engine.lib.positive_rewrite import rewrite_rule


def merge_rules(rules: list[Rule]) -> list[Rule]:
    """按 ID 去重，SAFETY 规则不可覆盖，EXPERIENTIAL 后声明的优先。"""
    seen: dict[str, Rule] = {}
    for r in rules:
        if r.id in seen:
            existing = seen[r.id]
            if existing.rule_class == RuleClass.SAFETY:
                continue
        seen[r.id] = r
    return list(seen.values())


def prepare_constraints(
    skill_name: str,
    category: str | None = None,
    rules_dir: Path | None = None,
    skills_dir: Path | None = None,
) -> ConstraintSet:
    rules_dir = rules_dir or RULES_DIR
    skills_dir = skills_dir or SKILLS_DIR

    skill = load_skill(skill_name, skills_dir)

    target_skill_id = skill_name if skill else None
    rules = load_rules_by_scope(target_skill_id, category, rules_dir)

    if skill:
        skill_rules: list[Rule] = []
        for ref in skill.boundary.rule_refs:
            if isinstance(ref, str) and ref.endswith("*"):
                prefix = ref.rstrip("*")
                skill_rules.extend([r for r in rules if r.id.startswith(prefix)])
            elif isinstance(ref, str):
                skill_rules.extend([r for r in rules if r.id == ref])
            elif isinstance(ref, dict) and "ref" in ref:
                rref = ref["ref"]
                if rref.endswith("*"):
                    prefix = rref.rstrip("*")
                    skill_rules.extend([r for r in rules if r.id.startswith(prefix)])
                else:
                    skill_rules.extend([r for r in rules if r.id == rref])
        rules = merge_rules(skill_rules)

    hard_rules = [r for r in rules if r.severity == Severity.HARD]
    positive_prompts = [rewrite_rule(r)["positive"] for r in hard_rules]
    scope_summary = f"skill={skill_name}, category={category or 'none'}, rules={len(rules)}"

    return ConstraintSet(
        positive_prompts=positive_prompts,
        guardrails=rules,
        scope_summary=scope_summary,
    )


def main():
    parser = argparse.ArgumentParser(description="ClipForge 约束引擎")
    parser.add_argument("--skill", required=True, help="Skill 名称（如 stage4-audio）")
    parser.add_argument("--category", default=None, help="分类（如 github）")
    parser.add_argument("--rules-dir", default=None, help="规则目录")
    parser.add_argument("--skills-dir", default=None, help="Skill 声明目录")
    parser.add_argument("--format", choices=["text", "json"], default="text")
    args = parser.parse_args()

    rules_dir = Path(args.rules_dir) if args.rules_dir else None
    skills_dir = Path(args.skills_dir) if args.skills_dir else None

    cs = prepare_constraints(args.skill, args.category, rules_dir, skills_dir)
    if args.format == "json":
        data = {
            "positive_prompts": cs.positive_prompts,
            "guardrails": [{"id": r.id, "pattern": r.pattern, "severity": r.severity.value} for r in cs.guardrails],
            "scope_summary": cs.scope_summary,
        }
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        print(f"# 约束集: {cs.scope_summary}")
        print(f"# 规则数: {len(cs.guardrails)}")
        for p in cs.positive_prompts:
            print(f"- {p}")


if __name__ == "__main__":
    main()
