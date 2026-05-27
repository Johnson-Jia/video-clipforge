#!/usr/bin/env python3
"""
apply_delta.py - Delta Rule 应用器

读取 _deltas/*.yaml，按 operation 类型修改 _rules-lib/*.yaml。
支持 ADDED / MODIFIED / REMOVED / DEPRECATED 四种操作。

用法: apply_delta.py [--delta_dir=_deltas] [--rules_dir=_rules-lib] [--dry_run]
"""

import os
import sys
import yaml
import argparse
from pathlib import Path
from datetime import datetime

def load_deltas(delta_dir):
  """加载所有待应用的 Delta 文件"""
  deltas = []
  delta_path = Path(delta_dir)

  if not delta_path.exists():
    return deltas

  for delta_file in sorted(delta_path.glob('D-*.yaml')):
    try:
      with open(delta_file, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)

      if not data or 'delta' not in data:
        print(f"WARNING: invalid delta file: {delta_file}", file=sys.stderr)
        continue

      deltas.append({
        'file': delta_file,
        'data': data['delta']
      })

    except Exception as e:
      print(f"WARNING: failed to parse {delta_file}: {e}", file=sys.stderr)

  return deltas

def find_rule_file(rule_id, rules_dir):
  """根据规则 ID 找到对应的规则库文件"""
  rules_path = Path(rules_dir)

  # 根据规则 ID 前缀判断文件
  if rule_id.startswith('R-GLOBAL-'):
    return rules_path / 'global-rules.yaml'
  elif rule_id.startswith('R-RENDER-'):
    return rules_path / 'video-production-rules.yaml'
  elif rule_id.startswith('R-CLEANUP-'):
    return rules_path / 'cleanup-rules.yaml'
  else:
    # 未知前缀，遍历所有文件
    for yaml_file in rules_path.glob('*.yaml'):
      if yaml_file.name == 'README.md':
        continue
      try:
        with open(yaml_file, 'r', encoding='utf-8') as f:
          data = yaml.safe_load(f)
        if data and 'rules' in data:
          for rule in data['rules']:
            if rule.get('id') == rule_id:
              return yaml_file
      except:
        pass

  return None

def apply_added(delta, rules_dir, dry_run):
  """应用 ADDED 操作：添加新规则"""
  new_rule = delta.get('new_rule')
  if not new_rule:
    print(f"  ERROR: ADDED operation missing 'new_rule'", file=sys.stderr)
    return False

  rule_id = new_rule.get('id')
  if not rule_id:
    print(f"  ERROR: new_rule missing 'id'", file=sys.stderr)
    return False

  # 找到目标文件
  rule_file = find_rule_file(rule_id, rules_dir)
  if not rule_file:
    # 新规则，根据 scope 创建或选择文件
    scope = new_rule.get('scope', 'GLOBAL')
    if scope == 'GLOBAL':
      rule_file = Path(rules_dir) / 'global-rules.yaml'
    elif scope == 'SCENE':
      scene = new_rule.get('scene', 'video-production')
      if scene == 'video-production':
        rule_file = Path(rules_dir) / 'video-production-rules.yaml'
      else:
        rule_file = Path(rules_dir) / f'{scene}-rules.yaml'
    else:
      print(f"  WARNING: unknown scope '{scope}', skipping", file=sys.stderr)
      return False

  if dry_run:
    print(f"  [DRY RUN] Would add rule {rule_id} to {rule_file.name}")
    return True

  # 读取现有规则
  if rule_file.exists():
    with open(rule_file, 'r', encoding='utf-8') as f:
      data = yaml.safe_load(f) or {}
  else:
    data = {'rules': []}

  if 'rules' not in data:
    data['rules'] = []

  # 检查是否已存在
  for rule in data['rules']:
    if rule.get('id') == rule_id:
      print(f"  WARNING: rule {rule_id} already exists, skipping", file=sys.stderr)
      return False

  # 添加新规则
  data['rules'].append(new_rule)

  # 写入文件
  with open(rule_file, 'w', encoding='utf-8') as f:
    yaml.dump(data, f, allow_unicode=True, sort_keys=False)

  print(f"  ✓ Added rule {rule_id} to {rule_file.name}")
  return True

def apply_modified(delta, rules_dir, dry_run):
  """应用 MODIFIED 操作：修改现有规则"""
  target_rule = delta.get('target_rule')
  modified_fields = delta.get('modified_fields', {})

  if not target_rule:
    print(f"  ERROR: MODIFIED operation missing 'target_rule'", file=sys.stderr)
    return False

  if not modified_fields:
    print(f"  ERROR: MODIFIED operation missing 'modified_fields'", file=sys.stderr)
    return False

  # 找到规则文件
  rule_file = find_rule_file(target_rule, rules_dir)
  if not rule_file or not rule_file.exists():
    print(f"  ERROR: rule file not found for {target_rule}", file=sys.stderr)
    return False

  if dry_run:
    print(f"  [DRY RUN] Would modify rule {target_rule} in {rule_file.name}")
    return True

  # 读取规则
  with open(rule_file, 'r', encoding='utf-8') as f:
    data = yaml.safe_load(f)

  # 找到并修改规则
  found = False
  for rule in data.get('rules', []):
    if rule.get('id') == target_rule:
      for field, change in modified_fields.items():
        if isinstance(change, dict) and 'old' in change and 'new' in change:
          rule[field] = change['new']
        else:
          rule[field] = change
      found = True
      break

  if not found:
    print(f"  ERROR: rule {target_rule} not found in {rule_file.name}", file=sys.stderr)
    return False

  # 写入文件
  with open(rule_file, 'w', encoding='utf-8') as f:
    yaml.dump(data, f, allow_unicode=True, sort_keys=False)

  print(f"  ✓ Modified rule {target_rule} in {rule_file.name}")
  return True

