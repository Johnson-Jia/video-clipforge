#!/bin/bash
# ═══════════════════════════════════════════════════════════
# install.sh — 一键安装 ClipForge 技能
# ═══════════════════════════════════════════════════════════
# 使用:
#   curl 安装: curl -sL https://raw.githubusercontent.com/Johnson-Jia/video-clipforge/main/install.sh | bash
#   clone 安装: git clone 后在仓库目录执行 ./install.sh [--global] [--project]
#   纯复制:    ./install.sh --copy-only（跳过依赖安装）

set -e

MODE="${1:---project}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_URL="https://github.com/Johnson-Jia/video-clipforge.git"
SKILL_NAME="clipforge"
TMP_DIR=$(mktemp -d)
trap 'rm -rf "$TMP_DIR"' EXIT

echo ""
echo "═══════════════════════════════════════════"
echo " ClipForge — 一键安装器"
echo "═══════════════════════════════════════════"
echo ""

# ── Step 1: 确定来源目录 ──

if [ -f "$SCRIPT_DIR/.claude/commands/${SKILL_NAME}.md" ]; then
  # 从 git clone 目录执行
  SRC_DIR="$SCRIPT_DIR"
  echo "📦 使用本地仓库: $SRC_DIR"
else
  # curl 管道执行，需要先 clone
  echo "📦 下载技能文件..."
  git clone --depth 1 "$REPO_URL" "$TMP_DIR" 2>/dev/null || {
    echo "❌ 克隆失败，请检查网络连接"
    exit 1
  }
  SRC_DIR="$TMP_DIR"
fi

# ── Step 2: 复制技能文件 ──

if [ "$MODE" = "--global" ]; then
  TARGET_DIR="$HOME/.claude/commands"
  echo "🌍 安装模式: 全局 ($TARGET_DIR)"
  echo "   全局安装不绑定项目，需要指定工作目录（视频/evolution/播放数据落处）"
  # 引导设置工作目录默认（tty 交互；curl|bash 非 tty 时只提示）
  WS_INPUT=""
  if [ -t 0 ]; then
    read -p "   请输入工作目录绝对路径（回车跳过）: " WS_INPUT
  fi
  if [ -n "$WS_INPUT" ]; then
    WS_RESOLVED="$(cd "$WS_INPUT" 2>/dev/null && pwd || echo "$WS_INPUT")"
    mkdir -p "$HOME/.claude"
    python - "$WS_RESOLVED" <<'PYEOF'
import json, sys, datetime
from pathlib import Path
cfg_path = Path.home()/'.claude'/'clipforge-config.json'
cfg = json.loads(cfg_path.read_text(encoding='utf-8')) if cfg_path.exists() else {}
cfg['workspace_default'] = sys.argv[1]
cfg['configured_at'] = datetime.datetime.now().isoformat()
cfg_path.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding='utf-8')
print(f"   ✅ 工作目录默认: {cfg['workspace_default']}")
PYEOF
  else
    echo "   未设置（curl 管道或跳过）。首次用时按 env>config>git>cwd 回退。"
    echo "   建议稍后运行 /clipforge-switch-workspace <路径> 显式指定"
  fi
elif [ "$MODE" = "--copy-only" ]; then
  TARGET_DIR=".claude/commands"
  echo "📋 安装模式: 仅复制文件，跳过依赖安装"
else
  TARGET_DIR=".claude/commands"
  echo "📁 安装模式: 项目级 ($TARGET_DIR)"
fi

mkdir -p "$TARGET_DIR/${SKILL_NAME}"

echo "📋 复制技能文件..."
cp "$SRC_DIR/.claude/commands/${SKILL_NAME}.md" "$TARGET_DIR/"

# 复制 clipforge 目录下所有文件（stages, shared, categories, scripts, etc.）
for subdir in stages shared categories scripts engine rules skills components patterns; do
  if [ -d "$SRC_DIR/.claude/commands/${SKILL_NAME}/${subdir}" ]; then
    mkdir -p "$TARGET_DIR/${SKILL_NAME}/${subdir}"
    cp -r "$SRC_DIR/.claude/commands/${SKILL_NAME}/${subdir}/"* "$TARGET_DIR/${SKILL_NAME}/${subdir}/" 2>/dev/null || true
  fi
done

# 复制 clipforge 目录下的 .md 文件（未被上面覆盖的顶层 md）
cp "$SRC_DIR/.claude/commands/${SKILL_NAME}/"*.md "$TARGET_DIR/${SKILL_NAME}/" 2>/dev/null || true

