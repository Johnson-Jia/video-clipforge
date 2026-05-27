#!/bin/bash
# inject_patterns.sh - 经验模式注入器
# 根据 skill_scope 过滤 _patterns/store.yaml，输出匹配的模式文本
# 用法: inject_patterns.sh <skill_scope>
# 示例: inject_patterns.sh "clipforge.stage3-scenes"
# 输出: 匹配的模式文本（直接拼入 SubAgent prompt）

set -euo pipefail

STORE=".claude/commands/clipforge/_patterns/store.yaml"
SCOPE="${1:-}"

if [ -z "$SCOPE" ]; then
  echo "用法: inject_patterns.sh <skill_scope>"
  echo "示例: inject_patterns.sh 'clipforge.stage3-scenes'"
  exit 1
fi

if [ ! -f "$STORE" ]; then
  echo "# 无经验模式库"
  exit 0
fi

# 使用 Python 解析 YAML 并过滤匹配模式
python3 - "$STORE" "$SCOPE" << 'PYTHON_SCRIPT'
import yaml
import sys

store_path = sys.argv[1]
scope = sys.argv[2]

try:
  with open(store_path, 'r', encoding='utf-8') as f:
    data = yaml.safe_load(f)

  patterns = data.get('patterns', [])

  # 过滤 skill_scope 匹配的模式，且类型为 SEED 或 VALIDATED
  matched = [p for p in patterns
             if p.get('skill_scope') == scope
             and p.get('type') in ('SEED', 'VALIDATED')]

  if not matched:
    print("# 无匹配经验模式")
    sys.exit(0)

  # 按 weight 排序：HIGH > MEDIUM > LOW
  weight_order = {'HIGH': 0, 'MEDIUM': 1, 'LOW': 2}
  matched.sort(key=lambda p: weight_order.get(
    p.get('as_preference', {}).get('weight', 'LOW'), 2))

  # 输出格式化的模式文本
  print("## 成功经验（来自历史高分案例，供参考）\n")

  for p in matched:
    pattern_id = p.get('id', 'UNKNOWN')
    pref = p.get('as_preference', {})
    text = pref.get('text', '')
    weight = pref.get('weight', 'MEDIUM')

    print(f"- {text}（{weight}） ← `{pattern_id}`")

    # 如果有 few-shot 示例（仅 VALIDATED 模式）
    fewshot = p.get('as_fewshot')
    if fewshot and p.get('type') == 'VALIDATED':
      print(f"  示例：{fewshot.get('example_output', '')}")

  print(f"\n> 共 {len(matched)} 条匹配模式")

except Exception as e:
  print(f"# 错误: {e}", file=sys.stderr)
  sys.exit(1)
PYTHON_SCRIPT
