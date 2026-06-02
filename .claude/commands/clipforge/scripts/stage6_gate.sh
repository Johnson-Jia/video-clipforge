#!/usr/bin/env bash
# Stage 6 完成门禁
#
# 用法: bash scripts/stage6_gate.sh
# 工作目录必须在项目目录下。
# 检查: 文件存在性、视频/音频轨、采样率、BGM 隔离性

set -e
FAIL=0

echo "=== Stage 6 完成门禁 ==="

# ── 导演门禁（Layer 1：HTML 设计意图验证）──
echo "--- 导演门禁（HTML 设计意图验证）---"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
python3 "${SCRIPT_DIR}/director_gate.py" . || {
  echo "FAIL: 导演门禁未通过（HTML 设计问题）"
  FAIL=1
}

# ── 文件存在性 ──
for f in index.html output.mp4 output_no_bgm.mp4; do
  if [ ! -s "$f" ]; then
    echo "FAIL: $f missing"
    FAIL=1
  fi
done

# ── 视频/音频轨 + 分辨率 + 时长 ──
for f in output.mp4 output_no_bgm.mp4; do
  ffprobe -v quiet -show_streams "$f" | grep -q "codec_name=h264" || { echo "FAIL: $f no video"; FAIL=1; }
  ffprobe -v quiet -show_streams "$f" | grep -q "codec_name=aac" || { echo "FAIL: $f no audio"; FAIL=1; }

  # 分辨率校验
  WIDTH=$(ffprobe -v quiet -show_entries stream=width -of csv=p=0 -select_streams v:0 "$f" 2>/dev/null)
  HEIGHT=$(ffprobe -v quiet -show_entries stream=height -of csv=p=0 -select_streams v:0 "$f" 2>/dev/null)
  if [ "$WIDTH" = "1080" ] && [ "$HEIGHT" = "1920" ]; then
    echo "PASS: $f 竖屏 1080x1920"
  elif [ "$WIDTH" = "1920" ] && [ "$HEIGHT" = "1080" ]; then
    echo "PASS: $f 横屏 1920x1080"
  elif [ -n "$WIDTH" ]; then
    echo "FAIL: $f 分辨率异常 ${WIDTH}x${HEIGHT}，预期 1080x1920 或 1920x1080"
    FAIL=1
  fi

  # 时长合理性
  DUR=$(ffprobe -v quiet -show_entries format=duration -of csv=p=0 "$f" 2>/dev/null)
  DUR_INT=${DUR%.*}
  if [ -n "$DUR_INT" ] && [ "$DUR_INT" -le 5 ]; then
    echo "FAIL: $f 时长过短 (${DUR}s)，可能渲染失败"
    FAIL=1
  fi
done

# ── 采样率校验 ──
for f in final.mp4 final_no_bgm.mp4; do
  if [ -f "$f" ]; then
    SR=$(ffprobe -v quiet -select_streams a -show_entries stream=sample_rate -of csv=p=0 "$f")
    [ "$SR" = "48000" ] || { echo "FATAL: $f sample_rate=${SR}, expected 48000"; FAIL=1; }
  fi
done

