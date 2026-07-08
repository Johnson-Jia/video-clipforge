#!/usr/bin/env python3
"""
分段 TTS 生成 + 时长测量 + 句子级时间戳提取

用法: python scripts/tts_segments.py <VOICE> <RATE>
  VOICE: edge-tts 音色，如 zh-CN-YunjianNeural
  RATE:  语速，如 +25%

输入: narration_segments.json（Stage 3 产出）
输出: segment_durations.json, sentence_timestamps.json,
      narration_seg_*.mp3, narration_seg_*.srt, narration_seg_*.txt

工作目录必须在项目目录下。
"""
import json, subprocess, sys, os, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from polyphone_fix import fix as fix_polyphone


def parse_srt(srt_path):
    """解析 SRT 文件，提取每个句子的 index、text、start、end 时间（秒）。"""
    with open(srt_path, 'r', encoding='utf-8') as f:
        content = f.read().strip()

    if not content:
        return []

    sentences = []
    blocks = re.split(r'\n\s*\n', content)
    for block in blocks:
        lines = block.strip().split('\n')
        if len(lines) < 3:
            continue

        idx = int(lines[0].strip())
        time_line = lines[1].strip()
        text = ' '.join(lines[2:]).strip()

        m = re.match(
            r'(\d{2}):(\d{2}):(\d{2})[,.](\d{3})\s*-->\s*(\d{2}):(\d{2}):(\d{2})[,.](\d{3})',
            time_line
        )
        if not m:
            continue

        start = (int(m.group(1)) * 3600 + int(m.group(2)) * 60 +
                 int(m.group(3)) + int(m.group(4)) / 1000)
        end = (int(m.group(5)) * 3600 + int(m.group(6)) * 60 +
               int(m.group(7)) + int(m.group(8)) / 1000)

        sentences.append({
            'index': idx - 1,
            'text': text,
            'start': round(start, 3),
            'end': round(end, 3)
        })

    return sentences


def main():
    if len(sys.argv) < 3:
        print("用法: python scripts/tts_segments.py <VOICE> <RATE>")
        sys.exit(1)

    voice = sys.argv[1]
    rate = sys.argv[2]

    with open('narration_segments.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    segments = data.get('segments', data) if isinstance(data, dict) else data

    durations = []
    all_sentence_timestamps = []

    for i, seg in enumerate(segments):
        # seg_id 优先取 scene_index（int），否则 id 若为 int 直接用，否则用 enumerate 索引
        raw_id = seg.get('scene_index', seg.get('id', i + 1))
        if isinstance(raw_id, int):
            seg_id = raw_id
        else:
            seg_id = i + 1
        text_file = f'narration_seg_{seg_id:02d}.txt'
        mp3_file = f'narration_seg_{seg_id:02d}.mp3'
        srt_file = f'narration_seg_{seg_id:02d}.srt'

        scene_id = seg.get('id', f's{i+1}')
        raw_text = seg.get('text') or seg.get('narration_segment', '') or seg.get('narration', '')
        if not raw_text:
            durations.append({'scene': scene_id, 'actual_duration': 0})
            all_sentence_timestamps.append({
                'scene': scene_id, 'segment_index': i, 'sentences': []
            })
            continue
        tts_text = fix_polyphone(raw_text)
        tts_text = tts_text.replace('_', ' ')  # 下划线不读"下划线"，换空格分词（daily_stock_analysis → daily stock analysis）

        with open(text_file, 'w', encoding='utf-8') as f:
            f.write(tts_text)

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
        durations.append({'scene': scene_id, 'actual_duration': round(dur, 2)})

        # 解析 SRT 提取句子级时间戳
        sentences = parse_srt(srt_file)
        all_sentence_timestamps.append({
            'scene': scene_id,
            'segment_index': i,
            'sentences': sentences
        })

        print(f'[Seg {i}] {scene_id}: {dur:.2f}s ({len(sentences)} sentences)')

    # 写入 segment_durations.json
    output = {
        'meta': {'voice': voice, 'rate': rate},
        'segments': durations
    }
    with open('segment_durations.json', 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    # 写入 sentence_timestamps.json
    ts_output = {
        'meta': {'voice': voice, 'rate': rate, 'source': 'edge-tts-srt'},
        'segments': all_sentence_timestamps
    }
    with open('sentence_timestamps.json', 'w', encoding='utf-8') as f:
        json.dump(ts_output, f, indent=2, ensure_ascii=False)

    total = sum(d['actual_duration'] for d in durations)
    total_sentences = sum(len(s['sentences']) for s in all_sentence_timestamps)
    print(f'Total: {total:.2f}s | {total_sentences} sentences')
    print(f'Voice: {voice}, Rate: {rate}')
    print(f'Output: segment_durations.json, sentence_timestamps.json')


if __name__ == '__main__':
    main()
