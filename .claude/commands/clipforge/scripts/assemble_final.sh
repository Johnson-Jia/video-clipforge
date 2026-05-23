#!/usr/bin/env bash
# 封面拼接 + final 输出
#
# 用法: bash scripts/assemble_final.sh [项目目录]
# 项目目录默认为当前目录
#
# 前置: cover.png + output.mp4 + output_no_bgm.mp4 必须存在
# 输出: final.mp4 + final_no_bgm.mp4

set -e
PROJECT_DIR="${1:-.}"
cd "$PROJECT_DIR"

echo "[assemble_final] 封面嵌入视频第一帧..."

# 门禁
[ -s cover.png ] || { echo "FAIL: cover.png 缺失"; exit 1; }
[ -s output.mp4 ] || { echo "FAIL: output.mp4 缺失"; exit 1; }
[ -s output_no_bgm.mp4 ] || { echo "FAIL: output_no_bgm.mp4 缺失"; exit 1; }

# 封面片段制备
FPS=$(ffprobe -v quiet -show_entries stream=r_frame_rate -select_streams v -of csv=p=0 output.mp4 | head -1)
FPS_NUM=$(echo "$FPS" | cut -d/ -f1)
FRAME_DUR=$(awk "BEGIN {printf \"%.4f\", 1/$FPS_NUM}")

ffmpeg -y -loop 1 -i cover.png -c:v libx264 -b:v 5M -t $FRAME_DUR \
  -pix_fmt yuv420p -r $FPS_NUM cover_clip.mp4 2>/dev/null

# 版本一：含 BGM
echo "[assemble_final] 生成 final.mp4（含BGM）..."
ffmpeg -y -i cover_clip.mp4 -i output.mp4 \
  -filter_complex "[0:v][1:v]concat=n=2:v=1:a=0[outv]" \
  -map "[outv]" -map 1:a \
  -c:v libx264 -b:v 5M -c:a copy \
  final.mp4 2>/dev/null

# 版本二：无 BGM
echo "[assemble_final] 生成 final_no_bgm.mp4（仅旁白）..."
ffmpeg -y -i cover_clip.mp4 -i output_no_bgm.mp4 \
  -filter_complex "[0:v][1:v]concat=n=2:v=1:a=0[outv]" \
  -map "[outv]" -map 1:a \
  -c:v libx264 -b:v 5M -c:a copy \
  final_no_bgm.mp4 2>/dev/null

# 清理
rm -f cover_clip.mp4

# 验证
ffmpeg -y -i final.mp4 -vf "select=eq(n\,0)" -vframes 1 verify_cover.png 2>/dev/null
ffmpeg -y -i final_no_bgm.mp4 -vf "select=eq(n\,0)" -vframes 1 verify_no_bgm.png 2>/dev/null
rm -f verify_cover.png verify_no_bgm.png

echo "[assemble_final] 完成:"
echo "  final.mp4: $(du -h final.mp4 | cut -f1)"
echo "  final_no_bgm.mp4: $(du -h final_no_bgm.mp4 | cut -f1)"
