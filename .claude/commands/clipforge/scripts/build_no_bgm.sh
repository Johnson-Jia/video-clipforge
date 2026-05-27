#!/usr/bin/env bash
# 无 BGM 视频构建
#
# 从 narration.mp3 + output.mp4（视频轨）合成 output_no_bgm.mp4。
# 真相源: narration.mp3（不经 output.mp4 音频轨，避免 BGM 污染）。
#
# 用法: bash scripts/build_no_bgm.sh [--project-dir DIR]

set -euo pipefail

PROJECT_DIR="."
while [[ $# -gt 0 ]]; do
  case $1 in
    --project-dir) PROJECT_DIR="$2"; shift 2 ;;
    *) shift ;;
  esac
done

cd "$PROJECT_DIR"

echo "=== 构建无 BGM 视频 ==="

# 前置检查
if [ ! -s "output.mp4" ]; then
  echo "FAIL: output.mp4 不存在"
  exit 1
fi
if [ ! -s "narration.mp3" ]; then
  echo "FAIL: narration.mp3 不存在（旁白真相源）"
  exit 1
fi

# 获取时长
VIDEO_DUR=$(ffprobe -v quiet -show_entries format=duration -of csv=p=0 output.mp4)
AUDIO_DUR=$(ffprobe -v quiet -show_entries format=duration -of csv=p=0 narration.mp3)

echo "视频轨时长: ${VIDEO_DUR}s"
echo "旁白时长:   ${AUDIO_DUR}s"

# 从 output.mp4 取视频轨 + narration.mp3 取音频轨合成
ffmpeg -y \
  -i output.mp4 \
  -i narration.mp3 \
  -c:v copy \
  -c:a aac -b:a 192k \
  -map 0:v:0 -map 1:a:0 \
  -shortest \
  output_no_bgm.mp4

echo "PASS: output_no_bgm.mp4 已生成"

# 验证
DUR=$(ffprobe -v quiet -show_entries format=duration -of csv=p=0 output_no_bgm.mp4)
echo "输出时长: ${DUR}s"

# 验证无 BGM（音频轨应只有旁白）
CHANNELS=$(ffprobe -v quiet -show_entries stream=channels -of csv=p=0 -select_streams a:0 output_no_bgm.mp4)
CODEC=$(ffprobe -v quiet -show_entries stream=codec_name -of csv=p=0 -select_streams a:0 output_no_bgm.mp4)
echo "音频: ${CODEC}, ${CHANNELS} 声道"
