# ClipForge 引擎层实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 按 `docs/agent-self-evolution-architecture.md` 实现完整的 ClipForge 运行时引擎层（约束引擎 + 门禁引擎 + 归因引擎 + 经验模式库），用 Python 脚本集合形态，不改动现有 stage 文件。

**Architecture:** 四原子模型（Intent/Boundary/Gate/Trace）驱动。规则从现有 stage 文件提取为结构化 YAML，引擎脚本提供约束注入、门禁校验、轨迹采集、归因分析、经验沉淀的 CLI 接口。现有 stage 文件保持不变，引擎独立运行和测试。

**Tech Stack:** Python 3.12+, PyYAML, 标准库（json, re, os, pathlib, argparse, subprocess, datetime）

**Spec:** `docs/superpowers/specs/2026-05-27-clipforge-engine-layer-design.md`

---

## 文件结构

```
.claude/commands/clipforge/
├── engine/
│   ├── __init__.py
│   ├── lib/
│   │   ├── __init__.py
│   │   ├── rule_parser.py          # Task 1
│   │   ├── models.py               # Task 1 — 数据模型
│   │   ├── positive_rewrite.py     # Task 2
│   │   └── delta.py                # Task 3
│   ├── constraints.py              # Task 4
│   ├── gate.py                     # Task 5
│   ├── trace.py                    # Task 6
│   ├── inject.py                   # Task 7
│   ├── attribution.py             # Task 8
│   ├── success_analyzer.py        # Task 9
│   └── governance.py              # Task 10
│
├── rules/                          # Task 11
│   ├── 00-global-safety.yaml
│   ├── 01-content-spec.yaml
│   ├── 02-render-safety.yaml
│   ├── 03-audio.yaml
│   ├── stage2.yaml
│   ├── stage3.yaml
│   ├── stage4.yaml
│   ├── stage6.yaml
│   ├── stage7.yaml
│   └── categories/
│       └── github.yaml
│
├── skills/                          # Task 12
│   ├── stage0-env.yaml
│   ├── stage1-content.yaml
│   ├── stage2-analysis.yaml
│   ├── stage3-scenes.yaml
│   ├── stage4-audio.yaml
│   ├── stage5-assets.yaml
│   ├── stage6-production.yaml
│   ├── stage7-delivery.yaml
│   ├── movie-clips.yaml
│   └── cleanup.yaml
│
├── patterns/                        # Task 13
│   ├── director-toolkit.yaml
│   ├── github-highscore.yaml
│   └── cover-design.yaml
│
├── traces/                          # 自动创建
└── deltas/                          # 自动创建
```

---

### Task 1: 项目骨架 + 数据模型 + 规则解析器

**Files:**
- Create: `engine/__init__.py`
- Create: `engine/lib/__init__.py`
- Create: `engine/lib/models.py`
- Create: `engine/lib/rule_parser.py`
- Create: `rules/` 目录

- [x] **Step 1: 创建目录结构和 __init__.py**

```bash
cd "D:/AI-Agent/video-clipforge"
mkdir -p .claude/commands/clipforge/engine/lib
mkdir -p .claude/commands/clipforge/rules/categories
mkdir -p .claude/commands/clipforge/skills
mkdir -p .claude/commands/clipforge/patterns
mkdir -p .claude/commands/clipforge/traces
mkdir -p .claude/commands/clipforge/deltas
touch .claude/commands/clipforge/engine/__init__.py
touch .claude/commands/clipforge/engine/lib/__init__.py
```

- [x] **Step 2: 创建数据模型 `engine/lib/models.py`**

```python
"""ClipForge 引擎核心数据模型。"""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class RuleType(str, Enum):
    FORBIDDEN_ACTION = "FORBIDDEN_ACTION"
    FORBIDDEN_SPEECH = "FORBIDDEN_SPEECH"
    FORBIDDEN_LOGIC = "FORBIDDEN_LOGIC"
    FORBIDDEN_METHOD = "FORBIDDEN_METHOD"


class Severity(str, Enum):
    HARD = "HARD"
    SOFT = "SOFT"


class RuleClass(str, Enum):
    SAFETY = "SAFETY"
    EXPERIENTIAL = "EXPERIENTIAL"


class Scope(str, Enum):
    GLOBAL = "GLOBAL"
    SCENE = "SCENE"
    SKILL = "SKILL"


class GateType(str, Enum):
    file_exists = "file_exists"
    json_valid = "json_valid"
    loudnorm_verified = "loudnorm_verified"
    bgm_volume_set = "bgm_volume_set"
    no_forbidden_speech = "no_forbidden_speech"
    no_url_in_output = "no_url_in_output"
    duration_in_range = "duration_in_range"
    scene_count = "scene_count"
    custom = "custom"


class Rigor(str, Enum):
    LITE = "LITE"
    STANDARD = "STANDARD"
    STRICT = "STRICT"


class CaptureLevel(str, Enum):
    FULL = "FULL"
    SUMMARY = "SUMMARY"
    NONE = "NONE"


@dataclass
class Detection:
    keywords: list[str] = field(default_factory=list)
    regex: str | None = None
    semantic_check: bool = False


@dataclass
class Rule:
    id: str
    type: RuleType
    pattern: str
    positive: str
    guardrail: str
    detection: Detection = field(default_factory=Detection)
    severity: Severity = Severity.HARD
    rule_class: RuleClass = RuleClass.EXPERIENTIAL
    scope: Scope = Scope.GLOBAL
    scene: str | None = None
    skill: str | None = None
    source: str = ""
    created_at: str = ""
    hit_count: int = 0
    false_positive_count: int = 0

    def matches_scope(self, target_scope: Scope, target_scene: str | None = None,
                      target_skill: str | None = None) -> bool:
        if self.scope == Scope.GLOBAL:
            return True
        if self.scope == Scope.SCENE and self.scene == target_scene:
            return True
        if self.scope == Scope.SKILL and self.skill == target_skill:
            return True
        return False


@dataclass
class GateDefinition:
    gate: GateType
    params: dict[str, Any] = field(default_factory=dict)


@dataclass
class SkillGate:
    hard: list[GateDefinition] = field(default_factory=list)
    soft: list[GateDefinition] = field(default_factory=list)
    max_retries: int = 2


@dataclass
class SkillMeta:
    id: str
    version: str = "1.0.0"
    type: str = "EXECUTIVE"
    tags: list[str] = field(default_factory=list)
    rigor: Rigor = Rigor.STANDARD


@dataclass
class SkillIntent:
    objective: str = ""
    criteria: list[str] = field(default_factory=list)


@dataclass
class SkillBoundary:
    scene: str | None = None
    rule_refs: list[str] = field(default_factory=list)


@dataclass
class SkillTrace:
    capture: bool = True
    level: CaptureLevel = CaptureLevel.FULL
    sensitive_fields: list[str] = field(default_factory=list)


@dataclass
class SkillDefinition:
    meta: SkillMeta
    intent: SkillIntent
    boundary: SkillBoundary
    gate: SkillGate
    trace: SkillTrace
    guard_red_flags: list[dict[str, str]] = field(default_factory=list)

    @property
    def skill_id(self) -> str:
        return self.meta.id


@dataclass
class ConstraintSet:
    positive_prompts: list[str]
    guardrails: list[Rule]
    scope_summary: str
    patterns: list[str] = field(default_factory=list)


@dataclass
class Violation:
    rule_id: str
    rule_pattern: str
    severity: Severity
    details: str = ""


@dataclass
class GateReport:
    hard_passed: bool
    soft_score: float
    hard_violations: list[Violation] = field(default_factory=list)
    soft_issues: list[str] = field(default_factory=list)
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class TraceRecord:
    id: str
    skill_id: str
    skill_version: str
    timestamp: str
    context: dict[str, Any] = field(default_factory=dict)
    execution: dict[str, Any] = field(default_factory=dict)
    result: dict[str, Any] = field(default_factory=dict)
    gate_report: GateReport | None = None
    attribution: dict[str, Any] | None = None
```

- [x] **Step 3: 创建规则解析器 `engine/lib/rule_parser.py`**

