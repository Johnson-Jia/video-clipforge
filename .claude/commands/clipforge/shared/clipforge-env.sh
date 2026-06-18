#!/usr/bin/env bash
# clipforge-env.sh — 定位技能目录 CF_DIR（命令 source 用）
# 用户级 ~/.claude 优先，项目级 .claude 兜底；支持技能 install 到用户级
CF_DIR=""
if [ -d "$HOME/.claude/commands/clipforge" ]; then
  CF_DIR="$HOME/.claude/commands/clipforge"
elif [ -n "${GIT_ROOT:-}" ] && [ -d "$GIT_ROOT/.claude/commands/clipforge" ]; then
  CF_DIR="$GIT_ROOT/.claude/commands/clipforge"
else
  GIT_ROOT=$(git rev-parse --show-toplevel 2>/dev/null)
  if [ -n "$GIT_ROOT" ] && [ -d "$GIT_ROOT/.claude/commands/clipforge" ]; then
    CF_DIR="$GIT_ROOT/.claude/commands/clipforge"
  fi
fi
[ -z "$CF_DIR" ] && { echo "FATAL: 找不到 clipforge 技能目录（~/.claude 或项目 .claude）" >&2; exit 1; }
export CF_DIR
cd "$CF_DIR"  # source 后自动进入技能目录（命令文档无需再 cd）
