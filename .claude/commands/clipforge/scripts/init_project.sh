#!/usr/bin/env bash
# 项目目录初始化
#
# 在 workspace/ 下创建指定名称的项目目录，生成标准目录结构。
# 用法: bash scripts/init_project.sh <项目名称>

set -euo pipefail

PROJECT_NAME="${1:?用法: bash scripts/init_project.sh <项目名称>}"

# 确定 workspace 目录（相对于项目根目录）
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
WORKSPACE_DIR="$(cd "$SCRIPT_DIR/../../.." && pwd)/workspace"

PROJECT_DIR="$WORKSPACE_DIR/$PROJECT_NAME"

if [ -d "$PROJECT_DIR" ]; then
  echo "WARNING: $PROJECT_DIR 已存在"
  read -p "继续初始化（可能覆盖空文件）？[y/N] " -r
  [[ ! $REPLY =~ ^[Yy]$ ]] && exit 0
fi

mkdir -p "$PROJECT_DIR"
cd "$PROJECT_DIR"

echo "=== 初始化项目: $PROJECT_NAME ==="

# 创建目录结构
mkdir -p narration_segs

# 生成空模板文件（不覆盖已有文件）
safe_touch() {
  if [ ! -f "$1" ]; then
    touch "$1"
    echo "  创建: $1"
  else
    echo "  存在: $1（跳过）"
  fi
}

# 核心文件
safe_touch content_summary.md
safe_touch design.md
safe_touch narration.txt
safe_touch narration_segments.json
safe_touch segment_durations.json
safe_touch douyin.md

# HTML 文件
safe_touch index.html
safe_touch cover.html

echo ""
echo "项目目录: $PROJECT_DIR"
echo "初始化完成。下一步: 填入内容摘要后运行 /clipforge"
