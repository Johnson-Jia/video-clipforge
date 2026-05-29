#!/usr/bin/env python3
"""
BGM 全程有声门禁 — 彻底杜绝 BGM 中段/后段静音

用法: python scripts/bgm_silence_check.py <bgm.wav> <narration_seconds>

检测逻辑:
  1. 将 bgm.wav 按 1 秒分块
  2. 计算每块 RMS 音量（dB）
  3. 在旁白时长覆盖范围内，如果出现连续 >= 3 秒静音（< -45 dB），FAIL
  4. 统计有效音频覆盖率，低于 80% 也 FAIL

退出码:
  0 = 通过
  1 = 不通过（并打印具体静音段位置）
"""

import sys
import wave
import struct
import math


def analyze_bgm(bgm_path, narration_sec, silence_db=-45, min_silent_blocks=3):
    with wave.open(bgm_path, "rb") as w:
        ch = w.getnchannels()
        sr = w.getframerate()
        sw = w.getsampwidth()
        n = w.getnframes()
        dur = n / sr
        raw = w.readframes(n)

    if sw != 2:
        print(f"ERROR: unsupported sample width {sw}")
        return [], [], 0.0, 0

    samples = struct.unpack("<" + "h" * (n * ch), raw)
    left = samples[0::ch]

    block_size = sr  # 1 second blocks
    check_range = min(int(narration_sec), int(dur))
    blocks = []

    for i in range(check_range):
        start = i * block_size
        end = min(start + block_size, len(left))
        block = left[start:end]
        if not block:
            break
        rms = math.sqrt(sum(s * s for s in block) / len(block))
        db = 20 * math.log10(rms / 32767) if rms > 0 else -96
        is_silent = db < silence_db
        blocks.append((i, db, is_silent))

    # Find continuous silent runs
    silent_runs = []
    run_start = None
    for sec, db, is_silent in blocks:
        if is_silent:
            if run_start is None:
                run_start = sec
        else:
            if run_start is not None:
                run_end = sec - 1
                run_len = run_end - run_start + 1
                if run_len >= min_silent_blocks:
                    silent_runs.append((run_start, run_end, run_len))
                run_start = None
    if run_start is not None:
        run_end = blocks[-1][0]
        run_len = run_end - run_start + 1
        if run_len >= min_silent_blocks:
            silent_runs.append((run_start, run_end, run_len))

    # Audio coverage
    active_blocks = sum(1 for _, _, s in blocks if not s)
    coverage = active_blocks / len(blocks) * 100 if blocks else 0

    return silent_runs, blocks, coverage, check_range


def main():
    if len(sys.argv) < 3:
        print("用法: python scripts/bgm_silence_check.py <bgm.wav> <narration_seconds>")
        sys.exit(1)

    bgm_path = sys.argv[1]
    narration_sec = float(sys.argv[2])

    silent_runs, blocks, coverage, check_range = analyze_bgm(bgm_path, narration_sec)

    print(f"=== BGM 全程有声门禁 ===")
    print(f"检测范围: 0~{check_range}s (旁白时长 {narration_sec:.1f}s)")

    # Print per-second levels (compact: only mark silent)
    for sec, db, is_silent in blocks:
        if is_silent:
            print(f"  {sec:3d}s  {db:7.1f} dB  <<< SILENT")

    if silent_runs:
        print(f"\nFAIL: 发现 {len(silent_runs)} 段连续静音（>= 3s）:")
        for start, end, length in silent_runs:
            print(f"  {start}s ~ {end}s ({length}s 连续静音)")
        print(f"音频覆盖率: {coverage:.0f}%")
        print(f"\n根因: BGM 文件在旁白时长范围内存在静音段。")
        print(f"修复: 更换 BGM 源文件，或确保 bgm_pipeline.sh 正确执行循环对齐。")
        sys.exit(1)

    if coverage < 80:
        print(f"\nFAIL: 音频覆盖率仅 {coverage:.0f}%（阈值 80%）")
        sys.exit(1)

    print(f"PASS: 全程 {check_range}s 覆盖率 {coverage:.0f}%，无连续静音段")
    sys.exit(0)


if __name__ == "__main__":
    main()
