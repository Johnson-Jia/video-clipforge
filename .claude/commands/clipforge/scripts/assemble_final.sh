#!/usr/bin/env bash
# 封面拼接 + final 输出（统一交付入口）
#
# 用法: bash scripts/assemble_final.sh [项目目录]
# 项目目录默认为当前目录
#
# 前置: cover.png + output.mp4 + narration.mp3 必须存在
# 输出: output_no_bgm.mp4 + final.mp4 + final_no_bgm.mp4
#
# 方式: TS concat + stream copy（不重编码主视频，无损拼接）
# 封面只占 1 帧，对时长和音频几乎无影响
# output_no_bgm.mp4 由本脚本从 output.mp4 视频 + narration.mp3 音频合成

set -e
PROJECT_DIR="${1:-.}"
cd "$PROJECT_DIR"

echo "[assemble_final] 封面嵌入视频第一帧..."

# ── Step 1: 门禁 ──
[ -s cover.png ] || { echo "FAIL: cover.png 缺失"; exit 1; }
[ -s output.mp4 ] || { echo "FAIL: output.mp4 缺失"; exit 1; }
[ -s narration.mp3 ] || { echo "FAIL: narration.mp3 缺失"; exit 1; }

# ── Step 2: 从 output.mp4 读取编码参数 + 分辨率 ──
FPS=$(ffprobe -v quiet -show_entries stream=r_frame_rate -select_streams v -of csv=p=0 output.mp4 | head -1)
FPS_NUM=$(echo "$FPS" | cut -d/ -f1)
PROFILE=$(ffprobe -v quiet -show_entries stream=profile -select_streams v -of csv=p=0 output.mp4 | head -1)
SOURCE_DUR=$(ffprobe -v quiet -show_entries format=duration -of csv=p=0 output.mp4)
FRAME_DUR=$(awk "BEGIN {printf \"%.6f\", 1/$FPS_NUM}")
VIDEO_W=$(ffprobe -v quiet -show_entries stream=width -select_streams v -of csv=p=0 output.mp4 | head -1)
VIDEO_H=$(ffprobe -v quiet -show_entries stream=height -select_streams v -of csv=p=0 output.mp4 | head -1)
echo "[assemble_final] 源视频: ${SOURCE_DUR}s, ${FPS}fps, profile=${PROFILE}, ${VIDEO_W}x${VIDEO_H}, 封面帧长: ${FRAME_DUR}s"

# ── Step 3: 生成 output_no_bgm.mp4（从 output.mp4 视频 + narration.mp3 音频）──
# 这是唯一正确的生成方式：禁止从 output.mp4 提取音频轨
# 音频强制 -ar 48000 -ac 2（stereo 48k），匹配 cover.mp4 的 anullsrc stereo 48k，
# 否则 Step 6 concat（cover + output_no_bgm）因声道/采样率不兼容致 final_no_bgm 只剩 cover 帧（0.5s 损坏）
echo "[assemble_final] 生成 output_no_bgm.mp4（output.mp4 视频 + narration.mp3 音频）..."
ffmpeg -y -i output.mp4 -i narration.mp3 \
  -map 0:v -map 1:a \
  -c:v copy -c:a aac -b:a 192k -ar 48000 -ac 2 \
  -shortest \
  output_no_bgm.mp4 2>/dev/null
echo "[assemble_final] output_no_bgm.mp4 已生成"

# ── Step 4: 封面片段制备（1 帧，mp4 格式，含静音音频轨匹配源，避免 concat 丢音频）──
ffmpeg -y -loop 1 -t $FRAME_DUR -framerate $FPS -i cover.png \
  -f lavfi -t $FRAME_DUR -i "anullsrc=channel_layout=stereo:sample_rate=48000" \
  -c:v libx264 -profile:v $PROFILE -pix_fmt yuv420p \
  -vf "scale=${VIDEO_W}:${VIDEO_H}" \
  -c:a aac -b:a 192k -ar 48000 \
  -shortest -frames:v 1 cover.mp4 2>/dev/null

# ── Step 5: 版本一：含 BGM（filter concat re-encode，根治 mpegts concat DTS 不单调）──
echo "[assemble_final] 生成 final.mp4（含BGM，filter concat）..."
printf "file 'cover.mp4'\nfile 'output.mp4'\n" > concat_final.txt
ffmpeg -y -f concat -safe 0 -i concat_final.txt \
  -c:v libx264 -preset fast -crf 18 -pix_fmt yuv420p -c:a aac -b:a 192k \
  -movflags +faststart final.mp4 2>/dev/null
rm -f concat_final.txt

# ── Step 6: 版本二：无 BGM（filter concat re-encode）──
echo "[assemble_final] 生成 final_no_bgm.mp4（filter concat）..."
printf "file 'cover.mp4'\nfile 'output_no_bgm.mp4'\n" > concat_nobgm.txt
ffmpeg -y -f concat -safe 0 -i concat_nobgm.txt \
  -c:v libx264 -preset fast -crf 18 -pix_fmt yuv420p -c:a aac -b:a 192k \
  -movflags +faststart final_no_bgm.mp4 2>/dev/null
rm -f concat_nobgm.txt cover.mp4

