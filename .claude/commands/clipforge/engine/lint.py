"""Skill/Rule 双轨 lint — 验证 skills/*.yaml, rules/*.yaml, stages/*.md 之间的一致性。

检查维度：
- lint_rules: 规则 ID 唯一性、枚举值合法性、scope 标准化
- lint_skills: GateType 合法性、rule refs 解析、intent 完整性
- lint_consistency: skill↔stage 跨文件匹配
"""
from __future__ import annotations
import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from engine.lib.rule_parser import load_all_rules, load_all_skills, RULES_DIR, SKILLS_DIR
from engine.lib.models import RuleType, Scope, GateType, RuleClass, Severity, Rule, Detection


STAGES_DIR = SKILLS_DIR.parent / "stages"

# 共享技能不需要对应 stage.md
SKILL_NO_STAGE_WHITELIST = {"movie-clips", "cleanup-rules"}
# 纯参考文档不需要对应 skill.yaml（机制/组件参考，不驱动执行）
# - stage6-components: 视觉组件参考手册
# - feedback-audit: 自进化闭环机制深度文档（clipforge.md §5.3 展开，stage8-feedback 引用）
STAGE_NO_SKILL_WHITELIST = {"stage6-components", "feedback-audit"}


# ── 编号规范检查（方案乙：声明-生效一致性）─────────────────────────────

_SECTION_NUM_RE = re.compile(r'^##\s+(\d+)\.?\s', re.MULTILINE)


def lint_numbering(markdown_text: str) -> list[str]:
    """检查主章节编号规范：§1 起，禁从 0 起号。

    CLAUDE.md 编号规范要求主章节从 §1 连续递增。本检查聚焦最确凿的违规——
    主章节从 ## 0. 起号（如 clipforge.md 历史「## 0. 角色」）。
    docs/ 设计参考文档豁免（见 CLAUDE.md 边界声明），本检查仅扫 .claude/commands/。
    """
    nums = [int(m.group(1)) for m in _SECTION_NUM_RE.finditer(markdown_text)]
    violations: list[str] = []
    if nums and nums[0] == 0:
        violations.append("主章节从 ## 0. 起号，违反「§1 起」规范（应从 ## 1. 起）")
    return violations


def _scan_numbering() -> list[str]:
    """扫描 .claude/commands/ 技能文档的章节编号，返回违规列表。

    覆盖 clipforge/ 子目录所有 md + 主控制器 commands/clipforge.md。
    """
    commands_dir = SKILLS_DIR.parent.parent
    clipforge_root = SKILLS_DIR.parent
    md_files = list(clipforge_root.rglob("*.md"))
    controller = commands_dir / "clipforge.md"
    if controller.exists():
        md_files.append(controller)
    violations: list[str] = []
    for md in md_files:
        try:
            text = md.read_text(encoding="utf-8")
        except Exception:
            continue
        for v in lint_numbering(text):
            violations.append(f"{md.relative_to(commands_dir)}: {v}")
    return violations


def lint_rigor_redflags(skills: dict | None = None) -> list[str]:
    """检测 guard.red_flags 声明完整性（每条应有 thought+reality+trigger）。

    inject ALL 注入 red_flags 后死声明概念消失，本检查转向声明质量——
    缺键的 red_flags 即使注入也无法有效引导（认知守卫需完整三要素）。
    """
    if skills is None:
        skills = load_all_skills()
    warnings: list[str] = []
    required = ("thought", "reality", "trigger")
    for name, skill in skills.items():
        for i, rf in enumerate(skill.guard_red_flags):
            missing = [k for k in required if not rf.get(k)]
            if missing:
                warnings.append(
                    f"{name}: guard.red_flags[{i}] 缺键 {missing}"
                    f"（认知守卫需 thought+reality+trigger 三要素）"
                )
    return warnings


