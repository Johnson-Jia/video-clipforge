#!/usr/bin/env python3
"""
分段 TTS 生成 + 时长测量

用法: python scripts/tts_segments.py <VOICE> <RATE>
  VOICE: edge-tts 音色，如 zh-CN-YunjianNeural
  RATE:  语速，如 +25%

输入: narration_segments.json（Stage 3 产出）
输出: segment_durations.json, narration_seg_*.mp3, narration_seg_*.srt, narration_seg_*.txt

工作目录必须在项目目录下。
"""
import json, subprocess, sys, os, glob

def main():
    if len(sys.argv) < 3:
        print("用法: python scripts/tts_segments.py <VOICE> <RATE>")
        sys.exit(1)

    voice = sys.argv[1]
    rate = sys.argv[2]

    with open('narration_segments.json', 'r', encoding='utf-8') as f:
        segments = json.load(f)

    durations = []
    for i, seg in enumerate(segments):
        text_file = f'narration_seg_{i}.txt'
        mp3_file = f'narration_seg_{i}.mp3'
        srt_file = f'narration_seg_{i}.srt'

        with open(text_file, 'w', encoding='utf-8') as f:
            f.write(seg['text'])

        subprocess.run([
            'python', '-m', 'edge_tts',
            '-f', text_file,
            '-v', voice,
            '--rate', rate,
            '--write-media', mp3_file,
            '--write-subtitles', srt_file
        ], check=True)

        result = subprocess.run([
            'ffprobe', '-v', 'quiet', '-show_entries', 'format=duration',
            '-of', 'csv=p=0', mp3_file
        ], capture_output=True, text=True)
        dur = float(result.stdout.strip())
        durations.append({'scene': seg['scene'], 'actual_duration': round(dur, 2)})
        print(f'[Seg {i}] {seg["scene"]}: {dur:.2f}s')

    output = {
        'meta': {'voice': voice, 'rate': rate},
        'segments': durations
    }
    with open('segment_durations.json', 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    total = sum(d['actual_duration'] for d in durations)
    print(f'Total: {total:.2f}s')
    print(f'Voice: {voice}, Rate: {rate}')

if __name__ == '__main__':
    main()