def apply_removed(delta, rules_dir, dry_run):
  """应用 REMOVED 操作：删除规则"""
  target_rule = delta.get('target_rule')

  if not target_rule:
    print(f"  ERROR: REMOVED operation missing 'target_rule'", file=sys.stderr)
    return False

  # 找到规则文件
  rule_file = find_rule_file(target_rule, rules_dir)
  if not rule_file or not rule_file.exists():
    print(f"  ERROR: rule file not found for {target_rule}", file=sys.stderr)
    return False

  if dry_run:
    print(f"  [DRY RUN] Would remove rule {target_rule} from {rule_file.name}")
    return True

  # 读取规则
  with open(rule_file, 'r', encoding='utf-8') as f:
    data = yaml.safe_load(f)

  # 找到并删除规则
  original_count = len(data.get('rules', []))
  data['rules'] = [r for r in data.get('rules', []) if r.get('id') != target_rule]

  if len(data['rules']) == original_count:
    print(f"  ERROR: rule {target_rule} not found in {rule_file.name}", file=sys.stderr)
    return False

  # 写入文件
  with open(rule_file, 'w', encoding='utf-8') as f:
    yaml.dump(data, f, allow_unicode=True, sort_keys=False)

  print(f"  ✓ Removed rule {target_rule} from {rule_file.name}")
  return True

def apply_deprecated(delta, rules_dir, dry_run):
  """应用 DEPRECATED 操作：标记规则为废弃"""
  target_rule = delta.get('target_rule')

  if not target_rule:
    print(f"  ERROR: DEPRECATED operation missing 'target_rule'", file=sys.stderr)
    return False

  # 找到规则文件
  rule_file = find_rule_file(target_rule, rules_dir)
  if not rule_file or not rule_file.exists():
    print(f"  ERROR: rule file not found for {target_rule}", file=sys.stderr)
    return False

  if dry_run:
    print(f"  [DRY RUN] Would deprecate rule {target_rule} in {rule_file.name}")
    return True

  # 读取规则
  with open(rule_file, 'r', encoding='utf-8') as f:
    data = yaml.safe_load(f)

  # 找到并标记废弃
  found = False
  for rule in data.get('rules', []):
    if rule.get('id') == target_rule:
      rule['deprecated'] = True
      rule['deprecated_at'] = datetime.now().isoformat()
      if 'superseded_by' in delta:
        rule['superseded_by'] = delta['superseded_by']
      if 'reason' in delta:
        rule['deprecation_reason'] = delta['reason']
      found = True
      break

  if not found:
    print(f"  ERROR: rule {target_rule} not found in {rule_file.name}", file=sys.stderr)
    return False

  # 写入文件
  with open(rule_file, 'w', encoding='utf-8') as f:
    yaml.dump(data, f, allow_unicode=True, sort_keys=False)

  print(f"  ✓ Deprecated rule {target_rule} in {rule_file.name}")
  return True

def main():
  parser = argparse.ArgumentParser(description='应用 Delta Rule 到规则库')
  parser.add_argument('--delta_dir', default='.claude/commands/clipforge/_deltas',
                      help='Delta 文件目录')
  parser.add_argument('--rules_dir', default='.claude/commands/clipforge/_rules-lib',
                      help='规则库目录')
  parser.add_argument('--dry_run', action='store_true',
                      help='仅模拟，不实际修改')

  args = parser.parse_args()

  print(f"Delta 目录: {args.delta_dir}")
  print(f"规则库目录: {args.rules_dir}")
  if args.dry_run:
    print("[DRY RUN MODE]")
  print()

  # 加载所有 Delta
  deltas = load_deltas(args.delta_dir)

  if not deltas:
    print("无待应用的 Delta")
    sys.exit(0)

  print(f"找到 {len(deltas)} 个待应用的 Delta")
  print()

  # 应用每个 Delta
  applied = 0
  failed = 0

  for delta_info in deltas:
    delta_file = delta_info['file']
    delta = delta_info['data']

    operation = delta.get('operation')
    delta_id = delta_file.stem

    print(f"处理 {delta_id}: operation={operation}")

    try:
      if operation == 'ADDED':
        success = apply_added(delta, args.rules_dir, args.dry_run)
      elif operation == 'MODIFIED':
        success = apply_modified(delta, args.rules_dir, args.dry_run)
      elif operation == 'REMOVED':
        success = apply_removed(delta, args.rules_dir, args.dry_run)
      elif operation == 'DEPRECATED':
        success = apply_deprecated(delta, args.rules_dir, args.dry_run)
      else:
        print(f"  ERROR: unknown operation '{operation}'", file=sys.stderr)
        success = False

      if success:
        applied += 1
      else:
        failed += 1

    except Exception as e:
      print(f"  ERROR: {e}", file=sys.stderr)
      failed += 1

    print()

  # 输出统计
  print(f"应用完成: {applied} 成功, {failed} 失败")

  if failed > 0:
    sys.exit(1)

if __name__ == '__main__':
  main()