# ── Step 7: Mastering: 平台响度标准化（双 pass linear，稳定）──
# 混音阶段管平衡（旁白 vs BGM），mastering 阶段管响度（匹配平台标准）。
# 目标 I=-14 LUFS（短视频平台标准），TP=-1.5 dB（防爆音）。
# 双 pass linear loudnorm：Pass1 measure → Pass2 linear 固定增益。
# 单 pass 动态 loudnorm 同段多次跑结果不同（重 render 段响度偏离 bug 根因）；
# 双 pass linear 用 measured_I/TP/LRA 固定增益，同段多次结果完全一致。
# 视频流 copy 不重编码，只重编码音频。
master_loudnorm_linear() {
    local FILE="$1"
    local TI="-14" TPV="-1.5"
    # 保存 shell 选项 → 全禁 set -e + pipefail（measure/grep 在某些段 SIGPIPE exit 非 0）
    local OLD_OPTS
    OLD_OPTS=$(set +o)
    set +e
    set +o pipefail 2>/dev/null || true
    # Pass 1: measure（loudnorm json 写临时文件）
    ffmpeg -i "$FILE" -af "loudnorm=I=${TI}:TP=${TPV}:print_format=json" -f null /dev/null 2> _ln.json >/dev/null || true
    local MI MTP MLRA OFF
    MI=$(grep -oP '"input_i"\s*:\s*"\K[^"]+' _ln.json | head -n1) || true
    MTP=$(grep -oP '"input_tp"\s*:\s*"\K[^"]+' _ln.json | head -n1) || true
    MLRA=$(grep -oP '"input_lra"\s*:\s*"\K[^"]+' _ln.json | head -n1) || true
    OFF=$(grep -oP '"target_offset"\s*:\s*"\K[^"]+' _ln.json | head -n1) || true
    rm -f _ln.json
    # 恢复 shell 选项
    eval "$OLD_OPTS"
    if [ -z "$MI" ]; then
        echo "[assemble_final]   WARN: measure 解析失败，跳过 Mastering（保留原 final）"
        return 0
    fi
    echo "[assemble_final]   measured: I=${MI} TP=${MTP} LRA=${MLRA} offset=${OFF}"
    # Pass 2: linear apply（固定增益，稳定）
    ffmpeg -y -i "$FILE" -c:v copy \
      -af "loudnorm=I=${TI}:TP=${TPV}:measured_I=${MI}:measured_TP=${MTP}:measured_LRA=${MLRA}:offset=${OFF}:linear=true" \
      -c:a aac -b:a 192k -ar 48000 \
      "${FILE}.mastered.mp4" 2>/dev/null && mv "${FILE}.mastered.mp4" "$FILE"
}
echo "[assemble_final] Mastering: 双 pass linear loudnorm (I=-14 LUFS 平台标准, TP=-1.5 dB)..."
for FINAL_FILE in final.mp4 final_no_bgm.mp4; do
    master_loudnorm_linear "$FINAL_FILE"
done
echo "[assemble_final] Mastering 完成"

# ── Step 8: 输出验证 ──
FINAL_DUR=$(ffprobe -v quiet -show_entries format=duration -of csv=p=0 final.mp4)
FINAL_AUDIO=$(ffprobe -v quiet -select_streams a -show_entries stream=codec_type -of csv=p=0 final.mp4 | wc -l)
NOBGM_DUR=$(ffprobe -v quiet -show_entries format=duration -of csv=p=0 final_no_bgm.mp4)
NOBGM_AUDIO=$(ffprobe -v quiet -select_streams a -show_entries stream=codec_type -of csv=p=0 final_no_bgm.mp4 | wc -l)

echo "[assemble_final] 完成:"
echo "  final.mp4: $(du -h final.mp4 | cut -f1), ${FINAL_DUR}s, 音频轨道: ${FINAL_AUDIO}"
echo "  final_no_bgm.mp4: $(du -h final_no_bgm.mp4 | cut -f1), ${NOBGM_DUR}s, 音频轨道: ${NOBGM_AUDIO}"

# ── Step 9: 硬性断言：时长不膨胀 + 音频不丢失 ──
# final.mp4 时长不应超过 output.mp4 + 0.15 秒
# （1帧封面 ≈ 0.033s + filter concat 对齐 ≤ 0.06s + 双 pass Mastering 重编码 ≤ 0.05s）
if awk "BEGIN{exit !($FINAL_DUR > $SOURCE_DUR + 0.15)}"; then
  echo "FAIL: final.mp4 时长 ($FINAL_DUR) 远超源视频 ($SOURCE_DUR)，封面膨胀导致 A/V 脱节风险"
  exit 1
fi
if [ "$FINAL_AUDIO" -eq 0 ]; then
  echo "FAIL: final.mp4 无音频轨道"
  exit 1
fi
if [ "$NOBGM_AUDIO" -eq 0 ]; then
  echo "FAIL: final_no_bgm.mp4 无音频轨道"
  exit 1
fi

echo "[assemble_final] 验证通过"

# ── Step 10: 写标记文件（gate 据此判断 final.mp4 是否由本脚本生成）──
cat > .assemble_marker.json <<EOFMarker
{
  "script": "assemble_final.sh",
  "timestamp": "$(date -Iseconds)",
  "source_duration": $SOURCE_DUR,
  "final_duration": $FINAL_DUR,
  "final_no_bgm_duration": $NOBGM_DUR,
  "cover_frames": 1,
  "fps": "$FPS",
  "no_bgm_audio_source": "narration.mp3"
}
EOFMarker
echo "[assemble_final] 标记文件已写入: .assemble_marker.json"
