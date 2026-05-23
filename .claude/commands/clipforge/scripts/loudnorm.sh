#!/usr/bin/env bash
# 两遍 loudnorm 响度标准化
#
# 用法: bash scripts/loudnorm.sh <input.mp3>
# 输出: 原地替换 input.mp3 为标准化后版本（48000Hz mono）
#
# 不依赖 jq，使用 Python 提取参数。

set -e
INPUT="${1:-narration.mp3}"

echo "[loudnorm] Pass 1: 分析响度..."
ffmpeg -i "$INPUT" -af "loudnorm=I=-16:TP=-1.5:LRA=11:print_format=json" -f null /dev/null 2>&1 | tail -12 > loudnorm_stats.json

echo "[loudnorm] Pass 2: 应用标准化..."
python -c "
import json, subprocess
with open('loudnorm_stats.json') as f:
    lines = f.readlines()
    json_str = ''
    started = False
    for line in lines:
        if '{' in line and not started:
            started = True
        if started:
            json_str += line
    stats = json.loads(json_str)
    measured_i = stats['input_i']
    measured_tp = stats['input_tp']
    measured_lra = stats['input_lra']
    measured_thresh = stats['input_thresh']
    offset = stats['target_offset']
    print(f'measured_I={measured_i}, measured_TP={measured_tp}, measured_LRA={measured_lra}, measured_thresh={measured_thresh}, offset={offset}')
    cmd = [
        'ffmpeg', '-y', '-i', '$INPUT',
        '-af', f'loudnorm=I=-16:TP=-1.5:LRA=11:measured_I={measured_i}:measured_TP={measured_tp}:measured_LRA={measured_lra}:measured_thresh={measured_thresh}:offset={offset}:linear=true',
        '-ar', '48000', '-ac', '1',
        '${INPUT%.*}_norm.${INPUT##*.}'
    ]
    subprocess.run(cmd, check=True)
"

mv "${INPUT%.*}_norm.${INPUT##*.}" "$INPUT"
rm -f loudnorm_stats.json
echo "[loudnorm] 完成: $INPUT 已标准化 (I=-16, TP=-1.5, LRA=11, 48kHz mono)"
