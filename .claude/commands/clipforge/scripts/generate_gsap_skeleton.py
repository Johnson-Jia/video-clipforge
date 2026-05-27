#!/usr/bin/env python3
"""
GSAP Timeline 骨架生成器

从 narration_segments.json 读取场景列表，生成 GSAP timeline JavaScript 骨架代码。
每个场景生成入场/退场占位、Phase 初始化（如有）、呼吸帧插入点。

用法:
  python scripts/generate_gsap_skeleton.py [--project-dir DIR] [--output gsap_skeleton.js]

输出:
  JavaScript 代码到 stdout 或指定文件
"""

import argparse
import json
import os
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')


def load_segments(project_dir):
    """加载 narration_segments.json"""
    path = os.path.join(project_dir, 'narration_segments.json')
    if not os.path.exists(path):
        print(f'ERROR: {path} 不存在', file=sys.stderr)
        sys.exit(1)
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data if isinstance(data, list) else data.get('segments', [])


def generate_skeleton(segments):
    """生成 GSAP timeline 骨架代码"""
    lines = []
    lines.append('// GSAP Timeline 骨架（自动生成，需手动补充动画细节）')
    lines.append('// 生成命令: python scripts/generate_gsap_skeleton.py')
    lines.append('')
    lines.append('const tl = gsap.timeline({})')
    lines.append('const S = [  // 场景配置数组')

    for i, seg in enumerate(segments):
        start = seg.get('start', 0)
        duration = seg.get('duration', seg.get('dur', 10))
        scene_class = seg.get('scene_class', f's-scene-{i+1}')
        num_phases = len(seg.get('visual_phases', []))
        text_preview = seg.get('text', '')[:30].replace('\n', ' ')
        lines.append(f'  {{id:{i}, cls:\'{scene_class}\', start:{start}, d:{duration:.2f}, p:{num_phases}, hint:\'{text_preview}...\'}},')

    lines.append('];')
    lines.append('')

    # 生成 Phase 断点占位数组
    has_phases = [s for s in segments if len(s.get('visual_phases', [])) > 1]
    if has_phases:
        lines.append('// Phase 断点占位（内容对齐，禁止均分）')
        lines.append('// 每行: [P1→P2时间, P2→P3时间, ...]')
        lines.append('const BP = [')
        for i, seg in enumerate(segments):
            num_phases = len(seg.get('visual_phases', []))
            if num_phases > 1:
                bp_count = num_phases - 1
                scene_class = seg.get('scene_class', f's-scene-{i+1}')
                phases_hint = ' → '.join(
                    vp.get('focus', '?')[:15]
                    for vp in seg.get('visual_phases', [])[:3]
                )
                lines.append(f'  [/* TODO */],  // {i}: {scene_class} — {phases_hint}')
        lines.append('];')
        lines.append('')

    # 生成场景循环骨架
    lines.append('S.forEach((sc, i) => {')
    lines.append('  const SCENE_START = sc.start;')
    lines.append('')
    lines.append('  // ── 场景入场动画 ──')
    lines.append('  // TODO: 添加入场动画（from opacity:0 / y:20 等）')
    lines.append('  // tl.from(\'.\' + sc.cls + \' ...\', {opacity:0, y:20, duration:0.4}, SCENE_START);')
    lines.append('')

    # Phase 初始化
    has_phases_in_seg = [s for s in segments if len(s.get('visual_phases', [])) > 1]
    if has_phases_in_seg:
        lines.append('  // ── Phase 初始化（多 phase 场景）──')
        lines.append('  if (sc.p > 1) {')
        lines.append('    for (let p = 2; p <= sc.p; p++) {')
        lines.append('      tl.set(\'.\' + sc.cls + \' .phase-\' + p, {opacity: 0}, SCENE_START);')
        lines.append('    }')
        lines.append('  }')
        lines.append('')

    # Phase 切换
    if has_phases_in_seg:
        lines.append('  // ── Phase 切换 ──')
        lines.append('  if (sc.p > 1) {')
        lines.append('    const bpIdx = /* 计算此场景在 BP 中的索引 */;')
        lines.append('    const bp = BP[bpIdx];')
        lines.append('    for (let p = 1; p < sc.p; p++) {')
        lines.append('      const offset = bp[p - 1];')
        lines.append('      tl.to(\'.\' + sc.cls + \' .phase-\' + p, {opacity: 0, duration: 0.3}, SCENE_START + offset);')
        lines.append('        .to(\'.\' + sc.cls + \' .phase-\' + (p + 1), {opacity: 1, duration: 0.4}, SCENE_START + offset + 0.3);')
        lines.append('    }')
        lines.append('  }')
        lines.append('')

    # 呼吸帧
    lines.append('  // ── 场景结束呼吸帧 ──')
    lines.append('  if (i < S.length - 1) {')
    lines.append('    const breathStart = SCENE_START + sc.d - 0.3;')
    lines.append('    tl.to(\'.\' + sc.cls + \' .scene-content\', {scale: 1.02, duration: 0.15, ease: \'power1.inOut\'}, breathStart);')
    lines.append('      .to(\'.\' + sc.cls + \' .scene-content\', {scale: 1.0, duration: 0.15, ease: \'power1.inOut\'}, breathStart + 0.15);')
    lines.append('  }')
    lines.append('});')
    lines.append('')
    lines.append('// ── 手动补充区域 ──')
    lines.append('// 1. 每个 Phase 的具体入场动画（from opacity/y）')
    lines.append('// 2. 特效层动画（粒子、光效等）')
    lines.append('// 3. Canvas/Three.js 驱动回调')

    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description='生成 GSAP Timeline 骨架')
    parser.add_argument('--project-dir', default='.', help='项目目录')
    parser.add_argument('--output', default=None, help='输出文件路径（默认 stdout）')
    args = parser.parse_args()

    project_dir = os.path.abspath(args.project_dir)
    segments = load_segments(project_dir)
    skeleton = generate_skeleton(segments)

    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(skeleton)
        print(f'骨架已写入: {args.output}（{len(segments)} 个场景）')
    else:
        print(skeleton)


if __name__ == '__main__':
    main()
