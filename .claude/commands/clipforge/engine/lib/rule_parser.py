"""规则文件解析器 — 加载 YAML 规则文件和 Skill 声明。"""
from __future__ import annotations
import json
import yaml
from pathlib import Path
from .models import (
    Rule, RuleType, Severity, RuleClass, Scope, Detection, Rigor,
    SkillDefinition, SkillMeta, SkillIntent, SkillBoundary, SkillGate,
    SkillTrace, GateDefinition, GateType, CaptureLevel, Preference,
    SpiritLetterEntry, SpiritMode,
)

from .data_paths import hit_counts_file

RULES_DIR = Path(__file__).parent.parent.parent / "rules"
SKILLS_DIR = Path(__file__).parent.parent.parent / "skills"
HIT_COUNTS_FILE = hit_counts_file()


def _resolve_scope(raw_scope: str) -> tuple[Scope, str | None]:
    """将 YAML scope 值解析为 (Scope 枚举, skill 名)。

    GLOBAL/SCENE/SKILL 直接匹配。其他值视为 SKILL 作用域，scope 值即为 skill 名。
    """
    try:
        return Scope(raw_scope), None
    except ValueError:
        return Scope.SKILL, raw_scope


def parse_rule(raw: dict) -> Rule:
    raw_scope = raw.get("scope", "GLOBAL")
    scope, skill_from_scope = _resolve_scope(raw_scope)
    return Rule(
        id=raw["id"],
        type=RuleType(raw["type"]),
        pattern=raw["pattern"],
        positive=raw.get("positive", ""),
        guardrail=raw.get("guardrail", ""),
        detection=Detection(
            keywords=raw.get("detection", {}).get("keywords", []),
            regex=raw.get("detection", {}).get("regex"),
            semantic_check=raw.get("detection", {}).get("semantic_check", False),
        ),
        severity=Severity(raw.get("severity", "HARD")),
        rule_class=RuleClass(raw.get("class", "EXPERIENTIAL")),
        scope=scope,
        scene=raw.get("scene"),
        skill=raw.get("skill") or skill_from_scope,
        source=raw.get("source", ""),
        created_at=raw.get("created_at", ""),
        hit_count=raw.get("hit_count", 0),
        false_positive_count=raw.get("false_positive_count", 0),
    )


