#!/bin/bash
# quality_gate.sh — ClipForge 视频质量门禁
# 用法: bash scripts/quality_gate.sh <project_dir>
# 返回: 0=通过, 1=失败

set -euo pipefail

PROJECT="${1:-.}"
cd "$PROJECT"

PASS=0
FAIL=0
WARN=0

green()  { echo -e "\033[32m  ✓ $1\033[0m"; PASS=$((PASS+1)); }
red()    { echo -e "\033[31m  ✗ $1\033[0m"; FAIL=$((FAIL+1)); }
yellow() { echo -e "\033[33m  ⚠ $1\033[0m"; WARN=$((WARN+1)); }

echo "========================================"
echo "  ClipForge 视频质量门禁"
echo "  项目: $PROJECT"
echo "========================================"

# ── 1. 文件完整性 ──
echo ""
echo "── 1. 文件完整性 ──"

if [ -f "final.mp4" ]; then green "final.mp4 存在"; else red "final.mp4 缺失"; fi
if [ -f "index.html" ]; then green "index.html 存在"; else red "index.html 缺失"; fi
if [ -f "segment_durations.json" ]; then green "segment_durations.json 存在"; else yellow "segment_durations.json 缺失（非分段TTS模式可忽略）"; fi
if [ -f "narration.mp3" ]; then green "narration.mp3 存在"; else red "narration.mp3 缺失"; fi

# ── 2. 视频基本信息 ──
echo ""
echo "── 2. 视频基本信息 ──"

VIDEO_FILE="final.mp4"
[ ! -f "$VIDEO_FILE" ] && VIDEO_FILE="output.mp4"

if [ -f "$VIDEO_FILE" ]; then
  DURATION=$(ffprobe -v quiet -show_entries format=duration -of csv=p=0 "$VIDEO_FILE")
  WIDTH=$(ffprobe -v quiet -show_entries stream=width -of csv=p=0 -select_streams v:0 "$VIDEO_FILE")
  HEIGHT=$(ffprobe -v quiet -show_entries stream=height -of csv=p=0 -select_streams v:0 "$VIDEO_FILE")
  VCODEC=$(ffprobe -v quiet -show_entries stream=codec_name -of csv=p=0 -select_streams v:0 "$VIDEO_FILE")
  ACODEC=$(ffprobe -v quiet -show_entries stream=codec_name -of csv=p=0 -select_streams a:0 "$VIDEO_FILE")

  echo "  时长: ${DURATION}s  分辨率: ${WIDTH}x${HEIGHT}  视频: ${VCODEC}  音频: ${ACODEC}"

  # 分辨率检查
  if [ "$WIDTH" = "1080" ] && [ "$HEIGHT" = "1920" ]; then
    green "竖屏分辨率正确 (1080x1920)"
  elif [ "$WIDTH" = "1920" ] && [ "$HEIGHT" = "1080" ]; then
    green "横屏分辨率正确 (1920x1080)"
  else
    red "分辨率异常: ${WIDTH}x${HEIGHT}，预期 1080x1920 或 1920x1080"
  fi

  # 时长合理性（至少5秒）
  DUR_INT=${DURATION%.*}
  if [ "$DUR_INT" -gt 5 ]; then
    green "时长合理 (${DURATION}s)"
  else
    red "时长过短 (${DURATION}s)，可能渲染失败"
  fi
else
  red "无法检查视频信息：无 final.mp4 或 output.mp4"
fi

# ── 3. 黑屏检测（抽帧分析）──
echo ""
echo "── 3. 黑屏检测 ──"

BLACK_FAIL=0
FRAME_COUNT=0

# 均匀抽 8 帧
TOTAL_DUR=${DURATION%.*}
[ -z "$TOTAL_DUR" ] && TOTAL_DUR=60
INTERVAL=$((TOTAL_DUR / 9))
[ "$INTERVAL" -lt 1 ] && INTERVAL=1

for i in $(seq 1 8); do
  T=$((INTERVAL * i))
  [ "$T" -ge "$TOTAL_DUR" ] && break

  FRAME_FILE="quality_frame_${T}.jpg"
  ffmpeg -y -ss "$T" -i "$VIDEO_FILE" -frames:v 1 -q:v 2 "$FRAME_FILE" 2>/dev/null

  if [ -f "$FRAME_FILE" ]; then
    FRAME_COUNT=$((FRAME_COUNT+1))
    # 计算平均亮度：用 showinfo 滤镜提取 Y 均值
    BRIGHTNESS=$(ffmpeg -i "$FRAME_FILE" -vf "showinfo" -frames:v 1 -f null - 2>&1 | grep -oP 'mean:\[\K[0-9]+' | head -1 || echo "0")
    [ -z "$BRIGHTNESS" ] && BRIGHTNESS=0
    BRIGHTNESS_INT=${BRIGHTNESS}

    if [ "$BRIGHTNESS_INT" -lt 3 ]; then
      red "第 ${T}s 帧疑似纯黑屏（亮度 ${BRIGHTNESS}）"
      BLACK_FAIL=$((BLACK_FAIL+1))
    else
      green "第 ${T}s 帧正常（亮度 ${BRIGHTNESS}）"
    fi
    rm -f "$FRAME_FILE"
  fi
