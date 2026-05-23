#!/usr/bin/env bash
# Stage 6 完成门禁
#
# 用法: bash scripts/stage6_gate.sh
# 工作目录必须在项目目录下。
# 检查: 文件存在性、视频/音频轨、采样率、BGM 隔离性

set -e
FAIL=0

echo "=== Stage 6 完成门禁 ==="

# ── 文件存在性 ──
for f in index.html output.mp4 output_no_bgm.mp4; do
  if [ ! -s "$f" ]; then
    echo "FAIL: $f missing"
    FAIL=1
  fi
done

# ── 视频/音频轨 ──
for f in output.mp4 output_no_bgm.mp4; do
  ffprobe -v quiet -show_streams "$f" | grep -q "codec_name=h264" || { echo "FAIL: $f no video"; FAIL=1; }
  ffprobe -v quiet -show_streams "$f" | grep -q "codec_name=aac" || { echo "FAIL: $f no audio"; FAIL=1; }
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
else
  echo "=== Stage 6 完成门禁失败 ==="
  exit 1
fi
