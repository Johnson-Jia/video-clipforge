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
    REQUIRED_METHOD = "REQUIRED_METHOD"


class Severity(str, Enum):
    HARD = "HARD"
    SOFT = "SOFT"


class RuleClass(str, Enum):
    SAFETY = "SAFETY"
    EXPERIENTIAL = "EXPERIENTIAL"
    QUALITY = "QUALITY"


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
    bg_visual_diversity = "bg_visual_diversity"
    adjacent_bg_diversity = "adjacent_bg_diversity"
    fx_layer_not_empty = "fx_layer_not_empty"
    video_bitrate_valid = "video_bitrate_valid"
    safezone_rendered = "safezone_rendered"
    html_no_css_visibility = "html_no_css_visibility"
    cover_layers_present = "cover_layers_present"
    bgm_silence_valid = "bgm_silence_valid"
    data_duration_source_valid = "data_duration_source_valid"
    estimation_accuracy_valid = "estimation_accuracy_valid"
    fx_animation_present = "fx_animation_present"
    root_attributes_complete = "root_attributes_complete"
    portrait_typography_valid = "portrait_typography_valid"
    phase_timings_valid = "phase_timings_valid"
    phase_anchor_coverage = "phase_anchor_coverage"
    douyin_platforms_complete = "douyin_platforms_complete"
    bgm_not_exceeds_narration = "bgm_not_exceeds_narration"
    final_duration_close_to_output = "final_duration_close_to_output"
    orientation_consistency = "orientation_consistency"
    narration_sample_rate_valid = "narration_sample_rate_valid"
    bgm_volume_provenance_valid = "bgm_volume_provenance_valid"
    bgm_volume_table_valid = "bgm_volume_table_valid"
    grad_text_shorthand_valid = "grad_text_shorthand_valid"
    phase_visibility_present = "phase_visibility_present"
    design_storyboard_valid = "design_storyboard_valid"
    no_real_person_name = "no_real_person_name"
    no_school_name = "no_school_name"
    no_competitor_attack = "no_competitor_attack"
    narration_translation_pattern = "narration_translation_pattern"  # SOFT: 翻译腔套路句（不是X而是Y）
    narration_emotion_type_valid = "narration_emotion_type_valid"  # SOFT: emotion 必 str 名（防 float 致 auto_evolve dominant 崩）
    no_search_cta = "no_search_cta"
    gradient_text_no_dark_shadow = "gradient_text_no_dark_shadow"
    no_scene_wrap = "no_scene_wrap"
    gsap_pattern = "gsap_pattern"
    no_global_text_shadow = "no_global_text_shadow"
    pre_render_deps = "pre_render_deps"
    html_structure_valid = "html_structure_valid"
    output_media_valid = "output_media_valid"
    bgm_isolation_valid = "bgm_isolation_valid"
    visual_phases_completeness = "visual_phases_completeness"
    safe_area_bounds = "safe_area_bounds"
    narration_audio_embedded = "narration_audio_embedded"
    delayed_animation_init = "delayed_animation_init"
    assemble_final_verified = "assemble_final_verified"
    bgm_pipeline_verified = "bgm_pipeline_verified"
    bg_component_source = "bg_component_source"
    description_fidelity_valid = "description_fidelity_valid"
    font_consistency = "font_consistency"
    list_alignment_valid = "list_alignment_valid"


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



class Platform(str, Enum):
    DOUYIN = "douyin"
    WECHAT_VIDEO = "wechat_video"
    XIAOHONGSHU = "xiaohongshu"
    BILIBILI = "bilibili"
    TOUTIAO = "toutiao"


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


# ═══════════════════════════════════════════════════════════════════════
# Creative Execution Engine — 骨架 + 创意插槽数据模型
# ═══════════════════════════════════════════════════════════════════════


@dataclass
class CreativeSlot:
    """骨架中的创意插槽 — LLM 在此注入自由创作的 CSS/HTML/GSAP 代码。

    每个插槽只是 HTML 注释标记（注入点），不是容器边界。
    LLM 可以往里面塞任意数量的子元素（多层渐变叠加、多个特效组合等）。
    """
    slot_id: str           # 格式: "{scene_id}-{layer}-{type}" 如 "s1-bg-html"
    scene_id: str          # 场景 ID，如 "s1"
    layer: str             # bg / fx / content / all
    slot_type: str         # css / html / gsap
    marker: str            # HTML 注释标记，如 "<!-- CREATIVE_SLOT:s1-bg-html -->"

    # ── 本场景上下文 ──
    scene_duration: float = 0.0
    emotion_tags: list[str] = field(default_factory=list)
    visual_intent: dict = field(default_factory=dict)
    narration_text: str = ""

    # ── 视觉节奏上下文（解决"不单调、不突兀"） ──

    # emotion_curve 位置（0.0~1.0）
    emotion_curve_position: float = 0.0
    # 情感强度值
    emotion_intensity: float = 0.5

    # 前序场景视觉指纹
    prev_scene_summary: dict = field(default_factory=dict)
    # 后续场景视觉指纹
    next_scene_summary: dict = field(default_factory=dict)

    # 全片视觉主题
    visual_theme: dict = field(default_factory=dict)
    # 节奏引导文字
    rhythm_guidance: str = ""

    # ── Phase 元数据（告知 LLM 该插槽属于多 phase 场景） ──
    has_multiple_phases: bool = False
    phase_breakpoints: list[float] = field(default_factory=list)

    # 可选：组件库参考
    suggested_components: list[str] = field(default_factory=list)


@dataclass
class SceneSkeleton:
    """单个场景的骨架数据。"""
    scene_id: str          # s1, s2, ...
    scene_name: str        # s1-hook, s2-top1, ...
    start: float           # data-start 秒
    duration: float        # data-duration 秒
    visual_phases: list[dict] = field(default_factory=list)
    phase_breakpoints: list[float] = field(default_factory=list)
    slots: list[CreativeSlot] = field(default_factory=list)