done

if [ "$FRAME_COUNT" -eq 0 ]; then
  red "无法抽帧检查"
fi

# ── 4. A/V 同步检查 ──
echo ""
echo "── 4. A/V 同步检查 ──"

if [ -f "segment_durations.json" ] && [ -f "$VIDEO_FILE" ]; then
  # 计算场景总时长
  SEG_TOTAL=$(python -c "
import json
with open('segment_durations.json','r') as f: segs=json.load(f)
print(f'{sum(s[\"actual_duration\"] for s in segs):.2f}')
" 2>/dev/null || echo "0")

  VIDEO_DUR=${DURATION}
  if [ "$SEG_TOTAL" != "0" ]; then
    DIFF=$(python -c "print(f'{abs(float($VIDEO_DUR) - float($SEG_TOTAL)):.2f}')" 2>/dev/null || echo "999")
    DIFF_INT=${DIFF%.*}
    if [ "$DIFF_INT" -gt 5 ]; then
      red "A/V 时长偏差 ${DIFF}s（场景总长 ${SEG_TOTAL}s vs 视频 ${VIDEO_DUR}s）"
    elif [ "$DIFF_INT" -gt 2 ]; then
      yellow "A/V 时长偏差 ${DIFF}s（场景总长 ${SEG_TOTAL}s vs 视频 ${VIDEO_DUR}s）"
    else
      green "A/V 时长偏差 ${DIFF}s，在容忍范围内"
    fi
  else
    yellow "无法计算分段时长（segment_durations.json 格式异常）"
  fi
else
  yellow "跳过 A/V 同步检查（缺少 segment_durations.json）"
fi

# ── 5. HTML 规范检查 ──
echo ""
echo "── 5. HTML 规范检查 ──"

if [ -f "index.html" ]; then
  # 检查关键规范
  if grep -q 'window.__timelines = {}' index.html; then
    green "__timelines 是 {} 对象"
  else
    red "__timelines 不是 {} 对象（可能是 [] 或未定义）"
  fi

  if grep -q 'paused: true' index.html || grep -q "paused: true" index.html; then
    green "timeline 设置了 paused: true"
  else
    red "timeline 未设置 paused: true"
  fi

  if grep -q 'data-composition-id' index.html; then
    green "根元素有 data-composition-id"
  else
    red "根元素缺少 data-composition-id"
  fi

  # 检查 CSS opacity:0 黑屏问题
  CSS_OPACITY_ZERO=$(grep -c 'opacity: *0 *;' index.html 2>/dev/null | head -1 || echo "0")
  BG_OPACITY=$(grep -E 'glow-orb|grid-overlay' -A5 index.html 2>/dev/null | grep -c 'opacity: *0 *;' | head -1 || echo "0")
  CSS_OPACITY_ZERO=$(echo "${CSS_OPACITY_ZERO:-0}" | tr -d '[:space:]')
  BG_OPACITY=$(echo "${BG_OPACITY:-0}" | tr -d '[:space:]')
  CONTENT_OPACITY=$((CSS_OPACITY_ZERO - BG_OPACITY))

  if [ "$CONTENT_OPACITY" -gt 5 ]; then
    red "内容元素有 ${CONTENT_OPACITY} 处 opacity:0（会导致黑屏！应删除或改用 GSAP fromTo）"
  else
    green "内容元素无多余 opacity:0"
  fi

  # 检查是否使用 gsap.from（应改为 fromTo）
  FROM_COUNT=$(grep -c 'tl\.from(' index.html 2>/dev/null || echo "0")
  FROMTO_COUNT=$(grep -c 'tl\.fromTo(' index.html 2>/dev/null || echo "0")

  if [ "$FROM_COUNT" -gt 0 ]; then
    red "使用了 ${FROM_COUNT} 处 gsap.from()（应改为 fromTo 防止黑屏）"
  else
    green "未使用 gsap.from()（已使用 fromTo 或无动画）"
  fi
fi

# ── 汇总 ──
echo ""
echo "========================================"
echo "  结果: ${PASS} 通过  ${FAIL} 失败  ${WARN} 警告"
echo "========================================"

if [ "$FAIL" -gt 0 ]; then
  echo -e "\033[31m  质量门禁未通过 — 修复上述 ✗ 项后重新提交\033[0m"
  exit 1
else
  echo -e "\033[32m  质量门禁通过\033[0m"
  exit 0
fi
