"""Skill/Rule 双轨 lint — 验证 skills/*.yaml, rules/*.yaml, stages/*.md 之间的一致性。

检查维度：
- lint_rules: 规则 ID 唯一性、枚举值合法性、scope 标准化
- lint_skills: GateType 合法性、rule refs 解析、intent 完整性
- lint_consistency: skill↔stage 跨文件匹配
"""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from engine.lib.rule_parser import load_all_rules, load_all_skills, RULES_DIR, SKILLS_DIR
from engine.lib.models import RuleType, Scope, GateType, RuleClass, Severity


STAGES_DIR = SKILLS_DIR.parent / "stages"

# 共享技能不需要对应 stage.md
SKILL_NO_STAGE_WHITELIST = {"movie-clips", "cleanup-rules"}
# 纯参考文档不需要对应 skill.yaml
STAGE_NO_SKILL_WHITELIST = {"stage6-components"}


def lint_rules(rules_dir: Path | None = None) -> dict:
    """校验规则文件：ID 唯一性、枚举值合法性、scope 标准化。"""
    rules_dir = rules_dir or RULES_DIR
    rules = load_all_rules(rules_dir)
    errors: list[str] = []
    warnings: list[str] = []
    passed = 0

    # ID 唯一性
    id_counts: dict[str, int] = {}
    for r in rules:
        id_counts[r.id] = id_counts.get(r.id, 0) + 1
    for rid, count in id_counts.items():
        if count > 1:
            errors.append(f"规则 ID 重复: {rid}（出现 {count} 次）")

    # 枚举值合法性
    for r in rules:
        issues: list[str] = []

        if r.type not in RuleType.__members__.values():
            issues.append(f"type={r.type.value} 不是合法 RuleType")

        if r.rule_class not in RuleClass.__members__.values():
            issues.append(f"class={r.rule_class.value} 不是合法 RuleClass")

        if r.severity not in Severity.__members__.values():
            issues.append(f"severity={r.severity.value} 不是合法 Severity")

        # scope 标准化检查
        if r.scope not in Scope.__members__.values():
            if r.skill:
                warnings.append(f"{r.id}: scope='{r.scope.value}' 非标准（已通过 skill 字段解析为 SKILL）")
            else:
                errors.append(f"{r.id}: scope='{r.scope.value}' 非标准且无 skill 字段")

        if issues:
            errors.extend([f"{r.id}: {i}" for i in issues])
        else:
            passed += 1

    return {"errors": errors, "warnings": warnings, "passed": passed}


def lint_skills(skills_dir: Path | None = None, rules_dir: Path | None = None) -> dict:
    """校验 Skill 定义：GateType 合法性、rule refs 解析、intent 完整性。"""
    skills_dir = skills_dir or SKILLS_DIR
    rules_dir = rules_dir or RULES_DIR
    skills = load_all_skills(skills_dir)
    rules = load_all_rules(rules_dir)
    errors: list[str] = []
    warnings: list[str] = []
    passed = 0

    valid_gate_types = {gt.value for gt in GateType}

    for name, skill in skills.items():
        issues: list[str] = []

        # intent.objective 非空
        if not skill.intent.objective:
            issues.append("intent.objective 为空")

        # gate.hard GateType 合法性
        for gd in skill.gate.hard:
            if gd.gate.value not in valid_gate_types:
                issues.append(f"gate.hard 包含无效 GateType: {gd.gate.value}")

        # gate.soft GateType 合法性
        for gd in skill.gate.soft:
            if gd.gate.value not in valid_gate_types:
                issues.append(f"gate.soft 包含无效 GateType: {gd.gate.value}")

        # boundary.rules 引用解析
        for ref in skill.boundary.rule_refs:
            if isinstance(ref, str):
                rref = ref
            elif isinstance(ref, dict) and "ref" in ref:
                rref = ref["ref"]
            else:
                continue

            if rref.endswith("*"):
                prefix = rref.rstrip("*")
                matched = [r for r in rules if r.id.startswith(prefix)]
                if not matched:
                    issues.append(f"rule ref '{rref}' 未匹配任何规则")
            else:
                matched = [r for r in rules if r.id == rref]
                if not matched:
                    issues.append(f"rule ref '{rref}' 未匹配任何规则")

        if issues:
            errors.extend([f"{name}: {i}" for i in issues])
        else:
            passed += 1

    return {"errors": errors, "warnings": warnings, "passed": passed}


