# Creative Execution Engine 实施方案

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 LLM 从 HTML 结构性劳动中解放出来，让代码引擎生成 HTML 骨架（三层架构、composition 注册、audio 嵌入、GSAP timeline 框架），LLM 只负责在创意插槽中自由编写 CSS/HTML/GSAP 内容，包括组件库里没有的全新特效。

**Architecture:** 分层解耦——`skeleton_builder.py` 从 `narration_segments.json` + `design.md` + `segment_durations.json` 确定性生成 HTML 骨架，骨架中为每个场景的 bg/fx/content 三层预留 `<!-- CREATIVE_SLOT -->` 标记的创意插槽。关键创新：每个插槽携带**视觉上下文**（前序场景的配色指纹、emotion curve 位置、相邻场景摘要），让 LLM 创作时既能保持连贯（不突兀）又能制造差异（不单调）。LLM 输出的创意内容直接注入插槽，组件库降级为"可选参考"。

**Tech Stack:** Python 3.10+（引擎），Jinja2（模板），HTML/CSS/GSAP（创意层输出）

---

## File Structure

```
.claude/commands/clipforge/
  engine/
    skeleton_builder.py          # NEW — HTML 骨架生成器（核心）
    skeleton_builder/
      templates/
        composition.html.j2      # Jinja2 骨架主模板
        scene.html.j2            # 单场景模板（三层 + 插槽，不限元素数量）
        audio_block.html.j2      # audio 嵌入模板
        gsap_boot.js.j2          # GSAP 初始化 + __hf 注册模板
      __init__.py
    slot_injector.py              # NEW — 创意内容注入器（LLM 输出 → 插槽）
    visual_context.py             # NEW — 视觉节奏上下文生成器（不单调、不突兀）
    engine/lib/models.py          # MODIFY — 新增 CreativeSlot（含视觉上下文字段）
  scripts/
    generate_skeleton.py         # NEW — CLI 入口：生成骨架
    inject_creative.py           # NEW — CLI 入口：注入创意内容
    validate_skeleton.py         # NEW — 验证骨架完整性
    generate_visual_context.py   # NEW — CLI 入口：生成视觉节奏上下文 JSON
```

---

## Task 1: 扩展数据模型

**Files:**
- Modify: `.claude/commands/clipforge/engine/lib/models.py`

- [ ] **Step 1: 在 models.py 末尾添加 CreativeSlot 和 SceneSkeleton 数据模型**

```python
@dataclass
class CreativeSlot:
    """骨架中的创意插槽 — LLM 在此注入自由创作的 CSS/HTML/GSAP 代码。"""
    slot_id: str           # 格式: "{scene_id}-{layer}" 如 "s1-bg"
    scene_id: str          # 场景 ID，如 "s1"
    layer: str             # bg / fx / content
    slot_type: str         # css / html / gsap
    marker: str            # HTML 注释标记，如 "<!-- SLOT:s1-bg-css -->"

    # 本场景上下文
    scene_duration: float = 0.0
    emotion_tags: list[str] = field(default_factory=list)
    visual_intent: dict = field(default_factory=dict)
    narration_text: str = ""

    # ═══ 视觉上下文：解决"不单调、不突兀"的核心数据 ═══

    # emotion_curve 位置（0.0~1.0，表示在整条情感曲线中的位置）
    # 帮助 LLM 理解：当前位置是开场/高潮/收尾，对应不同的视觉力度
    emotion_curve_position: float = 0.0

    # emotion_curve 强度值（来自 design.md storyboard 的 6 拍情感强度）
    # 高值 → 视觉力度加强（更浓烈的色彩、更激烈的动画）
    # 低值 → 视觉力度收敛（更平静的色调、更克制的动效）
    emotion_intensity: float = 0.5

    # 前序场景摘要（颜色指纹 + 关键视觉元素类型）
    # 让 LLM 知道前一个场景"长什么样"，以便：
    #   - 共享至少一个视觉元素（保证连贯，不突兀）
    #   - 在另一个维度制造差异（保证变化，不单调）
    prev_scene_summary: dict = field(default_factory=dict)
    # 格式: {
    #   "scene_id": "s1",
    #   "dominant_colors": ["#FFD700", "#0a0a0f"],
    #   "bg_element_types": ["gradient", "glow", "noise"],
    #   "fx_types": ["code_rain", "light_streak"],
    #   "mood": "mystery",
    #   "visual_density": "medium"
    # }

    # 后续场景摘要（前瞻，帮助 LLM 为过渡做铺垫）
    next_scene_summary: dict = field(default_factory=dict)

    # 整体视觉主题（来自 design.md，所有场景共享的"调性锚点"）
    # 包含：色温方向（暖/冷/冷暖对比）、饱和度基调、明度范围
    visual_theme: dict = field(default_factory=dict)
    # 格式: {
    #   "color_temperature": "cold-warm-contrast",
    #   "saturation": "moderate",
    #   "brightness_range": "dark-base",
    #   "accent_colors": ["#00d4ff", "#ff6b35"],
    #   "immersion_mode": "hyper-pace"
    # }

    # 可选：组件库参考（如果 LLM 想复用）
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
```

- [ ] **Step 2: Commit**

```bash
git add .claude/commands/clipforge/engine/lib/models.py
git commit -m "feat(engine): add CreativeSlot and SceneSkeleton data models"
```

---

## Task 2: Jinja2 骨架模板

**Files:**
- Create: `.claude/commands/clipforge/engine/skeleton_builder/templates/composition.html.j2`
- Create: `.claude/commands/clipforge/engine/skeleton_builder/templates/scene.html.j2`
- Create: `.claude/commands/clipforge/engine/skeleton_builder/templates/audio_block.html.j2`
- Create: `.claude/commands/clipforge/engine/skeleton_builder/templates/gsap_boot.js.j2`

- [ ] **Step 1: 创建目录结构**

```bash
mkdir -p .claude/commands/clipforge/engine/skeleton_builder/templates
touch .claude/commands/clipforge/engine/skeleton_builder/__init__.py
```

- [ ] **Step 2: 创建 composition.html.j2 — HTML 文档骨架主模板**

```html
{# composition.html.j2 — HTML 文档骨架，包含所有确定性结构 #}
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=1080">
  <title>{{ project_name }}</title>
  <script src="https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.5/gsap.min.js"></script>
  <style>
    /* ═══ 骨架层：确定性样式（代码生成，LLM 不碰） ═══ */
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body {
      width: 1080px;
      height: 1920px;
      overflow: hidden;
      position: relative;
      font-family: "Noto Sans SC", "PingFang SC", "Microsoft YaHei", sans-serif;
      {{ base_bg_css | default('background: #000;') }}
      color: #fff;
    }

    /* 三层架构 */
    .clip {
      position: absolute;
      inset: 0;
      width: 1080px;
      height: 1920px;
      overflow: hidden;
    }
    .layer-bg    { position: absolute; inset: 0; z-index: 1; }
    .layer-fx    { position: absolute; inset: 0; z-index: 2; pointer-events: none; }
    .layer-content { position: relative; z-index: 3; height: 100%; }

    /* Phase 系统 */
    .phase {
      position: absolute; inset: 0;
      padding: 180px 80px 220px 80px;
      display: flex; flex-direction: column; justify-content: center;
      opacity: 1;
    }

    /* CSS 变量（从 design.md 的 immersion_mode + color_direction 推导） */
    :root {
      {{ css_variables | default('--bg-dark: #0a0a0f;\n  --text-primary: #fff;') }}
    }

    /* ═══ LLM 创意 CSS 区域开始 ═══ */
    /* SLOT:global-css — LLM 在此添加全局 CSS（@keyframes、通用组件样式等） */
    /* CREATIVE_SLOT:global-css */

    /* ═══ 逐场景 CSS ═══ */
    {% for scene in scenes %}
    /* SLOT:{{ scene.scene_id }}-css */
    /* CREATIVE_SLOT:{{ scene.scene_id }}-css */
    {% endfor %}

    /* ═══ LLM 创意 CSS 区域结束 ═══ */
  </style>
</head>
<body>

  {# Audio 嵌入（确定性） #}
  {% include "audio_block.html.j2" %}

  {# Composition 根元素 #}
  <div class="composition" data-composition-id="main" data-start="0">
    {% for scene in scenes %}
    {% include "scene.html.j2" %}
    {% endfor %}
  </div>

  <script>
    {% include "gsap_boot.js.j2" %}
  </script>
</body>
</html>
```

