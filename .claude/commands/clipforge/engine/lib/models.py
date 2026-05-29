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
    hook_pattern_verified = "hook_pattern_verified"
    hf_api_present = "hf_api_present"
    scene_ids_match = "scene_ids_match"
    composition_structure = "composition_structure"
    output_no_bgm_valid = "output_no_bgm_valid"
    bgm_duration_covers = "bgm_duration_covers"


class Rigor(str, Enum):
    LITE = "LITE"
    STANDARD = "STANDARD"
    STRICT = "STRICT"


class CaptureLevel(str, Enum):
    FULL = "FULL"
    SUMMARY = "SUMMARY"
    NONE = "NONE"


class SpiritMode(str, Enum):
    SPIRIT = "SPIRIT"
    LETTER = "LETTER"


class DeltaOperation(str, Enum):
    ADDED = "ADDED"
    MODIFIED = "MODIFIED"
    REMOVED = "REMOVED"
    DEPRECATED = "DEPRECATED"


class Platform(str, Enum):
    DOUYIN = "douyin"
    WECHAT_VIDEO = "wechat_video"
    XIAOHONGSHU = "xiaohongshu"
    BILIBILI = "bilibili"


@dataclass
class PerformanceRecord:
    """发布后播放数据 — 播放数据接入双闭环的基础数据结构。"""
    platform: Platform
    title: str = ""
    plays: int = 0
    completion_rate: float = 0.0
    completion_5s_rate: float = 0.0
    cover_ctr: float = 0.0
    share_rate: float = 0.0
    save_rate: float = 0.0
    like_rate: float = 0.0
    comment_rate: float = 0.0
    follow_count: int = 0
    avg_watch_duration: float = 0.0
    hook_type: str = ""
    topic: str = ""
    duration_seconds: float = 0.0

    @property
    def is_high_performance(self) -> bool:
        if self.platform == Platform.DOUYIN:
            return self.completion_5s_rate >= 0.44
        if self.platform == Platform.WECHAT_VIDEO:
            return self.share_rate >= 0.04
        if self.platform == Platform.XIAOHONGSHU:
            return self.save_rate > self.like_rate * 1.5
        return self.plays > 0


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
class Preference:
    text: str
    weight: str = "MEDIUM"  # LOW / MEDIUM / HIGH
    source_pattern: str | None = None


@dataclass
class SpiritLetterEntry:
    rule_ref: str
    mode: SpiritMode = SpiritMode.SPIRIT
    intent: str = ""


@dataclass
class SkillBoundary:
    scene: str | None = None
    rule_refs: list[str] = field(default_factory=list)
    preferences: list[Preference] = field(default_factory=list)


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
    spirit_vs_letter: list[SpiritLetterEntry] = field(default_factory=list)

    @property
    def skill_id(self) -> str:
        return self.meta.id

    @property
    def rigor_level(self) -> Rigor:
        return self.meta.rigor


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
    performance: dict[str, Any] | None = None