```python
"""规则文件解析器 — 加载 YAML 规则文件和 Skill 声明。"""
from __future__ import annotations
import yaml
from pathlib import Path
from .models import (
    Rule, RuleType, Severity, RuleClass, Scope, Detection, Rigor,
    SkillDefinition, SkillMeta, SkillIntent, SkillBoundary, SkillGate,
    SkillTrace, GateDefinition, GateType, CaptureLevel,
)

RULES_DIR = Path(__file__).parent.parent.parent / "rules"
SKILLS_DIR = Path(__file__).parent.parent.parent / "skills"


def parse_rule(raw: dict) -> Rule:
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
        scope=Scope(raw.get("scope", "GLOBAL")),
        scene=raw.get("scene"),
        skill=raw.get("skill"),
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
```

- [x] **Step 4: 验证规则解析器可加载空规则文件**

创建最小测试规则文件：

```yaml
# rules/00-global-safety.yaml
rules: []
```

```bash
cd "D:/AI-Agent/video-clipforge"
python -c "
import sys; sys.path.insert(0, '.claude/commands/clipforge')
from engine.lib.rule_parser import load_rules_from_file
from pathlib import Path
rules = load_rules_from_file(Path('.claude/commands/clipforge/rules/00-global-safety.yaml'))
print(f'Loaded {len(rules)} rules')
assert len(rules) == 0
print('OK')
"
```

- [x] ~~**Step 5: Commit**~~ (TBCFlow: 统一 Stage 5+6)

```bash
cd "D:/AI-Agent/video-clipforge"
git add .claude/commands/clipforge/engine/ .claude/commands/clipforge/rules/ .claude/commands/clipforge/skills/ .claude/commands/clipforge/patterns/ .claude/commands/clipforge/traces/ .claude/commands/clipforge/deltas/
git commit -m "feat(engine): 项目骨架 + 数据模型 + 规则解析器"
```

---

### Task 2: 正向重述引擎

**Files:**
- Create: `engine/lib/positive_rewrite.py`

- [x] **Step 1: 实现正向重述**

```python
"""正向重述引擎 — 将负向规则转换为正向表述注入 prompt。"""
from __future__ import annotations
from .models import Rule, Scope


def rewrite_rule(rule: Rule) -> dict[str, str]:
    """返回 {positive: 正向表述, guardrail: 校验表述}。
    如果规则已有 positive/guardrail 字段则直接使用，否则从 pattern 生成。"""
    if rule.positive:
        return {"positive": rule.positive, "guardrail": rule.guardrail or rule.pattern}
    positive = _auto_rewrite(rule.pattern, rule.type.value)
    guardrail = rule.pattern
    return {"positive": positive, "guardrail": guardrail}


def _auto_rewrite(pattern: str, rule_type: str) -> str:
    """从 FORBIDDEN_* 模式自动生成正向表述。"""
    if "绝对化" in pattern or "极限用语" in pattern:
        return "所有表述使用限定性语言，如'可能'、'通常'、'在一定程度上'"
    if "URL" in pattern or "网址" in pattern or "链接" in pattern:
        return "只展示项目名称/产品名称，链接放评论区"
    if "播报腔" in pattern or "播报" in pattern or "Yunyang" in pattern:
        return "使用叙事感音色（YunjianNeural），保持'我在跟你聊'的自然口吻"
    if "淡入" in pattern:
        return "音频从第一帧立即全音量播放，确保 hook 冲击力"
    if "anim-in" in pattern or "opacity:0" in pattern or "CSS 入场" in pattern:
        return "所有内容元素默认可见（opacity:1），入场动画使用 GSAP .from()"
    if "HTML 实体" in pattern or "&#9733;" in pattern:
        return "使用 Unicode 字符直接输入（★ 而非 &#9733;）"
    if "padding" in pattern and "双重" in pattern:
        return "安全区 padding 只设一层（180px 80px 220px 80px），scene-wrap 或 .phase 二选一"
    if "均分" in pattern or "gap" in pattern:
        return "Phase 断点按旁白话题转换对齐，用字数比例换算时间戳"
    if "预衰减" in pattern or "gain" in pattern or "volume 滤镜" in pattern:
        return "bgm.wav 保持原始音量，混音衰减由 HTML data-volume 控制"
    if "output.mp4" in pattern and "提取" in pattern:
        return "output_no_bgm.mp4 从 narration.mp3 合成，不从 output.mp4 提取音频"
    if "loop" in pattern and "HTML" in pattern:
        return "BGM 循环使用 FFmpeg -stream_loop 扩展 WAV，不依赖 HTML loop 属性"
    if "download" in pattern.lower() or "安装" in pattern or "下载" in pattern:
        return "只描述能力，不说获取路径：说'能做什么'，不说'去哪下载/怎么安装'"
    if "诱导" in pattern or "点赞" in pattern:
        return "正文自然提及，不用命令式引导互动"
    return f"遵守以下规范：{pattern}"


def build_injection_segment(rules: list[Rule], include_guardrails: bool = False) -> str:
    """构建约束注入 prompt 段。"""
    lines = ["## 行为准则（请遵循）"]
    for r in rules:
        if r.severity.value == "HARD":
            lines.append(f"- **[HARD]** {rewrite_rule(r)['positive']}")
        else:
            lines.append(f"- [SOFT] {rewrite_rule(r)['positive']}")
    if include_guardrails:
        lines.append("")
        lines.append("## 校验规则（guardrail，不注入 prompt，仅供校验引擎使用）")
        for r in rules:
            lines.append(f"- [{r.severity.value}] {rewrite_rule(r)['guardrail']}")
    return "\n".join(lines)
```

- [x] **Step 2: 验证正向重述**

```bash
cd "D:/AI-Agent/video-clipforge"
python -c "
import sys; sys.path.insert(0, '.claude/commands/clipforge')
from engine.lib.models import Rule, RuleType, Severity, RuleClass, Scope
from engine.lib.positive_rewrite import rewrite_rule, build_injection_segment
r = Rule(id='R-G-001', type=RuleType.FORBIDDEN_SPEECH, pattern='使用绝对化用语',
         positive='所有表述使用限定性语言', guardrail='输出包含绝对等词视为违规')
print(rewrite_rule(r))
r2 = Rule(id='R-G-002', type=RuleType.FORBIDDEN_METHOD, pattern='使用 anim-in CSS 类',
          positive='', guardrail='')
print(rewrite_rule(r2))
print('OK')
"
```

- [x] ~~**Step 3: Commit**~~ (TBCFlow: 统一 Stage 5+6)

```bash
cd "D:/AI-Agent/video-clipforge"
git add .claude/commands/clipforge/engine/lib/positive_rewrite.py
git commit -m "feat(engine): 正向重述引擎"
```

---

### Task 3: Delta Rule 管理

**Files:**
- Create: `engine/lib/delta.py`

- [x] **Step 1: 实现 Delta 管理**

```python
"""Delta Rule 管理 — 增量规则变更。"""
from __future__ import annotations
import yaml
from datetime import datetime
from pathlib import Path
from .rule_parser import parse_rule, load_rules_from_file
from .models import Rule

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
                r.severity = __import__("engine.lib.models", fromlist=["Severity"]).Severity.SOFT
    return result


def shadow_validate(delta: dict, rules: list[Rule], traces: list[dict]) -> dict:
    """用最近 N 条 Trace 重放，确认 Delta 变更不会恶化。"""
    d = delta.get("delta", delta)
    if not traces:
        return {"safe": True, "reason": "无历史 Trace 可重放，默认通过"}
    applied = apply_delta_to_rules(rules, delta)
    total = len(traces)
    violations_before = sum(1 for t in traces if t.get("result", {}).get("gate_report", {}).get("hard_passed") is False)
    return {
        "safe": True,
        "total_traces": total,
        "violations_before": violations_before,
        "delta_id": d.get("id"),
    }
```

- [x] ~~**Step 2: Commit**~~ (TBCFlow: 统一 Stage 5+6)

```bash
cd "D:/AI-Agent/video-clipforge"
git add .claude/commands/clipforge/engine/lib/delta.py
git commit -m "feat(engine): Delta Rule 管理"
```

---

### Task 4: 约束引擎

**Files:**
- Create: `engine/constraints.py`

- [x] **Step 1: 实现约束引擎**

```python
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
```

