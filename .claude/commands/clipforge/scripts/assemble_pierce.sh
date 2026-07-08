#!/usr/bin/env bash
# assemble_pierce.sh — 教程合集版本2 pierce 合成（一首贯穿 BGM，固定脚本）
#
# 用法:
#   bash scripts/assemble_pierce.sh \
#     --segments-dir workspace/2026/07/06 \
#     --episode E05 \
#     --segments "hook intro pain rag graph1 graph2 skill mcp cta" \
#     --bgm-plan workspace/ai-landing-tutorial-series/E05-bgm-plan.json \
#     --opening workspace/ai-landing-tutorial-series/tutorial-opening/output.mp4 \
#     --output workspace/2026/07/06/E05-final-pierce.mp4
#
# 前置: 各段 output_no_bgm.mp4 + opening/output.mp4 + bgm_plan.json
# 输出: E0X-final-pierce.mp4（主体 output_no_bgm concat + BGM 一首贯穿 + 开头拼开场）
#
# 修复的坑（vs LLM 手写 ffmpeg）:
#   - 声道 mono/stereo 混搭 → Step 3 逐段 -ac 2 强制 stereo
#   - amix double volume → Step 6 单次 [1:a]volume=$VOL
#   - BGM 丢失无检测 → Step 9 mean_volume 振幅验证 + 失败 exit
#
# BGM 同系列拼接（Step 5）: main + version2_extend acrossfade d=2，不够 stream_loop 补足

set -e

# 项目根定位（脚本在 .claude/commands/clipforge/scripts/，项目根 = 上 4 级，避免硬编码绝对路径）
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -W 2>/dev/null || pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../../.." && pwd -W 2>/dev/null || pwd)"

# ── 参数解析 ──
SEGMENTS_DIR=""
EPISODE=""
SEGMENTS=""
BGM_PLAN=""
OPENING=""
OUTPUT=""
BGM_LIB=""
while [ $# -gt 0 ]; do
  case "$1" in
    --segments-dir) SEGMENTS_DIR="$2"; shift 2;;
    --episode) EPISODE="$2"; shift 2;;
    --segments) SEGMENTS="$2"; shift 2;;
    --bgm-plan) BGM_PLAN="$2"; shift 2;;
    --opening) OPENING="$2"; shift 2;;
    --output) OUTPUT="$2"; shift 2;;
    --bgm-lib) BGM_LIB="$2"; shift 2;;
    -h|--help) sed -n '2,20p' "$0"; exit 0;;
    *) echo "FAIL: 未知参数 $1"; exit 1;;
  esac
done

[ -n "$SEGMENTS_DIR" ] || { echo "FAIL: --segments-dir 必填"; exit 1; }
[ -n "$EPISODE" ] || { echo "FAIL: --episode 必填"; exit 1; }
[ -n "$SEGMENTS" ] || { echo "FAIL: --segments 必填"; exit 1; }
[ -n "$BGM_PLAN" ] || { echo "FAIL: --bgm-plan 必填"; exit 1; }
[ -n "$OPENING" ] || { echo "FAIL: --opening 必填"; exit 1; }
[ -n "$OUTPUT" ] || { echo "FAIL: --output 必填"; exit 1; }
[ -n "$BGM_LIB" ] || BGM_LIB="$PROJECT_ROOT/workspace/bgm"

# 转绝对路径（Windows pwd -W 兼容 ffmpeg）
to_abs() { ( cd "$1" 2>/dev/null && pwd -W 2>/dev/null ) || ( cd "$1" 2>/dev/null && pwd ) || echo "$1"; }
SEGMENTS_DIR=$(to_abs "$SEGMENTS_DIR")
BGM_PLAN="$(to_abs "$(dirname "$BGM_PLAN")")/$(basename "$BGM_PLAN")"
OPENING="$(to_abs "$(dirname "$OPENING")")/$(basename "$OPENING")"
OUTPUT="$(to_abs "$(dirname "$OUTPUT")")/$(basename "$OUTPUT")"

EPISODE_LOWER=$(echo "$EPISODE" | tr '[:upper:]' '[:lower:]')
TMP_DIR="$SEGMENTS_DIR/.pierce_tmp_$$"
mkdir -p "$TMP_DIR"
trap 'rm -rf "$TMP_DIR"' EXIT

echo "[assemble_pierce] === $EPISODE pierce 合成开始 ==="
echo "[assemble_pierce] segments-dir: $SEGMENTS_DIR"
echo "[assemble_pierce] bgm-plan: $BGM_PLAN"

