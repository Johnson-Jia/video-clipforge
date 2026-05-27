#!/usr/bin/env python3
"""
Phase 断点计算器（内容对齐）

根据 narration_segments.json 中的 visual_phases 和旁白文本，
按字数比例计算 Phase 切换断点。禁止均分。

用法:
  python scripts/compute_phase_breakpoints.py [--project-dir DIR] [--scene INDEX]

输出:
  JSON 格式的断点数组到 stdout
  例: {"scene": 0, "breakpoints": [3.21, 16.72], "duration": 50.14}
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


def find_text_boundary(text, focus_keyword):
    """
    在旁白文本中找到与 focus 关键词对应的段落边界。
    返回边界字符位置（占总字符数的比例）。
    """
    if not focus_keyword or not text:
        return None

    # 按句号/问号/感叹号分段
    sentences = [s.strip() for s in __import__('re').split(r'[。！？；\n]', text) if s.strip()]

    # 找到包含 focus 关键词的句子
    for idx, sentence in enumerate(sentences):
        if focus_keyword in sentence:
            # 计算该句结尾在全文中的字符位置比例
            char_count = sum(len(s) + 1 for s in sentences[:idx + 1])  # +1 for delimiter
            total_chars = sum(len(s) + 1 for s in sentences)
            return char_count / total_chars if total_chars > 0 else 0.5

    # 关键词未精确匹配，尝试模糊匹配（取前几个字）
    short_keyword = focus_keyword[:6]
    for idx, sentence in enumerate(sentences):
        if short_keyword in sentence:
            char_count = sum(len(s) + 1 for s in sentences[:idx + 1])
            total_chars = sum(len(s) + 1 for s in sentences)
            return char_count / total_chars if total_chars > 0 else 0.5

    return None


def compute_breakpoints(segment):
    """
    计算单个场景的 Phase 断点。
    返回 (breakpoints_list, duration) 或 (None, 0)
    """
    phases = segment.get('visual_phases', [])
    if len(phases) <= 1:
        return None, 0

    text = segment.get('text', '')
    duration = segment.get('duration', segment.get('dur', 10))

    breakpoints = []
    for i in range(1, len(phases)):
        focus = phases[i].get('focus', '')
        ratio = find_text_boundary(text, focus)

        if ratio is None:
            # 无法定位，按 Phase 数量等比估算（最后手段）
            ratio = i / len(phases)
            print(f'  WARNING: Phase {i} focus="{focus}" 未在文本中匹配，使用等比估算', file=sys.stderr)

        bp_time = round(ratio * duration, 2)
        breakpoints.append(bp_time)

    return breakpoints, duration


def main():
    parser = argparse.ArgumentParser(description='计算 Phase 断点（内容对齐）')
    parser.add_argument('--project-dir', default='.', help='项目目录')
    parser.add_argument('--scene', type=int, default=None, help='指定场景索引（不指定则输出全部）')
    parser.add_argument('--format', choices=['json', 'js'], default='json', help='输出格式')
    args = parser.parse_args()

    project_dir = os.path.abspath(args.project_dir)
    segments = load_segments(project_dir)

    results = []

    for i, seg in enumerate(segments):
        if args.scene is not None and i != args.scene:
            continue

        phases = seg.get('visual_phases', [])
        if len(phases) <= 1:
            continue

        breakpoints, duration = compute_breakpoints(seg)
        scene_class = seg.get('scene_class', f's-scene-{i+1}')

        result = {
            'scene': i,
            'scene_class': scene_class,
            'duration': duration,
            'num_phases': len(phases),
            'breakpoints': breakpoints,
        }
        results.append(result)

        if args.format == 'json':
            phases_desc = ' → '.join(p.get('focus', '?')[:20] for p in phases)
            print(f'场景 {i} ({scene_class}): {len(phases)} phases, {duration:.1f}s')
            print(f'  断点: {breakpoints}')
            print(f'  Phase: {phases_desc}')
            print()

    if args.format == 'js':
        # 输出 JS 数组格式
        print('const BP = [')
        for r in results:
            bp_str = ', '.join(f'{bp:.2f}' for bp in r['breakpoints'])
            phases_desc = ' → '.join(
                seg.get('visual_phases', [{}])[p].get('focus', '?')[:15]
                for p in range(len(seg.get('visual_phases', [])))
            ) if r['scene'] < len(segments) else ''
            print(f'  [{bp_str}],  // {r["scene"]}: {r["scene_class"]}')
        print('];')
    elif args.format == 'json' and results:
        # 最后输出一个汇总 JSON
        print('--- 汇总 JSON ---')
        print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
