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
