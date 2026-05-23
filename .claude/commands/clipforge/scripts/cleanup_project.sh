#!/usr/bin/env bash
# 项目清理（白名单保护）
#
# 用法: bash scripts/cleanup_project.sh <项目目录>
# 项目目录必填

set -e
PROJECT_DIR="${1:?用法: bash scripts/cleanup_project.sh <项目目录>}"
cd "$PROJECT_DIR"

echo "=== 项目清理 ==="

# ── 白名单：这些文件绝对不可删除 ──
RETAIN_FILES=(
  final.mp4 final_no_bgm.mp4
  output.mp4 output_no_bgm.mp4
  cover.html cover.png
  index.html design.md
  narration_segments.json narration.txt
  segment_durations.json
  douyin.md narration.mp3
  content.md content_summary.md
)
for f in "${RETAIN_FILES[@]}"; do
  [ -f "$f" ] && echo "  [保留] $f"
done

# 1. 删除必删文件
rm -f narration_seg_*.txt narration_seg_*.mp3 narration_seg_*.srt
rm -f loudnorm_stats.json concat.txt concat_new.txt
rm -f output_silent.mp4 output_with_audio.mp4
rm -f silence_*.mp3 hyperframes.json frame_check.png
rm -f verify_*.png scenes.yaml
rm -f stage-handoff.json skills-lock.json webreader_checklist.json
rm -f cover_final.png cover_segment.mp4 narration.srt
rm -f cover_1frame.mp4 cover_1frame_audio.mp4 cover.ts output.ts
rm -f cover_clip.mp4
echo "  已删除中间产物文件"

# 2. 删除临时目录
rm -rf work-*/
rm -rf .agents/
echo "  已删除 work-*/ 和 .agents/"

# 3. BGM 副本按条件删除
if [ -f bgm.wav ]; then
  BGM_FOUND_IN_LIB=false
  BGM_SOURCE=$(python3 -c "import json; d=json.load(open('segment_durations.json')); print(d.get('meta',{}).get('bgm_source',''))" 2>/dev/null)
  if [ -n "$BGM_SOURCE" ] && [ -f "../../workspace/bgm/${BGM_SOURCE}" ]; then
    BGM_FOUND_IN_LIB=true
  fi
  if [ "$BGM_FOUND_IN_LIB" = false ]; then
    BGM_DURATION=$(ffprobe -v quiet -show_entries format=duration -of csv=p=0 bgm.wav 2>/dev/null | cut -d. -f1)
    for f in ../../workspace/bgm/*.mp3 ../../workspace/bgm/*.wav; do
      if [ -f "$f" ]; then
        LIB_DUR=$(ffprobe -v quiet -show_entries format=duration -of csv=p=0 "$f" 2>/dev/null | cut -d. -f1)
        if [ "$BGM_DURATION" = "$LIB_DUR" ]; then
          BGM_FOUND_IN_LIB=true
          break
        fi
      fi
    done
  fi
  if [ "$BGM_FOUND_IN_LIB" = true ]; then
    rm -f bgm.wav
    echo "  已删除 bgm.wav（素材库已有）"
  else
    echo "  保留 bgm.wav（无法确认素材库来源）"
  fi
fi

# 4. 电影片段临时目录
[ -d clips_16x9 ] && rm -rf clips_16x9/ && echo "  已删除 clips_16x9/"

# 5. 清理后验证
RETAIN_CHECK_FILES=(final.mp4 final_no_bgm.mp4 cover.png douyin.md)
MISSING=0
for f in "${RETAIN_CHECK_FILES[@]}"; do
  if [ ! -f "$f" ]; then
    echo "  ⚠ 严重错误：保留文件 $f 被误删！"
    MISSING=$((MISSING+1))
  fi
done
[ $MISSING -gt 0 ] && echo "  ⚠ 有 $MISSING 个核心文件被误删！"

echo "项目大小: $(du -sh . 2>/dev/null | cut -f1)"
echo "=== 清理完成 ==="
