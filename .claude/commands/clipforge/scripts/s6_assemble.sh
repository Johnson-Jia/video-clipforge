#!/usr/bin/env bash
# s6_assemble.sh — Stage 6 创意后组装（全自动）
#
# 用法: bash scripts/s6_assemble.sh [--project-dir DIR]
# 无 --project-dir 时检查 CWD 是否为合法项目目录。
#
# 一次性完成: 碎片完整性验证 → HTML 结构校验 → 碎片组装 index.html → 导演门禁
# 替代原先 3 次独立 LLM 调用。
#
# 前置: creative/ 目录（LLM 已填充各 sNN.html 碎片）
# 输出: 验证通过的 index.html

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/_cd_project.sh" && cd_project "$@"

echo "=== Stage 6 创意后组装 ==="

# ── 前置检查 ──
if [ ! -d "creative" ]; then
  echo "FAIL: creative/ 目录不存在，请先运行 s6_prepare.sh"
  exit 1
fi

# ── Step 1: 碎片完整性验证 ──
echo "--- Step 1/4: 碎片完整性验证 ---"
python "${SCRIPT_DIR}/s6_assemble_html.py" --project-dir . --validate
echo "[OK] 所有创意碎片完整"

# ── Step 2: HTML 结构校验（标签平衡 + 三层容器）──
# 防止多余 </div> 导致 #sNN 容器提前闭合、phase 溢出、GSAP 切换静默失效
echo "--- Step 2/4: HTML 结构校验 ---"
python "${SCRIPT_DIR}/validate_html_structure.py" --project-dir .
echo "[OK] HTML 结构完整（标签平衡 + layer-content 存在）"

# ── Step 3: 碎片组装 index.html ──
echo "--- Step 3/4: 碎片组装 ---"
python "${SCRIPT_DIR}/s6_assemble_html.py" --project-dir .
echo "[OK] index.html 已生成"

# ── Step 4: 导演门禁（Layer 1 — HTML 设计意图验证）──
# 组装后即时校验：碎片刚拼成 index.html，立刻验证设计意图，趁早发现问题。
# 幂等防御性冗余：render 阶段（渲染前 fail-fast）、stage6_gate（独立入口自包含）也会各跑一次，见 clipforge.md §6。
echo "--- Step 4/4: 导演门禁 ---"
python "${SCRIPT_DIR}/director_gate.py" .
echo "[OK] 导演门禁通过"

echo "=== Stage 6 创意后组装完成 ==="
echo "产出: index.html（已通过全部门禁）"
echo "下一步: 运行 s6_render.sh 进行渲染"