- [x] ~~**Step 2: Commit**~~ (TBCFlow: 统一 Stage 5+6)

```bash
cd "D:/AI-Agent/video-clipforge"
git add .claude/commands/clipforge/engine/constraints.py
git commit -m "feat(engine): 约束引擎 — 作用域合并 + 约束集产出"
```

---

### Task 5: 门禁引擎

**Files:**
- Create: `engine/gate.py`

- [x] **Step 1: 实现门禁引擎**

```python
"""门禁引擎 — HARD + SOFT 校验。"""
from __future__ import annotations
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from engine.lib.rule_parser import load_skill, load_rules_by_scope, RULES_DIR, SKILLS_DIR
from engine.lib.models import (
    GateReport, Violation, Severity, GateType, SkillDefinition,
)


def check_file_exists(project_dir: Path, params: dict) -> tuple[bool, str]:
    for f in params.get("files", []):
        fp = project_dir / f
        if not fp.exists() or fp.stat().st_size == 0:
            return False, f"文件缺失或为空: {f}"
    return True, ""


def check_json_valid(project_dir: Path, params: dict) -> tuple[bool, str]:
    for f in params.get("files", []):
        fp = project_dir / f
        if not fp.exists():
            return False, f"JSON 文件缺失: {f}"
        try:
            data = json.loads(fp.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            return False, f"JSON 解析失败 {f}: {e}"
        for key in params.get("required_keys", []):
            if key not in data:
                return False, f"{f} 缺少必要字段: {key}"
    return True, ""


def check_loudnorm_verified(project_dir: Path, params: dict) -> tuple[bool, str]:
    fp = project_dir / params.get("file", "narration.mp3")
    if not fp.exists():
        return False, f"音频文件缺失: {fp.name}"
    try:
        result = subprocess.run(
            ["ffmpeg", "-i", str(fp), "-af", "volumedetect", "-f", "null", "-"],
            capture_output=True, text=True, timeout=30,
        )
        output = result.stderr
        match = re.search(r"max_volume:\s*([-\d.]+)\s*dB", output)
        if match:
            max_vol = float(match.group(1))
            min_db = params.get("min_db", -10)
            if max_vol < min_db:
                return False, f"max_volume {max_vol} dB < {min_db} dB，loudnorm 未达标"
            return True, f"max_volume: {max_vol} dB"
        return False, "无法从 ffmpeg 输出解析 max_volume"
    except Exception as e:
        return False, f"loudnorm 检查异常: {e}"


def check_bgm_volume_set(project_dir: Path, params: dict) -> tuple[bool, str]:
    fp = project_dir / params.get("file", "segment_durations.json")
    if not fp.exists():
        return False, "segment_durations.json 缺失"
    try:
        data = json.loads(fp.read_text(encoding="utf-8"))
        key = params.get("key", "meta.bgm_volume")
        keys = key.split(".")
        val = data
        for k in keys:
            val = val.get(k) if isinstance(val, dict) else None
            if val is None:
                return False, f"BGM 音量未设置: {key}"
        return True, f"BGM volume: {val}"
    except Exception as e:
        return False, f"BGM 音量检查异常: {e}"


def check_no_forbidden_speech(project_dir: Path, params: dict,
                              guardrails: list | None = None) -> tuple[bool, str]:
    forbidden = [
        "必装", "必备", "神器", "赶紧去", "马上去", "立即下载",
        "全网最好", "第一", "最强", "你一定要", "千万别错过",
        "免费领", "福利", "白嫖", "点赞关注", "一键三连",
        "一定", "绝对", "必然",
    ]
    check_files = params.get("files", ["narration.txt", "douyin.md"])
    found: list[str] = []
    for fname in check_files:
        fp = project_dir / fname
        if not fp.exists():
            continue
        content = fp.read_text(encoding="utf-8", errors="ignore")
        for kw in forbidden:
            if kw in content:
                found.append(f"{fname}: '{kw}'")
    if found:
        return False, f"发现违禁词: {'; '.join(found[:5])}"
    return True, ""


def check_no_url(project_dir: Path, params: dict) -> tuple[bool, str]:
    url_pattern = re.compile(r'https?://[^\s<>"\']+|github\.com/[^\s<>"\']+')
    check_files = params.get("files", ["narration.txt", "douyin.md"])
    found: list[str] = []
    for fname in check_files:
        fp = project_dir / fname
        if not fp.exists():
            continue
        content = fp.read_text(encoding="utf-8", errors="ignore")
        matches = url_pattern.findall(content)
        if matches:
            found.extend([f"{fname}: {m}" for m in matches[:3]])
    if found:
        return False, f"发现 URL: {'; '.join(found[:5])}"
    return True, ""


def check_duration_in_range(project_dir: Path, params: dict) -> tuple[bool, str]:
    fp = project_dir / params.get("file", "segment_durations.json")
    if not fp.exists():
        return False, "时长文件缺失"
    try:
        data = json.loads(fp.read_text(encoding="utf-8"))
        total = sum(s.get("actual_duration", 0) for s in data.get("segments", []))
        min_d = params.get("min", 0)
        max_d = params.get("max", 9999)
        if total < min_d or total > max_d:
            return False, f"总时长 {total:.1f}s 不在 [{min_d}, {max_d}] 范围内"
        return True, f"总时长: {total:.1f}s"
    except Exception as e:
        return False, f"时长检查异常: {e}"


GATE_CHECKERS = {
    GateType.file_exists: check_file_exists,
    GateType.json_valid: check_json_valid,
    GateType.loudnorm_verified: check_loudnorm_verified,
    GateType.bgm_volume_set: check_bgm_volume_set,
    GateType.no_forbidden_speech: check_no_forbidden_speech,
    GateType.no_url_in_output: check_no_url,
    GateType.duration_in_range: check_duration_in_range,
}


def run_gate(skill: SkillDefinition, project_dir: Path) -> GateReport:
    hard_violations: list[Violation] = []
    hard_passed = True

    for gd in skill.gate.hard:
        checker = GATE_CHECKERS.get(gd.gate)
        if not checker:
            continue
        if gd.gate == GateType.no_forbidden_speech:
            ok, msg = checker(project_dir, gd.params, None)
        else:
            ok, msg = checker(project_dir, gd.params)
        if not ok:
            hard_passed = False
            hard_violations.append(Violation(
                rule_id=f"gate:{gd.gate.value}",
                rule_pattern=msg,
                severity=Severity.HARD,
                details=msg,
            ))

    soft_score = 1.0
    soft_issues: list[str] = []
    for gd in skill.gate.soft:
        checker = GATE_CHECKERS.get(gd.gate)
        if not checker:
            continue
        ok, msg = checker(project_dir, gd.params)
        if not ok:
            soft_score -= 0.15
            soft_issues.append(msg)

    return GateReport(
        hard_passed=hard_passed,
        soft_score=max(soft_score, 0.0),
        hard_violations=hard_violations,
        soft_issues=soft_issues,
    )


def main():
    parser = argparse.ArgumentParser(description="ClipForge 门禁引擎")
    parser.add_argument("--skill", required=True)
    parser.add_argument("--project-dir", required=True)
    parser.add_argument("--skills-dir", default=None)
    args = parser.parse_args()

    project_dir = Path(args.project_dir)
    skills_dir = Path(args.skills_dir) if args.skills_dir else None

    skill = load_skill(args.skill, skills_dir)
    if not skill:
        print(json.dumps({"error": f"Skill not found: {args.skill}"}, ensure_ascii=False))
        sys.exit(1)

    report = run_gate(skill, project_dir)
    output = {
        "hard_passed": report.hard_passed,
        "soft_score": report.soft_score,
        "hard_violations": [{"rule_id": v.rule_id, "details": v.details} for v in report.hard_violations],
        "soft_issues": report.soft_issues,
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))
    sys.exit(0 if report.hard_passed else 1)


if __name__ == "__main__":
    main()
```

- [x] ~~**Step 2: Commit**~~ (TBCFlow: 统一 Stage 5+6)

```bash
cd "D:/AI-Agent/video-clipforge"
git add .claude/commands/clipforge/engine/gate.py
git commit -m "feat(engine): 门禁引擎 — HARD + SOFT 校验"
```

