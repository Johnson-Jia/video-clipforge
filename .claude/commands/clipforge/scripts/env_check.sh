#!/usr/bin/env bash
# 环境检测 + 自动安装
#
# 用法: bash scripts/env_check.sh
# 检测所有依赖，自动安装 HyperFrames Skills，创建标记文件。

set -e

# ── 定位仓库根（不依赖调用方 cwd）──
# 脚本路径: <repo-root>/.claude/commands/clipforge/scripts/env_check.sh
# 历史 bug：脚本用相对路径（.agents/skills/、workspace/）检查与安装，
# 若调用时 cwd 非仓库根，npx skills add 会在错误目录创建 HyperFrames
# （表现为 HyperFrames 装到 clipforge/ 子目录下）。此处强制 cd 到仓库根。
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../../.." && pwd)"
if [ ! -f "$REPO_ROOT/.claude/commands/clipforge/schema.yaml" ]; then
  echo "FATAL: 无法定位仓库根（$REPO_ROOT 无 .claude/commands/clipforge/schema.yaml）"
  exit 1
fi
cd "$REPO_ROOT"

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

# ── HyperFrames CLI 版本检查 + 刷新缓存（@latest 强制拉最新，确保后续 npx hyperframes 用最新版）──
echo "--- HyperFrames CLI 版本 ---"
HF_VER=$(npx hyperframes@latest --version 2>/dev/null | head -1)
if [ -n "$HF_VER" ]; then
  echo "✅ HyperFrames CLI: ${HF_VER}（已刷新至最新）"
else
  echo "⚠ HyperFrames CLI 版本检查失败（网络？），沿用缓存版本"
fi

# ── 可选依赖 ──
python -c "from transformers import MusicgenForConditionalGeneration; print('✅ MusicGen (可选)')" 2>/dev/null || echo "⚠ MusicGen not installed (可选，仅 AI 二创配乐)"

echo ""
echo "=== 检测完成 ==="
mkdir -p workspace
touch "$MARKER"
