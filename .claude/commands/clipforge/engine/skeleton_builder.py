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

# Allow running as script or as module
sys.path.insert(0, str(Path(__file__).parent.parent))
from engine.lib.models import CreativeSlot, SceneSkeleton


TEMPLATES_DIR = Path(__file__).parent / "skeleton_builder" / "templates"

# 沉浸模式 -> CSS 变量映射（从 stage6-components.md 的配色速查表提取）
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
        return {} if path.suffix == ".json" else []
    data = json.loads(path.read_text(encoding="utf-8"))
    return data


def _parse_design(project_dir: Path) -> dict:
    """从 design.md 提取关键视觉参数。"""
    design_path = project_dir / "design.md"
    if not design_path.exists():
        return {"immersion_mode": "hyper-pace", "color_direction": {}}

    content = design_path.read_text(encoding="utf-8")
    result: dict = {}

    # 提取 immersion_mode
    m = re.search(r"immersion_mode[:\s]+[\"']?(\S+)[\"']?", content)
    result["immersion_mode"] = m.group(1) if m else "hyper-pace"

    # 提取 color_direction 中的具体色值覆盖
    cd_section = re.search(
        r"color_direction:(.*?)(?=\n##|\nstoryboard|\Z)", content, re.DOTALL
    )
    color_overrides: dict[str, str] = {}
    if cd_section:
        for color_match in re.finditer(
            r"(\w+(?:_\w+)*):\s*(#[0-9a-fA-F]{3,8})", cd_section.group(1)
        ):
            color_overrides[color_match.group(1)] = color_match.group(2)
    result["color_direction"] = color_overrides

    return result


def _build_css_variables(design: dict) -> str:
    """根据 design.md 生成 CSS 变量声明。

    先取 immersion_mode 对应的基础变量，
    再用 color_direction 中的色值逐一覆盖。
    """
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


def _compute_phase_breakpoints(segment: dict, phase_timings: dict | None = None) -> list[float]:
    """为多 phase 场景计算断点。

    优先使用 phase_timings.json（TTS 句子锚点校准，精度 ±50ms），
    回退到文本比例估算。
    """
    phases = segment.get("visual_phases", [])
    if len(phases) <= 1:
        return []

    scene_name = segment.get("scene", "")

    # 优先：从 phase_timings.json 获取精确校准时间
    if phase_timings:
        for sc in phase_timings.get("scenes", []):
            if sc.get("scene") == scene_name:
                bps = []
                for p in sc.get("phases", []):
                    if p["phase"] > 1:
                        bps.append(p["start_offset"])
                return bps

    # 回退：按旁白文本比例估算
    duration = segment.get("duration", segment.get("dur", 10))
    text = segment.get("text", segment.get("narration_segment", ""))

    breakpoints: list[float] = []
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
    sentences = [s.strip() for s in re.split(r"[。！？；\n]", text) if s.strip()]
    for idx, sentence in enumerate(sentences):
        if focus_keyword in sentence or focus_keyword[:6] in sentence:
            char_count = sum(len(s) + 1 for s in sentences[: idx + 1])
            total_chars = sum(len(s) + 1 for s in sentences)
            return char_count / total_chars if total_chars > 0 else 0.5
    return None