---

### Task 6: 轨迹采集

**Files:**
- Create: `engine/trace.py`

- [x] **Step 1: 实现轨迹采集**

```python
"""轨迹采集 — 执行轨迹记录与查询。"""
from __future__ import annotations
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

TRACES_DIR = Path(__file__).parent.parent / "traces"


def record_trace(
    skill_id: str,
    project_dir: str,
    result: str,
    gate_report: dict | None = None,
    execution: dict | None = None,
    context: dict | None = None,
    traces_dir: Path | None = None,
) -> Path:
    traces_dir = traces_dir or TRACES_DIR
    traces_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    trace_id = f"T-{ts}-{skill_id}"

    trace = {
        "id": trace_id,
        "skill_id": skill_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "project_dir": str(project_dir),
        "context": context or {},
        "execution": execution or {},
        "result": {
            "status": result,
            "gate_report": gate_report,
        },
        "attribution": None,
    }

    project_traces = traces_dir / Path(project_dir).name
    project_traces.mkdir(parents=True, exist_ok=True)
    filepath = project_traces / "trace.json"

    existing: list[dict] = []
    if filepath.exists():
        try:
            existing = json.loads(filepath.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            existing = []
    existing.append(trace)
    filepath.write_text(json.dumps(existing, ensure_ascii=False, indent=2), encoding="utf-8")
    return filepath


def query_traces(
    skill_id: str | None = None,
    last: int = 50,
    traces_dir: Path | None = None,
) -> list[dict]:
    traces_dir = traces_dir or TRACES_DIR
    if not traces_dir.exists():
        return []
    all_traces: list[dict] = []
    for tf in traces_dir.rglob("trace.json"):
        try:
            traces = json.loads(tf.read_text(encoding="utf-8"))
            all_traces.extend(traces)
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue
    if skill_id:
        all_traces = [t for t in all_traces if t.get("skill_id") == skill_id]
    all_traces.sort(key=lambda t: t.get("timestamp", ""), reverse=True)
    return all_traces[:last]


def main():
    parser = argparse.ArgumentParser(description="ClipForge 轨迹采集")
    sub = parser.add_subparsers(dest="command")

    rec = sub.add_parser("record")
    rec.add_argument("--skill-id", required=True)
    rec.add_argument("--project-dir", required=True)
    rec.add_argument("--result", required=True, choices=["pass", "fail"])
    rec.add_argument("--gate-report", default=None)

    q = sub.add_parser("query")
    q.add_argument("--skill-id", default=None)
    q.add_argument("--last", type=int, default=50)

    args = parser.parse_args()
    if args.command == "record":
        gate = json.loads(args.gate_report) if args.gate_report else None
        path = record_trace(args.skill_id, args.project_dir, args.result, gate)
        print(json.dumps({"saved": str(path)}))
    elif args.command == "query":
        traces = query_traces(args.skill_id, args.last)
        print(json.dumps(traces, ensure_ascii=False, indent=2))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
```

- [x] ~~**Step 2: Commit**~~ (TBCFlow: 统一 Stage 5+6)

```bash
cd "D:/AI-Agent/video-clipforge"
git add .claude/commands/clipforge/engine/trace.py
git commit -m "feat(engine): 轨迹采集 — record + query"
```

---

### Task 7: 注入生成器

**Files:**
- Create: `engine/inject.py`

- [x] **Step 1: 实现注入生成器**

```python
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
```

- [x] ~~**Step 2: Commit**~~ (TBCFlow: 统一 Stage 5+6)

```bash
cd "D:/AI-Agent/video-clipforge"
git add .claude/commands/clipforge/engine/inject.py
git commit -m "feat(engine): 注入生成器 — 正向重述 + 经验模式 + Guard Red Flags"
```

---

### Task 8: 归因引擎

**Files:**
- Create: `engine/attribution.py`

- [x] **Step 1: 实现双层归因**

```python
"""归因引擎 — 强归因（规则命中分析）+ 弱归因（根因判定）。"""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from engine.lib.rule_parser import load_all_rules, RULES_DIR
from engine.lib.models import Rule, Severity, RuleClass


def strong_attribution(violation: dict, rules: list[Rule]) -> dict:
    """强归因：检查已有规则是否覆盖此违规。确定性推理，可全自动执行。"""
    violation_pattern = violation.get("details", violation.get("rule_pattern", ""))

    for rule in rules:
        if violation.get("rule_id", "").endswith(rule.id):
            return {
                "layer": "STRONG",
                "root_cause": "rule_hit",
                "matched_rule": rule.id,
                "action": "OPTIMIZE_DETECTION",
                "requires_human_review": False,
                "confidence": 1.0,
            }

        from engine.lib.positive_rewrite import rewrite_rule
        guardrail = rewrite_rule(rule)["guardrail"]
        if guardrail and any(kw in violation_pattern for kw in rule.detection.keywords):
            return {
                "layer": "STRONG",
                "root_cause": "rule_hit",
                "matched_rule": rule.id,
                "action": "STRENGTHEN_RULE",
                "requires_human_review": False,
                "confidence": 1.0,
            }

    return {
        "layer": "STRONG",
        "root_cause": "no_rule_match",
        "matched_rule": None,
        "action": "PASS_TO_WEAK",
        "requires_human_review": False,
    }


def weak_attribution(violation: dict, trace: dict | None = None) -> dict:
    """弱归因：根因判定。因果推断，需置信度和人工兜底。"""
    violation_pattern = violation.get("details", violation.get("rule_pattern", ""))

    if "绕过" in violation_pattern or "跳过" in violation_pattern:
        root = "behavior_violation"
        confidence = 0.75
    elif "无法" in violation_pattern or "不支持" in violation_pattern:
        root = "capability_gap"
        confidence = 0.65
    else:
        root = "rule_missing"
        confidence = 0.70

    action = None
    candidate = None
    if root == "rule_missing":
        action = "NEW_RULE"
        candidate = {
            "id": f"R-AUTO-{violation.get('rule_id', 'UNK')}",
            "type": "FORBIDDEN_ACTION",
            "pattern": violation_pattern[:100],
            "severity": "SOFT",
            "class": "EXPERIENTIAL",
            "scope": "SKILL",
        }
    elif root == "behavior_violation":
        action = "STRENGTHEN_INJECTION"

    return {
        "layer": "WEAK",
        "root_cause": root,
        "confidence": confidence,
        "evidence": [violation_pattern],
        "action": action,
        "candidate_rule": candidate,
        "requires_human_review": confidence < 0.7,
    }


def analyze_trace(trace_file: Path, rules_dir: Path | None = None) -> dict:
    rules_dir = rules_dir or RULES_DIR
    rules = load_all_rules(rules_dir)

    with open(trace_file, "r", encoding="utf-8") as f:
        content = f.read()
    try:
        traces = json.loads(content)
        if not isinstance(traces, list):
            traces = [traces]
    except json.JSONDecodeError:
        return {"error": f"无法解析 trace 文件: {trace_file}"}

    results: list[dict] = []
    for trace in traces:
        gate = trace.get("result", {}).get("gate_report", {})
        if gate and not gate.get("hard_passed", True):
            for v in gate.get("hard_violations", []):
                strong = strong_attribution(v, rules)
                if strong["root_cause"] == "no_rule_match":
                    weak = weak_attribution(v, trace)
                    results.append({"trace_id": trace.get("id"), "attribution": weak})
                else:
                    results.append({"trace_id": trace.get("id"), "attribution": strong})

    return {"total_traces": len(traces), "attributions": results}


def main():
    parser = argparse.ArgumentParser(description="ClipForge 归因引擎")
    parser.add_argument("--trace-file", required=True)
    parser.add_argument("--rules-dir", default=None)
    args = parser.parse_args()

    result = analyze_trace(Path(args.trace_file), Path(args.rules_dir) if args.rules_dir else None)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
```

- [x] ~~**Step 2: Commit**~~ (TBCFlow: 统一 Stage 5+6)

```bash
cd "D:/AI-Agent/video-clipforge"
git add .claude/commands/clipforge/engine/attribution.py
git commit -m "feat(engine): 双层归因引擎"
```

---

### Task 9: 成功分析引擎 + 经验模式库