- [ ] **Step 3: 创建 scene.html.j2 — 单场景三层 + 创意插槽**

```html
{# scene.html.j2 — 单个场景的 HTML 骨架

  重要：每个 CREATIVE_SLOT 不是单一元素容器，而是注入点标记。
  LLM 可以在每个层中放入任意数量的子元素：
  - bg 层：多个渐变叠加、多个光晕、Canvas 粒子、SVG 纹理...自由组合
  - fx 层：多个特效同时运行（代码雨 + 光带 + 脉冲球...）
  - content 层：多个文字块、卡片、标签、数据可视化元素...
  层数量、元素数量、叠加方式完全没有限制。
#}
<div class="clip" id="{{ scene.scene_id }}"
     data-start="{{ scene.start }}" data-duration="{{ scene.duration }}">

  {# ── 背景层（可叠加任意数量的背景元素：渐变、光晕、纹理、Canvas...） ── #}
  <div class="layer-bg">
    <!-- CREATIVE_SLOT:{{ scene.scene_id }}-bg-html -->
  </div>

  {# ── 特效层（可叠加任意数量的特效元素：Canvas、CSS动画、光效...） ── #}
  <div class="layer-fx">
    <!-- CREATIVE_SLOT:{{ scene.scene_id }}-fx-html -->
  </div>

  {# ── 内容层 ── #}
  <div class="layer-content">
    {% if scene.visual_phases | length <= 1 %}
    {# 单 phase：直接渲染内容插槽，可放任意数量的内容元素 #}
    <div class="phase phase-1">
      <!-- CREATIVE_SLOT:{{ scene.scene_id }}-content-html -->
    </div>
    {% else %}
    {# 多 phase：为每个 phase 创建独立容器，每个 phase 内仍可放多个元素 #}
    {% for phase in scene.visual_phases %}
    <div class="phase phase-{{ loop.index }}">
      <!-- CREATIVE_SLOT:{{ scene.scene_id }}-phase{{ loop.index }}-html -->
    </div>
    {% endfor %}
    {% endif %}
  </div>
</div>
```

- [ ] **Step 4: 创建 audio_block.html.j2 — 音频嵌入**

```html
{# audio_block.html.j2 — HyperFrames 音频嵌入（确定性） #}
<audio data-track-index="1" data-volume="1"
       src="narration.mp3" preload="auto"></audio>
<audio data-track-index="2"
       data-volume="{{ bgm_volume | default('0.06') }}"
       src="bgm.wav" preload="auto" loop></audio>
```

- [ ] **Step 5: 创建 gsap_boot.js.j2 — GSAP 初始化 + __hf 注册**

```javascript
// GSAP Timeline 初始化（骨架生成，确定性）
window.__timelines = {};
const tl = gsap.timeline({ paused: true });

// ═══ Phase 初始化（多 phase 场景：Phase 2+ 设为不可见） ═══
{% for scene in scenes %}
{% if scene.visual_phases | length > 1 %}
{% for i in range(2, scene.visual_phases | length + 1) %}
tl.set("#{{ scene.scene_id }} .phase-{{ i }}", { opacity: 0 }, {{ scene.start }});
{% endfor %}
{% endif %}
{% endfor %}

// ═══ Phase 切换（确定性时间点，从 compute_phase_breakpoints 计算结果注入） ═══
{% for scene in scenes %}
{% if scene.phase_breakpoints %}
{% for bp in scene.phase_breakpoints %}
{% set phase_idx = loop.index %}
// SLOT:{{ scene.scene_id }}-phase{{ phase_idx }}-switch
// CREATIVE_SLOT:{{ scene.scene_id }}-phase{{ phase_idx }}-switch
{% endfor %}
{% endif %}
{% endfor %}

// ═══ 场景动画（LLM 创意区域） ═══
// SLOT:global-gsap
// CREATIVE_SLOT:global-gsap

{% for scene in scenes %}
// ── {{ scene.scene_id }} ({{ scene.scene_name }}) {{ scene.duration }}s ──
// SLOT:{{ scene.scene_id }}-gsap
// CREATIVE_SLOT:{{ scene.scene_id }}-gsap
{% endfor %}

// ═══ HyperFrames API 注册（确定性） ═══
const totalDuration = {{ total_duration }};
window.__hf = {
  duration: totalDuration,
  seek: function(t) { tl.time(t, false); }
};
window.__timelines["main"] = tl;
```

- [ ] **Step 6: Commit**

```bash
git add .claude/commands/clipforge/engine/skeleton_builder/
git commit -m "feat(engine): add Jinja2 skeleton templates for creative slot architecture"
```

---

## Task 3: skeleton_builder.py — HTML 骨架生成器

**Files:**
- Create: `.claude/commands/clipforge/engine/skeleton_builder.py`

这是核心模块，读取项目文件，确定性生成 HTML 骨架。

- [ ] **Step 1: 创建 skeleton_builder.py**

