#!/usr/bin/env bash
# 封面拼接 + final 输出
#
# 用法: bash scripts/assemble_final.sh [项目目录]
# 项目目录默认为当前目录
#
# 前置: cover.png + output.mp4 + output_no_bgm.mp4 必须存在
# 输出: final.mp4 + final_no_bgm.mp4
#
# 方式: TS concat + stream copy（不重编码主视频，无损拼接）
# 封面只占 1 帧，对时长和音频几乎无影响

set -e
PROJECT_DIR="${1:-.}"
cd "$PROJECT_DIR"

echo "[assemble_final] 封面嵌入视频第一帧..."

# ── 门禁 ──
[ -s cover.png ] || { echo "FAIL: cover.png 缺失"; exit 1; }
[ -s output.mp4 ] || { echo "FAIL: output.mp4 缺失"; exit 1; }
[ -s output_no_bgm.mp4 ] || { echo "FAIL: output_no_bgm.mp4 缺失"; exit 1; }

# ── 从 output.mp4 读取编码参数 + 分辨率 ──
FPS=$(ffprobe -v quiet -show_entries stream=r_frame_rate -select_streams v -of csv=p=0 output.mp4 | head -1)
FPS_NUM=$(echo "$FPS" | cut -d/ -f1)
PROFILE=$(ffprobe -v quiet -show_entries stream=profile -select_streams v -of csv=p=0 output.mp4 | head -1)
SOURCE_DUR=$(ffprobe -v quiet -show_entries format=duration -of csv=p=0 output.mp4)
FRAME_DUR=$(awk "BEGIN {printf \"%.6f\", 1/$FPS_NUM}")
VIDEO_W=$(ffprobe -v quiet -show_entries stream=width -select_streams v -of csv=p=0 output.mp4 | head -1)
VIDEO_H=$(ffprobe -v quiet -show_entries stream=height -select_streams v -of csv=p=0 output.mp4 | head -1)
echo "[assemble_final] 源视频: ${SOURCE_DUR}s, ${FPS}fps, profile=${PROFILE}, ${VIDEO_W}x${VIDEO_H}, 封面帧长: ${FRAME_DUR}s"

# ── 封面片段制备（1 帧，TS 格式，匹配源视频参数）──
ffmpeg -y -loop 1 -t $FRAME_DUR -framerate $FPS -i cover.png \
  -c:v libx264 -profile:v $PROFILE -pix_fmt yuv420p \
  -vf "scale=${VIDEO_W}:${VIDEO_H}" \
  -frames:v 1 \
  -f mpegts cover.ts 2>/dev/null

# ── 版本一：含 BGM ──
echo "[assemble_final] 生成 final.mp4（含BGM）..."
ffmpeg -y -i output.mp4 -c copy -f mpegts main.ts 2>/dev/null
ffmpeg -y -f mpegts -i "concat:cover.ts|main.ts" \
  -c copy -movflags +faststart final.mp4 2>/dev/null
rm -f main.ts

# ── 版本二：无 BGM ──
echo "[assemble_final] 生成 final_no_bgm.mp4（仅旁白）..."
ffmpeg -y -i output_no_bgm.mp4 -c copy -f mpegts nobgm.ts 2>/dev/null
ffmpeg -y -f mpegts -i "concat:cover.ts|nobgm.ts" \
  -c copy -movflags +faststart final_no_bgm.mp4 2>/dev/null
rm -f nobgm.ts cover.ts

# ── 输出验证 ──
FINAL_DUR=$(ffprobe -v quiet -show_entries format=duration -of csv=p=0 final.mp4)
FINAL_AUDIO=$(ffprobe -v quiet -select_streams a -show_entries stream=codec_type -of csv=p=0 final.mp4 | wc -l)
NOBGM_DUR=$(ffprobe -v quiet -show_entries format=duration -of csv=p=0 final_no_bgm.mp4)
NOBGM_AUDIO=$(ffprobe -v quiet -select_streams a -show_entries stream=codec_type -of csv=p=0 final_no_bgm.mp4 | wc -l)

echo "[assemble_final] 完成:"
echo "  final.mp4: $(du -h final.mp4 | cut -f1), ${FINAL_DUR}s, 音频轨道: ${FINAL_AUDIO}"
echo "  final_no_bgm.mp4: $(du -h final_no_bgm.mp4 | cut -f1), ${NOBGM_DUR}s, 音频轨道: ${NOBGM_AUDIO}"

# ── 硬性断言：时长不膨胀 + 音频不丢失 ──
# final.mp4 时长不应超过 output.mp4 + 1 秒（1帧封面 + 余量）
if awk "BEGIN{exit !($FINAL_DUR > $SOURCE_DUR + 1)}"; then
  echo "FAIL: final.mp4 时长 ($FINAL_DUR) 远超源视频 ($SOURCE_DUR)，拼接异常"
  exit 1
fi
if [ "$FINAL_AUDIO" -eq 0 ]; then
  echo "FAIL: final.mp4 无音频轨道"
  exit 1
fi
if [ "$NOBGM_AUDIO" -eq 0 ]; then
  echo "FAIL: final_no_bgm.mp4 无音频轨道"
  exit 1
fi

echo "[assemble_final] 验证通过"