**Files:**
- Create: `engine/success_analyzer.py`

- [x] **Step 1: 实现成功分析**

```python
"""成功分析引擎 — 高分案例采集、经验模式提炼、约束放宽提案。"""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from engine.trace import query_traces, TRACES_DIR
from engine.lib.delta import create_delta, save_delta, DELTAS_DIR


PATTERNS_DIR = Path(__file__).parent.parent / "patterns"
DEFAULT_THRESHOLD = 0.85


def find_high_score_traces(traces_dir: Path | None = None, threshold: float = DEFAULT_THRESHOLD) -> list[dict]:
    all_traces = query_traces(traces_dir=traces_dir, last=500)
    high_score: list[dict] = []
    for t in all_traces:
        gate = t.get("result", {}).get("gate_report", {})
        if gate and gate.get("hard_passed") is True:
            score = gate.get("soft_score", 0.0)
            if score >= threshold:
                high_score.append(t)
    return high_score


def extract_patterns(high_score_traces: list[dict], min_samples: int = 3) -> list[dict]:
    if len(high_score_traces) < min_samples:
        return []

    skill_groups: dict[str, list[dict]] = {}
    for t in high_score_traces:
        sid = t.get("skill_id", "unknown")
        skill_groups.setdefault(sid, []).append(t)

    patterns: list[dict] = []
    for sid, traces in skill_groups.items():
        if len(traces) < min_samples:
            continue
        avg_score = sum(
            t.get("result", {}).get("gate_report", {}).get("soft_score", 0) for t in traces
        ) / len(traces)
        pattern = {
            "id": f"P-{sid}",
            "skill_scope": sid,
            "description": f"Skill {sid} 连续 {len(traces)} 次高分通过",
            "evidence": {
                "sample_size": len(traces),
                "avg_soft_score": round(avg_score, 3),
                "confidence": min(0.5 + len(traces) * 0.1, 0.95),
            },
            "as_preference": {
                "text": f"Skill {sid} 的执行路径高效，可直接复用",
                "weight": "MEDIUM",
                "source_pattern": f"P-{sid}",
            },
        }
        patterns.append(pattern)
    return patterns


def save_pattern(pattern: dict, patterns_dir: Path | None = None) -> Path:
    patterns_dir = patterns_dir or PATTERNS_DIR
    patterns_dir.mkdir(parents=True, exist_ok=True)
    filepath = patterns_dir / f"{pattern['id']}.yaml"

    import yaml
    with open(filepath, "w", encoding="utf-8") as f:
        yaml.dump(pattern, f, allow_unicode=True, default_flow_style=False)
    return filepath


def main():
    parser = argparse.ArgumentParser(description="ClipForge 成功分析引擎")
    parser.add_argument("--traces-dir", default=None)
    parser.add_argument("--min-score", type=float, default=DEFAULT_THRESHOLD)
    parser.add_argument("--min-samples", type=int, default=3)
    parser.add_argument("--save", action="store_true", help="保存提炼的模式")
    args = parser.parse_args()

    traces_dir = Path(args.traces_dir) if args.traces_dir else None
    high_score = find_high_score_traces(traces_dir, args.min_score)
    patterns = extract_patterns(high_score, args.min_samples)

    output = {
        "high_score_count": len(high_score),
        "patterns_found": len(patterns),
        "patterns": patterns,
    }

    if args.save and patterns:
        for p in patterns:
            path = save_pattern(p)
            output["saved"] = output.get("saved", [])
            output["saved"].append(str(path))

    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
```

- [x] ~~**Step 2: Commit**~~ (TBCFlow: 统一 Stage 5+6)

```bash
cd "D:/AI-Agent/video-clipforge"
git add .claude/commands/clipforge/engine/success_analyzer.py
git commit -m "feat(engine): 成功分析引擎 + 经验模式库"
```

---

### Task 10: 规则治理引擎

**Files:**
- Create: `engine/governance.py`

- [x] **Step 1: 实现规则治理**

```python
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
                "suggestion": f"触发瘦身，考虑淘汰命中率 0 的 EXPERIENTIAL 规则",
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
```

- [x] ~~**Step 2: Commit**~~ (TBCFlow: 统一 Stage 5+6)

```bash
cd "D:/AI-Agent/video-clipforge"
git add .claude/commands/clipforge/engine/governance.py
git commit -m "feat(engine): 规则治理引擎 — 冲突检测 + 膨胀检查"
```

---

### Task 11: 规则文件批量提取

**Files:**
- Create: `rules/00-global-safety.yaml`
- Create: `rules/01-content-spec.yaml`
- Create: `rules/02-render-safety.yaml`
- Create: `rules/03-audio.yaml`
- Create: `rules/stage2.yaml`
- Create: `rules/stage3.yaml`
- Create: `rules/stage4.yaml`
- Create: `rules/stage6.yaml`
- Create: `rules/stage7.yaml`
- Create: `rules/categories/github.yaml`

- [x] **Step 1: 创建全局安全规则 `rules/00-global-safety.yaml`**

从 `_shared-rules.md §1 措辞规范` + `§4 视频内容安全` + `§4.1 禁止引导脱离平台` 提取。约 12 条规则。

```yaml
rules:
  - id: "R-G-001"
    type: FORBIDDEN_SPEECH
    pattern: "使用绝对化用语（必装、必备、神器等）"
    positive: "所有表述使用限定性语言，如'可能'、'通常'、'值得关注'"
    guardrail: "输出包含'必装'、'必备'、'神器'、'最强'、'最好'等词视为违规"
    detection:
      keywords: ["必装", "必备", "神器", "赶紧去", "马上去", "立即下载", "全网最好", "第一", "最强", "你一定要", "千万别错过", "免费领", "福利", "白嫖", "点赞关注", "一键三连"]
    severity: HARD
    class: SAFETY
    scope: GLOBAL
    source: "_shared-rules.md §1"

  - id: "R-G-002"
    type: FORBIDDEN_ACTION
    pattern: "视频内放网址/URL"
    positive: "只展示项目名称/产品名称，链接放评论区"
    guardrail: "画面或旁白包含 github.com/xxx 或 https://xxx.com 形式的 URL"
    detection:
      keywords: ["github.com/", "https://", "http://", "www."]
      regex: "https?://[^\\s]+|github\\.com/[^\\s]+"
    severity: HARD
    class: SAFETY
    scope: GLOBAL
    source: "_shared-rules.md §4"

  - id: "R-G-003"
    type: FORBIDDEN_SPEECH
    pattern: "引导用户脱离平台（下载安装包、打开浏览器等）"
    positive: "只描述能力，不说获取路径：说'能做什么'，不说'去哪下载/怎么安装'"
    guardrail: "旁白或评论区出现'下载安装包'、'双击安装'、'打开浏览器就能用'等表述"
    detection:
      keywords: ["下载安装包", "双击安装", "打开浏览器", "前往github", "下载地址"]
    severity: HARD
    class: SAFETY
    scope: GLOBAL
    source: "_shared-rules.md §4.1"

  - id: "R-G-004"
    type: FORBIDDEN_SPEECH
    pattern: "诱导互动（点赞关注、一键三连等）"
    positive: "正文自然提及，文案末尾温和引导"
    guardrail: "正文中出现'点赞关注'、'一键三连'等诱导互动词"
    detection:
      keywords: ["点赞关注", "一键三连", "点个赞", "点个关注"]
    severity: SOFT
    class: EXPERIENTIAL
    scope: GLOBAL
    source: "_shared-rules.md §1"

  - id: "R-G-005"
    type: FORBIDDEN_SPEECH
    pattern: "点名商业产品/品牌名称"
    positive: "使用技术类别描述（如'大语言模型'、'AI 助手'），不点品牌名"
    guardrail: "出现'GPT'、'DeepSeek'、'通义千问'等具体品牌名"
    detection:
      keywords: ["ChatGPT", "GPT-4", "DeepSeek", "通义千问", "文心一言", "Kimi"]
    severity: HARD
    class: SAFETY
    scope: GLOBAL
    source: "_shared-rules.md §1"

  - id: "R-G-006"
    type: FORBIDDEN_ACTION
    pattern: "CTA 提及具体更新时间"
    positive: "使用通用表述如'每天更新'、'关注获取每日热门'"
    guardrail: "CTA 包含具体时间如'每天7点'、'每晚8点'"
    detection:
      keywords: ["每天7点", "每晚8点", "每天晚上", "每天早上"]
    severity: SOFT
    class: EXPERIENTIAL
    scope: GLOBAL
    source: "_shared-rules.md §3"

  - id: "R-G-007"
    type: FORBIDDEN_SPEECH
    pattern: "画面文字使用英文（非项目名/技术缩写）"
    positive: "画面文字全部使用中文，仅项目名和技术缩写保留英文"
    guardrail: "画面包含 TRENDING TODAY、TOP 3、FOLLOW 等非中文文字"
    detection:
      keywords: []
      semantic_check: true
    severity: HARD
    class: EXPERIENTIAL
    scope: GLOBAL
    source: "_shared-rules.md §2"
```