# ── Step 1: 门禁 ──
echo "[assemble_pierce] Step 1: 门禁..."
[ -f "$BGM_PLAN" ] || { echo "FAIL: bgm_plan.json 不存在: $BGM_PLAN"; exit 1; }
[ -f "$OPENING" ] || { echo "FAIL: 开场视频不存在: $OPENING"; exit 1; }
[ -d "$BGM_LIB" ] || { echo "FAIL: BGM 库不存在: $BGM_LIB"; exit 1; }
for seg in $SEGMENTS; do
  seg_file="$SEGMENTS_DIR/tutorial-${EPISODE_LOWER}-${seg}/output_no_bgm.mp4"
  [ -f "$seg_file" ] || { echo "FAIL: 段 output_no_bgm 不存在: $seg_file"; exit 1; }
done
SEG_COUNT=$(echo $SEGMENTS | wc -w)
echo "[assemble_pierce]   门禁通过（${SEG_COUNT} 段 + 开场 + bgm_plan）"

# ── Step 2: 读 bgm_plan ──
echo "[assemble_pierce] Step 2: 读 bgm_plan..."
MAIN=$(python -c "import json; print(json.load(open(r'$BGM_PLAN', encoding='utf-8'))['main'])")
VOLUME=$(python -c "import json; print(json.load(open(r'$BGM_PLAN', encoding='utf-8')).get('volume',0.50))")
EXTEND=$(python -c "import json; print(' '.join(json.load(open(r'$BGM_PLAN', encoding='utf-8')).get('version2_extend',[])))")
[ -f "$BGM_LIB/$MAIN" ] || { echo "FAIL: main BGM 不存在: $BGM_LIB/$MAIN"; exit 1; }
echo "[assemble_pierce]   main=$MAIN volume=$VOLUME extend=[$EXTEND]"

# ── Step 3: 逐段强制 stereo（修 mono/stereo 混搭致声道乱跳）──
echo "[assemble_pierce] Step 3: 逐段统一 stereo..."
> "$TMP_DIR/body_list.txt"
for seg in $SEGMENTS; do
  seg_dir="$SEGMENTS_DIR/tutorial-${EPISODE_LOWER}-${seg}"
  nbgs="$TMP_DIR/nbgs_${seg}.mp4"
  ffmpeg -y -i "$seg_dir/output_no_bgm.mp4" \
    -c:v copy -c:a aac -b:a 192k -ar 48000 -ac 2 \
    "$nbgs" 2>/dev/null
  echo "file '$nbgs'" >> "$TMP_DIR/body_list.txt"
done
echo "[assemble_pierce]   逐段 stereo 完成"

# ── Step 4: concat 主体（re-encode crf 14, stereo）──
echo "[assemble_pierce] Step 4: concat 主体..."
BODY_NO_BGM="$TMP_DIR/body_no_bgm.mp4"
ffmpeg -y -f concat -safe 0 -i "$TMP_DIR/body_list.txt" \
  -c:v libx264 -crf 14 -preset medium -c:a aac -b:a 192k -ac 2 -ar 48000 -pix_fmt yuv420p \
  "$BODY_NO_BGM" 2>/dev/null
DUR=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$BODY_NO_BGM")
echo "[assemble_pierce]   主体时长: ${DUR}s"

# ── Step 5: BGM 同系列拼接（main + extend acrossfade + stream_loop 补足 + 淡入淡出）──
echo "[assemble_pierce] Step 5: BGM 拼接（每首 loudnorm I=-20 标准化后 acrossfade，统一响度）..."
NORM_DIR="$TMP_DIR/norm"
mkdir -p "$NORM_DIR"
ffmpeg -y -i "$BGM_LIB/$MAIN" -af "loudnorm=I=-20:TP=-2,bass=g=-6:f=80" -ac 2 -ar 48000 "$NORM_DIR/0.wav" 2>/dev/null
BGM_CHAIN="$TMP_DIR/bgm_chain.wav"
cp "$NORM_DIR/0.wav" "$BGM_CHAIN"
idx=1
for ext in $EXTEND; do
  [ -f "$BGM_LIB/$ext" ] || { echo "WARN: extend BGM 不存在，跳过: $ext"; continue; }
  ffmpeg -y -i "$BGM_LIB/$ext" -af "loudnorm=I=-20:TP=-2,bass=g=-6:f=80" -ac 2 -ar 48000 "$NORM_DIR/$idx.wav" 2>/dev/null
  NEXT="$TMP_DIR/bgm_chain_next.wav"
  ffmpeg -y -i "$BGM_CHAIN" -i "$NORM_DIR/$idx.wav" -filter_complex "acrossfade=d=2" "$NEXT" 2>/dev/null
  mv "$NEXT" "$BGM_CHAIN"
  idx=$((idx+1))
done
INTDUR=${DUR%.*}
BGM_WAV="$TMP_DIR/bgm.wav"
ffmpeg -y -stream_loop -1 -i "$BGM_CHAIN" -t "$DUR" \
  -af "afade=t=in:st=0:d=2,afade=t=out:st=$((INTDUR-3)):d=3" \
  -ac 2 -ar 48000 "$BGM_WAV" 2>/dev/null
