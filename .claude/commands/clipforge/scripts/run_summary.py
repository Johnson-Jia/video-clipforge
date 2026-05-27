#!/usr/bin/env python3
"""
run_summary.py - 运行汇总生成器

读取 {project_dir}/trace/ 下所有 stage traces，
生成 run-summary.yaml（含整体状态、各阶段耗时、闭环反馈）。

用法: run_summary.py <project_dir>
"""

import os
import sys
import yaml
import argparse
from pathlib import Path
from datetime import datetime

def load_stage_traces(trace_dir):
  """加载所有 stage trace 文件"""
  traces = []
  trace_path = Path(trace_dir)

  if not trace_path.exists():
    return traces

  # 读取所有 stage trace 文件
  for trace_file in sorted(trace_path.glob('stage*.yaml')):
    try:
      with open(trace_file, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)

      if not data or 'trace' not in data:
        print(f"WARNING: invalid trace file: {trace_file}", file=sys.stderr)
        continue

      traces.append({
        'file': trace_file.name,
        'data': data['trace']
      })

    except Exception as e:
      print(f"WARNING: failed to parse {trace_file}: {e}", file=sys.stderr)

  return traces

def extract_project_info(project_dir):
  """从项目目录路径提取项目信息"""
  project_path = Path(project_dir)

  # 尝试从路径提取日期和项目名
  # 格式: workspace/YYYY/MM/DD/project-name
  parts = project_path.parts
  if len(parts) >= 5 and parts[-4].isdigit() and parts[-3].isdigit() and parts[-2].isdigit():
    year = parts[-4]
    month = parts[-3]
    day = parts[-2]
    project_name = parts[-1]
    return {
      'year': year,
      'month': month,
      'day': day,
      'project_name': project_name,
    }

  return {
    'project_name': project_path.name,
  }

def generate_summary(traces, project_dir):
  """生成运行汇总"""
  project_info = extract_project_info(project_dir)

  # 提取各阶段信息
  stages = []
  total_duration = 0
  overall_status = 'SUCCESS'

  for trace_info in traces:
    trace = trace_info['data']

    skill_id = trace.get('skill_id', 'unknown')
    status = trace.get('status', 'UNKNOWN')
    timestamp = trace.get('timestamp')

    # 提取阶段编号
    stage_match = skill_id.split('.')[-1] if '.' in skill_id else skill_id

    # 计算耗时（如果有 start/end 时间戳）
    duration_minutes = trace.get('duration_minutes', 0)
    total_duration += duration_minutes

    # 提取门禁报告
    gate_report = trace.get('gate_reports', {})
    process_passed = gate_report.get('process_passed', False)
    compliance_passed = gate_report.get('compliance_passed', False)
    quality_score = gate_report.get('quality_score')

    # 更新整体状态
    if status == 'FAILED':
      overall_status = 'FAILED'
    elif status == 'PASSED_WITH_CONCERNS' and overall_status != 'FAILED':
      overall_status = 'PARTIAL'

    stage_info = {
      'stage': stage_match,
      'status': status,
      'duration_minutes': duration_minutes,
      'trace_file': trace_info['file'],
      'process_passed': process_passed,
      'compliance_passed': compliance_passed,
    }

    if quality_score is not None:
      stage_info['quality_score'] = quality_score

    stages.append(stage_info)

  # 构建汇总
  summary = {
    'run': {
      'project': project_info.get('project_name'),
      'project_dir': str(project_dir),
      'generated_at': datetime.now().isoformat(),
      'overall_status': overall_status,
      'total_duration_minutes': total_duration,
      'stages': stages,
    }
  }

  # 添加日期信息（如果有）
  if 'year' in project_info:
    summary['run']['date'] = f"{project_info['year']}-{project_info['month']}-{project_info['day']}"

  # 检查是否有闭环反馈
  feedback = {
    'negative_loop': None,
    'positive_loop': None,
  }

  # 检查是否有归因（负向闭环）
  for trace_info in traces:
    trace = trace_info['data']
    if trace.get('attribution'):
      feedback['negative_loop'] = 'triggered'
      break

  # 检查是否有成功分析（正向闭环）
  for trace_info in traces:
    trace = trace_info['data']
    gate_report = trace.get('gate_reports', {})
    quality_score = gate_report.get('quality_score')
    if quality_score is not None and quality_score >= 0.85:
      feedback['positive_loop'] = 'triggered'
      break

  summary['run']['feedback'] = feedback

  return summary

def main():
  parser = argparse.ArgumentParser(description='生成运行汇总')
  parser.add_argument('project_dir', help='项目目录路径')

  args = parser.parse_args()

  project_path = Path(args.project_dir)
  if not project_path.exists():
    print(f"ERROR: project directory not found: {args.project_dir}", file=sys.stderr)
    sys.exit(1)

  trace_dir = project_path / 'trace'
  if not trace_dir.exists():
    print(f"ERROR: trace directory not found: {trace_dir}", file=sys.stderr)
    sys.exit(1)

  print(f"项目目录: {args.project_dir}")
  print(f"Trace 目录: {trace_dir}")
  print()

  # 加载所有 stage traces
  traces = load_stage_traces(trace_dir)

  if not traces:
    print("未找到 stage trace 文件")
    sys.exit(1)

  print(f"找到 {len(traces)} 个 stage trace")
  print()

  # 生成汇总
  summary = generate_summary(traces, args.project_dir)

  # 写入 run-summary.yaml
  summary_file = trace_dir / 'run-summary.yaml'
  with open(summary_file, 'w', encoding='utf-8') as f:
    yaml.dump(summary, f, allow_unicode=True, sort_keys=False)

  print(f"汇总已生成: {summary_file}")
  print()

  # 输出关键信息
  run = summary['run']
  print(f"整体状态: {run['overall_status']}")
  print(f"总耗时: {run['total_duration_minutes']} 分钟")
  print(f"阶段数: {len(run['stages'])}")
  print()

  # 输出各阶段状态
  print("各阶段状态:")
  for stage in run['stages']:
    status_icon = '✓' if stage['status'] == 'PASSED' else '✗'
    score_str = f" (quality: {stage.get('quality_score', 'N/A')})" if 'quality_score' in stage else ''
    print(f"  {status_icon} {stage['stage']}: {stage['status']}{score_str}")

  print()

  # 输出闭环反馈
  feedback = run['feedback']
  print("闭环反馈:")
  print(f"  负向闭环: {feedback['negative_loop'] or '未触发'}")
  print(f"  正向闭环: {feedback['positive_loop'] or '未触发'}")

if __name__ == '__main__':
  main()