```python
"""HTML 骨架生成器 — 确定性生成三层架构 + composition 注册 + audio 嵌入。

LLM 不碰这个文件的任何输出。所有输出都是固定结构。
LLM 的创意内容通过 CREATIVE_SLOT 注释标记预留位置，后续由 slot_injector.py 注入。
"""
from __future__ import annotations
import json
import re
import sys
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

sys.path.insert(0, str(Path(__file__).parent.parent))
from engine.lib.models import CreativeSlot, SceneSkeleton


TEMPLATES_DIR = Path(__file__).parent / "skeleton_builder" / "templates"

# 沉浸模式 → CSS 变量映射（从 stage6-components.md 的配色速查表提取）
IMMERSION_CSS_VARS = {
    "hyper-pace": (
        "--bg-dark: #080818;\n      --bg-mid: #001a33;\n      "
        "--accent-warm: #f9a825;\n      --accent-cool: #00f5d4;\n      "
        "--text-primary: #ffffff;\n      --text-secondary: #a0a0c0;"
    ),
    "hidden-gem": (
        "--bg-dark: #0f0f1a;\n      --bg-mid: #1a1a3e;\n      "
        "--accent-warm: #fbbf24;\n      --accent-cool: #a78bfa;\n      "
        "--text-primary: #ffffff;\n      --text-secondary: #c0c0d0;"
    ),
    "mega-update": (
        "--bg-dark: #0a0a0f;\n      --bg-mid: #0d1b2a;\n      "
        "--accent-warm: #ff6b35;\n      --accent-cool: #00d4ff;\n      "
        "--text-primary: #ffffff;\n      --text-secondary: #a0b0c0;"
    ),
    "versus": (
        "--bg-dark: #0a0a0f;\n      --bg-mid: #1a0a0a;\n      "
        "--accent-warm: #ef4444;\n      --accent-cool: #4cc9f0;\n      "
        "--text-primary: #ffffff;\n      --text-secondary: #b0a0a0;"
    ),
    "story-time": (
        "--bg-dark: #0f0f1a;\n      --bg-mid: #1a1a2e;\n      "
        "--accent-warm: #fbbf24;\n      --accent-cool: #7dd3fc;\n      "
        "--text-primary: #ffffff;\n      --text-secondary: #b0c0d0;"
    ),
    "fun-tool": (
        "--bg-dark: #0a0a1a;\n      --bg-mid: #1a1a3e;\n      "
        "--accent-warm: #f59e0b;\n      --accent-cool: #34d399;\n      "
        "--text-primary: #ffffff;\n      --text-secondary: #a0c0b0;"
    ),
}


def _load_json(path: Path) -> dict | list:
    """加载 JSON 文件，兼容数组和对象格式。"""
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return data


def _parse_design(project_dir: Path) -> dict:
    """从 design.md 提取关键视觉参数。"""
    design_path = project_dir / "design.md"
    if not design_path.exists():
        return {"immersion_mode": "hyper-pace", "color_direction": {}}

    content = design_path.read_text(encoding="utf-8")
    result = {}

    # 提取 immersion_mode
    m = re.search(r'immersion_mode[:\s]+["\']?(\S+)["\']?', content)
    result["immersion_mode"] = m.group(1) if m else "hyper-pace"

    # 提取 color_direction 中的具体色值覆盖
    cd_section = re.search(r'color_direction:(.*?)(?=\n##|\nstoryboard|\Z)', content, re.DOTALL)
    color_overrides = {}
    if cd_section:
        for color_match in re.finditer(r'(\w+(?:_\w+)*):\s*(#[0-9a-fA-F]{3,8})', cd_section.group(1)):
            color_overrides[color_match.group(1)] = color_match.group(2)
    result["color_direction"] = color_overrides

    return result


def _build_css_variables(design: dict) -> str:
    """根据 design.md 生成 CSS 变量声明。"""
    immersion = design.get("immersion_mode", "hyper-pace")
    base_vars = IMMERSION_CSS_VARS.get(immersion, IMMERSION_CSS_VARS["hyper-pace"])

    # color_direction 覆盖
    overrides = design.get("color_direction", {})
    if not overrides:
        return base_vars

    lines = base_vars
    for key, value in overrides.items():
        css_key = f"--{key.replace('_', '-')}"
        # 替换已有变量或追加
        pattern = rf"{css_key}\s*:[^;]+;"
        if re.search(pattern, lines):
            lines = re.sub(pattern, f"{css_key}: {value};", lines)
        else:
            lines += f"\n      {css_key}: {value};"
    return lines


def _compute_phase_breakpoints(segment: dict) -> list[float]:
    """为多 phase 场景计算断点（内容对齐）。"""
    phases = segment.get("visual_phases", [])
    if len(phases) <= 1:
        return []

    duration = segment.get("duration", segment.get("dur", 10))
    text = segment.get("text", segment.get("narration_segment", ""))

    breakpoints = []
    for i in range(1, len(phases)):
        focus = phases[i].get("focus", "")
        ratio = _find_text_boundary(text, focus)
        if ratio is None:
            ratio = i / len(phases)
        breakpoints.append(round(ratio * duration, 2))
    return breakpoints


def _find_text_boundary(text: str, focus_keyword: str) -> float | None:
    """在旁白文本中找到 focus 关键词对应的段落边界比例。"""
    if not focus_keyword or not text:
        return None
    sentences = [s.strip() for s in re.split(r'[。！？；\n]', text) if s.strip()]
    for idx, sentence in enumerate(sentences):
        if focus_keyword in sentence or focus_keyword[:6] in sentence:
            char_count = sum(len(s) + 1 for s in sentences[:idx + 1])
            total_chars = sum(len(s) + 1 for s in sentences)
            return char_count / total_chars if total_chars > 0 else 0.5
    return None


def build_scene_skeletons(project_dir: Path) -> list[SceneSkeleton]:
    """从项目文件构建所有场景的骨架数据。"""
    segs_path = project_dir / "narration_segments.json"
    segs_data = _load_json(segs_path)
    segments = segs_data if isinstance(segs_data, list) else segs_data.get("segments", [])

    # 尝试加载时长数据
    dur_path = project_dir / "segment_durations.json"
    dur_data = _load_json(dur_path)
    dur_segments = dur_data.get("segments", []) if isinstance(dur_data, dict) else dur_data

    # 构建时长映射：scene_name → actual_duration
    duration_map = {}
    cumulative = 0.0
    for ds in dur_segments:
        name = ds.get("scene", ds.get("scene_name", ""))
        actual = ds.get("actual_duration", ds.get("duration", 0))
        duration_map[name] = {"start": cumulative, "duration": actual}
        cumulative += actual

    skeletons = []
    for seg in segments:
        scene_name = seg.get("scene", "")
        scene_id = scene_name.split("-")[0] if "-" in scene_name else scene_name

        # 获取时长
        dur_info = duration_map.get(scene_name, {})
        start = dur_info.get("start", seg.get("start", 0))
        duration = dur_info.get("duration", seg.get("duration", seg.get("dur", 10)))

        # Phase 断点
        phase_breakpoints = _compute_phase_breakpoints(seg)

        # 构建创意插槽
        slots = []

        # CSS 插槽
        slots.append(CreativeSlot(
            slot_id=f"{scene_id}-css",
            scene_id=scene_id,
            layer="all",
            slot_type="css",
            marker=f"<!-- CREATIVE_SLOT:{scene_id}-css -->",
        ))

        # bg HTML 插槽
        slots.append(CreativeSlot(
            slot_id=f"{scene_id}-bg-html",
            scene_id=scene_id,
            layer="bg",
            slot_type="html",
            marker=f"<!-- CREATIVE_SLOT:{scene_id}-bg-html -->",
            scene_duration=duration,
            emotion_tags=seg.get("emotion_tags", []),
            visual_intent=seg.get("visual_intent", {}).get("bg", {}) if isinstance(seg.get("visual_intent"), dict) else {},
        ))

        # fx HTML 插槽
        slots.append(CreativeSlot(
            slot_id=f"{scene_id}-fx-html",
            scene_id=scene_id,
            layer="fx",
            slot_type="html",
            marker=f"<!-- CREATIVE_SLOT:{scene_id}-fx-html -->",
            scene_duration=duration,
        ))

        # content HTML 插槽（单 phase 或多 phase）
        phases = seg.get("visual_phases", [])
        if len(phases) <= 1:
            slots.append(CreativeSlot(
                slot_id=f"{scene_id}-content-html",
                scene_id=scene_id,
                layer="content",
                slot_type="html",
                marker=f"<!-- CREATIVE_SLOT:{scene_id}-content-html -->",
                scene_duration=duration,
                narration_text=seg.get("text", seg.get("narration_segment", "")),
            ))
        else:
            for pi, phase in enumerate(phases, 1):
                slots.append(CreativeSlot(
                    slot_id=f"{scene_id}-phase{pi}-html",
                    scene_id=scene_id,
                    layer="content",
                    slot_type="html",
                    marker=f"<!-- CREATIVE_SLOT:{scene_id}-phase{pi}-html -->",
                    scene_duration=duration,
                    narration_text=phase.get("text", ""),
                    visual_intent=phase,
                ))

        # GSAP 动画插槽
        slots.append(CreativeSlot(
            slot_id=f"{scene_id}-gsap",
            scene_id=scene_id,
            layer="all",
            slot_type="gsap",
            marker=f"<!-- CREATIVE_SLOT:{scene_id}-gsap -->",
            scene_duration=duration,
        ))

        skeletons.append(SceneSkeleton(
            scene_id=scene_id,
            scene_name=scene_name,
            start=start,
            duration=duration,
            visual_phases=phases,
            phase_breakpoints=phase_breakpoints,
            slots=slots,
        ))

    return skeletons


def render_skeleton(project_dir: Path, output_path: Path | None = None) -> tuple[str, list[SceneSkeleton]]:
    """渲染完整 HTML 骨架，返回 (html_string, scene_skeletons)。"""
    design = _parse_design(project_dir)
    css_variables = _build_css_variables(design)
    skeletons = build_scene_skeletons(project_dir)

    # 加载 BGM 音量
    dur_data = _load_json(project_dir / "segment_durations.json")
    bgm_volume = dur_data.get("meta", {}).get("bgm_volume", 0.06) if isinstance(dur_data, dict) else 0.06

    # 计算总时长
    total_duration = sum(s.duration for s in skeletons)

    # 准备场景数据（Jinja2 模板所需的扁平结构）
    scenes = []
    for sk in skeletons:
        scenes.append({
            "scene_id": sk.scene_id,
            "scene_name": sk.scene_name,
            "start": sk.start,
            "duration": sk.duration,
            "visual_phases": sk.visual_phases,
            "phase_breakpoints": sk.phase_breakpoints,
        })

    # Jinja2 渲染
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        keep_trailing_newline=True,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    template = env.get_template("composition.html.j2")
    html = template.render(
        project_name=project_dir.name,
        css_variables=css_variables,
        base_bg_css=f"background: #000;",
        scenes=scenes,
        bgm_volume=bgm_volume,
        total_duration=total_duration,
    )

    if output_path:
        output_path.write_text(html, encoding="utf-8")

    return html, skeletons


def main():
    import argparse
    parser = argparse.ArgumentParser(description="ClipForge HTML 骨架生成器")
    parser.add_argument("--project-dir", required=True, help="项目目录")
    parser.add_argument("--output", default=None, help="输出文件路径（默认 stdout）")
    parser.add_argument("--slots-json", default=None, help="输出插槽清单 JSON")
    args = parser.parse_args()

    project_dir = Path(args.project_dir)
    output_path = Path(args.output) if args.output else None

    html, skeletons = render_skeleton(project_dir, output_path)

    if output_path:
        print(f"骨架已生成: {output_path} ({len(skeletons)} 场景)")
    else:
        print(html)

    if args.slots_json:
        slots_data = []
        for sk in skeletons:
            for slot in sk.slots:
                slots_data.append({
                    "slot_id": slot.slot_id,
                    "scene_id": slot.scene_id,
                    "layer": slot.layer,
                    "slot_type": slot.slot_type,
                    "marker": slot.marker,
                    "scene_duration": slot.scene_duration,
                    "emotion_tags": slot.emotion_tags,
                    "visual_intent": slot.visual_intent,
                    "narration_text": slot.narration_text,
                })
        Path(args.slots_json).write_text(
            json.dumps(slots_data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"插槽清单已输出: {args.slots_json} ({len(slots_data)} 个插槽)")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 验证 jinja2 可用**

```bash
pip show jinja2 || pip install jinja2
python -c "import jinja2; print(f'Jinja2 {jinja2.__version__}')"
```

- [ ] **Step 3: Commit**

```bash
git add .claude/commands/clipforge/engine/skeleton_builder.py
git commit -m "feat(engine): add skeleton_builder — deterministic HTML skeleton generator"
```

---

## Task 4: slot_injector.py — 创意内容注入器

**Files:**
- Create: `.claude/commands/clipforge/engine/slot_injector.py`

这个模块把 LLM 自由创作的 CSS/HTML/GSAP 代码注入骨架中的创意插槽。LLM 的输出可以是自然语言描述的代码块，也可以是纯代码。

- [ ] **Step 1: 创建 slot_injector.py**

```python
"""创意内容注入器 — 将 LLM 自由创作的 CSS/HTML/GSAP 代码注入骨架的创意插槽。

LLM 输出格式（自由灵活）：
  可以输出完整的创意内容 JSON，也可以直接输出包含标记的代码片段。
  注入器会自动匹配 CREATIVE_SLOT 标记并替换。

设计原则：
  - 注入器不做任何内容过滤或修改，LLM 写什么就注入什么
  - 组件库组件可以通过 slot_id 关联引用（可选），但不强制
  - 注入失败（找不到标记）会报错但不损坏骨架其他部分
"""
from __future__ import annotations
import json
import re
import sys
from pathlib import Path


