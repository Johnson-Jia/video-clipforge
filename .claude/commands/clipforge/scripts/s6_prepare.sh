#!/usr/bin/env bash
# s6_prepare.sh — Stage 6 创意前准备（全自动）
#
# 用法: bash scripts/s6_prepare.sh [--project-dir DIR]
# 无 --project-dir 时检查 CWD 是否为合法项目目录。
#
# 一次性完成: phase 校准 → creative/ 碎片骨架生成 → 碎片验证 → 视觉上下文生成
# 替代原先 4 次独立 LLM 调用。
#
# 前置: design.md + segment_durations.json + narration_segments.json
# 输出: phase_timings.json + creative/*.html + visual_context.json

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/_cd_project.sh" && cd_project "$@"

echo "=== Stage 6 创意前准备 ==="

# ── Step 1: Phase 时间校准 ──
echo "--- Step 1/4: Phase 时间校准 ---"
if [ -f "sentence_timestamps.json" ]; then
  python "${SCRIPT_DIR}/phase_calibrator.py" --project-dir .
  echo "[OK] phase_timings.json 已生成"
else
  echo "[SKIP] 无 sentence_timestamps.json，跳过 phase 校准"
fi

# ── Step 2: 生成 creative/ 碎片骨架 ──
echo "--- Step 2/4: 创意碎片骨架生成 ---"
python "${SCRIPT_DIR}/s6_prepare_creative.py" --project-dir .
echo "[OK] creative/ 目录已生成（style.css + sNN.html 模板）"

# ── Step 3: 验证碎片完整性 ──
echo "--- Step 3/4: 碎片验证 ---"
python "${SCRIPT_DIR}/s6_assemble_html.py" --project-dir . --validate
echo "[OK] 碎片骨架完整性验证通过"

# ── Step 4: 生成视觉节奏上下文 ──
echo "--- Step 4/4: 视觉节奏上下文 ---"
python "${SCRIPT_DIR}/generate_visual_context.py" \
  --project-dir . \
  --output visual_context.json
echo "[OK] visual_context.json 已生成"

echo "=== Stage 6 创意前准备完成 ==="
echo "产出: creative/style.css + creative/sNN.html / visual_context.json"
echo "下一步: LLM 逐场景填充 creative/sNN.html 的视觉创意内容"