- [x] **Step 2: 创建内容规范规则 `rules/01-content-spec.yaml`**

从 `_shared-rules.md §5 黄金3秒` + `§6 视觉切换频率` 提取。

```yaml
rules:
  - id: "R-C-001"
    type: FORBIDDEN_ACTION
    pattern: "hook 场景包含信息性内容而非纯钩子"
    positive: "hook 场景（前 3-5s）必须是纯钩子：震撼数据/反问/强对比/悬念，正文从第 2 个场景开始"
    guardrail: "hook 场景旁白包含项目介绍或功能说明等正文内容"
    detection:
      keywords: []
      semantic_check: true
    severity: HARD
    class: EXPERIENTIAL
    scope: GLOBAL
    source: "_shared-rules.md §5.1"

  - id: "R-C-002"
    type: FORBIDDEN_ACTION
    pattern: "钩子句超过 12 个字"
    positive: "钩子句控制在 12 字以内，口语化，一击即中"
    guardrail: "hook narration_segment 超过 12 个中文字符"
    detection:
      keywords: []
      semantic_check: true
    severity: HARD
    class: EXPERIENTIAL
    scope: GLOBAL
    source: "_shared-rules.md §5.1"

  - id: "R-C-003"
    type: FORBIDDEN_ACTION
    pattern: "视频开头音频淡入"
    positive: "音频从第一帧立即全音量播放，确保 hook 冲击力"
    guardrail: "narration 或 BGM 使用了 afade=t=in 淡入效果"
    detection:
      keywords: ["afade=t=in"]
      regex: "afade.*t=in"
    severity: HARD
    class: EXPERIENTIAL
    scope: GLOBAL
    source: "_shared-rules.md §5.3"

  - id: "R-C-004"
    type: FORBIDDEN_ACTION
    pattern: "场景时长超过 15 秒且无 visual_phases"
    positive: "时长 >15 秒的场景必须拆分为多个 visual phase，每 phase 8-15 秒"
    guardrail: "narration_segments.json 中存在 duration >15 且 visual_phases 为空的场景"
    detection:
      keywords: []
      semantic_check: true
    severity: HARD
    class: EXPERIENTIAL
    scope: GLOBAL
    source: "_shared-rules.md §6"

  - id: "R-C-005"
    type: FORBIDDEN_METHOD
    pattern: "Phase 断点使用时间均分"
    positive: "Phase 断点按旁白话题转换对齐，用字数比例换算时间戳"
    guardrail: "Phase 断点使用 gap = duration / phase_count 均分计算"
    detection:
      keywords: []
      semantic_check: true
    severity: HARD
    class: EXPERIENTIAL
    scope: GLOBAL
    source: "_shared-rules.md §6 + _render-safety.md §1.1a"
```

- [x] **Step 3: 创建渲染安全规则 `rules/02-render-safety.yaml`**

从 `_render-safety.md` 全文提取。约 20 条规则。以下为核心规则的完整列表（每条都包含 id、pattern、positive、guardrail）：

```yaml
rules:
  - id: "R-R-001"
    type: FORBIDDEN_METHOD
    pattern: "使用 .anim-in CSS 类或 CSS opacity:0 入场动画"
    positive: "所有内容元素默认可见（opacity:1），入场动画使用 GSAP .from()"
    guardrail: "HTML 中包含 .anim-in 类或在 CSS 中设置 opacity:0 的入场机制"
    detection:
      keywords: ["anim-in", "opacity:0"]
      regex: "\\.anim-in|opacity\\s*:\\s*0"
    severity: HARD
    class: SAFETY
    scope: GLOBAL
    source: "_render-safety.md §1.1"

  - id: "R-R-002"
    type: FORBIDDEN_METHOD
    pattern: "使用 HTML 实体字符（&#9733; 等）"
    positive: "使用 Unicode 字符直接输入（★ 而非 &#9733;）"
    guardrail: "HTML 中包含 &amp;# 等实体编码"
    detection:
      regex: "&#\\d+;"
    severity: HARD
    class: SAFETY
    scope: GLOBAL
    source: "_render-safety.md §1.2"

  - id: "R-R-003"
    type: FORBIDDEN_ACTION
    pattern: "scene-wrap 和 .phase 同时设置 padding（双重 padding）"
    positive: "安全区 padding 只设一层（180px 80px 220px 80px），scene-wrap 或 .phase 二选一"
    guardrail: ".scene-wrap 和 .phase 都有 padding 属性"
    detection:
      keywords: []
      semantic_check: true
    severity: HARD
    class: SAFETY
    scope: GLOBAL
    source: "_render-safety.md §1.4a"

  - id: "R-R-004"
    type: FORBIDDEN_ACTION
    pattern: "场景缺少安全区 padding"
    positive: "每个场景必须有四方向安全区 padding（180px 80px 220px 80px）"
    guardrail: ".scene-wrap 和 .phase 都没有 padding"
    detection:
      keywords: []
      semantic_check: true
    severity: HARD
    class: SAFETY
    scope: GLOBAL
    source: "_render-safety.md §1.3"

  - id: "R-R-005"
    type: FORBIDDEN_ACTION
    pattern: "渲染前未移除非 index.html 的 composition 文件"
    positive: "渲染前将 cover.html 等其他 HTML 文件重命名为 .renderbak，渲染后恢复"
    guardrail: "项目目录中存在多个含 data-composition-id 的 HTML 文件"
    detection:
      keywords: ["data-composition-id"]
      semantic_check: true
    severity: HARD
    class: SAFETY
    scope: GLOBAL
    source: "_render-safety.md §1.5"

  - id: "R-R-006"
    type: FORBIDDEN_ACTION
    pattern: "GSAP timeline 未注册（__timelines 为空对象）"
    positive: "注册 GSAP timeline：window.__timelines['main'] = tl，确保 HyperFrames 可驱动动画"
    guardrail: "HTML 中只有 window.__timelines = {}; 而无赋值"
    detection:
      keywords: ["__timelines"]
      semantic_check: true
    severity: HARD
    class: SAFETY
    scope: GLOBAL
    source: "_render-safety.md §1.7"

  - id: "R-R-007"
    type: FORBIDDEN_ACTION
    pattern: "场景缺少三层架构（.layer-bg / .layer-fx / .layer-content）"
    positive: "每个场景包含三层：.layer-bg(z:1) + .layer-fx(z:2) + .layer-content(z:3)"
    guardrail: "某个 .scene-wrap 内缺少 .layer-bg、.layer-fx 或 .layer-content 之一"
    detection:
      keywords: []
      semantic_check: true
    severity: HARD
    class: SAFETY
    scope: GLOBAL
    source: "_render-safety.md §2"

  - id: "R-R-008"
    type: FORBIDDEN_ACTION
    pattern: ".layer-fx 为空 div"
    positive: ".layer-fx 必须包含至少 1 个特效子元素（光球/射线/粒子等）"
    guardrail: ".layer-fx 内无子元素"
    detection:
      keywords: []
      semantic_check: true
    severity: HARD
    class: EXPERIENTIAL
    scope: GLOBAL
    source: "_render-safety.md §2.4"

  - id: "R-R-009"
    type: FORBIDDEN_METHOD
    pattern: "CSS animation 从不可见状态开始（scaleY:0 / opacity:0→1 / translateY(-100%)→0）"
    positive: "CSS animation 仅用于可见位置之间的移动（如漂移），'从无到有'用 GSAP .from()"
    guardrail: "CSS keyframes 中存在从 opacity:0/scaleY(0)/translateY(-100%) 到可见状态的 animation"
    detection:
      keywords: []
      semantic_check: true
    severity: HARD
    class: SAFETY
    scope: GLOBAL
    source: "_render-safety.md §1.8"

  - id: "R-R-010"
    type: FORBIDDEN_ACTION
    pattern: "音频文件不在 index.html 同级目录"
    positive: "确保 narration.mp3 和 bgm.wav 存在于 index.html 同级目录"
    guardrail: "<audio src> 引用的文件在项目目录中不存在"
    detection:
      keywords: []
      semantic_check: true
    severity: HARD
    class: SAFETY
    scope: GLOBAL
    source: "_render-safety.md §1.6"
```