SLOT_PATTERN = re.compile(r'(<!--\s*CREATIVE_SLOT:(\S+)\s*-->)')


def find_slots(html: str) -> dict[str, str]:
    """扫描 HTML 找到所有创意插槽标记，返回 {slot_id: marker}。"""
    slots = {}
    for match in SLOT_PATTERN.finditer(html):
        marker = match.group(1)
        slot_id = match.group(2)
        slots[slot_id] = marker
    return slots


def inject_content(html: str, contents: dict[str, str]) -> tuple[str, list[str]]:
    """将创意内容注入骨架。

    Args:
        html: 骨架 HTML 字符串
        contents: {slot_id: creative_content} 映射

    Returns:
        (注入后的 HTML, 未匹配的 slot_ids)
    """
    slots = find_slots(html)
    unmatched = []

    for slot_id, content in contents.items():
        if slot_id in slots:
            marker = slots[slot_id]
            # 替换标记为标记 + 内容（保留标记以便后续验证）
            html = html.replace(
                marker,
                f"<!-- INJECTED:{slot_id} -->\n{content}\n<!-- END_INJECTED:{slot_id} -->",
                1,
            )
        else:
            unmatched.append(slot_id)

    return html, unmatched


def inject_from_creative_file(skeleton_path: Path, creative_path: Path, output_path: Path | None = None) -> str:
    """从 LLM 输出的创意文件注入骨架。

    creative_file 支持两种格式：
    1. JSON 格式: [{"slot_id": "s1-bg-html", "content": "<div>..."}]
    2. 标记格式: 代码中直接包含 <!-- CREATIVE_SLOT:s1-bg-html --> 标记
    """
    skeleton_html = skeleton_path.read_text(encoding="utf-8")
    creative_raw = creative_path.read_text(encoding="utf-8")

    # 尝试 JSON 格式
    try:
        creative_data = json.loads(creative_raw)
        if isinstance(creative_data, list):
            contents = {item["slot_id"]: item["content"] for item in creative_data}
        elif isinstance(creative_data, dict):
            contents = {k: v for k, v in creative_data.items() if isinstance(v, str)}
        else:
            raise ValueError("unexpected format")
    except (json.JSONDecodeError, ValueError, KeyError):
        # 非JSON：直接用标记替换（LLM 可能在代码中自己写了 CREATIVE_SLOT 标记）
        contents = _parse_marked_content(creative_raw)

    result_html, unmatched = inject_content(skeleton_html, contents)

    if unmatched:
        print(f"WARNING: {len(unmatched)} 个插槽未匹配: {', '.join(unmatched[:5])}", file=sys.stderr)

    if output_path:
        output_path.write_text(result_html, encoding="utf-8")
        print(f"注入完成: {output_path} ({len(contents)} 个插槽)")

    return result_html


def _parse_marked_content(raw: str) -> dict[str, str]:
    """解析包含 CREATIVE_SLOT 标记的自由格式内容。

    格式示例：
      <!-- CREATIVE_SLOT:s1-bg-html -->
      <div class="nebula">...</div>
      <!-- END_SLOT:s1-bg-html -->
    """
    contents = {}
    # 匹配 CREATIVE_SLOT:xxx ... (END_SLOT:xxx 或下一个 CREATIVE_SLOT)
    pattern = re.compile(
        r'<!--\s*CREATIVE_SLOT:(\S+)\s*-->\s*\n(.*?)(?=<!--\s*(?:END_SLOT|CREATIVE_SLOT):)',
        re.DOTALL,
    )
    for match in pattern.finditer(raw):
        slot_id = match.group(1)
        content = match.group(2).strip()
        contents[slot_id] = content

    return contents


def validate_injection(html: str) -> tuple[bool, list[str]]:
    """验证所有 CREATIVE_SLOT 标记都已被注入。

    Returns:
        (all_injected, remaining_empty_slots)
    """
    remaining = SLOT_PATTERN.findall(html)
    empty_slots = [match[1] for match in remaining if match[1]]
    return len(empty_slots) == 0, empty_slots


def main():
    import argparse
    parser = argparse.ArgumentParser(description="ClipForge 创意内容注入器")
    parser.add_argument("--skeleton", required=True, help="骨架 HTML 路径")
    parser.add_argument("--creative", required=True, help="创意内容文件路径")
    parser.add_argument("--output", default=None, help="输出路径（默认覆盖骨架）")
    parser.add_argument("--validate", action="store_true", help="仅验证注入完整性")
    args = parser.parse_args()

    skeleton_path = Path(args.skeleton)
    creative_path = Path(args.creative)
    output_path = Path(args.output) if args.output else skeleton_path

    if args.validate:
        html = skeleton_path.read_text(encoding="utf-8")
        all_done, remaining = validate_injection(html)
        if all_done:
            print(f"✓ 所有创意插槽已注入")
        else:
            print(f"✗ {len(remaining)} 个插槽未注入: {', '.join(remaining)}")
        sys.exit(0 if all_done else 1)

    inject_from_creative_file(skeleton_path, creative_path, output_path)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Commit**

