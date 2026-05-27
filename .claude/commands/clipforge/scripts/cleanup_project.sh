#!/usr/bin/env bash
# 项目清理（白名单保护 + --dry-run 支持）
#
# 用法:
#   bash scripts/cleanup_project.sh <项目目录>           # 执行清理
#   bash scripts/cleanup_project.sh <项目目录> --dry-run # 仅预览，不删除
#
# 项目目录必填

set -e
DRY_RUN=false
PROJECT_DIR=""

for arg in "$@"; do
  case $arg in
    --dry-run) DRY_RUN=true ;;
    *) [ -z "$PROJECT_DIR" ] && PROJECT_DIR="$arg" ;;
  esac
done

if [ -z "$PROJECT_DIR" ]; then
  echo "用法: bash scripts/cleanup_project.sh <项目目录> [--dry-run]"
  exit 1
fi

cd "$PROJECT_DIR"

if [ "$DRY_RUN" = true ]; then
  echo "=== 项目清理（DRY RUN — 仅预览） ==="
else
  echo "=== 项目清理 ==="
fi

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

# 辅助函数：安全删除
safe_rm() {
  local target="$1"
  if [ "$DRY_RUN" = true ]; then
    if [ -e "$target" ]; then
      echo "  [将删除] $target"
    fi
  else
    rm -f "$target"
  fi
}

safe_rm_rf() {
  local target="$1"
  if [ "$DRY_RUN" = true ]; then
    if [ -e "$target" ]; then
      echo "  [将删除] $target/ ($(du -sh "$target" 2>/dev/null | cut -f1))"
    fi
  else
    rm -rf "$target"
  fi
}

# 1. 删除必删文件
for f in narration_seg_*.txt narration_seg_*.mp3 narration_seg_*.srt \
         loudnorm_stats.json concat.txt concat_new.txt \
         output_silent.mp4 output_with_audio.mp4 \
         silence_*.mp3 hyperframes.json frame_check.png \
         verify_*.png scenes.yaml \
         stage-handoff.json skills-lock.json webreader_checklist.json \
         cover_final.png cover_segment.mp4 narration.srt \
         cover_1frame.mp4 cover_1frame_audio.mp4 cover.ts output.ts \
         cover_clip.mp4; do
  safe_rm "$f"
done
[ "$DRY_RUN" = false ] && echo "  已删除中间产物文件"

# 2. 删除临时目录
safe_rm_rf "work-*/"
safe_rm_rf ".agents/"
[ "$DRY_RUN" = false ] && echo "  已删除 work-*/ 和 .agents/"

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
    safe_rm "bgm.wav"
    [ "$DRY_RUN" = false ] && echo "  已删除 bgm.wav（素材库已有）"
  else
    echo "  保留 bgm.wav（无法确认素材库来源）"
  fi
fi

# 4. 电影片段临时目录
if [ -d clips_16x9 ]; then
  safe_rm_rf "clips_16x9/"
  [ "$DRY_RUN" = false ] && echo "  已删除 clips_16x9/"
fi

# 5. 清理后验证
RETAIN_CHECK_FILES=(final.mp4 final_no_bgm.mp4 cover.png douyin.md)
MISSING=0
for f in "${RETAIN_CHECK_FILES[@]}"; do
  if [ ! -f "$f" ]; then
    echo "  严重错误：保留文件 $f 被误删！"
    MISSING=$((MISSING+1))
  fi
done
[ $MISSING -gt 0 ] && echo "  有 $MISSING 个核心文件被误删！"

echo "项目大小: $(du -sh . 2>/dev/null | cut -f1)"

if [ "$DRY_RUN" = true ]; then
  echo "=== DRY RUN 完成（未实际删除） ==="
  echo "去掉 --dry-run 参数以执行清理"
else
  echo "=== 清理完成 ==="
fi
