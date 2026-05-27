#!/bin/bash
# check_injection_filter.sh - 注入过滤器一致性检查器
# 验证 inject_patterns.sh 的过滤逻辑与 store.yaml 的字段一致

set -euo pipefail

STORE=".claude/commands/clipforge/_patterns/store.yaml"
SCRIPT=".claude/commands/clipforge/scripts/inject_patterns.sh"

if [ ! -f "$STORE" ]; then
  echo "ERROR: Pattern Store not found: $STORE"
  exit 1
fi

if [ ! -f "$SCRIPT" ]; then
  echo "ERROR: inject_patterns.sh not found: $SCRIPT"
  exit 1
fi

echo "检查注入过滤器一致性..."
echo

# 检查 store.yaml 中的 type 字段
echo "1. 检查 type 字段使用情况："
python3 - "$STORE" << 'PYTHON_SCRIPT'
import yaml
import sys

with open(sys.argv[1], 'r', encoding='utf-8') as f:
  data = yaml.safe_load(f)

patterns = data.get('patterns', [])
types = {}
for p in patterns:
  t = p.get('type', 'UNKNOWN')
  types[t] = types.get(t, 0) + 1

for t, count in sorted(types.items()):
  print(f"  - {t}: {count} 个")
PYTHON_SCRIPT

echo

# 检查 inject_patterns.sh 的过滤条件
echo "2. 检查 inject_patterns.sh 过滤条件："
if grep -q "p.get('type') in ('SEED', 'VALIDATED')" "$SCRIPT"; then
  echo "  ✓ 过滤器正确使用 type: SEED | VALIDATED"
else
  echo "  ✗ 过滤器未正确检查 type 字段"
  echo "  期望: p.get('type') in ('SEED', 'VALIDATED')"
fi

echo

# 检查字段访问路径
echo "3. 检查字段访问路径："
if grep -q "as_preference.*text" "$SCRIPT"; then
  echo "  ✓ 正确访问 as_preference.text"
else
  echo "  ✗ 未正确访问 as_preference.text"
fi

if grep -q "as_preference.*weight" "$SCRIPT"; then
  echo "  ✓ 正确访问 as_preference.weight"
else
  echo "  ✗ 未正确访问 as_preference.weight"
fi

if grep -q "as_fewshot" "$SCRIPT"; then
  echo "  ✓ 正确访问 as_fewshot"
else
  echo "  ✗ 未正确访问 as_fewshot"
fi

echo
echo "✓ 检查完成"
