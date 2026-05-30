#!/usr/bin/env python3
"""
Phase 时间校准引擎

从 Edge TTS 句子级时间戳 + narration_anchor 精确计算每个 phase 的切换时间。

用法: python scripts/phase_calibrator.py
  或: python scripts/phase_calibrator.py --project-dir <path>

输入:
  narration_segments.json  — visual_phases[].narration_anchor（句子索引）
  sentence_timestamps.json — 每段每句的精确时间（Edge TTS SRT 提取）
  segment_durations.json   — 每段实际时长（用于计算 global_start）

输出:
  phase_timings.json — 每个 scene 内每个 phase 的精确起止时间

工作目录必须在项目目录下。
"""
import json, sys, os


def load_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def compute_global_starts(segments_durations):
    """计算每段的 global_start（全片中的起始秒数）。"""
    global_start = 0.0
    result = []
    for seg in segments_durations:
        result.append(global_start)
        global_start += seg['actual_duration']
    return result


def calibrate_scene(scene_id, segment_index, visual_phases, sentences,
                    global_start, duration):
    """
    根据 narration_anchor + 句子时间戳，计算 phase 精确切换点。

    返回 phases 列表，每个 phase 含 start_offset, end_offset, sentences 范围。
    """
    if not visual_phases:
        return None

    num_phases = len(visual_phases)
    num_sentences = len(sentences)

    if num_sentences == 0:
        # 无句子信息时回退到等分
        phase_dur = duration / max(num_phases, 1)
        phases = []
        for i in range(num_phases):
            phases.append({
                'phase': i + 1,
                'start_offset': round(i * phase_dur, 3),
                'end_offset': round((i + 1) * phase_dur, 3),
                'sentences': [],
                'calibration': 'fallback-equal-split'
            })
        phases[-1]['end_offset'] = round(duration, 3)
        return phases

    phases = []
    for i, vp in enumerate(visual_phases):
        anchor = vp.get('narration_anchor')

        if anchor and 'start_sentence' in anchor:
            start_idx = anchor['start_sentence']
            end_idx = anchor.get('end_sentence', start_idx)

            # 边界校验：负索引或越界 → 降级
            valid = (isinstance(start_idx, int) and start_idx >= 0
                     and start_idx < num_sentences)
            if valid and isinstance(end_idx, int):
                valid = end_idx >= start_idx

            if valid:
                # 精确校准
                end_clamped = min(end_idx, num_sentences - 1)
                start_time = sentences[start_idx]['start']
                end_time = sentences[end_clamped]['end']
                sentence_range = list(range(start_idx, end_clamped + 1))
                calibration = 'sentence-anchor'
            else:
                # anchor 无效 → 回退 auto-split
                per_phase = num_sentences / num_phases
                start_idx = int(i * per_phase)
                end_idx = int((i + 1) * per_phase) - 1
                start_time = sentences[min(start_idx, num_sentences - 1)]['start']
                end_time = sentences[min(end_idx, num_sentences - 1)]['end'] if end_idx >= 0 else duration
                sentence_range = list(range(start_idx, min(end_idx + 1, num_sentences)))
                calibration = 'anchor-invalid'
        else:
            # 无锚点：按句子数等分（均匀分配句子给各 phase）
            per_phase = num_sentences / num_phases
            start_idx = int(i * per_phase)
            end_idx = int((i + 1) * per_phase) - 1
            start_time = sentences[start_idx]['start'] if start_idx < num_sentences else 0.0
            end_time = (sentences[min(end_idx, num_sentences - 1)]['end']
                        if end_idx >= 0 and end_idx < num_sentences else duration)
            sentence_range = list(range(start_idx, min(end_idx + 1, num_sentences)))
            calibration = 'auto-split'

        phases.append({
            'phase': i + 1,
            'start_offset': round(start_time, 3),
            'end_offset': round(end_time, 3),
            'sentences': sentence_range,
            'calibration': calibration
        })

    # 修正边界：确保无间隙、无重叠
    for i in range(len(phases)):
        if i == 0:
            phases[i]['start_offset'] = 0.0
        else:
            phases[i]['start_offset'] = phases[i - 1]['end_offset']

    # 最后一个 phase 到 segment 结束
    phases[-1]['end_offset'] = round(duration, 3)

    return phases


def main():
    project_dir = '.'
    if len(sys.argv) >= 3 and sys.argv[1] == '--project-dir':
        project_dir = sys.argv[2]

    segments_path = os.path.join(project_dir, 'narration_segments.json')
    timestamps_path = os.path.join(project_dir, 'sentence_timestamps.json')
    durations_path = os.path.join(project_dir, 'segment_durations.json')
    output_path = os.path.join(project_dir, 'phase_timings.json')

    # 检查必需文件
    for p in [segments_path, timestamps_path, durations_path]:
        if not os.path.exists(p):
            print(f'ERROR: {os.path.basename(p)} not found')
            sys.exit(1)

    narration = load_json(segments_path)
    timestamps = load_json(timestamps_path)
    durations = load_json(durations_path)

    nsegs = narration.get('segments', narration) if isinstance(narration, dict) else narration
    tsegs = timestamps.get('segments', timestamps) if isinstance(timestamps, dict) else timestamps
    dsegs = durations.get('segments', durations) if isinstance(durations, dict) else durations

    global_starts = compute_global_starts(dsegs)

    scenes = []
    anchor_count = 0
    auto_count = 0

    for i, seg in enumerate(nsegs):
        scene_id = seg.get('scene') or seg.get('id', f's{i+1}')
        visual_phases = seg.get('visual_phases', [])

        if not visual_phases:
            continue

        # 查找对应的句子时间戳
        ts_seg = None
        for ts in tsegs:
            if ts.get('segment_index') == i or ts.get('scene') == scene_id:
                ts_seg = ts
                break

        sentences = ts_seg['sentences'] if ts_seg else []
        duration = dsegs[i]['actual_duration'] if i < len(dsegs) else 0
        global_start = global_starts[i] if i < len(global_starts) else 0

        phases = calibrate_scene(
            scene_id, i, visual_phases, sentences,
            global_start, duration
        )

        if phases is None:
            continue

        # 统计校准方式
        for p in phases:
            if p['calibration'] == 'sentence-anchor':
                anchor_count += 1
            else:
                auto_count += 1

        scenes.append({
            'scene': scene_id,
            'segment_index': i,
            'global_start': round(global_start, 3),
            'duration': round(duration, 3),
            'phases': phases
        })

    # 输出
    meta = durations.get('meta', {})
    meta['calibration_source'] = 'edge-tts-srt'
    output = {
        'meta': meta,
        'stats': {
            'total_scenes': len(scenes),
            'total_phases': anchor_count + auto_count,
            'anchor_calibrated': anchor_count,
            'auto_split': auto_count
        },
        'scenes': scenes
    }

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f'Phase calibration complete:')
    print(f'  Scenes with phases: {len(scenes)}')
    print(f'  Total phases: {anchor_count + auto_count}')
    print(f'  Anchor-calibrated: {anchor_count}')
    print(f'  Auto-split: {auto_count}')
    print(f'  Output: {output_path}')


if __name__ == '__main__':
    main()
