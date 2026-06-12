#!/usr/bin/env python3
"""s6_prepare_creative.py — 生成 creative/ 目录骨架。

为每个场景创建一个 .html 碎片模板（带三层结构 + phase 占位 + 旁白提示），
LLM 只需在模板中填充视觉创意内容。

用法:
  python scripts/s6_prepare_creative.py --project-dir workspace/2026/06/11/xxx
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path


def load_json(path: Path) -> dict | list:
    if not path.exists():
        return {} if path.suffix == ".json" else []
    return json.loads(path.read_text(encoding="utf-8"))


def parse_css_from_design(project_dir: Path) -> str:
    """从 design.md 提取配色方向，生成 :root CSS 变量。"""
    design_path = project_dir / "design.md"
    if not design_path.exists():
        return ":root {\n  --bg-deep: #0a0a0f;\n  --accent-warm: #f0b429;\n  --accent-cool: #06b6d4;\n}"

    content = design_path.read_text(encoding="utf-8")

    # 提取 immersion_mode
    m = re.search(r'immersion_mode[:\s]+["\']?(\S+)["\']?', content)
    immersion = m.group(1).rstrip('"') if m else "hyper-pace"

    # 内置配色方案
    PALETTES = {
        "hyper-pace": {"accent-warm": "#f9a825", "accent-cool": "#00f5d4", "bg": "#080818"},
        "hidden-gem": {"accent-warm": "#fbbf24", "accent-cool": "#a78bfa", "bg": "#0f0f1a"},
        "mega-update": {"accent-warm": "#ff6b35", "accent-cool": "#00d4ff", "bg": "#0a0a0f"},
        "versus": {"accent-warm": "#ef4444", "accent-cool": "#4cc9f0", "bg": "#0a0a0f"},
        "story-time": {"accent-warm": "#fbbf24", "accent-cool": "#7dd3fc", "bg": "#0f0f1a"},
        "fun-tool": {"accent-warm": "#f59e0b", "accent-cool": "#34d399", "bg": "#0a0a1a"},
    }
    palette = PALETTES.get(immersion, PALETTES["hyper-pace"])

    # color_direction 覆盖
    cd_section = re.search(
        r"color_direction:(.*?)(?=\n##|\nstoryboard|\Z)", content, re.DOTALL
    )
    if cd_section:
        for cm in re.finditer(r"(\w+):\s*(#[0-9a-fA-F]{3,8})", cd_section.group(1)):
            key = cm.group(1)
            if "bg" in key or "background" in key or "dark" in key:
                palette["bg"] = cm.group(2)
            elif "warm" in key or "amber" in key or "gold" in key or "orange" in key:
                palette["accent-warm"] = cm.group(2)
            elif "cool" in key or "cyan" in key or "teal" in key or "green" in key:
                palette["accent-cool"] = cm.group(2)

    return (
        f":root {{\n"
        f"  --bg-deep: {palette['bg']};\n"
        f"  --accent-warm: {palette['accent-warm']};\n"
        f"  --accent-cool: {palette['accent-cool']};\n"
        f"  --text: #ffffff;\n"
        f"  --text2: rgba(255,255,255,0.6);\n"
        f"}}"
    )


def build_scene_fragment(
    scene_name: str,
    narration: str,
    duration: float,
    phases: list | None = None,
    phase_timings_scene: dict | None = None,
) -> str:
    """生成单个场景的 HTML 碎片模板。

    只包含 bg/fx/content 三层，不含 clip 包裹和 data-start（由 assemble 脚本负责）。
    """
    # Phase 处理
    num_phases = 0
    if phase_timings_scene:
        num_phases = len(phase_timings_scene.get("phases", []))
    elif phases:
        num_phases = len(phases) if isinstance(phases, list) else int(phases)

    if num_phases <= 1:
        # 单 phase — 仍用 .phase-1 包裹（padding 载体，与旧骨架一致）
        content_inner = (
            f"<!-- 旁白: {narration[:60]}... -->\n"
            f"<!-- 在此填充视觉内容 -->"
        )
        content_html = (
            f'<div class="layer-content">\n'
            f'<div class="phase phase-1">\n'
            f'{content_inner}\n'
            f'</div>\n'
            f'</div>'
        )
    else:
        # 多 phase — 生成 phase-1, phase-2 div
        phase_divs = []
        narration_sents = re.split(r"[。！？\n]", narration)
        narration_sents = [s.strip() for s in narration_sents if s.strip()]

        for pi in range(num_phases):
            pn = pi + 1
            # 分配旁白句子到各 phase
            if phase_timings_scene and pi < len(phase_timings_scene["phases"]):
                pt = phase_timings_scene["phases"][pi]
                sent_indices = pt.get("sentences", [])
                phase_text = "。".join(
                    narration_sents[i] for i in sent_indices if i < len(narration_sents)
                )
            else:
                # 均分
                per = max(1, len(narration_sents) // num_phases)
                start_i = pi * per
                end_i = start_i + per if pi < num_phases - 1 else len(narration_sents)
                phase_text = "。".join(narration_sents[start_i:end_i])

            hint = phase_text[:80] if phase_text else "(自动分配)"
            phase_divs.append(
                f'<div class="phase phase-{pn}">\n'
                f"  <!-- phase-{pn} 旁白: {hint}... -->\n"
                f"  <!-- 在此填充 phase-{pn} 视觉内容 -->\n"
                f"</div>"
            )

        content_html = f'<div class="layer-content">\n{chr(10).join(phase_divs)}\n</div>'

    # 拼装完整碎片
    return (
        f"<!-- 场景: {scene_name} | 时长: {duration:.1f}s -->\n"
        f'<div class="layer-bg">\n'
        f"  <!-- 在此填充背景（radial-gradient / conic-gradient） -->\n"
        f"</div>\n"
        f'<div class="layer-fx">\n'
        f"  <!-- 在此填充特效（fx-glow / fx-line / fx-dot） -->\n"
        f"</div>\n"
        f"{content_html}"
    )


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="ClipForge creative/ 目录骨架生成器")
    parser.add_argument("--project-dir", required=True, help="项目目录")
    args = parser.parse_args()

    project_dir = Path(args.project_dir).resolve()
    creative_dir = project_dir / "creative"
    creative_dir.mkdir(exist_ok=True)

    # 加载数据
    segs_data = load_json(project_dir / "narration_segments.json")
    segments = segs_data if isinstance(segs_data, list) else segs_data.get("segments", [])

    dur_data = load_json(project_dir / "segment_durations.json")
    dur_segments = dur_data.get("segments", []) if isinstance(dur_data, dict) else dur_data

    phase_data = load_json(project_dir / "phase_timings.json")
    phase_scenes = phase_data.get("scenes", []) if isinstance(phase_data, dict) else []

    # 建立查找表
    dur_map: dict[str, float] = {}
    for ds in dur_segments:
        name = ds.get("scene", ds.get("scene_name", ""))
        dur_map[name] = float(ds.get("actual_duration", ds.get("duration", 0)))

    pt_map: dict[str, dict] = {}
    for ps in phase_scenes:
        pt_map[ps.get("scene", "")] = ps

    # 生成 style.css
    css_vars = parse_css_from_design(project_dir)
    style_css = (
        f"{css_vars}\n\n"
        f"/* ============================================\n"
        f" * LLM 在此追加自定义组件 CSS\n"
        f" * 基础层（.clip, .layer-*, .phase, .fx-*）\n"
        f" * 由 assemble 脚本自动注入，无需重复\n"
        f" * ============================================ */\n"
    )
    (creative_dir / "style.css").write_text(style_css, encoding="utf-8")

    # 生成每个场景碎片
    created = 0
    for idx, seg in enumerate(segments, 1):
        sid = f"s{idx:02d}"
        frag_path = creative_dir / f"{sid}.html"

        scene_name = seg.get("scene", seg.get("scene_name", f"scene-{idx}"))
        narration = seg.get("text", seg.get("narration_segment", ""))
        duration = dur_map.get(scene_name, seg.get("estimated_duration", 10.0))

        phases = seg.get("visual_phases", None)
        pt_scene = pt_map.get(scene_name)

        fragment = build_scene_fragment(scene_name, narration, duration, phases, pt_scene)
        frag_path.write_text(fragment, encoding="utf-8")
        created += 1

    print(f"[OK] creative/ 目录已生成")
    print(f"  style.css: 1")
    print(f"  场景碎片: {created} (s01.html ~ s{created:02d}.html)")
    print(f"  下一步: LLM 逐个填充 sNN.html 的视觉创意内容")


if __name__ == "__main__":
    main()
