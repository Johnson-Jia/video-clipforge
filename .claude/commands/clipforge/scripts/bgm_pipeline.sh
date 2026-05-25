#!/usr/bin/env bash
# bgm_pipeline.sh — BGM 配乐管线（AI 选曲后全自动）
#
# 用法: bash scripts/bgm_pipeline.sh [bgm_file]
# 工作目录必须在项目目录下。
#
# 前提: bgm.wav 已存在于项目目录（AI 在执行本脚本前已完成选曲）
#        narration.mp3 已存在（TTS 管线已完成）
#
# 产出:
#   bgm.wav (如需循环则覆盖)
#   segment_durations.json (更新 meta.bgm_volume)

set -euo pipefail

BGM_FILE="${1:-bgm.wav}"

echo "=== BGM 管线启动 ==="

if [ ! -f "$BGM_FILE" ]; then
    echo "ERROR: ${BGM_FILE} 不存在。AI 需先完成 BGM 选曲，将文件保存为 ${BGM_FILE}。"
    exit 1
fi

if [ ! -f "narration.mp3" ]; then
    echo "ERROR: narration.mp3 不存在。请先运行 TTS 管线。"
    exit 1
fi

# ── Step 1: BGM 音量守恒校验 ──
echo "--- Step 1: BGM 音量守恒校验 ---"
BGM_MEAN=$(ffmpeg -i "$BGM_FILE" -af "volumedetect" -f null /dev/null 2>&1 | grep mean_volume | grep -oP '[\-\d.]+(?= dB)')
echo "bgm.wav mean_volume: ${BGM_MEAN} dB"

if [ "$(echo "$BGM_MEAN < -35" | bc 2>/dev/null || echo "0")" -eq 1 ]; then
    echo "ERROR: bgm.wav 音量异常偏低 (${BGM_MEAN} dB)，疑似被预衰减。"
    echo "正确做法：bgm.wav 保持原始音量，Stage 6 通过 data-volume 控制混音。"
    exit 1
fi
echo "OK: BGM 音量正常"

# ── Step 2: 音量校准 + 峰值间距校验 + 写入 JSON ──
echo "--- Step 2: 音量校准 ---"
BGM_MAX=$(ffmpeg -i "$BGM_FILE" -af "volumedetect" -f null /dev/null 2>&1 | grep max_volume | grep -oP '[\-\d.]+(?= dB)')
NARR_MAX=$(ffmpeg -i narration.mp3 -af "volumedetect" -f null /dev/null 2>&1 | grep max_volume | grep -oP '[\-\d.]+(?= dB)')

python .claude/commands/clipforge/scripts/bgm_gap_check.py "$BGM_MEAN" "$BGM_MAX" "$NARR_MAX" || true
echo "OK: 音量校准完成"

# ── Step 3: BGM 循环扩展 ──
echo "--- Step 3: BGM 循环检查 ---"
NARRATION_DUR=$(ffprobe -v quiet -show_entries format=duration -of csv=p=0 narration.mp3)
BGM_DUR=$(ffprobe -v quiet -show_entries format=duration -of csv=p=0 "$BGM_FILE")

if [ "$(echo "$BGM_DUR < $NARRATION_DUR" | bc 2>/dev/null || echo "0")" -eq 1 ]; then
    TARGET_DUR=$(echo "$NARRATION_DUR + 1" | bc)
    echo "BGM 循环扩展: ${BGM_DUR}s → ${TARGET_DUR}s"
    ffmpeg -y -stream_loop -1 -i "$BGM_FILE" -t "$TARGET_DUR" -c:a pcm_s16le -ar 48000 bgm_looped.wav
    mv "$BGM_FILE" bgm_orig.wav
    mv bgm_looped.wav "$BGM_FILE"
    echo "OK: BGM 已循环"
else
    echo "OK: BGM 时长足够 (${BGM_DUR}s >= ${NARRATION_DUR}s)，无需循环"
fi

echo "=== BGM 管线完成 ==="
echo "segment_durations.json meta.bgm_volume 已更新"
