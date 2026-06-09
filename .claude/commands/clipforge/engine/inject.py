"""注入生成器 — 生成约束 prompt 段（正向重述 + 经验模式 + Guard Red Flags）。

根据 Skill 的 rigor 级别控制注入内容：
- LITE: 仅 HARD 规则
- STANDARD: 全量规则 + 经验模式
- STRICT: 全量 + Red Flags + spirit_vs_letter 声明
"""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from engine.lib.rule_parser import load_skill, load_rules_by_scope, RULES_DIR, SKILLS_DIR
from engine.lib.models import Severity, Rigor, Rule, RuleClass
from engine.lib.positive_rewrite import rewrite_rule
from engine.lib.delta import load_deltas, apply_delta_to_rules


PATTERNS_DIR = Path(__file__).parent.parent / "patterns"


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


def load_patterns(category: str | None = None, patterns_dir: Path | None = None) -> list[str]:
    from datetime import datetime, timedelta

    MAX_AGE_DAYS = 90
    patterns_dir = patterns_dir or PATTERNS_DIR
    if not patterns_dir.exists():
        return []
    patterns: list[str] = []
    for fp in sorted(patterns_dir.glob("*.yaml")):
        import yaml
        # 老化过滤：超过 90 天的 pattern 跳过
        mtime = datetime.fromtimestamp(fp.stat().st_mtime)
        if (datetime.now() - mtime).days > MAX_AGE_DAYS:
            continue
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

    # 应用高置信度 Delta（无需人工审核 + 7 天观察期已过）
    OBSERVATION_DAYS = 7
    from datetime import datetime as _dt, timezone as _tz
    try:
        deltas = load_deltas()
        auto_deltas = []
        for d in deltas:
            dd = d.get("delta", d)
            if dd.get("confidence", 0) < 0.70:
                continue
            # requires_human_review 可能在外层（attribution 写法）或内层（手动设置）
            needs_review = d.get("requires_human_review", dd.get("requires_human_review", True))
            if needs_review:
                continue
            # 7 天观察期：Delta 创建时间距今不足 7 天时不生效
            created = dd.get("created_at", "")
            if created:
                try:
                    created_dt = _dt.fromisoformat(created)
                    age_days = (_dt.now(_tz.utc) - created_dt).days
                    if age_days < OBSERVATION_DAYS:
                        continue
                except (ValueError, TypeError):
                    continue  # 日期解析失败 → 不自动应用
            auto_deltas.append(d)
        for delta in auto_deltas:
            rules = apply_delta_to_rules(rules, delta)
    except Exception:
        pass

    rigor = skill.rigor_level if skill else Rigor.STANDARD

    hard_rules = [r for r in rules if r.severity == Severity.HARD]
    soft_rules = [r for r in rules if r.severity == Severity.SOFT]

    lines: list[str] = []

    # Intent（所有严谨度都注入）
    if skill:
        lines.append(f"## 目标\n{skill.intent.objective}\n")
        if skill.intent.criteria:
            lines.append("## 成功标准")
            for c in skill.intent.criteria:
                lines.append(f"- {c}")
            lines.append("")

    # HARD 规则（所有严谨度都注入）
    lines.append("## 行为准则（必须遵守）")
    for r in hard_rules:
        rw = rewrite_rule(r)
        lines.append(f"- **[HARD]** {rw['positive']}")
    lines.append("")

    # SOFT 规则（STANDARD 和 STRICT 注入）
    if rigor in (Rigor.STANDARD, Rigor.STRICT) and soft_rules:
        lines.append("## 参考偏好（建议遵守）")
        for r in soft_rules:
            rw = rewrite_rule(r)
            lines.append(f"- [SOFT] {rw['positive']}")
        lines.append("")

    # Skill 声明的偏好（STANDARD 和 STRICT 注入）
    if rigor in (Rigor.STANDARD, Rigor.STRICT) and skill and skill.boundary.preferences:
        lines.append("## 偏好引导（来自 Skill 声明和历史经验）")
        for pref in skill.boundary.preferences:
            lines.append(f"- [{pref.weight}] {pref.text}")
        lines.append("")

    # 经验模式（STANDARD 和 STRICT 注入）
    if rigor in (Rigor.STANDARD, Rigor.STRICT):
        patterns = load_patterns(category, patterns_dir)
        if patterns:
            lines.append("## 成功经验（来自历史高分案例，供参考）")
            for p in patterns:
                lines.append(f"- {p}")
            lines.append("")

    # Guard Red Flags（仅 STRICT 注入）
    if rigor == Rigor.STRICT and skill and skill.guard_red_flags:
        lines.append("## 行为守卫（当以下念头出现时，立即 STOP）")
        lines.append("| 当你产生这个念头 | 现实是 |")
        lines.append("|---|---|")
        for rf in skill.guard_red_flags:
            lines.append(f"| {rf.get('thought', '')} | {rf.get('reality', '')} |")
        lines.append("任何 Red Flag 触发 → 暂停当前行为，回到约束检查。\n")

    # spirit_vs_letter LETTER 声明（STANDARD+ 注入，协议域核心约束）
    # SPIRIT 声明保留在 STRICT（生成域引导，非强制）
    if rigor in (Rigor.STANDARD, Rigor.STRICT) and skill and skill.spirit_vs_letter:
        letter_entries = [sl for sl in skill.spirit_vs_letter if sl.mode.value == "LETTER"]
        if letter_entries:
            lines.append("## 流程约束（必须按字面精确遵守）")
            for sl in letter_entries:
                lines.append(f"- 规则 {sl.rule_ref}: **按字面精确匹配** — {sl.intent}")
            lines.append("")

    # spirit_vs_letter SPIRIT 声明（仅 STRICT 注入）
    if rigor == Rigor.STRICT and skill and skill.spirit_vs_letter:
        spirit_entries = [sl for sl in skill.spirit_vs_letter if sl.mode.value == "SPIRIT"]
        if spirit_entries:
            lines.append("## 内容引导（按意图灵活解释）")
            for sl in spirit_entries:
                lines.append(f"- 规则 {sl.rule_ref}: 按意图解释 — {sl.intent}")
            lines.append("")

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
