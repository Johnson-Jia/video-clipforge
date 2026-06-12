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
# 完整保存 stderr，避免 tail 截断 JSON（新版 ffmpeg 的 loudnorm JSON 块行数不固定）
ffmpeg -i "$INPUT" -af "loudnorm=I=-16:TP=-1.5:LRA=11:print_format=json" -f null /dev/null 2> loudnorm_full.log

echo "[loudnorm] Pass 2: 应用标准化..."
python -c "
import json, re, subprocess
with open('loudnorm_full.log', encoding='utf-8', errors='replace') as f:
    log = f.read()
# loudnorm 输出扁平 JSON（无嵌套花括号），正则精确提取含 input_i 的块
m = re.search(r'\{[^{}]*\"input_i\"[^{}]*\}', log, re.DOTALL)
if not m:
    raise SystemExit('FATAL: loudnorm 未输出有效 JSON（input_i 缺失），检查 ffmpeg 版本与输入音频')
stats = json.loads(m.group(0))
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
rm -f loudnorm_full.log
echo "[loudnorm] 完成: $INPUT 已标准化 (I=-16, TP=-1.5, LRA=11, 48kHz mono)"
