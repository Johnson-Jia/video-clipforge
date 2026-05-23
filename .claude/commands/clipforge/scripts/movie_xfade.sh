#!/usr/bin/env bash
# 电影片段 xfade 拼接
#
# 用法: bash scripts/movie_xfade.sh <scene_id> <xfade_duration>
#   scene_id:       场景 ID（如 wives_video）
#   xfade_duration: 交叉溶解时长（秒，默认 0.5）
#
# 输入: clips_16x9/clip_{scene_id}_seg_*.mp4
# 输出: clips_16x9/clip_{scene_id}_xfade.mp4
#
# 自动检测片段数量：
#   1 段 → 直接复制
#   2 段 → 两段 xfade
#   3+ 段 → 链式 xfade

set -e
SCENE_ID="${1:?用法: bash scripts/movie_xfade.sh <scene_id> [xfade_duration]}"
XF="${2:-0.5}"
CLIPS_DIR="clips_16x9"

# 收集片段（按序号排序）
mapfile -t SEGMENTS < <(ls "$CLIPS_DIR"/clip_${SCENE_ID}_seg_*.mp4 2>/dev/null | sort -t_ -k3 -n)
COUNT=${#SEGMENTS[@]}

if [ "$COUNT" -eq 0 ]; then
  echo "ERROR: 未找到片段 $CLIPS_DIR/clip_${SCENE_ID}_seg_*.mp4"
  exit 1
fi

OUTPUT="$CLIPS_DIR/clip_${SCENE_ID}_xfade.mp4"

if [ "$COUNT" -eq 1 ]; then
  # 单段直接复制
  cp "${SEGMENTS[0]}" "$OUTPUT"
  echo "单段，直接复制: $OUTPUT"

elif [ "$COUNT" -eq 2 ]; then
  # 两段 xfade
  D0=$(ffprobe -v quiet -show_entries format=duration -of csv=p=0 "${SEGMENTS[0]}")
  OFFSET=$(awk "BEGIN {printf \"%.2f\", $D0 - $XF}")

  ffmpeg -y \
    -i "${SEGMENTS[0]}" -i "${SEGMENTS[1]}" \
    -filter_complex \
      "[0:v][1:v]xfade=transition=fade:duration=$XF:offset=$OFFSET[vout];\
       [0:a][1:a]acrossfade=d=$XF[aout]" \
    -map "[vout]" -map "[aout]" \
    -c:v libx264 -b:v 5M -c:a aac -b:a 192k \
    "$OUTPUT" 2>/dev/null
  echo "两段拼接完成: $OUTPUT"

else
  # 多段链式 xfade — 动态构建 filter_complex
  INPUT_ARGS=""
  VFILTER=""
  AFILTER=""
  PREV_V="0:v"
  PREV_A="0:a"

  for i in $(seq 0 $((COUNT-1))); do
    INPUT_ARGS="$INPUT_ARGS -i ${SEGMENTS[$i]}"
  done

  # 计算每段时长
  DURATIONS=()
  for seg in "${SEGMENTS[@]}"; do
    DURATIONS+=($(ffprobe -v quiet -show_entries format=duration -of csv=p=0 "$seg"))
  done

  for i in $(seq 1 $((COUNT-1))); do
    # offset = sum(D0..Di) - i * XF
    SUM=0
    for j in $(seq 0 $i); do
      SUM=$(awk "BEGIN {printf \"%.2f\", $SUM + ${DURATIONS[$j]}}")
    done
    Oi=$(awk "BEGIN {printf \"%.2f\", $SUM - ($i+1) * $XF}")

    if [ $i -eq $((COUNT-1)) ]; then
      VOUT="vout"
      AOUT="aout"
    else
      VOUT="v0$i"
      AOUT="a0$i"
    fi

    VFILTER="${VFILTER}[${PREV_V}][$i:v]xfade=transition=fade:duration=$XF:offset=$Oi[$VOUT];"
    AFILTER="${AFILTER}[${PREV_A}][$i:a]acrossfade=d=$XF[$AOUT];"

    PREV_V="$VOUT"
    PREV_A="$AOUT"
  done

  FILTER="${VFILTER}${AFILTER}"
  # 去掉末尾分号
  FILTER="${FILTER%;}"

  ffmpeg -y $INPUT_ARGS \
    -filter_complex "$FILTER" \
    -map "[vout]" -map "[aout]" \
    -c:v libx264 -b:v 5M -c:a aac -b:a 192k \
    "$OUTPUT" 2>/dev/null
  echo "${COUNT}段链式拼接完成: $OUTPUT"
fi

# 输出实际时长
ACTUAL=$(ffprobe -v quiet -show_entries format=duration -of csv=p=0 "$OUTPUT")
echo "实际时长: ${ACTUAL}s"
