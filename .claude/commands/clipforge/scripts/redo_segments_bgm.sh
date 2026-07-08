#!/usr/bin/env bash
# redo_segments_bgm.sh — 各段 BGM 连续（主轨 offset 截取，concat 后 BGM 像一首贯穿）
#
# 保留 narration + creative，只换 BGM（主轨对应片段）+ 重渲染
# 主轨 = main + extend 每首 loudnorm I=-20 标准化 + acrossfade + stream_loop 整集 + afade
# 各段 = 主轨 [累计offset, offset+段时长] 截取 → bgm.wav → bgm_pipeline + assemble + render
#
# 用法:
#   bash scripts/redo_segments_bgm.sh \
#     --segments-dir workspace/2026/07/06 --episode E05 \
#     --segments "hook intro pain rag graph1 graph2 skill mcp cta" \
#     --bgm-plan workspace/ai-landing-tutorial-series/E05-bgm-plan.json

set -eo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -W 2>/dev/null || pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../../.." && pwd -W 2>/dev/null || pwd)"

SEGMENTS_DIR=""; EPISODE=""; SEGMENTS=""; BGM_PLAN=""
while [ $# -gt 0 ]; do
  case "$1" in
    --segments-dir) SEGMENTS_DIR="$2"; shift 2;;
    --episode) EPISODE="$2"; shift 2;;
    --segments) SEGMENTS="$2"; shift 2;;
    --bgm-plan) BGM_PLAN="$2"; shift 2;;
    -h|--help) sed -n '2,12p' "$0"; exit 0;;
    *) echo "FAIL: 未知参数 $1"; exit 1;;
  esac
done

[ -n "$SEGMENTS_DIR" ] || { echo "FAIL: --segments-dir 必填"; exit 1; }
[ -n "$EPISODE" ] || { echo "FAIL: --episode 必填"; exit 1; }
[ -n "$SEGMENTS" ] || { echo "FAIL: --segments 必填"; exit 1; }
[ -n "$BGM_PLAN" ] || { echo "FAIL: --bgm-plan 必填"; exit 1; }

to_abs() { ( cd "$1" 2>/dev/null && pwd -W 2>/dev/null ) || ( cd "$1" 2>/dev/null && pwd ) || echo "$1"; }
SEGMENTS_DIR=$(to_abs "$SEGMENTS_DIR")
BGM_PLAN="$(to_abs "$(dirname "$BGM_PLAN")")/$(basename "$BGM_PLAN")"
BGM_LIB="$PROJECT_ROOT/workspace/bgm"
EPISODE_LOWER=$(echo "$EPISODE" | tr '[:upper:]' '[:lower:]')
TMP_DIR="$SEGMENTS_DIR/.redo_bgm_tmp_$$"
mkdir -p "$TMP_DIR"
trap 'rm -rf "$TMP_DIR"' EXIT
START_TIME=$(date +%s)

[ -f "$BGM_PLAN" ] || { echo "FAIL: bgm_plan 不存在: $BGM_PLAN"; exit 1; }
[ -d "$BGM_LIB" ] || { echo "FAIL: BGM 库不存在: $BGM_LIB"; exit 1; }

# 读 bgm_plan（main + extend，sys.argv 避免 encoding/括号 bug）
MAIN=$(python -c "import json,sys; print(json.load(open(sys.argv[1], encoding='utf-8'))['main'])" "$BGM_PLAN")
EXTEND=$(python -c "import json,sys; d=json.load(open(sys.argv[1], encoding='utf-8')); print(' '.join(d.get('extend', d.get('version2_extend',[]))))" "$BGM_PLAN")

echo "[redo_segments_bgm] === $EPISODE BGM 连续重做（主轨 offset 截取）==="
echo "[redo_segments_bgm] main=$MAIN extend=[$EXTEND]"

# ── Step 1: 算整集时长（各段 output.mp4 累加）──
TOTAL_DUR=0
for seg in $SEGMENTS; do
  segdir="$SEGMENTS_DIR/tutorial-${EPISODE_LOWER}-${seg}"
  [ -f "$segdir/output.mp4" ] || { echo "FAIL: output.mp4 不存在: $segdir"; exit 1; }
  d=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$segdir/output.mp4")
  TOTAL_DUR=$(awk "BEGIN{print $TOTAL_DUR + $d}")
done
echo "[redo_segments_bgm] 整集时长: ${TOTAL_DUR}s"

