#!/usr/bin/env python3
"""
CSS 样式骨架生成器

从 design.md 读取风格方向，生成场景通用 CSS 骨架（三层架构 + 安全区 padding）。
作为 Stage 6 的脚手架，AI 在此基础上补充具体样式。

用法:
  python scripts/generate_css_boilerplate.py [--project-dir DIR] [--output styles.css]

输出:
  CSS 代码到 stdout 或指定文件
"""

import argparse
import json
import os
import re
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# 安全区 padding（单层 padding 原则）— 按方向选择
SAFE_PADDING_PORTRAIT = '180px 80px 220px 80px'
SAFE_PADDING_LANDSCAPE = '60px 120px 60px 120px'

# 画布尺寸
CANVAS_PORTRAIT = (1080, 1920)
CANVAS_LANDSCAPE = (1920, 1080)

# 字号标准（竖屏/横屏）— 与 director-toolkit.md 排版表对齐
FONT_SIZES = {
    'portrait': {
        'phase_title': 72,
        'phase_header': 56,
        'feature_card': 36,
        'data_label': 32,
        'data_value': 36,
    },
    'landscape': {
        'phase_title': 64,
        'phase_header': 52,
        'feature_card': 32,
        'data_label': 28,
        'data_value': 32,
    },
}


def parse_design_style(project_dir):
    """从 design.md 读取风格"""
    path = os.path.join(project_dir, 'design.md')
    if not os.path.exists(path):
        return {}
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    style = {}
    m = re.search(r'style:\s*(.+)', content)
    if m:
        style['style'] = m.group(1).strip()
    m = re.search(r'immersion_mode:\s*["\']?(\S+)["\']?', content)
    if m:
        style['immersion_mode'] = m.group(1)
    return style


def load_segments(project_dir):
    """加载场景列表"""
    path = os.path.join(project_dir, 'narration_segments.json')
    if not os.path.exists(path):
        return []
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data if isinstance(data, list) else data.get('segments', [])


def get_base_colors(immersion_mode):
    """根据沉浸模式返回基础配色"""
    palettes = {
        'hyper-pace': {
            'bg': 'linear-gradient(135deg, #0a0a0f 0%, #1a1a2e 50%, #16213e 100%)',
            'accent_cool': '#00f5d4',
            'accent_warm': '#f9a825',
            'text': '#ffffff',
        },
        'hidden-gem': {
            'bg': 'linear-gradient(135deg, #0f0f1a 0%, #1a1a3e 50%, #2d1b4e 100%)',
            'accent_cool': '#a78bfa',
            'accent_warm': '#fbbf24',
            'text': '#ffffff',
        },
        'mega-update': {
            'bg': 'linear-gradient(135deg, #0a0a0f 0%, #0d1b2a 50%, #1b2838 100%)',
            'accent_cool': '#00d4ff',
            'accent_warm': '#ff6b35',
            'text': '#ffffff',
        },
        'versus': {
            'bg': 'linear-gradient(135deg, #0a0a0f 0%, #1a0a0a 50%, #2a1a1a 100%)',
            'accent_cool': '#4cc9f0',
            'accent_warm': '#ef4444',
            'text': '#ffffff',
        },
        'story-time': {
            'bg': 'linear-gradient(135deg, #0f0f1a 0%, #1a1a2e 50%, #0f2027 100%)',
            'accent_cool': '#7dd3fc',
            'accent_warm': '#fbbf24',
            'text': '#ffffff',
        },
        'fun-tool': {
            'bg': 'linear-gradient(135deg, #0a0a1a 0%, #1a1a3e 50%, #2e1065 100%)',
            'accent_cool': '#34d399',
            'accent_warm': '#f59e0b',
            'text': '#ffffff',
        },
    }
    return palettes.get(immersion_mode, palettes['hyper-pace'])


def get_orientation_config(orientation):
    """根据方向返回配置"""
    if orientation == 'landscape':
        return {
            'padding': SAFE_PADDING_LANDSCAPE,
            'canvas_w': CANVAS_LANDSCAPE[0],
            'canvas_h': CANVAS_LANDSCAPE[1],
            'fonts': FONT_SIZES['landscape'],
        }
    return {
        'padding': SAFE_PADDING_PORTRAIT,
        'canvas_w': CANVAS_PORTRAIT[0],
        'canvas_h': CANVAS_PORTRAIT[1],
        'fonts': FONT_SIZES['portrait'],
    }