def _probe_safety_rule() -> Rule:
    """构造一条 SAFETY 探测规则（不入库，仅用于 lint 行为探测）。"""
    return Rule(
        id="R-PROBE-SAFETY",
        type=RuleType.FORBIDDEN_ACTION,
        pattern="lint 探测用",
        positive="探测", guardrail="探测",
        detection=Detection(),
        severity=Severity.HARD,
        rule_class=RuleClass.SAFETY,
    )


def lint_safety_protection(apply_func=None) -> list[str]:
    """探测 apply_delta_to_rules 对 SAFETY 规则的保护完备性。

    §5.3 承诺「SAFETY 规则不可被 Delta 移除」。构造探测 Delta（针对 SAFETY 规则的
    MODIFIED/REMOVED/DEPRECATED），验证 apply 后 SAFETY 规则未被改/删/降级。
    依赖注入 apply_func 便于测试；默认用真实 apply_delta_to_rules。
    """
    if apply_func is None:
        from engine.lib.delta import apply_delta_to_rules as apply_func
    warnings: list[str] = []
    base = _probe_safety_rule()

    # MODIFIED 探测：试图把 SAFETY 规则 severity 降为 SOFT
    res = apply_func([base], {"delta": {"operation": "MODIFIED",
        "target_rule": base.id, "modified_fields": {"severity": "SOFT"}}})
    found = [r for r in res if r.id == base.id]
    if not found or found[0].severity != Severity.HARD:
        warnings.append("MODIFIED 操作未保护 SAFETY 规则（severity/字段可被改）——补 rule_class==SAFETY 检查")

    # REMOVED 探测：试图删除 SAFETY 规则
    res = apply_func([base], {"delta": {"operation": "REMOVED", "target_rule": base.id}})
    if not any(r.id == base.id for r in res):
        warnings.append("REMOVED 操作未保护 SAFETY 规则（可被删除）")

    # DEPRECATED 探测：试图降级 SAFETY 规则
    res = apply_func([base], {"delta": {"operation": "DEPRECATED", "target_rule": base.id}})
    found = [r for r in res if r.id == base.id]
    if found and found[0].severity != Severity.HARD:
        warnings.append("DEPRECATED 操作未保护 SAFETY 规则（severity 被降级）")

    return warnings


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
    """合并执行全部 lint 检查（含方案乙：声明-生效一致性三检查）。"""
    r = lint_rules(rules_dir)
    s = lint_skills(skills_dir, rules_dir)
    c = lint_consistency(skills_dir, stages_dir)

    # 方案乙：声明-生效一致性
    rigor_warns = lint_rigor_redflags()
    safety_errs = lint_safety_protection()  # SAFETY 保护缺失 = error
    numb_warns = _scan_numbering()

    return {
        "errors": r["errors"] + s["errors"] + c["errors"] + safety_errs,
        "warnings": r["warnings"] + s["warnings"] + c["warnings"] + rigor_warns + numb_warns,
        "passed": r["passed"] + s["passed"] + c["passed"],
        "details": {
            "rules": {"errors": len(r["errors"]), "warnings": len(r["warnings"]), "passed": r["passed"]},
            "skills": {"errors": len(s["errors"]), "warnings": len(s["warnings"]), "passed": s["passed"]},
            "consistency": {"errors": len(c["errors"]), "warnings": len(c["warnings"]), "passed": c["passed"]},
            "numbering": {"warnings": len(numb_warns)},
            "rigor_redflags": {"warnings": len(rigor_warns)},
            "safety_protection": {"errors": len(safety_errs)},
        },
    }


def main():
    parser = argparse.ArgumentParser(description="ClipForge 双轨 lint")
    parser.add_argument("command", choices=["check", "rules", "skills", "consistency", "numbering", "rigor", "safety"])
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
    elif args.command == "numbering":
        result = {"errors": [], "warnings": _scan_numbering()}
    elif args.command == "rigor":
        result = {"errors": [], "warnings": lint_rigor_redflags()}
    elif args.command == "safety":
        result = {"errors": lint_safety_protection(), "warnings": []}

    print(json.dumps(result, ensure_ascii=False, indent=2))
    if result["errors"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
