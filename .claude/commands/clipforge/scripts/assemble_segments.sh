#!/usr/bin/env bash
# assemble_segments.sh — 教程合集版本1 合成（各段 output.mp4 concat + 开场）
#
# 用法:
#   bash scripts/assemble_segments.sh \
#     --segments-dir workspace/2026/07/06 \
#     --episode E05 \
#     --segments "hook intro pain rag graph1 graph2 skill mcp cta" \
#     --opening workspace/ai-landing-tutorial-series/tutorial-opening/output.mp4 \
#     --output workspace/2026/07/06/E05-final.mp4
#
# 前置: 各段 output.mp4（含 BGM，HyperFrames 混音，stereo）+ opening/output.mp4
# 输出: E0X-final.mp4（开场 + 各段 output.mp4 concat）
#
# 各段 output.mp4 已是 stereo（HyperFrames 混音），concat demuxer + re-encode crf 14

set -eo pipefail

# 项目根定位（脚本在 .claude/commands/clipforge/scripts/，项目根 = 上 4 级）
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -W 2>/dev/null || pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../../.." && pwd -W 2>/dev/null || pwd)"

# ── 参数解析 ──
SEGMENTS_DIR=""
EPISODE=""
SEGMENTS=""
OPENING=""
OUTPUT=""
while [ $# -gt 0 ]; do
  case "$1" in
    --segments-dir) SEGMENTS_DIR="$2"; shift 2;;
    --episode) EPISODE="$2"; shift 2;;
    --segments) SEGMENTS="$2"; shift 2;;
    --opening) OPENING="$2"; shift 2;;
    --output) OUTPUT="$2"; shift 2;;
    -h|--help) sed -n '2,14p' "$0"; exit 0;;
    *) echo "FAIL: 未知参数 $1"; exit 1;;
  esac
done

[ -n "$SEGMENTS_DIR" ] || { echo "FAIL: --segments-dir 必填"; exit 1; }
[ -n "$EPISODE" ] || { echo "FAIL: --episode 必填"; exit 1; }
[ -n "$SEGMENTS" ] || { echo "FAIL: --segments 必填"; exit 1; }
[ -n "$OPENING" ] || { echo "FAIL: --opening 必填"; exit 1; }
[ -n "$OUTPUT" ] || { echo "FAIL: --output 必填"; exit 1; }

# 转绝对路径（Windows pwd -W 兼容 ffmpeg）
to_abs() { ( cd "$1" 2>/dev/null && pwd -W 2>/dev/null ) || ( cd "$1" 2>/dev/null && pwd ) || echo "$1"; }
SEGMENTS_DIR=$(to_abs "$SEGMENTS_DIR")
OPENING="$(to_abs "$(dirname "$OPENING")")/$(basename "$OPENING")"
OUTPUT="$(to_abs "$(dirname "$OUTPUT")")/$(basename "$OUTPUT")"
EPISODE_LOWER=$(echo "$EPISODE" | tr '[:upper:]' '[:lower:]')
TMP_DIR="$SEGMENTS_DIR/.segments_tmp_$$"
mkdir -p "$TMP_DIR"
trap 'rm -rf "$TMP_DIR"' EXIT

echo "[assemble_segments] === $EPISODE 版本1 concat 开始 ==="
echo "[assemble_segments] segments-dir: $SEGMENTS_DIR"

# ── Step 1: 门禁 ──
echo "[assemble_segments] Step 1: 门禁..."
[ -f "$OPENING" ] || { echo "FAIL: 开场不存在: $OPENING"; exit 1; }
for seg in $SEGMENTS; do
  seg_file="$SEGMENTS_DIR/tutorial-${EPISODE_LOWER}-${seg}/output.mp4"
  [ -f "$seg_file" ] || { echo "FAIL: 段 output.mp4 不存在: $seg_file"; exit 1; }
done
SEG_COUNT=$(echo $SEGMENTS | wc -w)
echo "[assemble_segments]   门禁通过（${SEG_COUNT} 段 + 开场）"

# ── Step 2: 生成 concat list（开场 + 各段 output.mp4）──
echo "[assemble_segments] Step 2: 生成 concat list..."
printf "file '%s'\n" "$OPENING" > "$TMP_DIR/concat_list.txt"
for seg in $SEGMENTS; do
  seg_file="$SEGMENTS_DIR/tutorial-${EPISODE_LOWER}-${seg}/output.mp4"
  printf "file '%s'\n" "$seg_file" >> "$TMP_DIR/concat_list.txt"
done

# ── Step 3: concat（re-encode crf 14, stereo）──
echo "[assemble_segments] Step 3: concat..."
ffmpeg -y -f concat -safe 0 -i "$TMP_DIR/concat_list.txt" \
  -c:v libx264 -crf 14 -preset medium -c:a aac -b:a 192k -ac 2 -ar 48000 -pix_fmt yuv420p \
  "$OUTPUT" 2>/dev/null
echo "[assemble_segments]   concat 完成"

# ── Step 4: 验证 ──
echo "[assemble_segments] Step 4: 验证..."
DUR=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$OUTPUT")
CH=$(ffprobe -v error -select_streams a -show_entries stream=channels -of csv=p=0 "$OUTPUT" | head -1)
SIZE=$(du -h "$OUTPUT" | cut -f1)
MEAN_VOL=$(ffmpeg -i "$OUTPUT" -af "volumedetect" -vn -f null /dev/null 2>&1 | grep mean_volume | grep -oP '[-\d.]+ dB' | head -1)
echo "[assemble_segments]   时长: ${DUR}s, 声道: $CH, 大小: $SIZE, mean_volume: $MEAN_VOL"
[ "$CH" = "2" ] || { echo "FAIL: 声道非 stereo ($CH)"; exit 1; }

# ── Step 5: 标记 ──
MARKER="$(dirname "$OUTPUT")/.assemble_segments_marker.json"
cat > "$MARKER" <<EOFMarker
{
  "script": "assemble_segments.sh",
  "episode": "$EPISODE",
  "timestamp": "$(date -Iseconds 2>/dev/null || echo unknown)",
  "segments": $SEG_COUNT,
  "final_duration": $DUR,
  "channels": $CH,
  "mean_volume": "$MEAN_VOL"
}
EOFMarker
echo "[assemble_segments] === $EPISODE 版本1 完成: $OUTPUT (${DUR}s) ==="
