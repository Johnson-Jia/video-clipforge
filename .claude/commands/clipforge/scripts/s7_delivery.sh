#!/usr/bin/env bash
# s7_delivery.sh — Stage 7 交付管线（全自动）
#
# 用法: bash scripts/s7_delivery.sh [--project-dir DIR]
# 无 --project-dir 时检查 CWD 是否为合法项目目录。
#
# 一次性完成: 封面生成+渲染 → 封面门禁 → 拼接+mastering → 磁盘报告
# 替代原先 4 次独立 LLM 调用。
#
# 前置: cover_params.json（LLM 创意输出）+ output.mp4 + narration.mp3
# 输出: cover.html + cover.png + final.mp4 + final_no_bgm.mp4 + 磁盘报告

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/_cd_project.sh" && cd_project "$@"

# 记住项目目录的绝对路径（generate_cover.py 需要绝对路径）
PROJECT_ABS="$(pwd)"

echo "=== Stage 7 交付管线 ==="

# ══════════════════════════════════════════════════
# Phase A: 前置检查
# ══════════════════════════════════════════════════

echo "--- 前置检查 ---"
if [ ! -s "output.mp4" ]; then
  echo "FAIL: output.mp4 缺失，Stage 6 未完成"
  exit 1
fi
if [ ! -s "index.html" ]; then
  echo "FAIL: index.html 缺失"
  exit 1
fi
if [ ! -s "cover_params.json" ]; then
  echo "FAIL: cover_params.json 缺失，LLM 需先完成封面参数设计"
  exit 1
fi
echo "[OK] 前置检查通过"

# ══════════════════════════════════════════════════
# Phase B: 封面生成
# ══════════════════════════════════════════════════

# ── Step 1: 封面生成 + 渲染 PNG ──
# generate_cover.py 需要从 clipforge 目录调用（模板路径相对解析）
echo "--- Step 1/4: 封面生成 + 渲染 ---"
CLIPFORGE_DIR="${SCRIPT_DIR}/.."
cd "$CLIPFORGE_DIR"
python scripts/generate_cover.py --project-dir "$PROJECT_ABS" --render
cd "$PROJECT_ABS"

if [ ! -s "cover.html" ]; then
  echo "FAIL: cover.html 生成失败"
  exit 1
fi
if [ ! -s "cover.png" ]; then
  echo "FAIL: cover.png 渲染失败"
  exit 1
fi
echo "[OK] cover.html + cover.png 已生成"

# ── Step 2: 封面完整性门禁 ──
echo "--- Step 2/4: 封面完整性门禁 ---"
python "${SCRIPT_DIR}/cover_check.py" cover.html
echo "[OK] 封面门禁通过"

# ══════════════════════════════════════════════════
# Phase C: 拼接 + Mastering
# ══════════════════════════════════════════════════

# ── Step 3: 封面嵌入视频第一帧 + 双版本输出 + Mastering ──
echo "--- Step 3/4: 封面拼接 + Mastering ---"
bash "${SCRIPT_DIR}/assemble_final.sh" .
echo "[OK] final.mp4 + final_no_bgm.mp4 已生成"

# ══════════════════════════════════════════════════
# Phase D: 报告
# ══════════════════════════════════════════════════

# ── Step 4: 磁盘占用报告 ──
echo "--- Step 4/4: 磁盘报告 ---"
bash "${SCRIPT_DIR}/disk_usage.sh" --project-dir .

echo "=== Stage 7 交付管线完成 ==="
echo "产出: cover.html / cover.png / final.mp4 / final_no_bgm.mp4"
echo "下一步: LLM 撰写平台文案（douyin.md 等）"
