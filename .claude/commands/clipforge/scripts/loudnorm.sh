#!/usr/bin/env bash
# 两遍 loudnorm 响度标准化
#
# 用法: bash scripts/loudnorm.sh <input.mp3>
# 输出: 原地替换 input.mp3 为标准化后版本（48000Hz mono）
#
# 不依赖 jq，使用 Python 提取参数。

set -e
INPUT="${1:-narration.mp3}"
NULLDEV="/dev/null"
# Windows Git Bash 兼容
[ "$(uname -s 2>/dev/null)" = "MINGW" ] || [ "$(uname -s 2>/dev/null)" = "MSYS" ] && NULLDEV="NUL"

echo "[loudnorm] Pass 1: 分析响度..."
ffmpeg -i "$INPUT" -af "loudnorm=I=-16:TP=-1.5:LRA=11:print_format=json" -f null "$NULLDEV" 2>&1 | python -c "
import sys, re, json

# 从 ffmpeg stderr 中提取 JSON 块（不依赖行数）
text = sys.stdin.read()

# 找到最后一个完整的 JSON 对象 {...}
# loudnorm print_format=json 输出唯一一个 {} 块
brace_start = text.rfind('{')
brace_end = text.rfind('}')

if brace_start == -1 or brace_end == -1 or brace_end < brace_start:
    sys.exit('ERROR: loudnorm 输出中未找到 JSON 块')

json_str = text[brace_start:brace_end+1]

try:
    stats = json.loads(json_str)
except json.JSONDecodeError as e:
    sys.exit(f'ERROR: JSON 解析失败: {e}\n原始 JSON:\n{json_str[:300]}')

# 写入临时文件供 Pass 2 使用
with open('loudnorm_stats.json', 'w') as f:
    json.dump(stats, f)

print(f'measured_I={stats[\"input_i\"]}, TP={stats[\"input_tp\"]}, LRA={stats[\"input_lra\"]}, thresh={stats[\"input_thresh\"]}, offset={stats[\"target_offset\"]}')
"

echo "[loudnorm] Pass 2: 应用标准化..."
python -c "
import json, subprocess, sys

with open('loudnorm_stats.json') as f:
    stats = json.load(f)

cmd = [
    'ffmpeg', '-y', '-i', sys.argv[1],
    '-af', f'loudnorm=I=-16:TP=-1.5:LRA=11:measured_I={stats[\"input_i\"]}:measured_TP={stats[\"input_tp\"]}:measured_LRA={stats[\"input_lra\"]}:measured_thresh={stats[\"input_thresh\"]}:offset={stats[\"target_offset\"]}:linear=true',
    '-ar', '48000', '-ac', '1',
    sys.argv[2]
]
subprocess.run(cmd, check=True)
" "$INPUT" "${INPUT%.*}_norm.${INPUT##*.}"

mv "${INPUT%.*}_norm.${INPUT##*.}" "$INPUT"
rm -f loudnorm_stats.json
echo "[loudnorm] 完成: $INPUT 已标准化 (I=-16, TP=-1.5, LRA=11, 48kHz mono)"
