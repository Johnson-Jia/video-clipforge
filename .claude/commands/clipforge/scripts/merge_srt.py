#!/usr/bin/env python3
"""
SRT 字幕合并 + 偏移重算

用法: python scripts/merge_srt.py

输入: narration_seg_*.srt, narration_seg_*.mp3（测时长）
输出: narration.srt

工作目录必须在项目目录下。
"""
import re, glob, subprocess

def main():
    srt_files = sorted(glob.glob('narration_seg_*.srt'))
    offset = 0
    all_lines = []
    idx = 1

    for sf in srt_files:
        with open(sf, 'r', encoding='utf-8') as f:
            content = f.read().strip()
        if not content:
            continue
        blocks = content.split('\n\n')
        for block in blocks:
            lines = block.strip().split('\n')
            if len(lines) >= 3:
                time_match = re.match(r'(\d{2}:\d{2}:\d{2},\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2},\d{3})', lines[1])
                if time_match:
                    def add_offset(t):
                        h, m, s = t.replace(',', '.').split(':')
                        return offset + int(h)*3600 + int(m)*60 + float(s)
                    start = add_offset(time_match.group(1))
                    end = add_offset(time_match.group(2))
                    def fmt(t):
                        h = int(t // 3600); m = int((t % 3600) // 60); s = t % 60
                        return f'{h:02d}:{m:02d}:{int(s):02d},{int((s%1)*1000):03d}'
                    all_lines.append(f'{idx}\n{fmt(start)} --> {fmt(end)}\n' + '\n'.join(lines[2:]))
                    idx += 1
        mp3 = sf.replace('.srt', '.mp3')
        r = subprocess.run(['ffprobe', '-v', 'quiet', '-show_entries', 'format=duration', '-of', 'csv=p=0', mp3], capture_output=True, text=True)
        offset += float(r.stdout.strip())

    with open('narration.srt', 'w', encoding='utf-8') as f:
        f.write('\n\n'.join(all_lines))
    print(f'narration.srt: {idx-1} blocks written')

if __name__ == '__main__':
    main()
