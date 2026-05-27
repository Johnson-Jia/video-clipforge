#!/usr/bin/env python3
"""
upgrade_patterns.py - SEED→VALIDATED 升级检查器

检查 _patterns/store.yaml 中的 SEED 模式，
如果 source_traces ≥ 3，升级为 VALIDATED 并重新计算 confidence。

用法: upgrade_patterns.py [--store=_patterns/store.yaml] [--min_traces=3]
"""

import yaml
import argparse
from pathlib import Path
from datetime import datetime


def calculate_confidence(sample_size, base_confidence=0.5):
  """
  根据样本量计算置信度
  - 3 个案例: 0.75
  - 5 个案例: 0.85
  - 10+ 案例: 0.95
  """
  if sample_size >= 10:
    return 0.95
  elif sample_size >= 5:
    return 0.85
  elif sample_size >= 3:
    return 0.75
  else:
    return base_confidence


def main():
  parser = argparse.ArgumentParser(description='升级 SEED 模式为 VALIDATED')
  parser.add_argument('--store', default='.claude/commands/clipforge/_patterns/store.yaml',
                      help='Pattern Store 路径')
  parser.add_argument('--min_traces', type=int, default=3,
                      help='最少需要多少个 source_traces 才能升级')
  parser.add_argument('--dry_run', action='store_true',
                      help='仅模拟，不实际修改')

  args = parser.parse_args()

  store_path = Path(args.store)
  if not store_path.exists():
    print(f"ERROR: Pattern Store not found: {args.store}")
    return

  with open(store_path, 'r', encoding='utf-8') as f:
    data = yaml.safe_load(f)

  patterns = data.get('patterns', [])
  upgraded = 0

  for p in patterns:
    if p.get('type') != 'SEED':
      continue

    source_traces = p.get('source_traces', [])
    if len(source_traces) < args.min_traces:
      continue

    # 满足升级条件
    pattern_id = p.get('id', 'UNKNOWN')
    old_confidence = p.get('evidence', {}).get('confidence', 0.5)
    new_confidence = calculate_confidence(len(source_traces))

    print(f"升级 {pattern_id}:")
    print(f"  source_traces: {len(source_traces)} 个")
    print(f"  confidence: {old_confidence:.2f} → {new_confidence:.2f}")
    print(f"  type: SEED → VALIDATED")
    print()

    if not args.dry_run:
      p['type'] = 'VALIDATED'
      p['requires_validation'] = False
      if 'evidence' not in p:
        p['evidence'] = {}
      p['evidence']['confidence'] = new_confidence
      p['evidence']['sample_size'] = len(source_traces)
      p['evidence']['upgraded_at'] = datetime.now().isoformat()
      upgraded += 1

  if upgraded > 0 and not args.dry_run:
    with open(store_path, 'w', encoding='utf-8') as f:
      yaml.dump(data, f, allow_unicode=True, sort_keys=False)
    print(f"✓ 已升级 {upgraded} 个模式")
  elif args.dry_run:
    print(f"[DRY RUN] 将升级 {upgraded} 个模式")
  else:
    print("无满足升级条件的模式")


if __name__ == '__main__':
  main()
