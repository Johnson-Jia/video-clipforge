#!/usr/bin/env python3
"""
calc_soft_score.py - 质量门禁评分计算器

根据内置评分函数计算质量门禁分数（供参考，最终评价由 evaluator: HUMAN 决定）。

用法: calc_soft_score.py <gate_name> [--param=value ...]
示例: calc_soft_score.py pacing_quality \
    --hook_duration=4 --focus_scenes_avg=7 --long_scenes_without_phases=0 \
    --word_count=310 --phase_compliance=1.0

输出: score: 0.85
"""

import sys
import argparse

def calc_pacing_quality(args):
  """
  节奏质量评分 (stage3-scenes.md)
  评分函数: hook≤5s(+0.2) + 重点场景6-8s(+0.2) + 无场景>15s且无visual_phases(+0.2)
            + 总字数在目标范围内(+0.2) + phase数量满足切换频率(+0.2)
  """
  score = 0.0

  # hook≤5s (+0.2)
  if args.hook_duration <= 5:
    score += 0.2

  # 重点场景6-8s (+0.2)
  if 6 <= args.focus_scenes_avg <= 8:
    score += 0.2

  # 无场景>15s且无visual_phases (+0.2)
  if args.long_scenes_without_phases == 0:
    score += 0.2

  # 总字数在目标范围内 (+0.2)
  # 标准模式: 250-380字, 深度解析: 300-450字
  if 250 <= args.word_count <= 450:
    score += 0.2

  # phase数量满足切换频率 (+0.2)
  if args.phase_compliance >= 1.0:
    score += 0.2
  elif args.phase_compliance >= 0.8:
    score += 0.1

  return score

def calc_humor_distribution(args):
  """
  幽默分布评分 (stage3-scenes.md)
  评分函数: grab/climax/summon无humor(+0.4) + build/reveal/settle有humor(+0.3)
            + humor密度≤每3-4段1次(+0.3)
  """
  score = 0.0

  # grab/climax/summon无humor (+0.4)
  if args.serious_beats_clean:
    score += 0.4

  # build/reveal/settle有humor (+0.3)
  if args.relaxed_beats_have_humor:
    score += 0.3

  # humor密度≤每3-4段1次 (+0.3)
  if 0.25 <= args.humor_density <= 0.33:
    score += 0.3
  elif args.humor_density < 0.25:
    score += 0.15

  return score

def calc_style_content_match(args):
  """
  风格内容匹配度 (stage2-analysis.md)
  评分函数: 情绪一致(+0.4) + 色彩方向合理(+0.3) + 反模式清单无违规(+0.3)
  """
  score = 0.0

  if args.emotion_match:
    score += 0.4
  if args.color_direction_valid:
    score += 0.3
  if args.no_anti_patterns:
    score += 0.3

  return score

def calc_audio_quality(args):
  """
  音频质量评分 (stage4-audio.md)
  评分函数: loudnorm余量(>-5dB得满分)(+0.3) + BGM音量写入(+0.2)
            + 无淡入(+0.2) + segment_durations完整(+0.3)
  """
  score = 0.0

  # loudnorm余量 (>-5dB得满分) (+0.3)
  if args.max_volume >= -5:
    score += 0.3
  elif args.max_volume >= -10:
    score += 0.15

  # BGM音量写入 (+0.2)
  if args.bgm_volume_written:
    score += 0.2

  # 无淡入 (+0.2)
  if args.no_fade_in:
    score += 0.2

  # segment_durations完整 (+0.3)
  if args.segment_durations_complete:
    score += 0.3

  return score

def calc_visual_quality(args):
  """
  视觉质量评分 (stage6-production.md)
  评分函数: 三层架构完整(+0.2) + layer-fx非空(+0.15) + hook视觉最强(≥100px标题)(+0.15)
            + Phase断点对齐(+0.15) + 相邻场景视觉差异(+0.15) + 安全区padding正确(+0.2)
  """
  score = 0.0

  if args.three_layers_complete:
    score += 0.2
  if args.layer_fx_nonempty:
    score += 0.15
  if args.hook_title_px >= 100:
    score += 0.15
  if args.phase_breakpoints_aligned:
    score += 0.15
  if args.adjacent_scenes_different:
    score += 0.15
  if args.safe_padding_correct:
    score += 0.2

  return score

def calc_cover_quality(args):
  """
  封面质量评分 (stage7-delivery.md)
  评分函数: 7层完整(+0.3) + 中文日期(+0.1) + 主标题≥80px(+0.15)
            + 双色光晕(+0.15) + 无URL(+0.15) + 背景三层(+0.15)
  """
  score = 0.0

  if args.seven_layers_complete:
    score += 0.3
  if args.chinese_date:
    score += 0.1
  if args.main_title_px >= 80:
    score += 0.15
  if args.dual_glow:
    score += 0.15
  if args.no_url:
    score += 0.15
  if args.bg_three_layers:
    score += 0.15

  return score