# ── HTML 结构完整性 ──
if [ -f "index.html" ]; then
  # 检查空 layer-fx（禁止 <div class="layer-fx"></div>）
  EMPTY_FX=$(grep -c '<div class="layer-fx"></div>' index.html 2>/dev/null || echo "0")
  if [ "$EMPTY_FX" -gt 0 ]; then
    echo "FAIL: ${EMPTY_FX} 个空 layer-fx（特效层无内容），必须填充特效后才能通过"
    FAIL=1
  fi

  # 检查三层架构：clip 数量应与 layer-fx 数量一致
  CLIP_COUNT=$(grep -c 'class="clip"' index.html 2>/dev/null || echo "0")
  LAYER_FX_COUNT=$(grep -c 'layer-fx' index.html 2>/dev/null || echo "0")
  if [ "$CLIP_COUNT" != "$LAYER_FX_COUNT" ]; then
    echo "FAIL: clip(${CLIP_COUNT}) 与 layer-fx(${LAYER_FX_COUNT}) 数量不匹配"
    FAIL=1
  fi

  echo "HTML 结构: ${CLIP_COUNT} scenes, ${LAYER_FX_COUNT} fx layers, ${EMPTY_FX:-0} empty"

  # 检查 fx 层最低元素密度（每个 layer-fx 至少 3 个子 div）
  # 简化检查：统计 layer-fx 到 /layer-fx 之间的 <div 数量
  FX_SINGLE=$(grep -oP 'class="layer-fx">\s*<div[^/]*></div>\s*</div>' index.html 2>/dev/null | wc -l || echo "0")
  if [ "${FX_SINGLE:-0}" -gt 0 ]; then
    echo "FAIL: ${FX_SINGLE} 个 layer-fx 仅含单元素（需≥3个特效元素，见 R-R-008）"
    FAIL=1
  fi

  # ── Padding 完整性检查 ──
  # 1. 每个 scene-wrap 必须有 padding
  SCENE_WRAPS=$(grep -c 'scene-wrap\|class="pfc\|class="hero-card\|class="project-full-card' index.html 2>/dev/null || echo "0")
  # 统计含 padding 声明的 scene-wrap（含内联 style 和 CSS 规则）
  PADDED_WRAPS=$(grep -E '(scene-wrap|class="(pfc|hero-card|project-full-card))' index.html 2>/dev/null | grep -ci 'padding' || echo "0")
  # 也检查内联 style padding
  INLINE_PAD=$(grep -c 'style="[^"]*padding' index.html 2>/dev/null || echo "0")
  # 检查 CSS 块中的 scene-wrap padding
  CSS_PAD=$(grep -A5 '\.scene-wrap' index.html 2>/dev/null | grep -c 'padding' || echo "0")

  if [ "$SCENE_WRAPS" -gt 0 ] && [ "$PADDED_WRAPS" -eq 0 ] && [ "$INLINE_PAD" -eq 0 ] && [ "$CSS_PAD" -eq 0 ]; then
    echo "FAIL: scene-wrap 存在但无 padding 声明（内容将塌陷）"
    FAIL=1
  fi

  # 2. 检测内层多重 padding（.phase/.layer-content/.pfc-main 有水平 padding）
  MULTI_PAD=$(grep -E '\.(phase|layer-content|pfc-main)' index.html 2>/dev/null | grep -cE 'padding-[left-right]|padding:\s*\d+.*\d+' || echo "0")
  if [ "$MULTI_PAD" -gt 0 ]; then
    echo "FAIL: 内层元素（.phase/.layer-content/.pfc-main）包含水平 padding（违反单层 padding 原则，会导致双重 padding）"
    FAIL=1
  fi

  echo "Padding 检查: scene-wraps=${SCENE_WRAPS}, padded=${PADDED_WRAPS}, inline=${INLINE_PAD}, multi-pad=${MULTI_PAD}"

  # ── layer-content height 检查（防止 Phase 塌陷到顶部）──
  LAYER_CONTENT_CSS=$(grep -A3 '\.layer-content\s*{' index.html 2>/dev/null)
  echo "$LAYER_CONTENT_CSS" | grep -q 'height' || {
    echo "FAIL: .layer-content 缺少 height（Phase 内容会塌陷到顶部，见 shared/render-safety.md §2.2）"
    FAIL=1
  }
fi

# ── 视觉分镜完整性（Phase 检查）──
if [ -f "narration_segments.json" ] && [ -f "segment_durations.json" ]; then
  PHASE_FAIL=$(python3 -c "
import json
dur = json.load(open('segment_durations.json'))['segments']
phases = json.load(open('narration_segments.json'))
fail = 0
warn = 0
for seg, narr in zip(dur, phases):
    d = seg['actual_duration']
    vp = narr.get('visual_phases', [])
    if d > 15 and len(vp) < 2:
        print(f'FAIL: {narr[\"scene\"]} ({d:.1f}s) needs >= 2 visual_phases, got {len(vp)}')
        fail = 1
    elif d > 25 and len(vp) < 3:
        print(f'WARN: {narr[\"scene\"]} ({d:.1f}s) has {len(vp)} phases, recommend >= 3')
        warn = 1
if fail:
    exit(1)
if warn:
    print('NOTE: some scenes could use more phases')
" 2>/dev/null)
  PHASE_EXIT=$?
  if [ $PHASE_EXIT -ne 0 ]; then
    echo "$PHASE_FAIL"
    echo "FAIL: 视觉分镜不完整（长场景缺少 visual_phases）"
    FAIL=1
  else
    echo "PASS: 视觉分镜完整性检查通过"
  fi
fi

# ── BGM 隔离性校验 ──
VOL_WITH=$(ffmpeg -i output.mp4 -af "volumedetect" -f null /dev/null 2>&1 | grep -oP 'mean_volume: \K[\-\d.]+')
VOL_WITHOUT=$(ffmpeg -i output_no_bgm.mp4 -af "volumedetect" -f null /dev/null 2>&1 | grep -oP 'mean_volume: \K[\-\d.]+')
echo "BGM check: with=${VOL_WITH} dB, without=${VOL_WITHOUT} dB"

if [ -z "$VOL_WITH" ] || [ -z "$VOL_WITHOUT" ]; then
  echo "FAIL: BGM volumedetect 数据缺失"
  FAIL=1
elif python3 -c "exit(0 if float('${VOL_WITHOUT}') < float('${VOL_WITH}') - 2.0 else 1)"; then
  echo "PASS: BGM 隔离校验通过"
else
  DIFF=$(python3 -c "print(abs(float('${VOL_WITHOUT:-0}') - float('${VOL_WITH:-0}')))")
  echo "FAIL: no_bgm 文件 BGM 未消除（差值仅 ${DIFF} dB，需 >= 3dB）"
  FAIL=1
fi

if [ $FAIL -eq 0 ]; then
  echo "=== Stage 6 完成门禁通过 ==="

  # ── 渲染帧视觉分析（Layer 2）──
  if [ -f "output.mp4" ]; then
    echo "--- 渲染帧视觉分析 ---"
    python3 "${SCRIPT_DIR}/frame_analysis.py" . || {
      echo "WARN: 帧分析发现问题，建议检查但可继续"
    }
  fi
else
  echo "=== Stage 6 完成门禁失败 ==="
  exit 1
fi