# ── Step 2: 生成主轨（每首 loudnorm I=-20 + acrossfade + stream_loop 整集 + afade）──
echo "[redo_segments_bgm] 生成主轨（每首 loudnorm I=-20 标准化）..."
NORM_DIR="$TMP_DIR/norm"
mkdir -p "$NORM_DIR"
ffmpeg -y -i "$BGM_LIB/$MAIN" -af "loudnorm=I=-20:TP=-2" -ac 2 -ar 48000 "$NORM_DIR/0.wav" 2>/dev/null
BGM_CHAIN="$TMP_DIR/bgm_chain.wav"
cp "$NORM_DIR/0.wav" "$BGM_CHAIN"
idx=1
for ext in $EXTEND; do
  [ -f "$BGM_LIB/$ext" ] || { echo "WARN: extend 不存在: $ext"; continue; }
  ffmpeg -y -i "$BGM_LIB/$ext" -af "loudnorm=I=-20:TP=-2" -ac 2 -ar 48000 "$NORM_DIR/$idx.wav" 2>/dev/null
  NEXT="$TMP_DIR/bgm_chain_next.wav"
  ffmpeg -y -i "$BGM_CHAIN" -i "$NORM_DIR/$idx.wav" -filter_complex "acrossfade=d=2" "$NEXT" 2>/dev/null
  mv "$NEXT" "$BGM_CHAIN"
  idx=$((idx+1))
done
INT_TOTAL=${TOTAL_DUR%.*}
BGM_TRACK="$TMP_DIR/bgm_track.wav"
ffmpeg -y -stream_loop -1 -i "$BGM_CHAIN" -t "$TOTAL_DUR" \
  -af "afade=t=in:st=0:d=2,afade=t=out:st=$((INT_TOTAL-3)):d=3" \
  -ac 2 -ar 48000 "$BGM_TRACK" 2>/dev/null
echo "[redo_segments_bgm] 主轨生成: ${TOTAL_DUR}s"
# 验证主轨各时段有声音（非静音，afade 语法正确）
for t in 0 50 100 200; do
  echo "  主轨 ${t}s: $(ffmpeg -ss $t -t 2 -i "$BGM_TRACK" -af volumedetect -f null /dev/null 2>&1 | grep mean_volume | grep -oP '[-\d.]+ dB')"
done

# ── Step 3: 各段截取主轨片段 + bgm_pipeline + assemble + render ──
offset=0
for seg in $SEGMENTS; do
  segdir="$SEGMENTS_DIR/tutorial-${EPISODE_LOWER}-${seg}"
  d=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$segdir/output.mp4")
  echo ""
  echo "========== $seg: offset=${offset}s dur=${d}s =========="
  [ -f "$segdir/narration.mp3" ] || { echo "FAIL: narration.mp3 不存在: $segdir"; exit 1; }
  [ -d "$segdir/creative" ] || { echo "FAIL: creative/ 不存在: $segdir"; exit 1; }

  # 截取主轨片段 → bgm.wav（-ss 输入 seek + 重编码，准确）
  rm -f "$segdir/.bgm_pipeline_marker.json"
  ffmpeg -y -ss "$offset" -t "$d" -i "$BGM_TRACK" -ac 2 -ar 48000 "$segdir/bgm.wav" 2>/dev/null
  actual=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$segdir/bgm.wav")
  echo "  bgm.wav 片段: ${actual}s（期望 ${d}s，offset=${offset}）"

  # 记 meta（sys.argv 避免 encoding/括号 bug）
  python -c "import json,sys; p=sys.argv[1]; d=json.load(open(p, encoding='utf-8')); d.setdefault('meta',{})['bgm_source']=sys.argv[2]; d['meta']['bgm_offset']=sys.argv[3]; json.dump(d, open(p,'w',encoding='utf-8'), ensure_ascii=False, indent=2)" "$segdir/segment_durations.json" "$MAIN" "$offset"

  # bgm_pipeline + assemble + render（$SCRIPT_DIR 绝对路径调子脚本）
  bash "$SCRIPT_DIR/bgm_pipeline.sh" --project-dir "$segdir" 2>&1 | grep -vE "^frame=|Press|encoded" | tail -2
  bash "$SCRIPT_DIR/s6_assemble.sh" --project-dir "$segdir" 2>&1 | tail -1
  bash "$SCRIPT_DIR/s6_render.sh" --project-dir "$segdir" 2>&1 | grep -vE "^frame=|Press|encoded" | tail -2

  # 真实验证：output.mp4 修改时间 > START_TIME（s6_render 真跑了）
  out_mtime=$(stat -c %Y "$segdir/output.mp4")
  if [ "$out_mtime" -gt "$START_TIME" ]; then
    echo "  [$seg] output.mp4 已更新 ✓"
  else
    echo "  [$seg] FAIL: output.mp4 未更新（s6_render 失败）"; exit 1
  fi

  offset=$(awk "BEGIN{print $offset + $d}")
done

echo ""
echo "[redo_segments_bgm] === $EPISODE BGM 连续重做完成（各段主轨片段，concat 后 BGM 连贯）==="
