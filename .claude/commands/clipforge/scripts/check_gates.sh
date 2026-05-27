#!/bin/bash
# check_gates.sh - 三类门禁检查器
# 检查指定阶段的 process（流程）+ compliance（合规）+ quality（质量）门禁
# 用法: check_gates.sh <stage> <project_dir>
# 示例: check_gates.sh stage3 /workspace/2026/05/27/my-project
# 输出: 三类门禁各自的 PASS/FAIL 结果

set -euo pipefail

STAGE="${1:-}"
DIR="${2:-}"

if [ -z "$STAGE" ] || [ -z "$DIR" ]; then
  echo "用法: check_gates.sh <stage> <project_dir>"
  echo "示例: check_gates.sh stage3 /workspace/2026/05/27/my-project"
  echo "支持的 stage: stage0, stage1, stage2, stage3, stage4, stage5, stage6, stage7, movie-clips, cron-renew, cleanup"
  exit 1
fi

# 检查目录是否存在
if [ ! -d "$DIR" ]; then
  echo "ERROR: directory not found: $DIR"
  exit 1
fi

# 默认结果
PROCESS_PASS=true
COMPLIANCE_PASS=true
PROCESS_MISSING=""
COMPLIANCE_MISSING=""
QUALITY_NOTE="(evaluator: HUMAN — 请人工评价)"

# 根据 stage 定义三类门禁
case "$STAGE" in
  stage0)
    # 流程门禁：依赖 + 标记文件
    [ -x "$(command -v node 2>/dev/null)" ] || PROCESS_MISSING="$PROCESS_MISSING node"
    [ -x "$(command -v ffmpeg 2>/dev/null)" ] || PROCESS_MISSING="$PROCESS_MISSING ffmpeg"
    [ -x "$(command -v edge-tts 2>/dev/null)" ] || PROCESS_MISSING="$PROCESS_MISSING edge-tts"
    [ -x "$(command -v yt-dlp 2>/dev/null)" ] || PROCESS_MISSING="$PROCESS_MISSING yt-dlp"
    [ -s "workspace/.env-checked" ] 2>/dev/null || PROCESS_MISSING="$PROCESS_MISSING .env-checked"
    ;;
  stage1)
    # 流程：数据验证（需要人工或分类配置判定，这里只检查文件）
    [ -s "$DIR/content_ready.txt" ] 2>/dev/null || PROCESS_MISSING="$PROCESS_MISSING content_ready.txt"
    ;;
  stage2)
    # 流程：design.md 字段完整性
    [ -s "$DIR/design.md" ] || PROCESS_MISSING="$PROCESS_MISSING design.md"
    ;;
  stage3)
    # 流程：narration_segments.json + narration.txt
    [ -s "$DIR/narration_segments.json" ] || PROCESS_MISSING="$PROCESS_MISSING narration_segments.json"
    [ -s "$DIR/narration.txt" ] || PROCESS_MISSING="$PROCESS_MISSING narration.txt"
    ;;
  stage4)
    # 流程：音频文件完整
    [ -s "$DIR/segment_durations.json" ] || PROCESS_MISSING="$PROCESS_MISSING segment_durations.json"
    [ -s "$DIR/narration.mp3" ] || PROCESS_MISSING="$PROCESS_MISSING narration.mp3"
    [ -s "$DIR/narration.srt" ] || PROCESS_MISSING="$PROCESS_MISSING narration.srt"
    [ -s "$DIR/bgm.wav" ] || PROCESS_MISSING="$PROCESS_MISSING bgm.wav"
    ;;
  stage5)
    # 流程：assets manifest（可选阶段）
    if [ -d "$DIR/assets" ]; then
      [ -s "$DIR/assets/manifest.md" ] || PROCESS_MISSING="$PROCESS_MISSING assets/manifest.md"
    fi
    ;;
  stage6)
    # 流程：渲染产物
    [ -s "$DIR/index.html" ] || PROCESS_MISSING="$PROCESS_MISSING index.html"
    [ -s "$DIR/output.mp4" ] || PROCESS_MISSING="$PROCESS_MISSING output.mp4"
    [ -s "$DIR/output_no_bgm.mp4" ] || PROCESS_MISSING="$PROCESS_MISSING output_no_bgm.mp4"
    ;;
  stage7)
    # 流程：交付产物
    [ -s "$DIR/cover.html" ] || PROCESS_MISSING="$PROCESS_MISSING cover.html"
    [ -s "$DIR/cover.png" ] || PROCESS_MISSING="$PROCESS_MISSING cover.png"
    [ -s "$DIR/final.mp4" ] || PROCESS_MISSING="$PROCESS_MISSING final.mp4"
    [ -s "$DIR/final_no_bgm.mp4" ] || PROCESS_MISSING="$PROCESS_MISSING final_no_bgm.mp4"
    [ -s "$DIR/douyin.md" ] || PROCESS_MISSING="$PROCESS_MISSING douyin.md"
    # 合规：文案关键词检查（可用 grep 自动检测）
    if [ -s "$DIR/douyin.md" ]; then
      # 简单检测：是否有敏感词（此处仅示意，实际应使用更完整的敏感词表）
      if grep -qE "(必装|必备|神器|全网最好|最强|第一|一键三连|点赞关注)" "$DIR/douyin.md" 2>/dev/null; then
        COMPLIANCE_MISSING="$COMPLIANCE_MISSING sensitive_words"
        COMPLIANCE_PASS=false
      fi
      if grep -qE "https?://|www\." "$DIR/douyin.md" 2>/dev/null; then
        COMPLIANCE_MISSING="$COMPLIANCE_MISSING url_in_copy"
        COMPLIANCE_PASS=false
      fi
    fi
    ;;
  movie-clips)
    [ -s "$DIR/clip_durations.json" ] || PROCESS_MISSING="$PROCESS_MISSING clip_durations.json"
    ;;
  cleanup)
    [ -s "$DIR/.cleaned" ] 2>/dev/null || PROCESS_MISSING="$PROCESS_MISSING .cleaned"
    ;;
  *)
    echo "ERROR: unknown stage '$STAGE'"
    exit 1
    ;;
esac

# 判定流程门禁
if [ -n "$PROCESS_MISSING" ]; then
  PROCESS_PASS=false
fi

# 输出结果
echo "=== Gate Check: $STAGE ==="
if [ "$PROCESS_PASS" = true ]; then
  echo "  process:    PASS"
else
  echo "  process:    FAIL (missing:$PROCESS_MISSING)"
fi
if [ "$COMPLIANCE_PASS" = true ]; then
  echo "  compliance: PASS"
else
  echo "  compliance: FAIL (violations:$COMPLIANCE_MISSING)"
fi
echo "  quality:    $QUALITY_NOTE"
echo

# 退出码
if [ "$PROCESS_PASS" = false ] || [ "$COMPLIANCE_PASS" = false ]; then
  exit 1
fi
exit 0