def generate_css(segments, colors, orientation='portrait'):
    """生成 CSS 骨架"""
    cfg = get_orientation_config(orientation)
    fonts = cfg['fonts']

    lines = []
    lines.append(f'/* ClipForge 场景样式骨架（自动生成） — {orientation} */')
    lines.append('/* 安全区 padding: 单层原则 — padding 只设在 .phase 或直接子元素上 */')
    lines.append('')

    # 通用样式
    lines.append('/* ── 通用 ── */')
    lines.append('* { margin: 0; padding: 0; box-sizing: border-box; }')
    lines.append('body {')
    lines.append(f'  background: {colors["bg"]};')
    lines.append('  font-family: "Noto Sans SC", "PingFang SC", sans-serif;')
    lines.append(f'  color: {colors["text"]};')
    lines.append('  overflow: hidden;')
    lines.append('}')
    lines.append('')

    # 三层架构
    lines.append('/* ── 三层架构 ── */')
    lines.append(f'.clip {{ position: relative; width: {cfg["canvas_w"]}px; height: {cfg["canvas_h"]}px; overflow: hidden; }}')
    lines.append('.scene-wrap { position: relative; width: 100%; height: 100%; }')
    lines.append('  /* scene-wrap 不设 padding — padding 由 .phase 统一管理 */')
    lines.append('.layer-bg { position: absolute; inset: 0; z-index: 1; }')
    lines.append('.layer-fx { position: absolute; inset: 0; z-index: 2; pointer-events: none; }')
    lines.append('.layer-content { position: relative; z-index: 3; height: 100%; }')
    lines.append('')

    # Phase 样式
    lines.append('/* ── Phase（视觉分镜）── */')
    lines.append('.phase {')
    lines.append(f'  position: absolute; inset: 0;')
    lines.append(f'  padding: {cfg["padding"]};')
    lines.append('  display: flex; flex-direction: column; justify-content: center;')
    lines.append('  opacity: 1;  /* Phase 1 默认可见，Phase 2+ 由 GSAP .set() 控制 */')
    lines.append('}')
    lines.append('')

    # 配色变量
    lines.append('/* ── 配色变量 ── */')
    lines.append(':root {')
    lines.append(f'  --accent-cool: {colors["accent_cool"]};')
    lines.append(f'  --accent-warm: {colors["accent_warm"]};')
    lines.append(f'  --text-primary: {colors["text"]};')
    lines.append('  --text-secondary: rgba(255,255,255,0.6);')
    lines.append('  --bg-card: rgba(255,255,255,0.06);')
    lines.append('  --border-subtle: rgba(255,255,255,0.1);')
    lines.append('}')
    lines.append('')

    # 各场景占位
    lines.append('/* ── 场景样式 ── */')
    for i, seg in enumerate(segments):
        scene_class = seg.get('scene_class', f's-scene-{i+1}')
        num_phases = len(seg.get('visual_phases', []))
        lines.append(f'.{scene_class} {{ /* TODO: 场景特定样式 */ }}')
        if num_phases > 1:
            for p in range(1, num_phases + 1):
                lines.append(f'.{scene_class} .phase-{p} {{ /* TODO: Phase {p} 样式 */ }}')
        lines.append('')

    # 通用组件
    lines.append('/* ── 通用组件样式 ── */')
    lines.append(f'.phase-title {{ font-size: {fonts["phase_title"]}px; font-weight: 800; margin-bottom: 32px; }}')
    lines.append(f'.phase-header {{ font-size: {fonts["phase_header"]}px; font-weight: 700; margin-bottom: 24px; color: var(--accent-cool); }}')
    lines.append('.feature-card {')
    lines.append('  background: var(--bg-card); border: 1px solid var(--border-subtle);')
    lines.append('  border-radius: 16px; padding: 24px 32px; margin-bottom: 16px;')
    lines.append(f'  font-size: {fonts["feature_card"]}px;')
    lines.append('}')
    lines.append('.data-row { display: flex; justify-content: space-between; padding: 12px 0; border-bottom: 1px solid var(--border-subtle); }')
    lines.append(f'.data-label {{ color: var(--text-secondary); font-size: {fonts["data_label"]}px; }}')
    lines.append(f'.data-value {{ color: var(--accent-warm); font-size: {fonts["data_value"]}px; font-weight: 700; }}')

    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description='生成场景 CSS 骨架')
    parser.add_argument('--project-dir', default='.', help='项目目录')
    parser.add_argument('--output', default=None, help='输出文件路径（默认 stdout）')
    parser.add_argument('--orientation', choices=['portrait', 'landscape'], default='portrait',
                        help='画布方向（默认 portrait）')
    args = parser.parse_args()

    project_dir = os.path.abspath(args.project_dir)
    design = parse_design_style(project_dir)
    immersion = design.get('immersion_mode', 'hyper-pace')
    colors = get_base_colors(immersion)
    segments = load_segments(project_dir)

    css = generate_css(segments, colors, orientation=args.orientation)

    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(css)
        print(f'CSS 骨架已写入: {args.output}（{len(segments)} 场景, 模式: {immersion}, 方向: {args.orientation}）')
    else:
        print(css)


if __name__ == '__main__':
    main()