def calc_copy_compliance(args):
  """
  文案合规评分 (stage7-delivery.md)
  评分函数: 无广告敏感词(+0.3) + 无URL(+0.2) + 标签≥5个(+0.2)
            + 无诱导互动(+0.15) + 无具体时间(+0.15)
  """
  score = 0.0

  if args.no_sensitive_words:
    score += 0.3
  if args.no_url:
    score += 0.2
  if args.hashtags_count >= 5:
    score += 0.2
  if args.no_engagement_bait:
    score += 0.15
  if args.no_specific_time:
    score += 0.15

  return score

def calc_external_metrics(args):
  """
  外部播放指标评分 (发布后回填)
  评分函数: 播放量超平均(+0.4) + 完播率(>40%)(+0.3) + 互动率(>5%)(+0.3)
  """
  score = 0.0

  # 播放量超同期平均倍数 (+0.4)
  if args.play_ratio >= 2.0:
    score += 0.4
  elif args.play_ratio >= 1.5:
    score += 0.2

  # 完播率 (+0.3)
  if args.completion_rate >= 0.40:
    score += 0.3
  elif args.completion_rate >= 0.30:
    score += 0.15

  # 互动率 (+0.3)
  if args.engagement_rate >= 0.05:
    score += 0.3
  elif args.engagement_rate >= 0.03:
    score += 0.15

  return score

def main():
  parser = argparse.ArgumentParser(description='计算软门禁评分')
  parser.add_argument('gate_name', help='门禁名称')

  # 通用参数
  parser.add_argument('--hook_duration', type=float, default=0)
  parser.add_argument('--focus_scenes_avg', type=float, default=0)
  parser.add_argument('--long_scenes_without_phases', type=int, default=0)
  parser.add_argument('--word_count', type=int, default=0)
  parser.add_argument('--phase_compliance', type=float, default=0)

  parser.add_argument('--serious_beats_clean', action='store_true')
  parser.add_argument('--relaxed_beats_have_humor', action='store_true')
  parser.add_argument('--humor_density', type=float, default=0)

  parser.add_argument('--emotion_match', action='store_true')
  parser.add_argument('--color_direction_valid', action='store_true')
  parser.add_argument('--no_anti_patterns', action='store_true')

  parser.add_argument('--max_volume', type=float, default=-20)
  parser.add_argument('--bgm_volume_written', action='store_true')
  parser.add_argument('--no_fade_in', action='store_true')
  parser.add_argument('--segment_durations_complete', action='store_true')

  parser.add_argument('--three_layers_complete', action='store_true')
  parser.add_argument('--layer_fx_nonempty', action='store_true')
  parser.add_argument('--hook_title_px', type=int, default=0)
  parser.add_argument('--phase_breakpoints_aligned', action='store_true')
  parser.add_argument('--adjacent_scenes_different', action='store_true')
  parser.add_argument('--safe_padding_correct', action='store_true')

  parser.add_argument('--seven_layers_complete', action='store_true')
  parser.add_argument('--chinese_date', action='store_true')
  parser.add_argument('--main_title_px', type=int, default=0)
  parser.add_argument('--dual_glow', action='store_true')
  parser.add_argument('--no_url', action='store_true')
  parser.add_argument('--bg_three_layers', action='store_true')

  parser.add_argument('--no_sensitive_words', action='store_true')
  parser.add_argument('--hashtags_count', type=int, default=0)
  parser.add_argument('--no_engagement_bait', action='store_true')
  parser.add_argument('--no_specific_time', action='store_true')

  parser.add_argument('--play_ratio', type=float, default=0)
  parser.add_argument('--completion_rate', type=float, default=0)
  parser.add_argument('--engagement_rate', type=float, default=0)

  args = parser.parse_args()

  # 路由到对应的评分函数
  gate_functions = {
    'pacing_quality': calc_pacing_quality,
    'humor_distribution': calc_humor_distribution,
    'style_content_match': calc_style_content_match,
    'audio_quality': calc_audio_quality,
    'visual_quality': calc_visual_quality,
    'cover_quality': calc_cover_quality,
    'copy_compliance': calc_copy_compliance,
    'external_metrics': calc_external_metrics,
  }

  if args.gate_name not in gate_functions:
    print(f"ERROR: unknown gate '{args.gate_name}'", file=sys.stderr)
    print(f"Valid gates: {', '.join(gate_functions.keys())}", file=sys.stderr)
    sys.exit(1)

  score = gate_functions[args.gate_name](args)
  print(f"score: {score:.2f}")

if __name__ == '__main__':
  main()
