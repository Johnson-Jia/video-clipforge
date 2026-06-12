"""视觉节奏上下文生成器 — 为创意插槽提供"不单调、不突兀"的上下文。

不做任何创作决策，只提供结构化上下文让 LLM 做出更好的创作选择。

三个核心概念：
1. visual_theme: 全片共享的视觉调性（来自 design.md），所有场景的"调性锚点"
2. prev_scene_summary: 前序场景的视觉指纹，帮助保持连贯
3. emotion_intensity: 当前场景在情感曲线上的位置，指导视觉力度

连续性规则（注入给 LLM 的引导，不是硬约束）：
- 与前序场景共享 >= 1 个视觉维度（色调族/纹理类型/动画节奏）
- 在 >= 1 个其他维度上制造差异
- 情感曲线高点 -> 视觉力度加强；低点 -> 收敛
"""
from __future__ import annotations
import json
import re
import sys
from pathlib import Path

# engine/ 目录需要 gate.py 所在路径可达
sys.path.insert(0, str(Path(__file__).parent))


# ──────────────────────────────────────────────────────────────────────
# 1. Emotion curve
# ──────────────────────────────────────────────────────────────────────

def parse_emotion_curve(design_md: str) -> list[float]:
    """从 design.md 提取 emotion_curve（6 拍情感强度 0.0~1.0）。

    查找 storyboard 区域中的 `emotion_curve: [v1, v2, v3, v4, v5, v6]` 格式。
    如果未找到则返回默认曲线：开场强 -> 中间低 -> 结尾收束。
    """
    match = re.search(r'emotion_curve:\s*\[([^\]]+)\]', design_md)
    if match:
        try:
            return [float(v.strip()) for v in match.group(1).split(',')]
        except ValueError:
            pass
    # 默认曲线：开场强 -> 中间低 -> 结尾收束
    return [0.8, 0.5, 0.6, 0.7, 0.4, 0.3]


def get_emotion_for_scene(
    scene_index: int,
    total_scenes: int,
    curve: list[float],
) -> tuple[float, float]:
    """获取场景在情感曲线中的 (position_0_to_1, intensity)。

    将 scene_index 线性映射到 emotion_curve 的拍点上，使用线性插值。

    Args:
        scene_index: 场景在 segments 中的 0-based 索引
        total_scenes: 总场景数
        curve: emotion_curve 数值列表（通常 6 个值）

    Returns:
        (position, intensity) — position 是 0~1 的归一化位置，
        intensity 是线性插值后的情感强度值
    """
    if total_scenes <= 1:
        return 0.0, curve[0] if curve else 0.5

    position = scene_index / (total_scenes - 1)

    if not curve:
        return position, 0.5

    # 将 position (0~1) 映射到 curve 的索引空间
    curve_pos = position * (len(curve) - 1)
    idx = int(curve_pos)
    frac = curve_pos - idx

    if idx >= len(curve) - 1:
        intensity = curve[-1]
    else:
        intensity = curve[idx] * (1 - frac) + curve[idx + 1] * frac

    return position, intensity


# ──────────────────────────────────────────────────────────────────────
# 2. Visual theme
# ──────────────────────────────────────────────────────────────────────

def parse_visual_theme(design_md: str) -> dict:
    """从 design.md 提取全片视觉主题。

    提取字段：
        color_temperature: str — 色温方向（warm / cold / cold-warm-contrast / neutral）
        saturation: str — 饱和度基调（high / moderate / low）
        brightness_range: str — 明度范围（dark-base / bright-base）
        accent_colors: list[str] — 从 color_direction 区域提取的色值列表
        immersion_mode: str — 沉浸模式标识
    """
    theme: dict = {}

    # ── color_direction 区域 ──
    cd_match = re.search(
        r'color_direction:(.*?)(?=\n##|\nstoryboard|\Z)',
        design_md, re.DOTALL,
    )
    if cd_match:
        section = cd_match.group(1)
        if '暖' in section and '冷' in section:
            theme['color_temperature'] = 'cold-warm-contrast'
        elif '暖' in section:
            theme['color_temperature'] = 'warm'
        elif '冷' in section:
            theme['color_temperature'] = 'cold'
        else:
            theme['color_temperature'] = 'neutral'

        # 提取色值（6 位 hex）
        theme['accent_colors'] = re.findall(r'#[0-9a-fA-F]{6}\b', section)
    else:
        theme['color_temperature'] = 'neutral'
        theme['accent_colors'] = []

    # ── immersion_mode ──
    m = re.search(r'immersion_mode[:\s]+["\']?(\S+)["\']?', design_md)
    theme['immersion_mode'] = m.group(1) if m else 'hyper-pace'

    # ── saturation / brightness（从 style 字段推断）──
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


