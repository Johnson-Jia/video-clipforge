#!/usr/bin/env bash
# 环境检测 + 自动安装
#
# 用法: bash scripts/env_check.sh
# 检测所有依赖，自动安装 HyperFrames Skills，创建标记文件。

set -e
MARKER="workspace/.env-checked"

if [ -f "$MARKER" ]; then
  echo "环境已检测过，跳过。删除 $MARKER 可重新检测。"
  exit 0
fi

echo "=== 环境检测 ==="

# ── 必须依赖 ──
NODE_VER=$(node -v 2>/dev/null | sed 's/v//' | cut -d. -f1)
[ -n "$NODE_VER" ] && [ "$NODE_VER" -ge 22 ] && echo "✅ Node.js $(node -v)" || echo "❌ Node.js >= 22 required"
command -v ffmpeg &>/dev/null && echo "✅ FFmpeg" || echo "❌ FFmpeg not found"
python -m edge_tts --version &>/dev/null && echo "✅ edge-tts" || echo "❌ edge-tts not found"
command -v yt-dlp &>/dev/null && echo "✅ yt-dlp $(yt-dlp --version 2>/dev/null)" || echo "❌ yt-dlp not found"
command -v gh &>/dev/null && echo "✅ GitHub CLI (gh)" || echo "⚠ gh not found（用于 GitHub 项目数据）"
command -v jq &>/dev/null && echo "✅ jq" || echo "⚠ jq not found（缺失时 loudnorm 降级单遍处理）"

# ── 自动安装 HyperFrames Skills ──
if [ -f ".agents/skills/hyperframes/SKILL.md" ]; then
  echo "✅ HyperFrames skills"
else
  echo "⏳ HyperFrames skills 未安装，正在自动安装..."
  npx skills add heygen-com/hyperframes
  [ $? -eq 0 ] && echo "✅ HyperFrames skills 安装成功" || echo "❌ 自动安装失败，请手动执行: npx skills add heygen-com/hyperframes"
fi

# ── 可选依赖 ──
python -c "from transformers import MusicgenForConditionalGeneration; print('✅ MusicGen (可选)')" 2>/dev/null || echo "⚠ MusicGen not installed (可选，仅 AI 二创配乐)"

# 工具脚本
mkdir -p scripts
if [ ! -f "scripts/generate_bgm.py" ] || [ ! -f "scripts/merge_video_audio.sh" ]; then
  echo "⏳ 复制工具脚本（从本地仓库）..."
  SCRIPTS_DIR="$(git rev-parse --show-toplevel)/.claude/commands/clipforge/scripts"
  mkdir -p "$WORKSPACE/scripts"
  for f in generate_bgm.py merge_video_audio.sh; do
    if [ -f "$SCRIPTS_DIR/$f" ]; then
      cp "$SCRIPTS_DIR/$f" "scripts/$f"
    fi
  done
  chmod +x scripts/merge_video_audio.sh 2>/dev/null
  echo "✅ 工具脚本就绪"
fi

echo ""
echo "=== 检测完成 ==="
mkdir -p workspace
touch "$MARKER"