def load_rules_from_file(filepath: Path) -> list[Rule]:
    with open(filepath, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not data or "rules" not in data:
        return []
    return [parse_rule(r) for r in data["rules"]]


def load_all_rules(rules_dir: Path | None = None) -> list[Rule]:
    rules_dir = rules_dir or RULES_DIR
    rules: list[Rule] = []
    for fp in sorted(rules_dir.glob("*.yaml")):
        rules.extend(load_rules_from_file(fp))
    cat_dir = rules_dir / "categories"
    if cat_dir.exists():
        for fp in sorted(cat_dir.glob("*.yaml")):
            rules.extend(load_rules_from_file(fp))
    return rules


def load_rules_by_scope(
    skill_id: str | None = None,
    category: str | None = None,
    rules_dir: Path | None = None,
) -> list[Rule]:
    all_rules = load_all_rules(rules_dir)
    matched: list[Rule] = []
    for r in all_rules:
        if r.scope == Scope.GLOBAL:
            matched.append(r)
        elif r.scope == Scope.SCENE and category and r.scene == category:
            matched.append(r)
        elif r.scope == Scope.SKILL and skill_id and r.skill == skill_id:
            matched.append(r)
    if category:
        cat_dir = (rules_dir or RULES_DIR) / "categories"
        cat_file = cat_dir / f"{category}.yaml"
        if cat_file.exists():
            matched.extend(load_rules_from_file(cat_file))
    return matched


def parse_gate_def(raw: dict) -> GateDefinition:
    return GateDefinition(
        gate=GateType(raw["gate"]),
        params=raw.get("params", {}),
    )


def parse_skill(raw: dict) -> SkillDefinition:
    s = raw.get("skill", raw)
    meta_raw = s.get("meta", {})
    intent_raw = s.get("intent", {})
    boundary_raw = s.get("boundary", {})
    gate_raw = s.get("gate", {})
    trace_raw = s.get("trace", {})
    guard_raw = s.get("guard", {})

    hard_gates = [parse_gate_def(g) for g in gate_raw.get("hard", [])]
    soft_gates = [parse_gate_def(g) for g in gate_raw.get("soft", [])]

    red_flags = guard_raw.get("red_flags", [])
    red_flag_dicts = [
        {"thought": rf.get("thought", ""), "reality": rf.get("reality", ""), "trigger": rf.get("trigger", "")}
        for rf in red_flags
    ]

    spirit_entries = [
        SpiritLetterEntry(
            rule_ref=sl.get("rule_ref", ""),
            mode=SpiritMode(sl.get("mode", "SPIRIT")),
            intent=sl.get("intent", ""),
        )
        for sl in guard_raw.get("spirit_vs_letter", [])
    ]

    prefs = [
        Preference(
            text=p.get("text", ""),
            weight=p.get("weight", "MEDIUM"),
            source_pattern=p.get("source_pattern"),
        )
        for p in boundary_raw.get("preferences", [])
    ]

    return SkillDefinition(
        meta=SkillMeta(
            id=meta_raw.get("id", ""),
            version=meta_raw.get("version", "1.0.0"),
            type=meta_raw.get("type", "EXECUTIVE"),
            tags=meta_raw.get("tags", []),
            rigor=Rigor(meta_raw.get("rigor", "STANDARD")),
        ),
        intent=SkillIntent(
            objective=intent_raw.get("objective", ""),
            criteria=intent_raw.get("criteria", []),
        ),
        boundary=SkillBoundary(
            scene=boundary_raw.get("scene"),
            rule_refs=boundary_raw.get("rules", []),
            preferences=prefs,
        ),
        gate=SkillGate(
            hard=hard_gates,
            soft=soft_gates,
            max_retries=gate_raw.get("max_retries", 2),
        ),
        trace=SkillTrace(
            capture=trace_raw.get("capture", True),
            level=CaptureLevel(trace_raw.get("level", "FULL")),
            sensitive_fields=trace_raw.get("sensitive_fields", []),
        ),
        guard_red_flags=red_flag_dicts,
        spirit_vs_letter=spirit_entries,
    )


def load_skill(skill_name: str, skills_dir: Path | None = None) -> SkillDefinition | None:
    skills_dir = skills_dir or SKILLS_DIR
    filepath = skills_dir / f"{skill_name}.yaml"
    if not filepath.exists():
        return None
    with open(filepath, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return parse_skill(data)


def load_all_skills(skills_dir: Path | None = None) -> dict[str, SkillDefinition]:
    skills_dir = skills_dir or SKILLS_DIR
    result: dict[str, SkillDefinition] = {}
    for fp in sorted(skills_dir.glob("*.yaml")):
        with open(fp, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        skill = parse_skill(data)
        name = fp.stem
        result[name] = skill
    return result


def _load_hit_counts() -> dict[str, int]:
    """从磁盘加载持久化的规则命中计数。"""
    if HIT_COUNTS_FILE.exists():
        try:
            return json.loads(HIT_COUNTS_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return {}
    return {}


def _save_hit_counts(counts: dict[str, int]) -> None:
    """将规则命中计数持久化到磁盘。"""
    HIT_COUNTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    HIT_COUNTS_FILE.write_text(json.dumps(counts, ensure_ascii=False, indent=2), encoding="utf-8")


def update_hit_counts(scope: str, rule_ids: list[str], rules_db: dict = None):
    """更新规则命中计数并持久化。gate 通过时调用。

    Args:
        scope: 作用域标识（如 "global"），预留扩展用。
        rule_ids: 命中的规则 ID 列表。
        rules_db: 规则字典 {rule_id: Rule}。为 None 时从磁盘重新加载。
    """
    if rules_db is None:
        all_rules = load_all_rules()
        rules_db = {r.id: r for r in all_rules}

    counts = _load_hit_counts()
    for rule_id in rule_ids:
        if rule_id in rules_db:
            rules_db[rule_id].hit_count += 1
        counts[rule_id] = counts.get(rule_id, 0) + 1
    _save_hit_counts(counts)


def get_persistent_hit_counts() -> dict[str, int]:
    """获取持久化的规则命中计数（跨进程累积）。"""
    return _load_hit_counts()