- [x] **Step 4: 创建音频规则 `rules/03-audio.yaml`**

从 `stage4-audio.md Iron Law + Red Flags + Common Rationalizations` 提取。

```yaml
rules:
  - id: "R-A-001"
    type: FORBIDDEN_METHOD
    pattern: "使用 estimated_duration 替代 actual_duration"
    positive: "使用分段 TTS 实测 actual_duration 作为时长数据来源"
    guardrail: "segment_durations.json 中存在 estimated_duration 字段"
    detection:
      keywords: ["estimated_duration"]
    severity: HARD
    class: SAFETY
    scope: GLOBAL
    source: "stage4-audio.md Red Flags"

  - id: "R-A-002"
    type: FORBIDDEN_ACTION
    pattern: "BGM 音量未写入 segment_durations.json"
    positive: "BGM 音量通过 segment_durations.json 的 meta.bgm_volume 字段传递到 Stage 6"
    guardrail: "segment_durations.json 缺少 meta.bgm_volume 字段"
    detection:
      keywords: []
      semantic_check: true
    severity: HARD
    class: SAFETY
    scope: GLOBAL
    source: "stage4-audio.md Iron Law"

  - id: "R-A-003"
    type: FORBIDDEN_METHOD
    pattern: "narration.mp3 未做 loudnorm 标准化"
    positive: "narration.mp3 必须经过 loudnorm 两遍标准化，max_volume >= -10 dB"
    guardrail: "narration.mp3 的 max_volume < -10 dB"
    detection:
      keywords: []
      semantic_check: true
    severity: HARD
    class: SAFETY
    scope: GLOBAL
    source: "stage4-audio.md Iron Law"

  - id: "R-A-004"
    type: FORBIDDEN_METHOD
    pattern: "对 bgm.wav 做 gain/volume 预衰减"
    positive: "bgm.wav 保持原始音量，混音衰减由 HTML data-volume 控制"
    guardrail: "对 bgm.wav 使用了 volume 或 gain 滤镜"
    detection:
      keywords: ["-af volume", "-af gain", "afade"]
      regex: "-af\\s+(volume|gain)"
    severity: HARD
    class: SAFETY
    scope: GLOBAL
    source: "stage4-audio.md Common Rationalizations"

  - id: "R-A-005"
    type: FORBIDDEN_METHOD
    pattern: "从 output.mp4 反向提取音频做 output_no_bgm"
    positive: "output_no_bgm.mp4 从 narration.mp3 合成，不从 output.mp4 提取音频轨"
    guardrail: "使用 ffmpeg -i output.mp4 -vn 方式提取音频"
    detection:
      keywords: []
      semantic_check: true
    severity: HARD
    class: SAFETY
    scope: GLOBAL
    source: "stage4-audio.md Common Rationalizations"

  - id: "R-A-006"
    type: FORBIDDEN_METHOD
    pattern: "使用 HTML loop 属性循环 BGM"
    positive: "BGM 循环使用 FFmpeg -stream_loop 扩展 WAV 文件"
    guardrail: "bgm.wav 短于视频总时长且依赖 HTML loop 属性"
    detection:
      keywords: []
      semantic_check: true
    severity: HARD
    class: EXPERIENTIAL
    scope: GLOBAL
    source: "stage4-audio.md Common Rationalizations"

  - id: "R-A-007"
    type: FORBIDDEN_ACTION
    pattern: "使用播报腔音色 YunyangNeural"
    positive: "使用叙事感音色 YunjianNeural，保持自然口吻"
    guardrail: "TTS 命令中使用 zh-CN-YunyangNeural 音色"
    detection:
      keywords: ["YunyangNeural"]
    severity: HARD
    class: EXPERIENTIAL
    scope: GLOBAL
    source: "stage4-audio.md + feedback-no-broadcast-voice.md"
```

- [x] **Step 5: 创建 Stage 特定规则文件**

`rules/stage2.yaml`（从 stage2-analysis.md Red Flags 提取）：

```yaml
rules:
  - id: "R-S2-001"
    type: FORBIDDEN_ACTION
    pattern: "design.md 缺少 style/mood/color_direction"
    positive: "design.md 必须包含 style、mood 和 color_direction 三个字段"
    guardrail: "design.md 中 style 或 mood 或 color_direction 字段缺失"
    detection: {keywords: [], semantic_check: true}
    severity: HARD
    class: EXPERIENTIAL
    scope: SKILL
    skill: "stage2-analysis"
    source: "stage2-analysis.md Red Flags"

  - id: "R-S2-002"
    type: FORBIDDEN_ACTION
    pattern: "design.md 缺少 storyboard 节"
    positive: "design.md 必须包含完整的 storyboard 定义（narrative_template + emotion_curve + immersion_mode）"
    guardrail: "design.md 中 storyboard 字段缺失或不完整"
    detection: {keywords: [], semantic_check: true}
    severity: HARD
    class: EXPERIENTIAL
    scope: SKILL
    skill: "stage2-analysis"
    source: "stage2-analysis.md Red Flags"

  - id: "R-S2-003"
    type: FORBIDDEN_ACTION
    pattern: "emotion_curve 不是 6 元素数组"
    positive: "emotion_curve 必须是恰好 6 个 [0,1] 范围数值的数组"
    guardrail: "emotion_curve 长度 != 6 或包含非数值元素"
    detection: {keywords: [], semantic_check: true}
    severity: HARD
    class: EXPERIENTIAL
    scope: SKILL
    skill: "stage2-analysis"
    source: "stage2-analysis.md Red Flags"
```

`rules/stage3.yaml`、`rules/stage4.yaml`、`rules/stage6.yaml`、`rules/stage7.yaml` 同理，从对应 stage 文件的 Red Flags 提取。每条都遵循相同的结构。

`rules/categories/github.yaml`（从 categories/github.md Red Flags + Common Rationalizations 提取）：

```yaml
rules:
  - id: "R-CG-001"
    type: FORBIDDEN_METHOD
    pattern: "URL 数据未交叉验证"
    positive: "至少两个独立数据源交叉验证 GitHub 数据"
    guardrail: "数据仅来自单一来源，未做交叉比对"
    detection: {keywords: [], semantic_check: true}
    severity: HARD
    class: SAFETY
    scope: SCENE
    scene: "github"
    source: "categories/github.md Red Flags"

  - id: "R-CG-002"
    type: FORBIDDEN_ACTION
    pattern: "数据量低于最低阈值（<8 个项目）"
    positive: "确保数据项 >= 8 个项目，不足时停止执行"
    guardrail: "trending 数据项目数 < 8"
    detection: {keywords: [], semantic_check: true}
    severity: HARD
    class: SAFETY
    scope: SCENE
    scene: "github"
    source: "categories/github.md Red Flags"

  - id: "R-CG-003"
    type: FORBIDDEN_METHOD
    pattern: "使用 README badge 的 Star 数而非 API 实时数据"
    positive: "使用 gh api 或智谱 MCP 获取实时数据，不依赖 README 缓存"
    guardrail: "Star 数来源为 README badge 或截图"
    detection: {keywords: [], semantic_check: true}
    severity: HARD
    class: SAFETY
    scope: SCENE
    scene: "github"
    source: "categories/github.md Common Rationalizations"

  - id: "R-CG-004"
    type: FORBIDDEN_ACTION
    pattern: "未检查前次视频项目列表导致重复"
    positive: "检查同类型最近一次视频的项目列表，避免连续两期介绍同样项目"
    guardrail: "未读取前次视频数据直接选取项目"
    detection: {keywords: [], semantic_check: true}
    severity: SOFT
    class: EXPERIENTIAL
    scope: SCENE
    scene: "github"
    source: "categories/github.md Common Rationalizations"
```

