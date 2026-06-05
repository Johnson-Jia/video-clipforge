#!/usr/bin/env bash
# bgm_pipeline.sh — BGM 配乐管线（AI 选曲后全自动）
#
# 用法: bash scripts/bgm_pipeline.sh [--project-dir DIR] [bgm_file] [--extend] [--bgms ...]
# 无 --project-dir 时检查 CWD 是否为合法项目目录。
#
# 前提: bgm.wav 已存在于项目目录（AI 在执行本脚本前已完成选曲）
#        narration.mp3 已存在（TTS 管线已完成）
#
# 产出:
#   bgm.wav (如需循环则覆盖)
#   segment_durations.json (更新 meta.bgm_volume)
#
# 管线顺序: 验证清理 → 测量 → 校准 → 时长对齐
# 测量在验证之后、校准之前进行，确保公式基于清理后的 BGM 特征计算。

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/_cd_project.sh" && cd_project "$@"

# 解析剩余参数（cd_project 已消费 --project-dir）
BGM_FILE="bgm.wav"
while [[ $# -gt 0 ]]; do
  case $1 in
    --extend) EXTEND_MODE=true; shift ;;
    --bgms) EXTRA_BGMS="$2"; shift 2 ;;
    --project-dir) shift 2 ;;
    *) BGM_FILE="$1"; shift ;;
  esac
done

echo "=== BGM 管线启动 ==="

if [ ! -f "$BGM_FILE" ]; then
    echo "ERROR: ${BGM_FILE} 不存在。AI 需先完成 BGM 选曲，将文件保存为 ${BGM_FILE}。"
    exit 1
fi

if [ ! -f "narration.mp3" ]; then
    echo "ERROR: narration.mp3 不存在。请先运行 TTS 管线。"
    exit 1
fi

# ── Step 1: BGM 音量守恒校验（快速筛查） ──
echo "--- Step 1: BGM 音量守恒校验 ---"
BGM_MEAN=$(ffmpeg -i "$BGM_FILE" -af "volumedetect" -f null /dev/null 2>&1 | grep mean_volume | grep -oP '[\-\d.]+(?= dB)')
echo "bgm.wav mean_volume: ${BGM_MEAN} dB"

if [ "$(echo "$BGM_MEAN < -35" | bc 2>/dev/null || echo "0")" -eq 1 ]; then
    echo "ERROR: bgm.wav 音量异常偏低 (${BGM_MEAN} dB)，疑似被预衰减。"
    echo "正确做法：bgm.wav 保持原始音量，Stage 6 通过 data-volume 控制混音。"
    exit 1
fi
echo "OK: BGM 音量正常"

# ── Step 2: BGM 全段验证（静音检测 + 清理） ──
# 在测量之前执行，确保后续测量基于清理后的 BGM。
echo "--- Step 2: BGM 全段验证 ---"
python "${SCRIPT_DIR}/bgm_validate.py" "$BGM_FILE"

# 重新获取时长（验证可能裁剪了文件）
BGM_DUR=$(ffprobe -v quiet -show_entries format=duration -of csv=p=0 "$BGM_FILE")
echo "BGM 时长: ${BGM_DUR}s"

# ── Step 3: 音量校准（基于清理后的 BGM 测量） ──
echo "--- Step 3: 音量校准 ---"
BGM_MEAN=$(ffmpeg -i "$BGM_FILE" -af "volumedetect" -f null /dev/null 2>&1 | grep mean_volume | grep -oP '[\-\d.]+(?= dB)')
BGM_MAX=$(ffmpeg -i "$BGM_FILE" -af "volumedetect" -f null /dev/null 2>&1 | grep max_volume | grep -oP '[\-\d.]+(?= dB)')
NARR_MAX=$(ffmpeg -i narration.mp3 -af "volumedetect" -f null /dev/null 2>&1 | grep max_volume | grep -oP '[\-\d.]+(?= dB)')

echo "BGM: mean=${BGM_MEAN} dB, max=${BGM_MAX} dB"
echo "旁白: max=${NARR_MAX} dB"

python "${SCRIPT_DIR}/bgm_gap_check.py" "$BGM_MEAN" "$BGM_MAX" "$NARR_MAX"
echo "OK: 音量校准完成"