# ──────────────────────────────────────────────────────────────────────
# 3. Scene summaries（从已注入的 index.html 提取视觉指纹）
# ──────────────────────────────────────────────────────────────────────

def build_scene_summaries(project_dir: Path) -> dict[str, dict]:
    """从已注入的 index.html 中提取每个场景的实际视觉摘要。

    这是"反馈循环"：第一轮 LLM 创作完成后，提取实际使用的视觉元素，
    作为第二轮创作的 prev_scene_summary 上下文。

    在第一轮（尚未注入）时返回空 dict。

    Returns:
        {scene_id: {"scene_id", "dominant_colors", "bg_element_types", "fx_types", "has_content"}}
    """
    index_path = project_dir / "index.html"
    if not index_path.exists():
        return {}

    # 复用 gate.py 的场景拆分和分类逻辑
    from engine.gate import (
        _split_into_scenes,
        _extract_layer_chunk,
        _classify_bg_element_types,
    )

    html = index_path.read_text(encoding="utf-8", errors="ignore")
    scenes = _split_into_scenes(html)
    if not scenes:
        return {}

    summaries: dict[str, dict] = {}
    for scene_id, scene_html in scenes:
        bg = _extract_layer_chunk(scene_html, "layer-bg")
        fx = _extract_layer_chunk(scene_html, "layer-fx")

        # 提取主色调（去重排序）
        colors = sorted(set(re.findall(r'#[0-9a-fA-F]{6}\b', bg)))

        # 分类 bg 层视觉元素类型
        bg_types = sorted(_classify_bg_element_types(bg)) if bg.strip() else []

        # 提取 fx 层的关键词
        fx_types: list[str] = []
        if fx:
            fx_lower = fx.lower()
            if 'canvas' in fx_lower:
                fx_types.append('canvas')
            if re.search(r'filter\s*:\s*blur', fx):
                fx_types.append('glow')
            if 'animation' in fx_lower:
                fx_types.append('animated')
            if '<svg' in fx_lower:
                fx_types.append('svg')

        summaries[scene_id] = {
            "scene_id": scene_id,
            "dominant_colors": colors[:5],
            "bg_element_types": bg_types,
            "fx_types": fx_types,
            "has_content": bool(
                re.search(r'<(h[1-6]|p|span|div)[^>]*>[^<]+', scene_html)
            ),
        }

    return summaries


# ──────────────────────────────────────────────────────────────────────
# 4. Intensity labels & rhythm guidance
# ──────────────────────────────────────────────────────────────────────

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
    """生成视觉节奏引导文字（注入给 LLM 的创意参考，不是硬约束）。

    包含三个层次的引导：
    1. 情感位置引导 — 当前在片中的大致位置和对应的视觉力度建议
    2. 连贯性引导 — 基于前序场景的视觉指纹，建议保留哪些元素
    3. 变化引导 — 基于情感强度，建议在哪些维度制造差异

    Args:
        position: 0~1 的归一化位置
        intensity: 线性插值后的情感强度
        prev_summary: 前序场景的视觉摘要（可能为空 dict）
        theme: 全片视觉主题
    """
    lines: list[str] = []

    # ── 1. 情感位置引导 ──
    if position < 0.15:
        lines.append(
            "位置：开场阶段 — 视觉必须抓住注意力，"
            "但保留最强效果用于后续铺垫悬念"
        )
    elif position < 0.5:
        lines.append(
            "位置：递进阶段 — 视觉可以随内容展开"
            "逐步丰富层次"
        )
    elif position < 0.75:
        lines.append(
            "位置：高潮区域 — 视觉力度应达到峰值，"
            "大胆使用强烈特效"
        )
    else:
        lines.append(
            "位置：收尾阶段 — 视觉开始收敛，"
            "呼应开场但不重复"
        )

    # ── 2. 连贯性引导（基于前序场景） ──
    if prev_summary:
        prev_colors = prev_summary.get("dominant_colors", [])
        prev_types = prev_summary.get("bg_element_types", [])

        if prev_colors:
            lines.append(
                f"前序场景色彩: {', '.join(prev_colors[:3])}"
            )
            lines.append(
                "  -> 至少保留一个色系一致（暖色/冷色），"
                "在其他维度制造变化"
            )
        if prev_types:
            lines.append(
                f"前序背景元素: {', '.join(prev_types)}"
            )
            lines.append(
                "  -> 保留一种元素类型，替换其他类型，"
                "营造'熟悉又不同'的感觉"
            )
    else:
        lines.append(
            "首个场景：建立视觉基调，"
            "后续场景将在此基础上构建"
        )

    # ── 3. 变化引导（避免单调） ──
    if intensity > 0.6:
        lines.append(
            "高强度：引入此前未使用的特效类型或色彩，"
            "制造视觉冲击"
        )
    elif intensity < 0.3:
        lines.append(
            "低强度：减少特效，使用大面积纯色/渐变/柔光"
            "营造氛围 — 不是'空洞'而是'沉静'"
        )

    return '\n'.join(lines)