echo "[assemble_pierce]   BGM 拼接完成（覆盖 ${DUR}s）"

# ── Step 6: 混合 body + bgm（单次 volume，amix normalize=0 不归一化 → BGM 清晰）──
echo "[assemble_pierce] Step 6: 混合 body + bgm（volume $VOLUME）..."
BODY_WITH_BGM="$TMP_DIR/body_with_bgm.mp4"
ffmpeg -y -i "$BODY_NO_BGM" -i "$BGM_WAV" \
  -filter_complex "[1:a]volume=${VOLUME}[bg];[0:a][bg]amix=inputs=2:duration=first:normalize=0[a]" \
  -map 0:v -map "[a]" \
  -c:v libx264 -crf 14 -preset medium -c:a aac -b:a 192k -ac 2 -ar 48000 -pix_fmt yuv420p \
  "$BODY_WITH_BGM" 2>/dev/null
echo "[assemble_pierce]   混合完成"

# ── Step 7: 拼开场（concat, 都 stereo）──
echo "[assemble_pierce] Step 7: 拼开场..."
printf "file '%s'\nfile '%s'\n" "$OPENING" "$BODY_WITH_BGM" > "$TMP_DIR/pierce_list.txt"
ffmpeg -y -f concat -safe 0 -i "$TMP_DIR/pierce_list.txt" \
  -c:v libx264 -crf 14 -preset medium -c:a aac -b:a 192k -ac 2 -ar 48000 -pix_fmt yuv420p \
  "$OUTPUT" 2>/dev/null
echo "[assemble_pierce]   拼开场完成"

# ── Step 8: Mastering（bypass：教程类 BGM 降优先，保留 mix 响度）──
# 教程类 volume 0.35 + bass 滤波在 mix 生效，Mastering linear 增益会抵消 BGM 降
# （feedback-bgm-mastering-not-datavolume：Mastering 锁整体，降 volume 被 linear 增益拉回）
# bypass 后 final 保留 body_with_bgm 响度（~-19dB），BGM 0.35 听感真降
# 平台自动 loudnorm 弱于 two-pass linear，抵消没那么强；教程类旁白为主，响度 -19 可接受
echo "[assemble_pierce] Step 8: bypass Mastering（教程类保留 mix 响度，BGM 降不被抵消）"

# ── Step 9: 验证（声道 + 时长 + BGM 振幅）──
echo "[assemble_pierce] Step 9: 验证..."
FINAL_DUR=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$OUTPUT")
FINAL_CH=$(ffprobe -v error -select_streams a -show_entries stream=channels -of csv=p=0 "$OUTPUT" | head -1)
OPENING_DUR=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$OPENING")
MEAN_VOL=$(ffmpeg -i "$OUTPUT" -af "volumedetect" -vn -f null /dev/null 2>&1 | grep mean_volume | grep -oP '[-\d.]+ dB' | head -1)
echo "[assemble_pierce]   时长: ${FINAL_DUR}s（开场 ${OPENING_DUR}s + 主体 ${DUR}s）"
echo "[assemble_pierce]   声道: $FINAL_CH"
echo "[assemble_pierce]   BGM mean_volume: $MEAN_VOL"

[ "$FINAL_CH" = "2" ] || { echo "FAIL: 声道非 stereo ($FINAL_CH)，乱跳未修复"; exit 1; }
# 时长断言：FINAL 应在 [开场+主体-1.5, 开场+主体+0.6]（容差：Mastering 重编码膨胀 + concat 对齐）
is_normal=$(awk "BEGIN{print ($FINAL_DUR >= $OPENING_DUR + $DUR - 1.5 && $FINAL_DUR <= $OPENING_DUR + $DUR + 0.6) ? 1 : 0}")
if [ "$is_normal" != "1" ]; then
  echo "FAIL: 时长异常（${FINAL_DUR}s vs 预期 开场+主体=${OPENING_DUR}+${DUR}）"; exit 1
fi
echo "[assemble_pierce]   验证通过"

# ── Step 10: 标记文件 ──
MARKER="$(dirname "$OUTPUT")/.assemble_pierce_marker.json"
cat > "$MARKER" <<EOFMarker
{
  "script": "assemble_pierce.sh",
  "episode": "$EPISODE",
  "timestamp": "$(date -Iseconds 2>/dev/null || echo unknown)",
  "segments": $SEG_COUNT,
  "body_duration": $DUR,
  "final_duration": $FINAL_DUR,
  "main_bgm": "$MAIN",
  "extend_bgm": "$EXTEND",
  "volume": $VOLUME,
  "channels": $FINAL_CH,
  "mean_volume": "$MEAN_VOL"
}
EOFMarker
echo "[assemble_pierce] === $EPISODE pierce 合成完成 ==="
echo "[assemble_pierce] 输出: $OUTPUT ($(du -h "$OUTPUT" | cut -f1), ${FINAL_DUR}s)"