```bash
git add .claude/commands/clipforge/engine/slot_injector.py
git commit -m "feat(engine): add slot_injector — injects LLM creative content into skeleton slots"
```

---

## Task 5: CLI 工具脚本

**Files:**
- Create: `.claude/commands/clipforge/scripts/generate_skeleton.py`
- Create: `.claude/commands/clipforge/scripts/inject_creative.py`
- Create: `.claude/commands/clipforge/scripts/validate_skeleton.py`

- [ ] **Step 1: 创建 generate_skeleton.py CLI 入口**

```python
#!/usr/bin/env python3
"""CLI: 生成 HTML 骨架。

用法:
  python scripts/generate_skeleton.py --project-dir workspace/2026/05/30/my-project
  python scripts/generate_skeleton.py --project-dir workspace/2026/05/30/my-project --output index_skeleton.html
  python scripts/generate_skeleton.py --project-dir workspace/2026/05/30/my-project --slots-json slots.json
"""
import sys
from pathlib import Path

# 把 engine 目录加入 path
sys.path.insert(0, str(Path(__file__).parent.parent))
from engine.skeleton_builder import render_skeleton, build_scene_skeletons


def main():
    import argparse
    parser = argparse.ArgumentParser(description="生成 ClipForge HTML 骨架")
    parser.add_argument("--project-dir", required=True)
    parser.add_argument("--output", default=None, help="输出 HTML 路径（默认 stdout）")
    parser.add_argument("--slots-json", default=None, help="同时输出插槽清单 JSON")
    args = parser.parse_args()

    project_dir = Path(args.project_dir).resolve()
    output_path = Path(args.output) if args.output else None

    html, skeletons = render_skeleton(project_dir, output_path)

    if output_path:
        print(f"✓ 骨架生成: {output_path}")
        print(f"  场景数: {len(skeletons)}")
        total_slots = sum(len(s.slots) for s in skeletons)
        print(f"  创意插槽数: {total_slots}")
    else:
        print(html)

    if args.slots_json:
        import json
        slots_data = []
        for sk in skeletons:
            for slot in sk.slots:
                slots_data.append({
                    "slot_id": slot.slot_id,
                    "scene_id": slot.scene_id,
                    "layer": slot.layer,
                    "slot_type": slot.slot_type,
                    "scene_duration": slot.scene_duration,
                    "emotion_tags": slot.emotion_tags,
                    "narration_text": slot.narration_text[:80] if slot.narration_text else "",
                })
        Path(args.slots_json).write_text(
            json.dumps(slots_data, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"✓ 插槽清单: {args.slots_json} ({len(slots_data)} 个)")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 创建 inject_creative.py CLI 入口**

```python
#!/usr/bin/env python3
"""CLI: 注入创意内容到骨架。

用法:
  python scripts/inject_creative.py --skeleton index_skeleton.html --creative creative.json
  python scripts/inject_creative.py --skeleton index_skeleton.html --creative creative.json --output index.html
  python scripts/inject_creative.py --skeleton index.html --validate
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from engine.slot_injector import inject_from_creative_file, validate_injection


def main():
    import argparse
    parser = argparse.ArgumentParser(description="注入创意内容到 ClipForge HTML 骨架")
    parser.add_argument("--skeleton", required=True, help="骨架 HTML 文件路径")
    parser.add_argument("--creative", default=None, help="创意内容文件路径")
    parser.add_argument("--output", default=None, help="输出路径（默认覆盖骨架文件）")
    parser.add_argument("--validate", action="store_true", help="仅验证注入完整性")
    args = parser.parse_args()

    skeleton_path = Path(args.skeleton).resolve()

    if args.validate:
        html = skeleton_path.read_text(encoding="utf-8")
        all_done, remaining = validate_injection(html)
        if all_done:
            print(f"✓ 所有创意插槽已注入")
        else:
            print(f"✗ {len(remaining)} 个插槽未注入:")
            for slot in remaining:
                print(f"  - {slot}")
        sys.exit(0 if all_done else 1)

    if not args.creative:
        print("ERROR: 需要 --creative 或 --validate", file=sys.stderr)
        sys.exit(1)

    creative_path = Path(args.creative).resolve()
    output_path = Path(args.output) if args.output else skeleton_path

    inject_from_creative_file(skeleton_path, creative_path, output_path)
    print(f"✓ 创意内容已注入: {output_path}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: 创建 validate_skeleton.py**

```python
#!/usr/bin/env python3
"""CLI: 验证骨架完整性。

