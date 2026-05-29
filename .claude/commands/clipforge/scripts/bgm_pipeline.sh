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
# 策略选择：
#   - BGM >= 旁白 95%：直接使用（裁剪到目标时长）
#   - BGM < 旁白但差距 ≤ 3x：stream_loop 循环（同曲目自然重复）
#   - BGM < 旁白且差距 > 3x：多首拼接（--extend 模式）
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

RATIO=$(python -c "print(round($TOTAL_DUR / $BGM_DUR, 1))" 2>/dev/null || echo "1")
echo "旁白/BGM 比率: ${RATIO}x"

# 检查是否指定了 --extend 模式（多首拼接）
EXTEND_MODE=false
EXTRA_BGMS=""
while [[ $# -gt 0 ]]; do
    case $1 in
        --extend) EXTEND_MODE=true; shift ;;
        --bgms) EXTRA_BGMS="$2"; shift 2 ;;
        *) shift ;;
    esac
done

if [ "$EXTEND_MODE" = true ] || [ "$(echo "$RATIO > 3" | bc 2>/dev/null || echo "0")" -eq 1 ]; then
    # ── 多首拼接模式 ──
    # 当 BGM 远短于旁白（> 3x），单纯循环同一首会听觉疲劳。
    # 从 BGM 库中选取多首同风格曲目，用 xfade 交叉淡入拼接。
    echo "--- Step 3a: 多首 BGM 拼接 ---"

    BGM_LIB="${BGM_LIB_DIR:-workspace/bgm}"

    # 获取当前 BGM 的风格标签
    # 优先从 segment_durations.json 的 meta.bgm_source 提取（如 clean-corporate-1.mp3 → clean-corporate）
    # 兜底从当前文件名提取
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

    # 查找同风格的其他 BGM 文件
    if [ -z "$EXTRA_BGMS" ]; then
        EXTRA_BGMS=$(find "$BGM_LIB" -name "${STYLE_TAG}*" -not -name "$(basename "$BGM_FILE" .wav | sed 's/$/.*/')" 2>/dev/null | head -10)
        # 也搜索 .mp3 和 .wav
        if [ -z "$EXTRA_BGMS" ]; then
            EXTRA_BGMS=$(find "$BGM_LIB" -name "${STYLE_TAG}*.mp3" -o -name "${STYLE_TAG}*.wav" 2>/dev/null | head -10)
        fi
    fi

    if [ -z "$EXTRA_BGMS" ]; then
        echo "WARNING: 未找到同风格 BGM，回退到 stream_loop 循环模式"
    else
        echo "找到候选 BGM:"
        echo "$EXTRA_BGMS" | while read -r f; do echo "  $(basename "$f")"; done

        # 将当前 BGM + 候选 BGM 转为统一格式并拼接
        XFADE_DUR=3  # 交叉淡入时长 3 秒
        PLAYLIST=""
        IDX=0

        # 首先加入当前 BGM
        cp "$BGM_FILE" /tmp/bgm_part_00.wav
        PLAYLIST="/tmp/bgm_part_00.wav"
        IDX=1

        # 依次加入候选 BGM，直到总时长超过目标
        CURRENT_DUR=$BGM_DUR
        while read -r candidate; do
            if [ -z "$candidate" ] || [ ! -f "$candidate" ]; then
                continue
            fi

            if [ "$(echo "$CURRENT_DUR >= $TARGET_DUR" | bc 2>/dev/null || echo "0")" -eq 1 ]; then
                break
            fi

            # 转码为 WAV（统一格式）
            PADDED_IDX=$(printf "%02d" $IDX)
            ffmpeg -y -i "$candidate" -c:a pcm_s16le -ar 44100 "/tmp/bgm_part_${PADDED_IDX}.wav" 2>/dev/null
            PART_DUR=$(ffprobe -v quiet -show_entries format=duration -of csv=p=0 "/tmp/bgm_part_${PADDED_IDX}.wav")

            # 使用 xfade 拼接
            NEXT_IDX=$(printf "%02d" $((IDX + 1)))
            if [ $IDX -eq 1 ]; then
                # 第一次拼接：part_00 + part_01
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

        # 找到最终合并文件
        FINAL_IDX=$(printf "%02d" $IDX)
        FINAL_MERGED="/tmp/bgm_merged_${FINAL_IDX}.wav"

        # 如果没有成功拼接（只有1首），使用原 BGM
        if [ ! -f "$FINAL_MERGED" ]; then
            # 回退到 stream_loop
            echo "WARNING: 多首拼接未成功，回退到 stream_loop"
        else
            # 裁剪到目标时长 + 淡入淡出
            ffmpeg -y -i "$FINAL_MERGED" \
                -t "$TARGET_DUR" \
                -af "afade=t=in:st=0:d=1.5,afade=t=out:st=${FADE_START}:d=2" \
                -c:a pcm_s16le bgm_aligned.wav

            mv "$BGM_FILE" bgm_orig.wav
            mv bgm_aligned.wav "$BGM_FILE"

            # 清理临时文件
            rm -f /tmp/bgm_part_*.wav /tmp/bgm_merged_*.wav

            echo "OK: 多首 BGM 拼接完成，总时长 ${TARGET_DUR}s（${IDX} 首，xfade ${XFADE_DUR}s）"
            echo "=== BGM 管线完成 ==="
            exit 0
        fi
    fi
fi

# ── 默认：concat 拼接模式（取代 stream_loop，WAV 格式可靠） ──
# stream_loop 对 WAV 文件不可靠：RIFF 头声明 data chunk 大小后，
# seek 回去再读会超过声明长度，ffmpeg 输出静音。
# 改用 concat 协议：将 BGM 复制足够份数拼接，再截取目标时长。
echo "拼接对齐: ${BGM_DUR}s × N → ${TARGET_DUR}s"

COPIES=$(python -c "import math; print(math.ceil($TARGET_DUR / $BGM_DUR + 0.5))")
echo "需要 ${COPIES} 份拼接（${BGM_DUR}s × ${COPIES} = $(python -c "print(round($BGM_DUR * $COPIES, 1))")s）"

# 生成 concat 清单
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
