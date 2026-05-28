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

# 获取 BGM 时长（后续 Step 2.7 和 Step 3 使用）
BGM_DUR=$(ffprobe -v quiet -show_entries format=duration -of csv=p=0 "$BGM_FILE")
echo "bgm.wav 时长: ${BGM_DUR}s"

# ── Step 2: 音量校准 + 峰值间距校验 + 写入 JSON ──
echo "--- Step 2: 音量校准 ---"
BGM_MAX=$(ffmpeg -i "$BGM_FILE" -af "volumedetect" -f null /dev/null 2>&1 | grep max_volume | grep -oP '[\-\d.]+(?= dB)')
NARR_MAX=$(ffmpeg -i narration.mp3 -af "volumedetect" -f null /dev/null 2>&1 | grep max_volume | grep -oP '[\-\d.]+(?= dB)')

python .claude/commands/clipforge/scripts/bgm_gap_check.py "$BGM_MEAN" "$BGM_MAX" "$NARR_MAX" || true
echo "OK: 音量校准完成"

# ── Step 2.5: bgm_volume 合理性门禁 ──
echo "--- Step 2.5: bgm_volume 合理性门禁 ---"
BGM_VOL=$(python -c "import json; print(json.load(open('segment_durations.json'))['meta']['bgm_volume'])")
echo "bgm_volume = ${BGM_VOL}"
if [ "$(echo "$BGM_VOL < 0.10" | bc 2>/dev/null || echo "0")" -eq 1 ]; then
    echo "ERROR: bgm_volume=${BGM_VOL} < 0.10，BGM 几乎静音。检查 bgm_gap_check.py 输出。"
    exit 1
fi
if [ "$(echo "$BGM_VOL > 0.50" | bc 2>/dev/null || echo "0")" -eq 1 ]; then
    echo "ERROR: bgm_volume=${BGM_VOL} > 0.50，BGM 可能盖过旁白。检查 bgm_gap_check.py 输出。"
    exit 1
fi
echo "OK: bgm_volume=${BGM_VOL} 在合理范围内 [0.10, 0.50]"

# ── Step 2.7: BGM 静音尾段检测 ──
# BGM 源文件可能只有前 N 秒有实际音乐内容，后面是余音/静音尾段。
# 对比前半 vs 后半音量，如果差异 > 4dB，定位内容结束点并裁剪。
echo "--- Step 2.7: BGM 静音尾段检测 ---"

HALF_DUR=$(python -c "print(round($BGM_DUR / 2, 2))")

FRONT_VOL=$(ffmpeg -y -i "$BGM_FILE" -t "$HALF_DUR" -af volumedetect -f null /dev/null 2>&1 | grep mean_volume | grep -oP '[\-\d.]+(?= dB)')
BACK_VOL=$(ffmpeg -y -i "$BGM_FILE" -ss "$HALF_DUR" -af volumedetect -f null /dev/null 2>&1 | grep mean_volume | grep -oP '[\-\d.]+(?= dB)')

VOL_DROP=$(python -c "print(round($FRONT_VOL - $BACK_VOL, 1))")
echo "前半: ${FRONT_VOL} dB | 后半: ${BACK_VOL} dB | 差异: ${VOL_DROP} dB"

if [ "$(echo "$VOL_DROP > 4" | bc 2>/dev/null || echo "0")" -eq 1 ]; then
    echo "WARNING: 检测到静音尾段（后半比前半低 ${VOL_DROP} dB），定位内容结束点..."

    # 从后向前每 5 秒扫描，找到第一个音量接近前半平均的段落
    CONTENT_END=$(python -c "
import subprocess, sys
bgm_file = '$BGM_FILE'
front_vol = $FRONT_VOL
bgm_dur = $BGM_DUR
for t in range(int(bgm_dur) - 5, 0, -5):
    r = subprocess.run(
        ['ffmpeg', '-y', '-i', bgm_file, '-ss', str(t), '-t', '5',
         '-af', 'volumedetect', '-f', 'null', 'NUL'],
        capture_output=True, text=True
    )
    for line in r.stderr.split('\n'):
        if 'mean_volume' in line:
            vol = float(line.split('mean_volume:')[1].strip().split()[0])
            if vol > front_vol - 3:
                print(t + 5)
                sys.exit()
print(int(bgm_dur))
" 2>/dev/null)

    if [ "$(echo "$CONTENT_END < $BGM_DUR" | bc 2>/dev/null || echo "0")" -eq 1 ]; then
        echo "音乐内容结束点: ${CONTENT_END}s / ${BGM_DUR}s"
        ffmpeg -y -i "$BGM_FILE" -t "$CONTENT_END" -c:a pcm_s16le bgm_content.wav
        mv "$BGM_FILE" bgm_with_tail.wav
        mv bgm_content.wav "$BGM_FILE"
        BGM_DUR="$CONTENT_END"
        echo "OK: 已裁剪到 ${CONTENT_END}s（移除静音尾段）"
    else
        echo "OK: 未找到明确分界，保留原文件"
    fi
else
    echo "OK: BGM 内容覆盖完整"
fi

# ── Step 3: BGM 时长对齐（以旁白总时长为基准） ──
# 无论 BGM 长于或短于旁白，都通过 stream_loop 从头循环填充。
# 静音尾段已在 Step 2.7 移除，此处 BGM 内容是纯净的音乐段落。
echo "--- Step 3: BGM 时长对齐 ---"

# 优先从 segment_durations.json 获取精确旁白总时长，兜底 narration.mp3
TOTAL_DUR=$(python -c "
import json
d = json.load(open('segment_durations.json'))
print(round(sum(s['actual_duration'] for s in d['segments']), 2))
" 2>/dev/null || ffprobe -v quiet -show_entries format=duration -of csv=p=0 narration.mp3)

BGM_DUR=$(ffprobe -v quiet -show_entries format=duration -of csv=p=0 "$BGM_FILE")

# 目标 = 旁白 + 1s 缓冲；淡出起点 = 旁白 - 1s
TARGET_DUR=$(python -c "print(round($TOTAL_DUR + 1, 2))")
FADE_START=$(python -c "print(round($TOTAL_DUR - 1, 2))")

echo "旁白: ${TOTAL_DUR}s | BGM: ${BGM_DUR}s | 目标: ${TARGET_DUR}s"

# 始终用 stream_loop 循环（BGM 已在 Step 2.7 裁掉尾段，内容是纯音乐）
echo "循环对齐: ${BGM_DUR}s → ${TARGET_DUR}s"
ffmpeg -y -stream_loop -1 -i "$BGM_FILE" \
    -t "$TARGET_DUR" \
    -af "afade=t=in:st=0:d=1.5,afade=t=out:st=${FADE_START}:d=2" \
    -c:a pcm_s16le bgm_aligned.wav

mv "$BGM_FILE" bgm_orig.wav
mv bgm_aligned.wav "$BGM_FILE"
echo "OK: BGM 已对齐到 ${TARGET_DUR}s（含 1s 缓冲 + 淡入 1.5s + 淡出 2s）"

echo "=== BGM 管线完成 ==="
echo "segment_durations.json meta.bgm_volume 已更新"
