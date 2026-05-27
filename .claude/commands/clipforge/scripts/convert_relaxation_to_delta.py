#!/usr/bin/env python3
"""
convert_relaxation_to_delta.py - 放宽提案转 Delta Rule 转换器

读取 _patterns/store.yaml 中的 as_constraint_relaxation 字段，
转换为 Delta Rule 格式并写入 _deltas/ 目录。

用法: convert_relaxation_to_delta.py [--store=_patterns/store.yaml]
                                      [--deltas_dir=_deltas]
"""

import yaml
import argparse
from pathlib import Path
from datetime import datetime


def main():
  parser = argparse.ArgumentParser(description='转换放宽提案为 Delta Rule')
  parser.add_argument('--store', default='.claude/commands/clipforge/_patterns/store.yaml',
                      help='Pattern Store 路径')
  parser.add_argument('--deltas_dir', default='.claude/commands/clipforge/_deltas',
                      help='Delta 输出目录')
  parser.add_argument('--dry_run', action='store_true',
                      help='仅模拟，不实际写入')

  args = parser.parse_args()

  store_path = Path(args.store)
  deltas_path = Path(args.deltas_dir)

  if not store_path.exists():
    print(f"ERROR: Pattern Store not found: {args.store}")
    return

  with open(store_path, 'r', encoding='utf-8') as f:
    data = yaml.safe_load(f)

  patterns = data.get('patterns', [])
  converted = 0

  for p in patterns:
    relaxation = p.get('as_constraint_relaxation')
    if not relaxation:
      continue

    # 必须是 VALIDATED 模式才能生成放宽提案
    if p.get('type') != 'VALIDATED':
      print(f"跳过 {p.get('id')}: 仅 VALIDATED 模式可生成放宽提案")
      continue

    pattern_id = p.get('id', 'UNKNOWN')
    target_rule = relaxation.get('target_rule')
    evidence = relaxation.get('evidence', {})
    proposal = relaxation.get('proposal', 'DOWNGRADE_HARD_TO_SOFT')

    if not target_rule:
      print(f"跳过 {pattern_id}: 缺少 target_rule")
      continue

    # 生成 Delta Rule
    timestamp = datetime.now().strftime('%Y%m%dT%H%M%S')
    delta_id = f"D-{timestamp}-{converted:03d}"

    delta = {
      'delta': {
        'id': delta_id,
        'operation': 'MODIFIED',
        'target_rule': target_rule,
        'source': f"pattern:{pattern_id}",
        'confidence': evidence.get('confidence', 0.7),
        'approved_by': None,  # 需要人工审批
        'modified_fields': {
          'severity': {
            'old': 'HARD',
            'new': 'SOFT' if proposal == 'DOWNGRADE_HARD_TO_SOFT' else 'HARD'
          }
        },
        'evidence': evidence,
        'proposal': proposal,
        'requires_human_review': True
      }
    }

    print(f"生成 Delta {delta_id}:")
    print(f"  pattern: {pattern_id}")
    print(f"  target_rule: {target_rule}")
    print(f"  proposal: {proposal}")
    print()

    if not args.dry_run:
      deltas_path.mkdir(exist_ok=True)
      delta_file = deltas_path / f"{delta_id}.yaml"
      with open(delta_file, 'w', encoding='utf-8') as f:
        yaml.dump(delta, f, allow_unicode=True, sort_keys=False)
      print(f"  ✓ 已写入: {delta_file}")

    converted += 1

  if converted > 0 and not args.dry_run:
    print(f"\n✓ 已转换 {converted} 个放宽提案")
  elif args.dry_run:
    print(f"\n[DRY RUN] 将转换 {converted} 个放宽提案")
  else:
    print("\n无放宽提案需要转换")


if __name__ == '__main__':
  main()