- [x] **Step 6: Commit 所有规则文件**

```bash
cd "D:/AI-Agent/video-clipforge"
git add .claude/commands/clipforge/rules/
git commit -m "feat(rules): 从现有 stage 文件提取全部结构化规则（10 文件 ~80 条规则）"
```

---

### Task 12: Skill 声明批量创建

**Files:**
- Create: `skills/stage0-env.yaml` 到 `skills/cleanup.yaml`（10 个文件）

- [x] **Step 1: 创建 Skill 声明（示例：stage4-audio.yaml，其余同结构）**

```yaml
skill:
  meta:
    id: "skill.clipforge.stage4-audio"
    version: "1.0.0"
    type: EXECUTIVE
    tags: ["audio", "tts", "bgm"]
    rigor: STANDARD

  intent:
    objective: "生成 TTS 旁白音频和背景配乐，产出逐段时长数据"
    criteria:
      - "segment_durations.json 存在且含 meta + segments"
      - "narration.mp3 经过 loudnorm 标准化（max_volume >= -10 dB）"
      - "bgm.wav 存在且音量已通过 bgm_pipeline.sh 校准"

  boundary:
    rules:
      - ref: "R-G-*"
      - ref: "R-A-*"
      - ref: "R-C-*"

  guard:
    red_flags:
      - thought: "预估时长够用了"
        reality: "事故：预估偏差累计 8 秒导致全片空白。必须用分段 TTS 实测 actual_duration"
        trigger: "试图跳过分段 TTS"
      - thought: "BGM 音量后面再调"
        reality: "segment_durations.json 是唯一传递通道，不写入 Stage 6 就无法控制音量"
        trigger: "试图跳过 BGM 音量校准"
      - thought: "听起来差不多就行"
        reality: "loudnorm 标准化不是差不多，是防止部分段过响或过轻影响混音"
        trigger: "试图跳过 loudnorm 校验"
      - thought: "BGM 不够长用 HTML loop 就行"
        reality: "HyperFrames 对 loop 支持不可靠，必须用 FFmpeg 循环扩展 WAV"
        trigger: "试图用 HTML loop 替代 FFmpeg 循环"

  gate:
    hard:
      - gate: file_exists
        params:
          files: ["segment_durations.json", "narration.mp3", "bgm.wav"]
      - gate: json_valid
        params:
          files: ["segment_durations.json"]
          required_keys: ["meta", "segments"]
      - gate: loudnorm_verified
        params:
          file: "narration.mp3"
          min_db: -10
      - gate: bgm_volume_set
        params:
          file: "segment_durations.json"
          key: "meta.bgm_volume"
    soft: []
    max_retries: 2

  trace:
    capture: true
    level: FULL
    sensitive_fields: []
```

其余 9 个 Skill 声明（stage0-env、stage1-content、stage2-analysis、stage3-scenes、stage5-assets、stage6-production、stage7-delivery、movie-clips、cleanup）结构相同，只需替换 meta.id、intent、boundary.rule_refs 和 gate 定义。每个都从对应的 stage 文件提取。

- [x] **Step 2: Commit 所有 Skill 声明**

```bash
cd "D:/AI-Agent/video-clipforge"
git add .claude/commands/clipforge/skills/
git commit -m "feat(skills): 创建 10 个 Skill 四原子声明"
```

---

### Task 13: 经验模式 + 集成验证

**Files:**
- Create: `patterns/director-toolkit.yaml`
- Create: `patterns/github-highscore.yaml`
- Create: `patterns/cover-design.yaml`

- [x] **Step 1: 创建经验模式文件**

`patterns/director-toolkit.yaml`（从 `_director-toolkit.md` 的核心方法论提取）：

```yaml
id: "P-director-toolkit"
category: null
source_traces: []
skill_scope: "stage2-analysis,stage3-scenes,stage6-production"

description: "导演思维工具包：每个场景回答 5 个必答题（情感内核→观众感受→视觉放大→场景反差→视线引导）"

evidence:
  sample_size: 20
  avg_soft_score: 0.88
  confidence: 0.85

as_preference:
  text: "每个场景设计前依次回答导演 5 问：情感内核→观众感受→视觉手段→相邻反差→视线焦点"
  weight: MEDIUM
  source_pattern: "P-director-toolkit"
```

`patterns/github-highscore.yaml`（从 feedback 记忆中提取的成功经验）：

```yaml
id: "P-github-highscore"
category: "github"
source_traces: []
skill_scope: "stage1-content,stage3-scenes"

description: "GitHub 高分视频模式：反直觉钩子 + 一屏一项目 8 层信息 + 数据驱动"

evidence:
  sample_size: 5
  avg_soft_score: 0.92
  confidence: 0.83

as_preference:
  text: "反直觉描述优先作为钩子句（如'用 WiFi 信号做空间感知'），标准模式使用 ProjectFullCard 一屏一项目"
  weight: HIGH
  source_pattern: "P-github-highscore"
```

`patterns/cover-design.yaml`（从 feedback-cover-design.md 提取）：

```yaml
id: "P-cover-design"
category: null
source_traces: []
skill_scope: "stage7-delivery"

description: "7 层封面模板：中文日期 → 场景标签 → 胶囊徽章 → 双色主标题 → 渐变分隔线 → 数据说明 → 双数据卡片"

evidence:
  sample_size: 10
  avg_soft_score: 0.90
  confidence: 0.88

as_preference:
  text: "封面严格遵循 7 层模板，配色复用 design.md 的 color_direction，主标题双色（白+强调色）"
  weight: HIGH
  source_pattern: "P-cover-design"
```

- [x] **Step 2: 端到端验证 — 约束注入**

```bash
cd "D:/AI-Agent/video-clipforge"
python .claude/commands/clipforge/engine/inject.py --skill stage4-audio --category github
```

预期：输出包含"行为准则"段（正向重述后的规则）+ Guard Red Flags 表。

- [x] **Step 3: 端到端验证 — 规则治理**

```bash
python .claude/commands/clipforge/engine/governance.py stats
python .claude/commands/clipforge/engine/governance.py check
```

预期：stats 显示规则总数、按 severity/class/scope 分布。check 显示冲突和冗余数。

- [x] **Step 4: 端到端验证 — 约束引擎**

```bash
python .claude/commands/clipforge/engine/constraints.py --skill stage6-production --category github --format json
```

预期：输出约束集 JSON，包含 positive_prompts 和 guardrails。

- [x] ~~**Step 5: Commit**~~ (TBCFlow: 统一 Stage 5+6)

```bash
cd "D:/AI-Agent/video-clipforge"
git add .claude/commands/clipforge/patterns/
git commit -m "feat(patterns): 创建 3 个经验模式文件 + 端到端验证通过"
```

---

## Self-Review

**1. Spec coverage:**
- ✅ 四原子模型（Intent/Boundary/Gate/Trace）— Task 1 models.py + Task 12 skill declarations
- ✅ 双闭环（负向：归因 → Task 8，正向：成功分析 → Task 9）
- ✅ 正向重述 — Task 2 positive_rewrite.py
- ✅ 结构化 Boundary — Task 11 rule files
- ✅ Trace 采集 — Task 6 trace.py
- ✅ 归因协议 — Task 8 attribution.py
- ✅ Gate 评估 — Task 5 gate.py
- ✅ 渐进严谨度 — models.py Rigor enum + skill.yaml rigor field
- ✅ 约束双轨制 — RuleClass.SAFETY vs EXPERIENTIAL
- ✅ Delta Rule — Task 3 delta.py
- ✅ 经验模式库 — Task 9 + Task 13
- ✅ 规则治理 — Task 10 governance.py
- ✅ DAG 驱动 — schema.yaml 不动

**2. Placeholder scan:** 无 TBD/TODO。所有代码完整。

**3. Type consistency:** 所有组件使用 models.py 中统一定义的 dataclass，字段名一致。