# ── Step 3.5: bgm_volume 合理性门禁 ──
echo "--- Step 3.5: bgm_volume 合理性门禁 ---"
BGM_VOL=$(python -c "import json; print(json.load(open('segment_durations.json'))['meta']['bgm_volume'])")
echo "bgm_volume = ${BGM_VOL}"
if [ "$(echo "$BGM_VOL < 0.01" | bc 2>/dev/null || echo "0")" -eq 1 ]; then
    echo "ERROR: bgm_volume=${BGM_VOL} < 0.01，BGM 几乎静音。检查 bgm_gap_check.py 输出。"
    exit 1
fi
if [ "$(echo "$BGM_VOL > 1.0" | bc 2>/dev/null || echo "0")" -eq 1 ]; then
    echo "ERROR: bgm_volume=${BGM_VOL} > 1.0，超出 HTML audio 物理极限。检查 bgm_gap_check.py 输出。"
    exit 1
fi
echo "OK: bgm_volume=${BGM_VOL} 在物理范围内 (0, 1.0]"

# ── Step 4: BGM 时长对齐（以旁白总时长为基准） ──
echo "--- Step 4: BGM 时长对齐 ---"

# 优先从 segment_durations.json 获取精确旁白总时长，兜底 narration.mp3
TOTAL_DUR=$(python -c "
import json
d = json.load(open('segment_durations.json'))
print(round(sum(s['actual_duration'] for s in d['segments']), 2))
" 2>/dev/null || ffprobe -v quiet -show_entries format=duration -of csv=p=0 narration.mp3)

BGM_DUR=$(ffprobe -v quiet -show_entries format=duration -of csv=p=0 "$BGM_FILE")

TARGET_DUR=$(python -c "print(round($TOTAL_DUR, 2))")
FADE_START=$(python -c "print(round($TOTAL_DUR - 1, 2))")

echo "旁白: ${TOTAL_DUR}s | BGM: ${BGM_DUR}s | 目标: ${TARGET_DUR}s"

RATIO=$(python -c "print(round($TOTAL_DUR / $BGM_DUR, 1))" 2>/dev/null || echo "1")
echo "旁白/BGM 比率: ${RATIO}x"

if [ "${EXTEND_MODE:-false}" = true ] || [ "$(echo "$RATIO > 3" | bc 2>/dev/null || echo "0")" -eq 1 ]; then
    # ── 多首拼接模式 ──
    echo "--- Step 4a: 多首 BGM 拼接 ---"

    BGM_LIB="${BGM_LIB_DIR:-workspace/bgm}"

    STYLE_TAG=$(python -c "
import json, re
try:
    d = json.load(open('segment_durations.json'))
    src = d.get('meta', {}).get('bgm_source', '')
    if src:
        base = re.sub(r'\.\w+$', '', src)
        tag = re.sub(r'[\-_]?\d+$', '', base)
        print(tag)
except Exception:
    pass
" 2>/dev/null)
    if [ -z "$STYLE_TAG" ]; then
        BGM_BASENAME=$(basename "$BGM_FILE" | sed 's/\.\w*$//')
        STYLE_TAG=$(echo "$BGM_BASENAME" | sed 's/[0-9]*$//' | sed 's/[-]$//')
    fi

    echo "当前 BGM 风格标签: ${STYLE_TAG}"

    if [ -z "$EXTRA_BGMS" ]; then
        EXTRA_BGMS=$(find "$BGM_LIB" -name "${STYLE_TAG}*" -not -name "$(basename "$BGM_FILE" .wav | sed 's/$/.*/')" 2>/dev/null | head -10)
        if [ -z "$EXTRA_BGMS" ]; then
            EXTRA_BGMS=$(find "$BGM_LIB" -name "${STYLE_TAG}*.mp3" -o -name "${STYLE_TAG}*.wav" 2>/dev/null | head -10)
        fi
    fi

    if [ -z "$EXTRA_BGMS" ]; then
        echo "WARNING: 未找到同风格 BGM，回退到 concat 循环模式"
    else
        echo "找到候选 BGM:"
        echo "$EXTRA_BGMS" | while read -r f; do echo "  $(basename "$f")"; done

        XFADE_DUR=3
        PLAYLIST=""
        IDX=0

        cp "$BGM_FILE" /tmp/bgm_part_00.wav
        PLAYLIST="/tmp/bgm_part_00.wav"
        IDX=1

        CURRENT_DUR=$BGM_DUR
        while read -r candidate; do
            if [ -z "$candidate" ] || [ ! -f "$candidate" ]; then
                continue
            fi

            if [ "$(echo "$CURRENT_DUR >= $TARGET_DUR" | bc 2>/dev/null || echo "0")" -eq 1 ]; then
                break
            fi

            PADDED_IDX=$(printf "%02d" $IDX)
            ffmpeg -y -i "$candidate" -c:a pcm_s16le -ar 44100 "/tmp/bgm_part_${PADDED_IDX}.wav" 2>/dev/null
            PART_DUR=$(ffprobe -v quiet -show_entries format=duration -of csv=p=0 "/tmp/bgm_part_${PADDED_IDX}.wav")

            NEXT_IDX=$(printf "%02d" $((IDX + 1)))
            if [ $IDX -eq 1 ]; then
                OFFSET=$(python -c "print(round($CURRENT_DUR - $XFADE_DUR, 2))")
                ffmpeg -y -i "/tmp/bgm_part_00.wav" -i "/tmp/bgm_part_01.wav" \
                    -filter_complex "[0:a][1:a]acrossfade=d=${XFADE_DUR}:c1=tri:c2=tri[aout]" \
                    -map "[aout]" -c:a pcm_s16le "/tmp/bgm_merged_${NEXT_IDX}.wav" 2>/dev/null
            else
                PREV_MERGED=$(printf "/tmp/bgm_merged_%02d.wav" $IDX)
                OFFSET=$(python -c "print(round($CURRENT_DUR - $XFADE_DUR, 2))")
                ffmpeg -y -i "$PREV_MERGED" -i "/tmp/bgm_part_${PADDED_IDX}.wav" \
                    -filter_complex "[0:a][1:a]acrossfade=d=${XFADE_DUR}:c1=tri:c2=tri[aout]" \
                    -map "[aout]" -c:a pcm_s16le "/tmp/bgm_merged_${NEXT_IDX}.wav" 2>/dev/null
            fi

            CURRENT_DUR=$(python -c "print(round($CURRENT_DUR + $PART_DUR - $XFADE_DUR, 2))")
            echo "  拼接 $(basename "$candidate"): 累计 ${CURRENT_DUR}s / 目标 ${TARGET_DUR}s"
            IDX=$((IDX + 1))
        done < <(echo "$EXTRA_BGMS")

        FINAL_IDX=$(printf "%02d" $IDX)
        FINAL_MERGED="/tmp/bgm_merged_${FINAL_IDX}.wav"

        if [ ! -f "$FINAL_MERGED" ]; then
            echo "WARNING: 多首拼接未成功，回退到 concat"
        else
            ffmpeg -y -i "$FINAL_MERGED" \
                -t "$TARGET_DUR" \
                -af "afade=t=in:st=0:d=1.5,afade=t=out:st=${FADE_START}:d=2" \
                -c:a pcm_s16le bgm_aligned.wav

            mv "$BGM_FILE" bgm_orig.wav
            mv bgm_aligned.wav "$BGM_FILE"

            rm -f /tmp/bgm_part_*.wav /tmp/bgm_merged_*.wav

            echo "OK: 多首 BGM 拼接完成，总时长 ${TARGET_DUR}s（${IDX} 首，xfade ${XFADE_DUR}s）"
            echo "=== BGM 管线完成 ==="
            exit 0
        fi
    fi
fi

# ── 默认：concat 拼接模式 ──
echo "拼接对齐: ${BGM_DUR}s × N → ${TARGET_DUR}s"

COPIES=$(python -c "import math; print(math.ceil($TARGET_DUR / $BGM_DUR + 0.5))")
echo "需要 ${COPIES} 份拼接（${BGM_DUR}s × ${COPIES} = $(python -c "print(round($BGM_DUR * $COPIES, 1))")s）"

BGM_ABS=$(python -c "import os; print(os.path.abspath('$BGM_FILE'))")
> _bgm_concat.txt
for _i in $(seq 1 "$COPIES"); do
    echo "file '${BGM_ABS}'" >> _bgm_concat.txt
done

ffmpeg -y -f concat -safe 0 -i _bgm_concat.txt \
    -t "$TARGET_DUR" \
    -af "afade=t=in:st=0:d=1.5,afade=t=out:st=${FADE_START}:d=2" \
    -c:a pcm_s16le bgm_aligned.wav

rm -f _bgm_concat.txt

mv "$BGM_FILE" bgm_orig.wav
mv bgm_aligned.wav "$BGM_FILE"
echo "OK: BGM 已拼接对齐到 ${TARGET_DUR}s（${COPIES} 份 concat + 淡入 1.5s + 淡出 2s）"

echo "=== BGM 管线完成 ==="
echo "segment_durations.json meta.bgm_volume 已更新"