def lint_consistency(
    skills_dir: Path | None = None,
    stages_dir: Path | None = None,
) -> dict:
    """校验 skill↔stage 跨文件一致性。"""
    skills_dir = skills_dir or SKILLS_DIR
    stages_dir = stages_dir or STAGES_DIR
    errors: list[str] = []
    warnings: list[str] = []
    passed = 0

    # 收集文件名（不含扩展名）
    skill_stems = set()
    for fp in skills_dir.glob("*.yaml"):
        skill_stems.add(fp.stem)

    stage_stems = set()
    if stages_dir.exists():
        for fp in stages_dir.glob("*.md"):
            stage_stems.add(fp.stem)

    # skill.yaml 无对应 stage.md → error（排除白名单）
    for stem in sorted(skill_stems):
        if stem in SKILL_NO_STAGE_WHITELIST:
            continue
        if stem not in stage_stems:
            errors.append(f"skill '{stem}.yaml' 无对应 stage '{stem}.md'")
        else:
            passed += 1

    # stage.md 无对应 skill.yaml → warning（排除白名单）
    for stem in sorted(stage_stems):
        if stem in STAGE_NO_SKILL_WHITELIST:
            continue
        if stem not in skill_stems:
            warnings.append(f"stage '{stem}.md' 无对应 skill '{stem}.yaml'（孤儿文件）")

    return {"errors": errors, "warnings": warnings, "passed": passed}


def lint_all(
    rules_dir: Path | None = None,
    skills_dir: Path | None = None,
    stages_dir: Path | None = None,
) -> dict:
    """合并执行全部 lint 检查。"""
    r = lint_rules(rules_dir)
    s = lint_skills(skills_dir, rules_dir)
    c = lint_consistency(skills_dir, stages_dir)

    return {
        "errors": r["errors"] + s["errors"] + c["errors"],
        "warnings": r["warnings"] + s["warnings"] + c["warnings"],
        "passed": r["passed"] + s["passed"] + c["passed"],
        "details": {
            "rules": {"errors": len(r["errors"]), "warnings": len(r["warnings"]), "passed": r["passed"]},
            "skills": {"errors": len(s["errors"]), "warnings": len(s["warnings"]), "passed": s["passed"]},
            "consistency": {"errors": len(c["errors"]), "warnings": len(c["warnings"]), "passed": c["passed"]},
        },
    }


def main():
    parser = argparse.ArgumentParser(description="ClipForge 双轨 lint")
    parser.add_argument("command", choices=["check", "rules", "skills", "consistency"])
    parser.add_argument("--rules-dir", default=None)
    parser.add_argument("--skills-dir", default=None)
    parser.add_argument("--stages-dir", default=None)
    args = parser.parse_args()

    rules_dir = Path(args.rules_dir) if args.rules_dir else None
    skills_dir = Path(args.skills_dir) if args.skills_dir else None
    stages_dir = Path(args.stages_dir) if args.stages_dir else None

    if args.command == "check":
        result = lint_all(rules_dir, skills_dir, stages_dir)
    elif args.command == "rules":
        result = lint_rules(rules_dir)
    elif args.command == "skills":
        result = lint_skills(skills_dir, rules_dir)
    elif args.command == "consistency":
        result = lint_consistency(skills_dir, stages_dir)

    print(json.dumps(result, ensure_ascii=False, indent=2))
    if result["errors"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
