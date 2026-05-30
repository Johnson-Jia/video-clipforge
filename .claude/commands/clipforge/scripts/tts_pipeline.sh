#!/usr/bin/env bash
# tts_pipeline.sh — TTS 旁白管线（全自动）
#
# 用法: bash scripts/tts_pipeline.sh <voice> <rate>
# 工作目录必须在项目目录下。
#
# 产出:
#   narration_seg_0.mp3 ~ narration_seg_N.mp3
#   segment_durations.json
#   narration.mp3 (合并 + loudnorm 标准化)
#   narration.srt

set -euo pipefail

VOICE="${1:-zh-CN-YunjianNeural}"
RATE="${2:-+25\%}"

echo "=== TTS 管线启动 ==="
echo "音色: ${VOICE}  语速: ${RATE}"

# ── Step 1: 分段 TTS ──
echo "--- Step 1: 分段 TTS ---"
python .claude/commands/clipforge/scripts/tts_segments.py "$VOICE" "$RATE"

# ── Step 2: 合并为完整旁白 ──
echo "--- Step 2: 合并旁白 ---"
echo "" > concat.txt
for i in $(seq 0 $(($(ls narration_seg_*.mp3 | wc -l) - 1))); do
    echo "file 'narration_seg_${i}.mp3'" >> concat.txt
done
ffmpeg -y -f concat -safe 0 -i concat.txt -c copy narration.mp3

# ── Step 3: 合并 SRT ──
echo "--- Step 3: 合并字幕 ---"
python .claude/commands/clipforge/scripts/merge_srt.py

# ── Step 4: loudnorm 标准化 ──
echo "--- Step 4: loudnorm 标准化 ---"
bash .claude/commands/clipforge/scripts/loudnorm.sh narration.mp3

# ── Step 5: loudnorm 校验 ──
echo "--- Step 5: loudnorm 校验 ---"
NARR_MAX=$(ffmpeg -i narration.mp3 -af "volumedetect" -f null /dev/null 2>&1 | grep max_volume | grep -oP '[\-\d.]+(?= dB)')
echo "narration.mp3 max_volume: ${NARR_MAX} dB"
python -c "v=float('${NARR_MAX}'); exit(1 if v < -10 else 0)" || {
    echo "FATAL: loudnorm 未生效，max_volume=${NARR_MAX} dB < -10 dB"
    exit 1
}
echo "OK: loudnorm 校验通过"

# ── Step 6: 初始化 segment_durations.json meta ──
echo "--- Step 6: 写入 meta ---"
python -c "
import json
with open('segment_durations.json', 'r') as f:
    data = json.load(f)
data.setdefault('meta', {})
data['meta']['voice'] = '${VOICE}'
data['meta']['rate'] = '${RATE}'
with open('segment_durations.json', 'w') as f:
    json.dump(data, f, indent=2, ensure_ascii=False)
print(f'meta: voice=${VOICE}, rate=${RATE}')
"

# ── Step 7: Phase 时间校准 ──
echo "--- Step 7: Phase 时间校准 ---"
if [ -f "sentence_timestamps.json" ]; then
    python .claude/commands/clipforge/scripts/phase_calibrator.py
    echo "OK: phase_timings.json 已生成"
else
    echo "SKIP: sentence_timestamps.json 不存在，跳过 phase 校准"
fi

echo "=== TTS 管线完成 ==="
echo "产出: narration.mp3, narration.srt, segment_durations.json, sentence_timestamps.json, phase_timings.json"