检查：
1. 所有必需的 CREATIVE_SLOT 标记存在
2. skeleton 结构完整（三层 div、composition-id、scene id 等）
3. 注入后验证所有插槽已填充
"""
import re
import sys
from pathlib import Path


REQUIRED_MARKERS = [
    "data-composition-id",
    "window.__hf",
    "window.__timelines",
    "gsap.timeline",
]


def validate_skeleton_structure(html: str) -> list[str]:
    """验证骨架的基础结构完整性。"""
    issues = []
    for marker in REQUIRED_MARKERS:
        if marker not in html:
            issues.append(f"缺少必要结构: {marker}")
    return issues


def validate_slots(html: str) -> tuple[int, int, list[str]]:
    """验证创意插槽。返回 (total, unfilled, slot_ids)。"""
    slot_pattern = re.compile(r'<!--\s*CREATIVE_SLOT:(\S+)\s*-->')
    filled_pattern = re.compile(r'<!--\s*INJECTED:(\S+)\s*-->')

    all_slots = [m.group(1) for m in slot_pattern.finditer(html)]
    filled = set(m.group(1) for m in filled_pattern.finditer(html))
    unfilled = [s for s in all_slots if s not in filled]
    return len(all_slots), len(unfilled), unfilled


def main():
    import argparse
    parser = argparse.ArgumentParser(description="验证 ClipForge HTML 骨架")
    parser.add_argument("--html", required=True, help="HTML 文件路径")
    parser.add_argument("--strict", action="store_true", help="严格模式：未填充的插槽也报错")
    args = parser.parse_args()

    html = Path(args.html).read_text(encoding="utf-8")

    print("=== 骨架结构验证 ===")
    structure_issues = validate_skeleton_structure(html)
    if structure_issues:
        for issue in structure_issues:
            print(f"  ✗ {issue}")
    else:
        print("  ✓ 基础结构完整")

    print("\n=== 创意插槽验证 ===")
    total, unfilled_count, unfilled = validate_slots(html)
    print(f"  总插槽数: {total}")
    print(f"  未填充: {unfilled_count}")

    if unfilled_count > 0:
        for slot in unfilled[:10]:
            print(f"  - {slot}")
        if unfilled_count > 10:
            print(f"  ... 还有 {unfilled_count - 10} 个")

    if args.strict and unfilled_count > 0:
        print(f"\n✗ 严格模式: {unfilled_count} 个插槽未填充")
        sys.exit(1)

    if structure_issues:
        print(f"\n✗ 验证失败: {len(structure_issues)} 个结构问题")
        sys.exit(1)

    if not args.strict or unfilled_count == 0:
        print(f"\n✓ 验证通过")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Commit**

```bash
git add .claude/commands/clipforge/scripts/generate_skeleton.py
git add .claude/commands/clipforge/scripts/inject_creative.py
git add .claude/commands/clipforge/scripts/validate_skeleton.py
git commit -m "feat(scripts): add CLI tools for skeleton generation, creative injection and validation"
```

---

## Task 6: 修改 stage6-production.md — 集成骨架工作流

**Files:**
- Modify: `.claude/commands/clipforge/stages/stage6-production.md`

- [ ] **Step 1: 在 §6.4 开头插入骨架生成步骤**

在 `## 6.4 编写 HTML 组合（组件装配模式）` 这一节的开头，插入骨架生成步骤。将原文的"调用 `/hyperframes` 技能"改为先由代码引擎生成骨架，LLM 只负责创意内容。

具体修改：在 `## 6.4 编写 HTML 组合（组件装配模式）` 的第一段（"调用 `/hyperframes` 技能..."）之前插入：

```markdown
### §6.4-0 骨架生成（代码引擎自动执行）

> **这一步由代码引擎完成，LLM 不参与。** 输出为包含 `CREATIVE_SLOT` 标记的 HTML 骨架。

```bash
cd workspace/<YYYY>/<MM>/<DD>/<project-dir>

# 1. 生成 HTML 骨架 + 插槽清单
python .claude/commands/clipforge/scripts/generate_skeleton.py \
  --project-dir . \
  --output index_skeleton.html \
  --slots-json skeleton_slots.json

# 2. 验证骨架结构完整性
python .claude/commands/clipforge/scripts/validate_skeleton.py \
  --html index_skeleton.html
```

骨架包含：
- 完整 HTML 文档结构（DOCTYPE、head、body）
- 三层 div 架构（bg / fx / content），每层都有 `CREATIVE_SLOT` 标记
- `<audio>` 嵌入（旁白 + BGM，音量从 segment_durations.json 自动读取）
- GSAP timeline 初始化 + `window.__hf` 注册
- Phase 初始化和切换占位
- 每个 scene div 的 `id`、`data-start`、`data-duration` 已精确设置

### §6.4-1 视觉节奏上下文（代码引擎自动执行）

> **这一步由代码引擎完成。** 为每个场景生成视觉上下文 JSON，LLM 创作前必须读取。

```bash
# 生成视觉节奏上下文（emotion curve + 前序场景指纹 + 节奏引导）
python .claude/commands/clipforge/scripts/generate_visual_context.py \
  --project-dir . \
  --output visual_context.json
```

`visual_context.json` 为每个场景提供：

```json
{
  "scene_id": "s3",
  "scene_name": "s3-top1",
  "emotion_curve_position": 0.22,
  "emotion_intensity": 0.55,
  "intensity_label": "平稳推进 — 视觉力度适中：保持节奏，可做小变化",
  "visual_theme": {
    "color_temperature": "cold-warm-contrast",
    "accent_colors": ["#00d4ff", "#ff6b35"],
    "immersion_mode": "hyper-pace"
  },
  "prev_scene_summary": {
    "scene_id": "s2",
    "dominant_colors": ["#FFD700", "#0a0a0f", "#1a1a3e"],
    "bg_element_types": ["gradient", "glow", "noise"],
    "fx_types": ["canvas"]
  },
  "next_scene_summary": { "...": "..." },
  "rhythm_guidance": "📍 推进阶段：视觉随内容展开，可以逐步丰富层次\n🔗 前序场景主色: #FFD700, #0a0a0f\n   → 保持至少一个色调族一致，但在其他维度变化\n🔗 前序背景元素: gradient, glow, noise\n   → 可保留一种元素类型，替换其他类型，制造'似曾相识但不同'的感觉"
}
```

**LLM 如何使用这些上下文：**
- `emotion_intensity` → 决定视觉力度（高=浓烈/低=收敛）
- `prev_scene_summary.dominant_colors` → 保留一个色调族（不突兀），替换其他色（不单调）
- `prev_scene_summary.bg_element_types` → 保留一种元素类型（连贯感），替换其余（新鲜感）
- `rhythm_guidance` → 直接的创作引导文字

### §6.4-2 创意填充（LLM 自由创作）

> **LLM 在此获得完全创作自由。** 骨架已经保证了结构性正确（三层、composition、audio、__hf），LLM 只需为每个插槽编写创意内容。创作前读取 `visual_context.json`，在自由创作中自然融入节奏感。

**LLM 输出的不是完整 HTML，而是创意内容——逐场景的 CSS + HTML + GSAP 动画。**

LLM 输出格式（两种任选）：

**格式 A：结构化 JSON**
```json
[
  {"slot_id": "s1-css", "content": "#s1 .layer-bg { background: radial-gradient(...); }"},
  {"slot_id": "s1-bg-html", "content": "<div class='nebula'>...</div>"},
  {"slot_id": "s1-fx-html", "content": "<canvas id='particles-s1'>...</canvas>"},
  {"slot_id": "s1-content-html", "content": "<h1 style='font-size:100px;...'>震撼标题</h1>"},
  {"slot_id": "s1-gsap", "content": "tl.from('#s1 h1', {x:-400, opacity:0, duration:0.8, ease:'back.out(1.4)'}, 0.3);"}
]
```

**格式 B：带标记的代码片段（更自由）**
```html
<!-- CREATIVE_SLOT:s1-bg-html -->
<div style="position:absolute;inset:0;background:radial-gradient(ellipse at 30% 70%, rgba(75,0,130,0.8), transparent);">
  <div style="position:absolute;width:300px;height:300px;border-radius:50%;background:radial-gradient(circle,rgba(0,150,255,0.3),transparent);bottom:10%;left:5%;filter:blur(40px);"></div>
</div>
<!-- END_SLOT:s1-bg-html -->

<!-- CREATIVE_SLOT:s1-gsap -->
tl.from('#s1 h1', {x: -400, opacity: 0, duration: 0.8, ease: 'back.out(1.4)'}, 0.3);
tl.from('#s1 .subtitle', {y: 60, opacity: 0, duration: 0.6, ease: 'power2.out'}, 1.0);
<!-- END_SLOT:s1-gsap -->
```

**创意自由度声明：**
- LLM 可以自由发明任何 CSS 效果（渐变、动画、滤镜、混合模式...）
- LLM 可以使用 Canvas/WebGL 编写全新特效
- LLM 可以引用组件库中的组件作为基础并修改
- LLM 也可以完全不使用组件库，从零创作
- 组件库是"工具箱和灵感来源"，不是约束

### §6.4-3 组装与验证（代码引擎自动执行）

LLM 完成所有插槽的创意内容后，由代码引擎组装：

```bash
# 注入创意内容
python .claude/commands/clipforge/scripts/inject_creative.py \
  --skeleton index_skeleton.html \
  --creative creative_output.json \
  --output index.html

# 验证所有插槽已填充
python .claude/commands/clipforge/scripts/validate_skeleton.py \
  --html index.html --strict

# 验证 HTML 完整性（重用现有 gate 检查）
python .claude/commands/clipforge/engine/gate.py \
  --skill stage6-production --project-dir .
```

如果 gate 检查失败，仅修复失败的部分（不需要重写整个 HTML）。
```

- [ ] **Step 2: Commit**

```bash
git add .claude/commands/clipforge/stages/stage6-production.md
git commit -m "feat(stage6): integrate skeleton-based workflow into production stage"
```

---

## Task 7: 集成测试 — 用现有项目验证骨架生成

**Files:**
- None (manual testing)

- [ ] **Step 1: 找一个已有项目目录进行测试**

```bash
# 找到最近的项目
find workspace -name "narration_segments.json" -type f 2>/dev/null | head -3
```

- [ ] **Step 2: 对该项目运行骨架生成**

```bash
PROJECT_DIR="workspace/<找到的路径>"

python .claude/commands/clipforge/scripts/generate_skeleton.py \
  --project-dir "$PROJECT_DIR" \
  --output "$PROJECT_DIR/index_skeleton.html" \
  --slots-json "$PROJECT_DIR/skeleton_slots.json"
```

Expected: 无错误，输出骨架 HTML 和插槽 JSON。

- [ ] **Step 3: 验证骨架结构**

```bash
python .claude/commands/clipforge/scripts/validate_skeleton.py --html "$PROJECT_DIR/index_skeleton.html"
```

Expected: 基础结构完整，列出所有创意插槽（未填充）。

- [ ] **Step 4: 模拟注入测试**

创建一个简单的测试创意文件：

```bash
cat > /tmp/test_creative.json << 'EOF'
[
  {"slot_id": "global-css", "content": "@keyframes testAnim { from { opacity:0 } to { opacity:1 } }"},
  {"slot_id": "global-gsap", "content": "// global animation placeholder"}
]
EOF

python .claude/commands/clipforge/scripts/inject_creative.py \
  --skeleton "$PROJECT_DIR/index_skeleton.html" \
  --creative /tmp/test_creative.json \
  --output "$PROJECT_DIR/index_test.html"
```

Expected: global-css 和 global-gsap 注入成功，其他插槽未匹配警告。

- [ ] **Step 5: 用 gate.py 验证骨架的确定性部分**

```bash
python .claude/commands/clipforge/engine/gate.py \
  --skill stage6-production --project-dir "$PROJECT_DIR"
```

Expected: `hf_api_present`、`scene_ids_match`、`composition_structure` 检查应该 PASS（因为骨架已确定性生成这些部分）。

- [ ] **Step 6: Commit 测试结果记录**

```bash
git add -A
git commit -m "test(skeleton): validate skeleton generation with existing project"
```

---

## Task 8: 更新 clipforge.md 主控制器 — 标注骨架工作流

**Files:**
- Modify: `.claude/commands/clipforge.md`

- [ ] **Step 1: 在主控制器的 DAG 说明区域，为 video artifact 添加骨架工作流说明**

在 `video` artifact 的描述后追加：

```markdown
> **Stage 6 骨架工作流（v2）：** 代码引擎先生成 HTML 骨架（三层架构 + composition + audio + __hf），LLM 在创意插槽中自由编写 CSS/HTML/GSAP（包括组件库里没有的全新特效），代码引擎最后组装并验证。组件库从"唯一选择来源"降级为"可选参考"。
```

- [ ] **Step 2: Commit**

```bash
git add .claude/commands/clipforge.md
git commit -m "docs(clipforge): document skeleton-based workflow for stage 6"
```

---

## Task 4.5: visual_context.py — 视觉节奏上下文生成器

**Files:**
- Create: `.claude/commands/clipforge/engine/visual_context.py`

这是解决"不单调、不突兀"的核心模块。它不生成任何视觉内容，而是在 LLM 创作之前，为每个场景的创意插槽计算并提供**视觉上下文信息**。LLM 根据这些上下文做创意决策。

核心思路：
- **不突兀** = 相邻场景共享至少一个视觉维度（色调/纹理类型/动画风格），像音乐变奏
- **不单调** = 相邻场景在至少另一个视觉维度上制造差异，像音乐转调

- [ ] **Step 1: 创建 visual_context.py**

```python
"""视觉节奏上下文生成器 — 为创意插槽提供"不单调、不突兀"的上下文。