# 复制 schema.yaml
if [ -f "$SRC_DIR/.claude/commands/${SKILL_NAME}/schema.yaml" ]; then
  cp "$SRC_DIR/.claude/commands/${SKILL_NAME}/schema.yaml" "$TARGET_DIR/${SKILL_NAME}/"
fi

echo "✅ 技能文件已复制"

# ── Step 3: 依赖检测与安装 ──

if [ "$MODE" = "--copy-only" ]; then
  echo ""
  echo "═══════════════════════════════════════════"
  echo " ✅ 安装完成（仅文件复制）"
  echo ""
  echo " 使用方式: 在 Claude Code 中输入"
  echo "   /${SKILL_NAME}"
  echo "═══════════════════════════════════════════"
  exit 0
fi

echo ""
echo "── 依赖检测与安装 ──"

ERRORS=()
WARNINGS=()

# ── Node.js ──
NODE_VER=$(node -v 2>/dev/null | sed 's/v//' | cut -d. -f1)
if [ -n "$NODE_VER" ] && [ "$NODE_VER" -ge 22 ]; then
  echo "✅ Node.js $(node -v)"
else
  echo "❌ Node.js >= 22 未安装"
  ERRORS+=("Node.js >= 22: winget install OpenJS.NodeJS.LTS (Win) / brew install node@22 (Mac)")
fi

# ── FFmpeg ──
if command -v ffmpeg &>/dev/null; then
  echo "✅ FFmpeg"
else
  echo "❌ FFmpeg 未安装"
  ERRORS+=("FFmpeg: winget install Gyan.FFmpeg (Win) / brew install ffmpeg (Mac)")
fi

# ── edge-tts ──
if python -m edge_tts --version &>/dev/null 2>&1; then
  echo "✅ edge-tts"
else
  echo "❌ edge-tts 未安装"
  ERRORS+=("edge-tts: pip install edge-tts")
fi

# ── yt-dlp ──
if command -v yt-dlp &>/dev/null; then
  echo "✅ yt-dlp $(yt-dlp --version 2>/dev/null)"
else
  echo "❌ yt-dlp 未安装"
  ERRORS+=("yt-dlp: pip install yt-dlp")
fi

# ── GitHub CLI ──
if command -v gh &>/dev/null; then
  echo "✅ GitHub CLI (gh)"
else
  echo "⚠ GitHub CLI (gh) 未安装 (推荐，用于获取 GitHub 项目实时数据)"
  WARNINGS+=("GitHub CLI: winget install GitHub.cli (Win) / brew install gh (Mac)")
fi

# ── jq（音量精确处理用） ──
if command -v jq &>/dev/null; then
  echo "✅ jq"
else
  echo "⚠ jq 未安装 (推荐，用于 loudnorm 两遍精确音量标准化)"
  WARNINGS+=("jq: winget install jqlang.jq (Win) / brew install jq (Mac)")
fi

# ── HyperFrames Skills ──
if [ -f ".agents/skills/hyperframes/SKILL.md" ]; then
  echo "✅ HyperFrames skills"
else
  echo "⏳ HyperFrames skills 未安装，正在安装..."
  npx skills add heygen-com/hyperframes && echo "✅ HyperFrames skills 安装成功" || {
    echo "❌ 自动安装失败"
    ERRORS+=("HyperFrames: 在项目目录执行 npx skills add heygen-com/hyperframes")
  }
fi

# ── MusicGen（可选） ──
if python -c "from transformers import MusicgenForConditionalGeneration" 2>/dev/null; then
  echo "✅ MusicGen (可选，AI 二创配乐)"
else
  echo "⚠ MusicGen 未安装 (可选，仅 AI 二创配乐时需要)"
fi

# ── 结果汇总 ──

echo ""
echo "═══════════════════════════════════════════"

if [ ${#ERRORS[@]} -eq 0 ]; then
  echo " ✅ 所有必须依赖已就绪"
else
  echo " ⚠️ 以下依赖需要手动安装："
  for err in "${ERRORS[@]}"; do
    echo "   • $err"
  done
  echo ""
  echo " 安装后重新运行此脚本即可"
fi

if [ ${#WARNINGS[@]} -gt 0 ]; then
  echo ""
  for warn in "${WARNINGS[@]}"; do
    echo " ⚠ $warn"
  done
fi

echo ""
echo " 技能文件: $TARGET_DIR/${SKILL_NAME}.md"
echo " 完整目录: $TARGET_DIR/${SKILL_NAME}/"
echo ""
echo " 使用方式: 在 Claude Code 中输入"
echo "   /${SKILL_NAME}"
echo "═══════════════════════════════════════════"
