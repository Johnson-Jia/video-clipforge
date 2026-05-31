#!/usr/bin/env python3
"""
BGM 音量校准 + 均值间距校验

用法: python scripts/bgm_gap_check.py <BGM_MEAN_dB> <BGM_MAX_dB> <NARR_MAX_dB>

输入:
  BGM_MEAN: bgm.wav 的 mean_volume (dB) — 用于查表获取推荐 volume
  BGM_MAX:  bgm.wav 的 max_volume (dB)
  NARR_MAX: narration.mp3 的 max_volume (dB)

输出:
  打印查表结果、均值间距分析和 FINAL_VOL
  将 FINAL_VOL 写入 segment_durations.json 的 meta.bgm_volume
  退出码: 0=OK, 1=需要调整（已自动修正并写入）

校准基准: 均值（mean_volume），目标 BGM 有效均值比旁白均值低 7-9 dB。

前提: narration.mp3 已经过 loudnorm I=-16 标准化（均值约 -17 dB，峰值约 -1.5 dB）。
"""
import json
import math
import os
import sys

# ── 均值校准音量表 ──
#
# 设计原理:
#   narr_mean ≈ -17 dB（loudnorm I=-16 标准化后稳定）
#   目标: bgm_effective_mean = narr_mean - 8 dB（可感知但不抢）
#   required_attenuation = target_mean - bgm_mean
#   volume = 10^(required_attenuation / 20)
#
# 每档 2 dB，覆盖 -5 ~ -27 dB 的 BGM 均值范围。
# < -27 dB 的 BGM 素材质量太差，建议更换。
#
VOLUME_TABLE = [
    # (threshold, volume, note)
    (-4,   0.07,  "极端响"),
    (-6,   0.09,  "非常响"),
    (-8,   0.11,  "很响"),
    (-10,  0.14,  "响"),
    (-12,  0.17,  "偏响"),
    (-14,  0.22,  "中等"),
    (-16,  0.27,  "标准"),
    (-18,  0.34,  "偏安静"),
    (-20,  0.40,  "安静"),
    (-22,  0.45,  "很安静"),
    (-24,  0.48,  "极安静"),
    (-27,  0.50,  "接近极限"),
]

# 旁白均值基准（loudnorm I=-16 后稳定值）
NARR_MEAN_REF = -17.0

# 均值间距目标范围
MEAN_GAP_MIN = 6.0   # BGM 均值比旁白均值低 6 dB = 可听到但明显
MEAN_GAP_MAX = 10.0  # BGM 均值比旁白均值低 10 dB = 存在感弱
MEAN_GAP_TARGET = 8.0  # 理想值

# 峰值间距安全下限（防止 BGM 峰值盖过旁白）
PEAK_GAP_MIN = 8.0   # 峰值至少差 8 dB


def lookup_volume(mean_db):
    """根据 BGM mean_volume 查表获取推荐 volume 值"""
    for threshold, vol, note in VOLUME_TABLE:
        if mean_db > threshold:
            return vol, note

    # < -27 dB: 素材太安静，无法通过提音量解决
    return None, "太安静(< -27 dB)，建议更换 BGM"


def db(val):
    """将线性值转为 dB"""
    if val <= 0:
        return -120
    return 20 * math.log10(val)


def main():
    if len(sys.argv) < 4:
        print("用法: python scripts/bgm_gap_check.py <BGM_MEAN_dB> <BGM_MAX_dB> <NARR_MAX_dB>")
        sys.exit(1)

    bgm_mean = float(sys.argv[1])
    bgm_max = float(sys.argv[2])
    narr_max = float(sys.argv[3])

    # 估算旁白均值（如果没传入，用参考值）
    narr_mean = NARR_MEAN_REF

    # 查表
    vol, note = lookup_volume(bgm_mean)

    if vol is None:
        print(f"ERROR: BGM mean_volume={bgm_mean:.1f} dB {note}")
        print("请更换更响的 BGM 素材（mean_volume > -27 dB）")
        sys.exit(1)

    print(f'BGM mean_volume: {bgm_mean:.1f} dB ({note}) → 查表推荐 volume: {vol}')

    # 计算均值间距
    attenuation_db = db(vol)
    bgm_eff_mean = bgm_mean + attenuation_db
    mean_gap = narr_mean - bgm_eff_mean
    print(f'音量衰减: {attenuation_db:.1f} dB')
    print(f'BGM 有效均值: {bgm_eff_mean:.1f} dB | 旁白均值: {narr_mean:.1f} dB')
    print(f'均值间距: {mean_gap:.1f} dB (目标 {MEAN_GAP_MIN:.0f}~{MEAN_GAP_MAX:.0f} dB，理想 {MEAN_GAP_TARGET:.0f} dB)')

    # 计算峰值间距
    bgm_eff_max = bgm_max + attenuation_db
    peak_gap = narr_max - bgm_eff_max
    print(f'BGM 有效峰值: {bgm_eff_max:.1f} dB | 旁白峰值: {narr_max:.1f} dB')
    print(f'峰值间距: {peak_gap:.1f} dB (安全下限 {PEAK_GAP_MIN:.0f} dB)')

    final_vol = vol
    adjusted = False

    # 均值间距修正
    if mean_gap < MEAN_GAP_MIN:
        # BGM 太响（均值间距不足），降低音量
        needed_atten = narr_mean - MEAN_GAP_TARGET - bgm_mean
        needed_vol = 10 ** (needed_atten / 20)
        needed_vol = max(0.05, math.floor(needed_vol * 100) / 100)
        print(f'WARNING: BGM 均值太响（间距 {mean_gap:.1f} dB < {MEAN_GAP_MIN:.0f} dB），volume 从 {vol} 降至 {needed_vol}')
        final_vol = needed_vol
        adjusted = True
    elif mean_gap > MEAN_GAP_MAX:
        # BGM 太安静（均值间距过大），提升音量
        needed_atten = narr_mean - MEAN_GAP_TARGET - bgm_mean
        needed_vol = 10 ** (needed_atten / 20)
        needed_vol = min(0.50, math.ceil(needed_vol * 100) / 100)
        print(f'WARNING: BGM 均值太小（间距 {mean_gap:.1f} dB > {MEAN_GAP_MAX:.0f} dB），volume 从 {vol} 升至 {needed_vol}')
        final_vol = needed_vol
        adjusted = True
    else:
        print(f'均值间距 OK: {mean_gap:.1f} dB')

    # 峰值安全检查（独立于均值间距）
    final_atten = db(final_vol)
    final_peak_gap = narr_max - (bgm_max + final_atten)
    if final_peak_gap < PEAK_GAP_MIN:
        # 峰值太近，需要额外降低
        needed_atten = narr_max - PEAK_GAP_MIN - bgm_max
        safe_vol = 10 ** (needed_atten / 20)
        safe_vol = max(0.05, math.floor(safe_vol * 100) / 100)
        print(f'WARNING: 峰值间距不足（{final_peak_gap:.1f} dB < {PEAK_GAP_MIN:.0f} dB），volume 从 {final_vol} 降至 {safe_vol}')
        final_vol = safe_vol
        adjusted = True

    # 最终验证
    final_atten = db(final_vol)
    final_mean = bgm_mean + final_atten
    final_peak = bgm_max + final_atten
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
        data.setdefault('meta', {})['bgm_volume'] = final_vol
        with open(sd_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        if old_vol != final_vol:
            print(f'segment_durations.json: bgm_volume {old_vol} → {final_vol}')
        else:
            print(f'segment_durations.json: bgm_volume={final_vol}（未变）')

    sys.exit(1 if adjusted else 0)


if __name__ == '__main__':
    main()