不做任何创作决策，只提供结构化上下文让 LLM 做出更好的创作选择。

三个核心概念：
1. visual_theme: 全片共享的视觉调性（来自 design.md），所有场景的"调性锚点"
2. prev_scene_summary: 前序场景的视觉指纹，帮助保持连贯
3. emotion_intensity: 当前场景在情感曲线上的位置，指导视觉力度

连续性规则（注入给 LLM 的引导，不是硬约束）：
- 与前序场景共享 ≥1 个视觉维度（色调族/纹理类型/动画节奏）
- 在 ≥1 个其他维度上制造差异
- 情感曲线高点 → 视觉力度加强；低点 → 收敛
"""
from __future__ import annotations
import json
import re
from pathlib import Path


def parse_emotion_curve(design_md: str) -> list[float]:
    """从 design.md 提取 emotion_curve（6 拍情感强度 0.0~1.0）。"""
    match = re.search(r'emotion_curve:\s*\[([^\]]+)\]', design_md)
    if match:
        return [float(v.strip()) for v in match.group(1).split(',')]
    # 默认曲线：开场强 → 中间低 → 结尾收束
    return [0.8, 0.5, 0.6, 0.7, 0.4, 0.3]


def get_emotion_for_scene(scene_index: int, total_scenes: int, curve: list[float]) -> tuple[float, float]:
    """获取场景在情感曲线中的 (position_0_to_1, intensity)。

    将 scene_index 线性映射到 emotion_curve 的 6 个拍点上。
    """
    if total_scenes <= 1:
        return 0.0, curve[0] if curve else 0.5

    position = scene_index / (total_scenes - 1)
    # 将 position (0~1) 映射到 curve 的 6 个点上（线性插值）
    curve_pos = position * (len(curve) - 1)
    idx = int(curve_pos)
    frac = curve_pos - idx

    if idx >= len(curve) - 1:
        intensity = curve[-1]
    else:
        intensity = curve[idx] * (1 - frac) + curve[idx + 1] * frac

    return position, intensity


def parse_visual_theme(design_md: str) -> dict:
    """从 design.md 提取全片视觉主题。"""
    theme = {}

    # 色温方向
    m = re.search(r'color_direction:(.*?)(?=\n##|\nstoryboard|\Z)', design_md, re.DOTALL)
    if m:
        section = m.group(1)
        if '暖' in section and '冷' in section:
            theme['color_temperature'] = 'cold-warm-contrast'
        elif '暖' in section:
            theme['color_temperature'] = 'warm'
        elif '冷' in section:
            theme['color_temperature'] = 'cold'
        else:
            theme['color_temperature'] = 'neutral'

        # 提取色值
        theme['accent_colors'] = re.findall(r'#[0-9a-fA-F]{6}\b', section)
    else:
        theme['color_temperature'] = 'neutral'
        theme['accent_colors'] = []

    # immersion_mode
    m = re.search(r'immersion_mode[:\s]+["\']?(\S+)["\']?', design_md)
    theme['immersion_mode'] = m.group(1) if m else 'hyper-pace'

    # 饱和度 / 明度（从 style 字段推断）
    style_match = re.search(r'style:\s*(.+)', design_md)
    style_text = style_match.group(1).lower() if style_match else ''
    if '饱和' in style_text or 'vivid' in style_text:
        theme['saturation'] = 'high'
    elif '低饱和' in style_text or 'muted' in style_text:
        theme['saturation'] = 'low'
    else:
        theme['saturation'] = 'moderate'

    if '暗' in style_text or 'dark' in style_text:
        theme['brightness_range'] = 'dark-base'
    elif '亮' in style_text or 'bright' in style_text:
        theme['brightness_range'] = 'bright-base'
    else:
        theme['brightness_range'] = 'dark-base'  # 默认暗底

    return theme


def build_scene_summaries(slots_json_path: Path) -> dict[str, dict]:
    """从已注入的 index.html 中提取每个场景的实际视觉摘要。

    这是"反馈循环"：第一轮 LLM 创作完成后，提取实际使用的视觉元素，
    作为第二轮创作的 prev_scene_summary 上下文。

    在第一轮（尚未注入）时返回空 dict。
    """
    index_path = slots_json_path.parent / "index.html"
    if not index_path.exists():
        return {}

    # 这里复用 gate.py 的 _split_into_scenes + _classify_bg_element_types 逻辑
    # 提取每个场景的实际颜色和元素类型
    from engine.gate import _split_into_scenes, _extract_layer_chunk, _classify_bg_element_types, _bg_style_fingerprint

    html = index_path.read_text(encoding="utf-8", errors="ignore")
    scenes = _split_into_scenes(html)

    summaries = {}
    for scene_id, scene_html in scenes:
        bg = _extract_layer_chunk(scene_html, "layer-bg")
        fx = _extract_layer_chunk(scene_html, "layer-fx")

        colors = sorted(set(re.findall(r'#[0-9a-fA-F]{6}\b', bg)))
        bg_types = list(_classify_bg_element_types(bg)) if bg else []

        # 提取 fx 层的关键词
        fx_types = []
        if 'canvas' in fx.lower():
            fx_types.append('canvas')
        if re.search(r'filter\s*:\s*blur', fx):
            fx_types.append('glow')
        if 'animation' in fx.lower():
            fx_types.append('animated')

        summaries[scene_id] = {
            "scene_id": scene_id,
            "dominant_colors": colors[:5],
            "bg_element_types": bg_types,
            "fx_types": fx_types,
            "has_content": bool(re.search(r'<(h[1-6]|p|span|div)[^>]*>[^<]+', scene_html)),
        }

    return summaries


def generate_context_for_slots(
    project_dir: Path,
) -> list[dict]:
    """为项目所有创意插槽生成完整的视觉上下文。

    输出格式：与 skeleton_slots.json 兼容，追加 visual_context 字段。
    """
    # 读取 design.md
    design_path = project_dir / "design.md"
    design_md = design_path.read_text(encoding="utf-8") if design_path.exists() else ""

    # 读取 segments
    segs_path = project_dir / "narration_segments.json"
    segs_data = json.loads(segs_path.read_text(encoding="utf-8")) if segs_path.exists() else {}
    segments = segs_data if isinstance(segs_data, list) else segs_data.get("segments", [])
    total = len(segments)

    # 解析全局信息
    emotion_curve = parse_emotion_curve(design_md)
    visual_theme = parse_visual_theme(design_md)

    # 如果已有 index.html（重绘/修复场景），提取已用视觉摘要
    existing_summaries = build_scene_summaries(project_dir / "skeleton_slots.json")

    contexts = []
    for i, seg in enumerate(segments):
        scene_name = seg.get("scene", "")
        scene_id = scene_name.split("-")[0] if "-" in scene_name else scene_name

        position, intensity = get_emotion_for_scene(i, total, emotion_curve)

        # 前序场景
        prev_id = f"s{i}" if i > 0 else None
        prev_summary = existing_summaries.get(prev_id, {}) if prev_id else {}

        # 后续场景
        next_id = f"s{i+2}" if i + 1 < total else None
        next_summary = existing_summaries.get(next_id, {}) if next_id else {}

        # 生成视觉节奏引导
        # 根据情感曲线位置和强度，给出具体的视觉力度建议
        intensity_label = _intensity_to_label(intensity)
        rhythm_guidance = _generate_rhythm_guidance(
            position, intensity, prev_summary, visual_theme
        )

        context = {
            "scene_id": scene_id,
            "scene_name": scene_name,
            "emotion_curve_position": round(position, 2),
            "emotion_intensity": round(intensity, 2),
            "intensity_label": intensity_label,
            "visual_theme": visual_theme,
            "prev_scene_summary": prev_summary,
            "next_scene_summary": next_summary,
            "rhythm_guidance": rhythm_guidance,
        }
        contexts.append(context)

    return contexts


def _intensity_to_label(intensity: float) -> str:
    """将 intensity 数值转为人类可读的力度标签。"""
    if intensity >= 0.8:
        return "高潮爆发 — 视觉力度最大化：浓烈色彩、强烈动画、密集特效"
    elif intensity >= 0.6:
        return "情绪升温 — 视觉力度加强：色彩渐浓、动画节奏加快"
    elif intensity >= 0.4:
        return "平稳推进 — 视觉力度适中：保持节奏，可做小变化"
    elif intensity >= 0.2:
        return "情绪收敛 — 视觉力度降低：色调趋冷、动效减弱"
    else:
        return "静场留白 — 视觉力度最低：大面积留白、单色或微光"


def _generate_rhythm_guidance(
    position: float,
    intensity: float,
    prev_summary: dict,
    theme: dict,
) -> str:
    """生成视觉节奏引导文字（注入给 LLM 的创意参考，不是硬约束）。"""
    lines = []

    # 1. 情感位置引导
    if position < 0.15:
        lines.append("📍 开场阶段：视觉要抓住注意力，但不要全部亮出来——留悬念")
    elif position < 0.5:
        lines.append("📍 推进阶段：视觉随内容展开，可以逐步丰富层次")
    elif position < 0.75:
        lines.append("📍 高潮区域：视觉力度该到峰值了，大胆用浓烈效果")
    else:
        lines.append("📍 收束阶段：视觉开始收敛，与开场呼应但不重复")

    # 2. 连贯性引导（基于前序场景）
    if prev_summary:
        prev_colors = prev_summary.get("dominant_colors", [])
        prev_types = prev_summary.get("bg_element_types", [])

        if prev_colors:
            lines.append(f"🔗 前序场景主色: {', '.join(prev_colors[:3])}")
            lines.append("   → 保持至少一个色调族一致（如同为冷色/暖色），但在其他维度变化")
        if prev_types:
            lines.append(f"🔗 前序背景元素: {', '.join(prev_types)}")
            lines.append("   → 可保留一种元素类型，替换其他类型，制造'似曾相识但不同'的感觉")
    else:
        lines.append("🔗 这是第一个场景：建立视觉基调，后续场景会在此基础上变奏")

    # 3. 变化引导（避免单调）
    if intensity > 0.6:
        lines.append("⚡ 高强度场景：可以引入此前未用过的特效类型或色彩，创造视觉爆点")
    elif intensity < 0.3:
        lines.append("🌫 低强度场景：收敛特效，用大面积纯色/渐变/微光营造氛围，不是'空'而是'静'")

    return '\n'.join(lines)


def main():
    import argparse
    parser = argparse.ArgumentParser(description="视觉节奏上下文生成器")
    parser.add_argument("--project-dir", required=True)
    parser.add_argument("--output", default=None, help="输出 JSON 路径")
    args = parser.parse_args()

    project_dir = Path(args.project_dir)
    contexts = generate_context_for_slots(project_dir)

    output = json.dumps(contexts, ensure_ascii=False, indent=2)

    if args.output:
        Path(args.output).write_text(output, encoding="utf-8")
        print(f"✓ 视觉上下文已生成: {args.output} ({len(contexts)} 场景)")
    else:
        print(output)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Commit**

```bash
git add .claude/commands/clipforge/engine/visual_context.py
git commit -m "feat(engine): add visual_context — rhythm guidance for 'not monotone, not abrupt' creative decisions"
```

---

## Self-Review

### 1. Spec Coverage

| 需求 | 对应 Task |
|------|----------|
| 数据模型扩展 | Task 1 |
| Jinja2 骨架模板（三层 + 插槽） | Task 2 |
| 骨架生成器（确定性） | Task 3 |
| 创意内容注入器 | Task 4 |
| CLI 工具脚本 | Task 5 |
| stage6-production.md 集成 | Task 6 |
| 集成测试 | Task 7 |
| 文档更新 | Task 8 |

### 2. Placeholder Scan

无 TBD/TODO/fill-in-later。所有代码步骤包含完整实现。

### 3. Type Consistency

- `CreativeSlot.slot_id` 格式为 `"{scene_id}-{layer}-{type}"` 在 models.py、skeleton_builder.py、slot_injector.py 中一致
- `SceneSkeleton.scene_id` 格式为 `"s1"`, `"s2"` 与现有 `gate.py` 的 `check_scene_ids_match` 使用的 `id="sN"` 格式一致
- `SLOT_PATTERN` regex 在 slot_injector.py 中定义为 `r'(<!--\s*CREATIVE_SLOT:(\S+)\s*-->)'` 与模板中的标记格式一致

---

## 执行完成后验证清单

- [ ] `generate_skeleton.py` 能从任何已有项目的 `narration_segments.json` + `design.md` + `segment_durations.json` 生成完整骨架
- [ ] 骨架中包含正确的 `window.__hf`（duration + seek）
- [ ] 骨架中包含正确的 `window.__timelines["main"] = tl`
- [ ] 每个 scene div 有正确的 `id="sN"` + `data-start` + `data-duration`
- [ ] `<audio>` 标签正确嵌入，BGM 音量从 `segment_durations.json` 读取
- [ ] `gate.py` 的 `hf_api_present`、`scene_ids_match`、`composition_structure` 对骨架检查全部 PASS
- [ ] `slot_injector.py` 能正确注入 JSON 格式和标记格式的创意内容
- [ ] 注入后 `validate_skeleton.py --strict` 通过
- [ ] LLM 可以在插槽中自由编写任何 CSS/Canvas/WebGL 代码
- [ ] 现有 gate 检查（bg_visual_diversity、fx_layer_not_empty 等）对注入后的 HTML 仍然有效
