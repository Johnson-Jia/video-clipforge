"""注入生成器 — 生成约束 prompt 段（正向重述 + 经验模式 + Guard Red Flags）。"""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from engine.lib.rule_parser import load_skill, load_rules_by_scope, RULES_DIR, SKILLS_DIR
from engine.lib.models import Severity
from engine.lib.positive_rewrite import rewrite_rule
from engine.constraints import merge_rules


PATTERNS_DIR = Path(__file__).parent.parent / "patterns"


def load_patterns(category: str | None = None, patterns_dir: Path | None = None) -> list[str]:
    patterns_dir = patterns_dir or PATTERNS_DIR
    if not patterns_dir.exists():
        return []
    patterns: list[str] = []
    for fp in sorted(patterns_dir.glob("*.yaml")):
        import yaml
        with open(fp, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        if not data:
            continue
        if category and data.get("category") != category and data.get("category") is not None:
            continue
        if "as_preference" in data:
            patterns.append(data["as_preference"].get("text", ""))
        if "as_fewshot" in data:
            patterns.append(data["as_fewshot"].get("example_output", "")[:200])
    return [p for p in patterns if p]


def generate_injection(
    skill_name: str,
    category: str | None = None,
    rules_dir: Path | None = None,
    skills_dir: Path | None = None,
    patterns_dir: Path | None = None,
) -> str:
    rules_dir = rules_dir or RULES_DIR
    skills_dir = skills_dir or SKILLS_DIR

    skill = load_skill(skill_name, skills_dir)
    rules = load_rules_by_scope(skill_name if skill else None, category, rules_dir)

    if skill:
        skill_rules: list = []
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
    soft_rules = [r for r in rules if r.severity == Severity.SOFT]

    lines: list[str] = []

    if skill:
        lines.append(f"## 目标\n{skill.intent.objective}\n")
        if skill.intent.criteria:
            lines.append("## 成功标准")
            for c in skill.intent.criteria:
                lines.append(f"- {c}")
            lines.append("")

    lines.append("## 行为准则（必须遵守）")
    for r in hard_rules:
        rw = rewrite_rule(r)
        lines.append(f"- **[HARD]** {rw['positive']}")
    lines.append("")

    if soft_rules:
        lines.append("## 参考偏好（建议遵守）")
        for r in soft_rules:
            rw = rewrite_rule(r)
            lines.append(f"- [SOFT] {rw['positive']}")
        lines.append("")

    patterns = load_patterns(category, patterns_dir)
    if patterns:
        lines.append("## 成功经验（来自历史高分案例，供参考）")
        for p in patterns:
            lines.append(f"- {p}")
        lines.append("")

    if skill and skill.guard_red_flags:
        lines.append("## 行为守卫（当以下念头出现时，立即 STOP）")
        lines.append("| 当你产生这个念头 | 现实是 |")
        lines.append("|---|---|")
        for rf in skill.guard_red_flags:
            lines.append(f"| {rf.get('thought', '')} | {rf.get('reality', '')} |")
        lines.append("任何 Red Flag 触发 → 暂停当前行为，回到约束检查。")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="ClipForge 注入生成器")
    parser.add_argument("--skill", required=True)
    parser.add_argument("--category", default=None)
    parser.add_argument("--rules-dir", default=None)
    parser.add_argument("--skills-dir", default=None)
    parser.add_argument("--patterns-dir", default=None)
    parser.add_argument("--format", choices=["text", "json"], default="text")
    args = parser.parse_args()

    injection = generate_injection(
        args.skill, args.category,
        Path(args.rules_dir) if args.rules_dir else None,
        Path(args.skills_dir) if args.skills_dir else None,
        Path(args.patterns_dir) if args.patterns_dir else None,
    )
    if args.format == "json":
        print(json.dumps({"injection": injection}, ensure_ascii=False, indent=2))
    else:
        print(injection)


if __name__ == "__main__":
    main()
