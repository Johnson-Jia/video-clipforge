#!/usr/bin/env python3
"""
aggregate_traces.py - Trace 聚合器

扫描 workspace/ 下所有项目的 trace/ 目录，
汇总高分成功案例（quality_score >= 0.85 或 process_passed + compliance_passed），
输出到 _success-traces/ 全局目录。

用法: aggregate_traces.py [--min_score=0.85] [--process_only] [--output_dir=_success-traces]
"""

import os
import sys
import yaml
import shutil
import argparse
from pathlib import Path
from datetime import datetime

def scan_project_traces(workspace_dir, min_score=0.85, process_only=False):
  """
  扫描 workspace/ 下所有项目的 trace 文件
  返回高分成功的 trace 信息列表
  """
  success_traces = []

  # 遍历 workspace/YYYY/MM/DD/*/trace/
  workspace_path = Path(workspace_dir)
  if not workspace_path.exists():
    print(f"ERROR: workspace directory not found: {workspace_dir}", file=sys.stderr)
    return success_traces

  # 查找所有 trace 目录
  trace_dirs = list(workspace_path.glob('**/trace'))

  for trace_dir in trace_dirs:
    # 读取该 trace 目录下所有 stage trace 文件
    for trace_file in trace_dir.glob('stage*.yaml'):
      try:
        with open(trace_file, 'r', encoding='utf-8') as f:
          data = yaml.safe_load(f)

        if not data or 'trace' not in data:
          continue

        trace = data['trace']

        # 检查是否为成功案例
        gate_report = trace.get('gate_report', {})

        if process_only:
          # 流程完整性模式：process_passed AND compliance_passed
          process_passed = gate_report.get('process_passed', False)
          compliance_passed = gate_report.get('compliance_passed', False)

          if process_passed and compliance_passed:
            project_dir = trace_dir.parent
            project_info = {
              'trace_file': str(trace_file),
              'project_dir': str(project_dir),
              'skill_id': trace.get('skill_id'),
              'timestamp': trace.get('timestamp'),
              'quality_score': gate_report.get('quality_score'),
              'status': trace.get('status'),
              'trigger_type': 'process_complete',
            }
            success_traces.append(project_info)
        else:
          # 质量评分模式：quality_score >= min_score
          quality_score = gate_report.get('quality_score')

          if quality_score is not None and quality_score >= min_score:
            project_dir = trace_dir.parent
            project_info = {
              'trace_file': str(trace_file),
              'project_dir': str(project_dir),
              'skill_id': trace.get('skill_id'),
              'timestamp': trace.get('timestamp'),
              'quality_score': quality_score,
              'quality_evaluator': gate_report.get('quality_evaluator'),
              'status': trace.get('status'),
              'trigger_type': 'quality_score',
            }
            success_traces.append(project_info)

      except Exception as e:
        print(f"WARNING: failed to parse {trace_file}: {e}", file=sys.stderr)

  return success_traces

def copy_to_global(success_traces, output_dir):
  """
  将高分成功 trace 复制到全局 _success-traces/ 目录
  """
  output_path = Path(output_dir)
  output_path.mkdir(exist_ok=True)

  copied = 0
  for info in success_traces:
    src_file = Path(info['trace_file'])
    if not src_file.exists():
      continue

    # 生成目标文件名：skill_id-timestamp.yaml
    skill_id = info['skill_id'] or 'unknown'
    timestamp = info['timestamp'] or datetime.now().strftime('%Y%m%dT%H%M%SZ')
    dst_file = output_path / f"{skill_id}-{timestamp}.yaml"

    try:
      shutil.copy2(src_file, dst_file)
      copied += 1
    except Exception as e:
      print(f"WARNING: failed to copy {src_file} to {dst_file}: {e}", file=sys.stderr)

  return copied

def generate_report(success_traces, output_dir):
  """
  生成聚合报告
  """
  report_path = Path(output_dir) / 'aggregation-report.yaml'

  # 按 skill_id 分组统计
  by_skill = {}
  for info in success_traces:
    skill_id = info['skill_id'] or 'unknown'
    if skill_id not in by_skill:
      by_skill[skill_id] = []
    by_skill[skill_id].append(info)

  report = {
    'aggregated_at': datetime.now().isoformat(),
    'total_success_traces': len(success_traces),
    'by_skill': {}
  }

  for skill_id, traces in by_skill.items():
    scores = [t.get('quality_score') or 0 for t in traces]
    report['by_skill'][skill_id] = {
      'count': len(traces),
      'avg_score': sum(scores) / len(scores) if scores else 0,
      'min_score': min(scores) if scores else 0,
      'max_score': max(scores) if scores else 0,
    }

  with open(report_path, 'w', encoding='utf-8') as f:
    yaml.dump(report, f, allow_unicode=True, sort_keys=False)

  return report_path

def main():
  parser = argparse.ArgumentParser(description='聚合高分成功 Trace')
  parser.add_argument('--workspace', default='workspace', help='workspace 目录路径')
  parser.add_argument('--min_score', type=float, default=0.85, help='最小 quality_score 阈值')
  parser.add_argument('--process_only', action='store_true',
                      help='仅聚合流程完整案例（process_passed + compliance_passed）')
  parser.add_argument('--output_dir', default='.claude/commands/clipforge/_success-traces',
                      help='输出目录')

  args = parser.parse_args()

  print(f"扫描 workspace: {args.workspace}")
  if args.process_only:
    print("模式: 流程完整案例聚合")
  else:
    print(f"模式: 质量评分聚合（阈值: {args.min_score}）")
  print()

  # 扫描成功 trace
  success_traces = scan_project_traces(args.workspace, args.min_score, args.process_only)

  if not success_traces:
    print("未找到符合条件的 trace")
    sys.exit(0)

  print(f"找到 {len(success_traces)} 条符合条件的 trace")
  print()

  # 复制到全局目录
  copied = copy_to_global(success_traces, args.output_dir)
  print(f"已复制 {copied} 条 trace 到 {args.output_dir}")
  print()

  # 生成报告
  report_path = generate_report(success_traces, args.output_dir)
  print(f"聚合报告已生成: {report_path}")
  print()

  # 输出统计
  by_skill = {}
  for info in success_traces:
    skill_id = info['skill_id'] or 'unknown'
    if skill_id not in by_skill:
      by_skill[skill_id] = 0
    by_skill[skill_id] += 1

  print("按 Skill 统计:")
  for skill_id, count in sorted(by_skill.items()):
    print(f"  {skill_id}: {count} 条")

if __name__ == '__main__':
  main()
