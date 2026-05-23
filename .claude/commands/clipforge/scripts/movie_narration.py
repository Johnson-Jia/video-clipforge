#!/usr/bin/env python3
"""
电影模式旁白构建：静音填充 + 合并 + loudnorm 标准化

用法: python scripts/movie_narration.py

输入:
  narration_segments.json — 含 null 段（video_clip 场景）
  clip_durations.json    — movie-clips 阶段产出的片段时长
  narration_seg_*.mp3    — 有旁白场景的音频

输出:
  narration_new.mp3 — 完整旁白（含静音填充），替代 narration.mp3

工作目录必须在项目目录下。
"""
import json, subprocess, os

def main():
    with open('narration_segments.json', 'r', encoding='utf-8') as f:
        segments = json.load(f)
    with open('clip_durations.json', 'r', encoding='utf-8') as f:
        clip_durs = json.load(f)

    # 构建 clip_durations 的 scene → duration 映射
    clip_map = {c['scene']: c['actual_duration'] for c in clip_durs['clips']}

    # 生成静音文件 + concat 列表
    concat_entries = []
    for i, seg in enumerate(segments):
        if seg.get('narration_segment') is None:
            # video_clip 场景 → 插入静音
            scene_id = seg['scene']
            dur = clip_map.get(scene_id, 5.0)
            silence_file = f'silence_{scene_id}.mp3'
            subprocess.run([
                'ffmpeg', '-y', '-f', 'lavfi',
                '-i', f'anullsrc=r=44100:cl=stereo',
                '-t', str(dur), '-c:a', 'libmp3lame',
                silence_file
            ], check=True)
            concat_entries.append(silence_file)
            print(f'[Silence] {scene_id}: {dur:.2f}s')
        else:
            # 有旁白的场景
            concat_entries.append(f'narration_seg_{i}.mp3')

    # 写入 concat 文件
    with open('concat_new.txt', 'w') as f:
        for entry in concat_entries:
            f.write(f"file '{entry}'\n")

    # 合并
    subprocess.run([
        'ffmpeg', '-y', '-f', 'concat', '-safe', '0',
        '-i', 'concat_new.txt', '-c', 'copy', 'narration_new.mp3'
    ], check=True)
    print(f'narration_new.mp3: {len(concat_entries)} segments merged')

    # loudnorm 标准化
    print('[loudnorm] Pass 1...')
    subprocess.run([
        'ffmpeg', '-i', 'narration_new.mp3',
        '-af', 'loudnorm=I=-16:TP=-1.5:LRA=11:print_format=json',
        '-f', 'null', '/dev/null'
    ], capture_output=True)

    # 提取 loudnorm 统计并 pass 2
    result = subprocess.run([
        'ffmpeg', '-i', 'narration_new.mp3',
        '-af', 'loudnorm=I=-16:TP=-1.5:LRA=11:print_format=json',
        '-f', 'null', '/dev/null'
    ], capture_output=True, text=True)
    output = result.stderr

    json_str = ''
    started = False
    for line in output.split('\n'):
        if '{' in line and not started:
            started = True
        if started:
            json_str += line + '\n'
    stats = json.loads(json_str)

    print('[loudnorm] Pass 2...')
    subprocess.run([
        'ffmpeg', '-y', '-i', 'narration_new.mp3',
        '-af', f"loudnorm=I=-16:TP=-1.5:LRA=11:measured_I={stats['input_i']}:measured_TP={stats['input_tp']}:measured_LRA={stats['input_lra']}:measured_thresh={stats['input_thresh']}:offset={stats['target_offset']}:linear=true",
        '-ar', '48000', '-ac', '1',
        'narration_new_norm.mp3'
    ], check=True)

    os.replace('narration_new_norm.mp3', 'narration_new.mp3')
    print('[loudnorm] 完成: narration_new.mp3 已标准化')

if __name__ == '__main__':
    main()
