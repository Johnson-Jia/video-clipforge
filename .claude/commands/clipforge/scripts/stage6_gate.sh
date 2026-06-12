#!/usr/bin/env bash
# Stage 6 完成门禁（thin wrapper）
#
# 用法: bash scripts/stage6_gate.sh [--project-dir DIR]
# 所有检查逻辑已迁移到 engine/gate.py，本脚本仅做编排调用。

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/_cd_project.sh" && cd_project "$@"

# cd_project() 的 PROJECT_DIR 是 local 变量，函数返回后丢失。
# 在此保存绝对路径供后续 gate.py 使用。
PROJECT_ABS="$(pwd)"

echo "=== Stage 6 完成门禁 ==="

FAIL=0

# ── 导演门禁（Layer 1：HTML 设计意图验证）──
echo "--- 导演门禁 ---"
python "${SCRIPT_DIR}/director_gate.py" . || {
  echo "FAIL: 导演门禁未通过"
  FAIL=1
}

# ── gate.py 门禁（HTML 结构 + 输出视频 + BGM 隔离 + 渲染前依赖）──
echo "--- engine/gate.py 门禁 ---"
cd "${SCRIPT_DIR}/.."
python engine/gate.py --skill stage6-production --project-dir "${PROJECT_ABS}" || {
  echo "FAIL: gate.py 门禁未通过"
  FAIL=1
}
cd - > /dev/null

if [ $FAIL -eq 0 ]; then
  echo "=== Stage 6 完成门禁通过 ==="

  # ── 渲染帧视觉分析（Layer 2，非阻塞）──
  if [ -f "output.mp4" ]; then
    echo "--- 渲染帧视觉分析 ---"
    python "${SCRIPT_DIR}/frame_analysis.py" . || {
      echo "WARN: 帧分析发现问题，建议检查但可继续"
    }
  fi
else
  echo "=== Stage 6 完成门禁失败 ==="
  exit 1
fi
