#!/usr/bin/env python3
"""
交付报告生成器

收集项目目录中的关键文件信息，生成 douyin.md 格式的交付报告。

用法:
  python scripts/delivery_report.py [--project-dir DIR]

输出:
  douyin.md — 写入项目目录
"""

import argparse
import json
import os
import re
import subprocess
import sys
import io
from datetime import datetime

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')


def get_duration(filepath):
    """获取音视频文件时长"""
    try:
        result = subprocess.run(
            ['ffprobe', '-v', 'quiet', '-show_entries', 'format=duration',
             '-of', 'csv=p=0', filepath],
            capture_output=True, text=True, timeout=10
        )
        return float(result.stdout.strip())
    except Exception:
        return 0


def get_file_size(filepath):
    """获取文件大小"""
    try:
        return os.path.getsize(filepath)
    except OSError:
        return 0


def format_size(size_bytes):
    """格式化文件大小"""
    if size_bytes < 1024:
        return f'{size_bytes} B'
    elif size_bytes < 1024 * 1024:
        return f'{size_bytes / 1024:.1f} KB'
    else:
        return f'{size_bytes / (1024 * 1024):.1f} MB'


def load_json_safe(filepath):
    """安全加载 JSON"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return None


def extract_title_from_segments(segments):
    """从旁白段提取标题"""
    if not segments:
        return '视频标题'
    text = segments[0].get('text', '')
    first = re.split(r'[。！？\n]', text)[0].strip()
    return first[:40] if first else '视频标题'


def extract_tags(segments, content_summary=None):
    """提取标签建议"""
    tags = []
    # 从内容摘要提取关键词
    if content_summary:
        keywords = re.findall(r'[一-鿿]{2,6}', content_summary[:500])
        # 取高频词
        from collections import Counter
        counter = Counter(keywords)
        tags = [w for w, _ in counter.most_common(5) if len(w) >= 2]
    return tags[:5]


def main():
    parser = argparse.ArgumentParser(description='生成交付报告')
    parser.add_argument('--project-dir', default='.', help='项目目录')
    args = parser.parse_args()

    project_dir = os.path.abspath(args.project_dir)

    # 收集信息
    segments_data = load_json_safe(os.path.join(project_dir, 'narration_segments.json'))
    segments = segments_data if isinstance(segments_data, list) else (segments_data or {}).get('segments', [])
    sd_data = load_json_safe(os.path.join(project_dir, 'segment_durations.json'))

    title = extract_title_from_segments(segments)

    # 读取内容摘要
    content_summary = ''
    for fname in ['content_summary.md', 'content.md']:
        fpath = os.path.join(project_dir, fname)
        if os.path.exists(fpath):
            with open(fpath, 'r', encoding='utf-8') as f:
                content_summary = f.read()
            break

    # 文件信息
    files_info = {}
    for fname in ['final.mp4', 'final_no_bgm.mp4', 'cover.png', 'narration.mp3']:
        fpath = os.path.join(project_dir, fname)
        if os.path.exists(fpath):
            files_info[fname] = {
                'size': format_size(get_file_size(fpath)),
                'duration': f'{get_duration(fpath):.1f}s' if fname.endswith(('.mp4', '.mp3')) else '-',
            }

    # 时长信息
    final_duration = get_duration(os.path.join(project_dir, 'final.mp4'))
    minutes = int(final_duration) // 60
    seconds = int(final_duration) % 60

    # 标签
    tags = extract_tags(segments, content_summary)
    tags_str = ' '.join(f'#{t}' for t in tags) if tags else '#AI视频 #科技'

    # 生成报告
    report = f"""# {title}

## 交付信息
- 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}
- 视频时长: {minutes}分{seconds}秒 ({final_duration:.1f}s)
- 场景数量: {len(segments)}

## 文件清单
"""
    for fname, info in files_info.items():
        report += f"- `{fname}`: {info['size']}"
        if info['duration'] != '-':
            report += f", {info['duration']}"
        report += '\n'

    report += f"""
## 发布信息
- 标题: {title}
- 标签: {tags_str}

## 备注
- 此视频由 ClipForge 自动生成
- 封面: cover.png
- 无配乐版: final_no_bgm.mp4
"""

    output_path = os.path.join(project_dir, 'douyin.md')
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(report)

    print(f'交付报告已写入: {output_path}')
    print(f'标题: {title}')
    print(f'时长: {minutes}分{seconds}秒')
    print(f'标签: {tags_str}')


if __name__ == '__main__':
    main()
