#!/usr/bin/env python3
"""
BGM 音量校准：均值公式 + 峰值安全上限

用法: python scripts/bgm_gap_check.py <BGM_MEAN_dB> <BGM_MAX_dB> <NARR_MAX_dB>

输入:
  BGM_MEAN: bgm.wav 的 mean_volume (dB)
  BGM_MAX:  bgm.wav 的 max_volume (dB)
  NARR_MAX: narration.mp3 的 max_volume (dB)

输出:
  打印计算过程和 FINAL_VOL
  将 FINAL_VOL 写入 segment_durations.json 的 meta.bgm_volume
  退出码: 0=OK, 1=需要调整（已自动修正并写入）

原理:
  1. 均值层：volume = 10^((narr_mean - target_gap - bgm_mean) / 20)
     旁白均值固定（loudnorm I=-16 后 ≈ -17 dB），BGM 均值实测，
     target_gap 控制BGM比旁白低多少 dB。
  2. 峰值层：如果 BGM 有效峰值距旁白峰值不足安全值，降低 volume 上限。

前提: narration.mp3 已经过 loudnorm I=-16 标准化（均值约 -17 dB，峰值约 -1.5 dB）。
"""
import json
import math
import os
import sys


# ── 旁白基准 ──
NARR_MEAN_REF = -17.0  # loudnorm I=-16 标准化后的稳定均值

# ── 均值层参数 ──
MEAN_GAP_TARGET = 12.0  # BGM 有效均值比旁白均值低 12 dB（自然融合，不抢不弱）

# ── 峰值层参数 ──
PEAK_GAP_MIN = 8.0  # BGM 有效峰值至少比旁白峰值低 8 dB

# ── 物理极限（HTML <audio> volume 范围） ──
VOLUME_FLOOR = 0.01  # 接近静音，仅在极端响 BGM 时触发
VOLUME_CEIL = 1.0    # 原始音量，不可放大


def db(val):
    """将线性值转为 dB"""
    if val <= 0:
        return -120
    return 20 * math.log10(val)


def calc_volume(bgm_mean, bgm_max, narr_mean, narr_max):
    """
    两层计算：
    1. 均值层：算出目标 volume
    2. 峰值层：如果峰值不安全，限制 volume 上限
    返回 (final_vol, reason)

    公式自调节：对任意响度 BGM，volume 自动使有效均值落在旁白下方 MEAN_GAP_TARGET dB。
    唯一物理约束：HTML <audio> volume ∈ (0, 1.0]。
    """
    # ── 第一层：均值公式 ──
    needed_atten = narr_mean - MEAN_GAP_TARGET - bgm_mean
    vol = 10 ** (needed_atten / 20)
    vol = round(max(VOLUME_FLOOR, min(VOLUME_CEIL, vol)), 2)

    reason = "均值公式"

    # 触碰上限 → BGM 太安静，无法压到目标间距
    if vol >= VOLUME_CEIL:
        eff_mean = bgm_mean + db(vol)
        actual_gap = narr_mean - eff_mean
        reason = f"均值公式（触碰上限，实际间距 {actual_gap:.1f} dB > 目标 {MEAN_GAP_TARGET:.0f} dB，BGM 偏弱）"

    # ── 第二层：峰值安全上限 ──
    eff_max = bgm_max + db(vol)
    peak_gap = narr_max - eff_max
    if peak_gap < PEAK_GAP_MIN:
        safe_atten = narr_max - PEAK_GAP_MIN - bgm_max
        safe_vol = 10 ** (safe_atten / 20)
        safe_vol = round(max(VOLUME_FLOOR, min(VOLUME_CEIL, safe_vol)), 2)
        reason = f"峰值限制（峰值间距 {peak_gap:.1f} dB < {PEAK_GAP_MIN:.0f} dB）"
        vol = min(vol, safe_vol)

    return vol, reason


def main():
    if len(sys.argv) < 4:
        print("用法: python scripts/bgm_gap_check.py <BGM_MEAN_dB> <BGM_MAX_dB> <NARR_MAX_dB>")
        sys.exit(1)

    bgm_mean = float(sys.argv[1])
    bgm_max = float(sys.argv[2])
    narr_max = float(sys.argv[3])
    narr_mean = NARR_MEAN_REF

    # 计算
    final_vol, reason = calc_volume(bgm_mean, bgm_max, narr_mean, narr_max)

    # 输出分析
    final_atten = db(final_vol)
    final_mean = bgm_mean + final_atten
    final_peak = bgm_max + final_atten

    print(f'BGM 原始: mean={bgm_mean:.1f} dB, max={bgm_max:.1f} dB')
    print(f'旁白基准: mean={narr_mean:.1f} dB, max={narr_max:.1f} dB')
    print(f'目标间距: {MEAN_GAP_TARGET:.0f} dB (BGM 均值比旁白低)')
    print(f'计算方式: {reason}')
    print(f'--- 最终结果 ---')
    print(f'FINAL_VOL={final_vol}')
    print(f'BGM 有效均值: {final_mean:.1f} dB (距旁白 {narr_mean - final_mean:.1f} dB)')
    print(f'BGM 有效峰值: {final_peak:.1f} dB (距旁白 {narr_max - final_peak:.1f} dB)')

    # 写入 segment_durations.json
    sd_path = 'segment_durations.json'
    if os.path.exists(sd_path):
        with open(sd_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        old_vol = data.get('meta', {}).get('bgm_volume', 'N/A')
        meta = data.setdefault('meta', {})
        meta['bgm_volume'] = final_vol
        meta['bgm_volume_source'] = 'formula'
        meta['bgm_mean_db'] = round(bgm_mean, 1)
        meta['bgm_max_db'] = round(bgm_max, 1)
        meta['bgm_narr_max_db'] = round(narr_max, 1)
        meta['bgm_gap_target'] = MEAN_GAP_TARGET
        if old_vol != final_vol:
            print(f'segment_durations.json: bgm_volume {old_vol} → {final_vol}')
        else:
            print(f'segment_durations.json: bgm_volume={final_vol}（未变）')
        with open(sd_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)


if __name__ == '__main__':
    main()