def build_scene_skeletons(project_dir: Path) -> list[SceneSkeleton]:
    """从项目文件构建所有场景的骨架数据。

    依次读取 narration_segments.json、segment_durations.json，
    为每个 segment 生成 SceneSkeleton 及其 CreativeSlot 列表。
    """
    segs_path = project_dir / "narration_segments.json"
    segs_data = _load_json(segs_path)
    segments = segs_data if isinstance(segs_data, list) else segs_data.get("segments", [])

    # 尝试加载时长数据
    dur_path = project_dir / "segment_durations.json"
    dur_data = _load_json(dur_path)
    dur_segments = dur_data.get("segments", []) if isinstance(dur_data, dict) else dur_data

    # 加载 phase 校准数据（TTS 句子锚点）
    pt_path = project_dir / "phase_timings.json"
    phase_timings = _load_json(pt_path) if pt_path.exists() else None

    # 构建时长映射：scene_name -> {start, duration}
    duration_map: dict[str, dict[str, float]] = {}
    cumulative = 0.0
    for ds in dur_segments:
        name = ds.get("scene", ds.get("scene_name", ""))
        actual = ds.get("actual_duration", ds.get("duration", 0))
        duration_map[name] = {"start": cumulative, "duration": actual}
        cumulative += actual

    skeletons: list[SceneSkeleton] = []
    for seg in segments:
        scene_name = seg.get("scene", "")
        scene_id = scene_name.split("-")[0] if "-" in scene_name else scene_name

        # 获取时长
        dur_info = duration_map.get(scene_name, {})
        start = dur_info.get("start", seg.get("start", 0))
        duration = dur_info.get("duration", seg.get("duration", seg.get("dur", 10)))

        # Phase 断点（优先 phase_timings.json，回退文本比例估算）
        phase_breakpoints = _compute_phase_breakpoints(seg, phase_timings)

        # 构建创意插槽
        slots: list[CreativeSlot] = []

        # CSS 插槽
        slots.append(
            CreativeSlot(
                slot_id=f"{scene_id}-css",
                scene_id=scene_id,
                layer="all",
                slot_type="css",
                marker=f"<!-- CREATIVE_SLOT:{scene_id}-css -->",
            )
        )

        # bg HTML 插槽
        slots.append(
            CreativeSlot(
                slot_id=f"{scene_id}-bg-html",
                scene_id=scene_id,
                layer="bg",
                slot_type="html",
                marker=f"<!-- CREATIVE_SLOT:{scene_id}-bg-html -->",
                scene_duration=duration,
                emotion_tags=seg.get("emotion_tags", []),
                visual_intent=(
                    seg.get("visual_intent", {}).get("bg", {})
                    if isinstance(seg.get("visual_intent"), dict)
                    else {}
                ),
            )
        )

        # fx HTML 插槽
        slots.append(
            CreativeSlot(
                slot_id=f"{scene_id}-fx-html",
                scene_id=scene_id,
                layer="fx",
                slot_type="html",
                marker=f"<!-- CREATIVE_SLOT:{scene_id}-fx-html -->",
                scene_duration=duration,
            )
        )

        # content HTML 插槽（单 phase 或多 phase）
        phases = seg.get("visual_phases", [])
        if len(phases) <= 1:
            slots.append(
                CreativeSlot(
                    slot_id=f"{scene_id}-content-html",
                    scene_id=scene_id,
                    layer="content",
                    slot_type="html",
                    marker=f"<!-- CREATIVE_SLOT:{scene_id}-content-html -->",
                    scene_duration=duration,
                    narration_text=seg.get("text", seg.get("narration_segment", "")),
                )
            )
        else:
            for pi, phase in enumerate(phases, 1):
                slots.append(
                    CreativeSlot(
                        slot_id=f"{scene_id}-phase{pi}-html",
                        scene_id=scene_id,
                        layer="content",
                        slot_type="html",
                        marker=f"<!-- CREATIVE_SLOT:{scene_id}-phase{pi}-html -->",
                        scene_duration=duration,
                        narration_text=phase.get("text", ""),
                        visual_intent=phase,
                    )
                )

        # GSAP 动画插槽
        slots.append(
            CreativeSlot(
                slot_id=f"{scene_id}-gsap",
                scene_id=scene_id,
                layer="all",
                slot_type="gsap",
                marker=f"<!-- CREATIVE_SLOT:{scene_id}-gsap -->",
                scene_duration=duration,
            )
        )

        skeletons.append(
            SceneSkeleton(
                scene_id=scene_id,
                scene_name=scene_name,
                start=start,
                duration=duration,
                visual_phases=phases,
                phase_breakpoints=phase_breakpoints,
                slots=slots,
            )
        )

    return skeletons


def render_skeleton(
    project_dir: Path, output_path: Path | None = None
) -> tuple[str, list[SceneSkeleton]]:
    """渲染完整 HTML 骨架，返回 (html_string, scene_skeletons)。

    加载 Jinja2 composition.html.j2 模板（场景 HTML 已内联），
    注入 CSS 变量、音频音量、场景列表和总时长后渲染。
    """
    design = _parse_design(project_dir)
    css_variables = _build_css_variables(design)
    skeletons = build_scene_skeletons(project_dir)

    # 加载 BGM 音量
    dur_data = _load_json(project_dir / "segment_durations.json")
    bgm_volume = (
        dur_data.get("meta", {}).get("bgm_volume", 0.06)
        if isinstance(dur_data, dict)
        else 0.06
    )

    # 计算总时长
    total_duration = sum(s.duration for s in skeletons)

    # 加载 phase_timings.json 供模板注入
    pt_path = project_dir / "phase_timings.json"
    phase_timings_data = _load_json(pt_path) if pt_path.exists() else {}
    phase_timings_json = json.dumps(phase_timings_data, ensure_ascii=False)

    # 准备场景数据（Jinja2 模板所需的扁平结构）
    scenes: list[dict] = []
    for sk in skeletons:
        scenes.append(
            {
                "scene_id": sk.scene_id,
                "scene_name": sk.scene_name,
                "start": sk.start,
                "duration": sk.duration,
                "visual_phases": sk.visual_phases,
                "phase_breakpoints": sk.phase_breakpoints,
            }
        )

    # Jinja2 渲染 — 只加载 composition.html.j2（场景 HTML 已内联）
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
        base_bg_css="background: #000;",
        scenes=scenes,
        bgm_volume=bgm_volume,
        total_duration=total_duration,
        phase_timings_json=phase_timings_json,
    )

    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(html, encoding="utf-8")

    return html, skeletons


def main() -> None:
    """CLI 入口：生成 HTML 骨架 + 可选的插槽清单 JSON。"""
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
        slots_data: list[dict] = []
        for sk in skeletons:
            for slot in sk.slots:
                slots_data.append(
                    {
                        "slot_id": slot.slot_id,
                        "scene_id": slot.scene_id,
                        "layer": slot.layer,
                        "slot_type": slot.slot_type,
                        "marker": slot.marker,
                        "scene_duration": slot.scene_duration,
                        "emotion_tags": slot.emotion_tags,
                        "visual_intent": slot.visual_intent,
                        "narration_text": slot.narration_text,
                    }
                )
        slots_path = Path(args.slots_json)
        slots_path.parent.mkdir(parents=True, exist_ok=True)
        slots_path.write_text(
            json.dumps(slots_data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"插槽清单已输出: {args.slots_json} ({len(slots_data)} 个插槽)")


if __name__ == "__main__":
    main()