# ──────────────────────────────────────────────────────────────────────
# 5. Main entry point
# ──────────────────────────────────────────────────────────────────────

def generate_context_for_slots(
    project_dir: Path,
) -> list[dict]:
    """为项目所有创意插槽生成完整的视觉上下文。

    输出格式：与 skeleton_slots.json 兼容，每个场景一个 dict。

    Args:
        project_dir: 项目目录（包含 design.md, narration_segments.json 等）

    Returns:
        list of context dicts, 每个包含:
          scene_id, scene_name,
          emotion_curve_position, emotion_intensity, intensity_label,
          visual_theme, prev_scene_summary, next_scene_summary,
          rhythm_guidance
    """
    # ── 读取 design.md ──
    design_path = project_dir / "design.md"
    design_md = design_path.read_text(encoding="utf-8") if design_path.exists() else ""

    # ── 读取 segments ──
    segs_path = project_dir / "narration_segments.json"
    if segs_path.exists():
        segs_data = json.loads(segs_path.read_text(encoding="utf-8"))
    else:
        segs_data = {}

    segments = segs_data if isinstance(segs_data, list) else segs_data.get("segments", [])
    total = len(segments)

    # ── 解析全局信息 ──
    emotion_curve = parse_emotion_curve(design_md)
    visual_theme = parse_visual_theme(design_md)

    # ── 如果已有 index.html（重绘/修复场景），提取已用视觉摘要 ──
    existing_summaries = build_scene_summaries(project_dir)

    contexts: list[dict] = []
    for i, seg in enumerate(segments):
        scene_name = str(seg.get("scene", ""))
        scene_id = scene_name.split("-")[0] if "-" in scene_name else scene_name

        position, intensity = get_emotion_for_scene(i, total, emotion_curve)

        # ── 前序场景 ──
        prev_id = f"s{i}" if i > 0 else None
        prev_summary = existing_summaries.get(prev_id, {}) if prev_id else {}

        # ── 后续场景 ──
        next_id = f"s{i + 2}" if i + 1 < total else None
        next_summary = existing_summaries.get(next_id, {}) if next_id else {}

        # ── 生成视觉节奏引导 ──
        intensity_label = _intensity_to_label(intensity)
        rhythm_guidance = _generate_rhythm_guidance(
            position, intensity, prev_summary, visual_theme,
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


# ──────────────────────────────────────────────────────────────────────
# 6. CLI
# ──────────────────────────────────────────────────────────────────────

def main():
    """CLI 入口：生成视觉节奏上下文 JSON。"""
    import argparse

    parser = argparse.ArgumentParser(
        description="ClipForge visual context — rhythm guidance for creative slots",
    )
    parser.add_argument(
        "--project-dir", required=True,
        help="Project directory containing design.md, narration_segments.json, etc.",
    )
    parser.add_argument(
        "--output", default=None,
        help="Output JSON path (default: stdout)",
    )
    args = parser.parse_args()

    project_dir = Path(args.project_dir)
    contexts = generate_context_for_slots(project_dir)

    output = json.dumps(contexts, ensure_ascii=False, indent=2)

    if args.output:
        Path(args.output).write_text(output, encoding="utf-8")
        print(f"Visual context generated: {args.output} ({len(contexts)} scenes)")
    else:
        print(output)


if __name__ == "__main__":
    main()
