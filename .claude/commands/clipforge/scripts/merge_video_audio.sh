#!/bin/bash
# ═══════════════════════════════════════════════════════════
# merge_video_audio.sh — 音视频合成脚本
# ═══════════════════════════════════════════════════════════
# 使用方法:
#   ./merge_video_audio.sh video.mp4 bgm.wav output.mp4 [fade_start_seconds]
#
# 示例:
#   ./merge_video_audio.sh output.mp4 bgm.wav final.mp4 39
#   # fade_start_seconds 默认为视频时长-3秒

set -e

VIDEO="${1:?用法: merge_video_audio.sh <video.mp4> <bgm.wav> <output.mp4> [fade_start]}"
BGM="${2:?请指定 bgm.wav 路径}"
OUTPUT="${3:?请指定输出文件路径}"
FADE_START="${4:-auto}"

# 获取视频时长
DURATION=$(ffprobe -v quiet -show_entries format=duration -of csv=p=0 "$VIDEO" | cut -d. -f1)

if [ "$FADE_START" = "auto" ]; then
    FADE_START=$((DURATION - 3))
fi

echo "═══════════════════════════════════════════"
echo "视频: $VIDEO (${DURATION}s)"
echo "配乐: $BGM"
echo "输出: $OUTPUT"
echo "淡出: ${FADE_START}s 开始, 1s 淡出"
echo "═══════════════════════════════════════════"

# 检查 BGM 音量
BGM_VOL=$(ffmpeg -i "$BGM" -af "volumedetect" -f null /dev/null 2>&1 | grep "mean_volume" | grep -oP '\-?\d+\.\d+' | head -1)
echo "BGM 平均音量: ${BGM_VOL} dB"

# 如果音量太低，自动增益
VOLUME_FILTER=""
if [ -n "$BGM_VOL" ]; then
	    # 用 python 比较浮点数（跨平台兼容）
	    NEED_BOOST=$(python -c "print(1 if float('${BGM_VOL}') < -30 else 0)")
    if [ "$NEED_BOOST" = "1" ]; then
	        GAIN=$(python -c "print(int(30 + float('${BGM_VOL}')))")
        VOLUME_FILTER="volume=${GAIN}dB,"
        echo "⚠ 音量过低，自动增益 +${GAIN}dB"
    fi
fi

# 合并
ffmpeg -y \
    -i "$VIDEO" \
    -stream_loop -1 -i "$BGM" \
    -c:v copy \
    -c:a aac -b:a 192k \
    -shortest \
    -af "${VOLUME_FILTER}afade=t=out:st=${FADE_START}:d=3" \
    "$OUTPUT"

# 验证
FINAL_SIZE=$(ls -lh "$OUTPUT" | awk '{print $5}')
FINAL_DUR=$(ffprobe -v quiet -show_entries format=duration -of csv=p=0 "$OUTPUT")
echo ""
echo "✅ 完成: $OUTPUT ($FINAL_SIZE, ${FINAL_DUR}s)"
