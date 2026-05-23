#!/usr/bin/env bash
# 封面渲染（含三级降级）
#
# 用法: bash scripts/render_cover.sh [项目目录]
# 项目目录默认为当前目录
#
# 降级策略: HyperFrames 隔离渲染 → ffmpeg 视频首帧 → 报错退出

set -e
PROJECT_DIR="${1:-.}"
cd "$PROJECT_DIR"

echo "[render_cover] 检查封面..."

if [ -s cover.png ]; then
  echo "[render_cover] cover.png 已存在，跳过"
  exit 0
fi

echo "[render_cover] cover.png 缺失，尝试渲染..."

# 方案 A: HyperFrames 隔离渲染
TMPDIR="${TEMP:-/tmp}/cover-render"
mkdir -p "$TMPDIR"
cp cover.html "$TMPDIR/index.html" 2>/dev/null || true
if npx hyperframes render "$TMPDIR" --output "$TMPDIR/cover.mp4" --video-bitrate 5M 2>/dev/null; then
  ffmpeg -y -i "$TMPDIR/cover.mp4" -vf "select=eq(n\,0),scale=1080:1920:flags=lanczos" -vframes 1 -update 1 cover.png 2>/dev/null
  rm -rf "$TMPDIR"
  echo "[render_cover] 方案A成功: HyperFrames 隔离渲染"
fi

# 方案 B: ffmpeg 从视频首帧提取
if [ ! -s cover.png ]; then
  ffmpeg -y -i output.mp4 -vf "select=eq(n\,0)" -vframes 1 -update 1 cover.png 2>/dev/null
  echo "[render_cover] WARNING: 使用视频首帧作为封面降级方案"
fi

# 最终检查
if [ -s cover.png ]; then
  echo "[render_cover] cover.png 已生成 ($(du -h cover.png | cut -f1))"
else
  echo "[render_cover] FAIL: 所有封面渲染方案失败"
  exit 1
fi
