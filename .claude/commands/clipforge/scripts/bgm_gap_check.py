#!/usr/bin/env python3
"""
BGM 音量校准 + 峰值间距校验

用法: python scripts/bgm_gap_check.py <BGM_MEAN_dB> <BGM_MAX_dB> <NARR_MAX_dB>

输入:
  BGM_MEAN: bgm.wav 的 mean_volume (dB) — 用于查表获取推荐 volume
  BGM_MAX:  bgm.wav 的 max_volume (dB)
  NARR_MAX: narration.mp3 的 max_volume (dB)

输出:
  打印查表结果、间距分析和 FINAL_VOL
  将 FINAL_VOL 写入 segment_durations.json 的 meta.bgm_volume
  退出码: 0=OK, 1=需要调整（已自动修正并写入）

工作目录必须在项目目录下。

前提: narration.mp3 已经过 loudnorm I=-16 标准化（峰值约 -1.5 dB）。
"""
import json
import math
import os
import sys

# 音量校准表（基于旁白峰值 -1.5 dB，目标 BGM 峰值比旁白低 17 dB）
VOLUME_TABLE = [
    (-5,   0.12),   # > -5 dB（极端响）
    (-10,  0.12),   # -5 ~ -10 dB（非常响）
    (-15,  0.13),   # > -10 ~ -15 dB（很响）
    (-20,  0.13),   # -15 ~ -20 dB
    (-25,  0.15),   # -20 ~ -25 dB（最常见）→ 默认
    (-30,  0.17),   # -25 ~ -30 dB（偏安静）
    (-999, 0.21),   # < -30 dB（很安静）
]


def lookup_volume(mean_db):
    """根据 BGM mean_volume 查表获取推荐 volume 值"""
    for threshold, vol in VOLUME_TABLE:
        if mean_db > threshold:
            return vol
    return 0.21


def main():
    if len(sys.argv) < 4:
        print("用法: python scripts/bgm_gap_check.py <BGM_MEAN_dB> <BGM_MAX_dB> <NARR_MAX_dB>")
        sys.exit(1)

    bgm_mean = float(sys.argv[1])
    bgm_max = float(sys.argv[2])
    narr_max = float(sys.argv[3])

    # 查表获取推荐 volume
    vol = lookup_volume(bgm_mean)
    print(f'BGM mean_volume: {bgm_mean:.1f} dB → 查表推荐 volume: {vol}')

    # 峰值间距校验
    attenuated = bgm_max + 20 * math.log10(vol)
    gap = narr_max - attenuated
    print(f'BGM 衰减后峰值: {attenuated:.1f} dB')
    print(f'旁白峰值: {narr_max:.1f} dB')
    print(f'间距: {gap:.1f} dB (目标 15~20 dB)')

    final_vol = vol
    adjusted = False

    if gap < 15:
        needed_vol = 10 ** ((narr_max - 17 - bgm_max) / 20)
        needed_vol = math.floor(needed_vol * 100) / 100
        if needed_vol < 0.01:
            needed_vol = 0.01
        print(f'WARNING: BGM 太响（间距 {gap:.1f} dB < 15 dB），volume 从 {vol} 降至 {needed_vol}')
        final_vol = needed_vol
        adjusted = True
    elif gap > 22:
        needed_vol = 10 ** ((narr_max - 17 - bgm_max) / 20)
        needed_vol = math.ceil(needed_vol * 100) / 100
        if needed_vol > 0.50:
            needed_vol = 0.50
        print(f'WARNING: BGM 太小听不到（间距 {gap:.1f} dB > 22 dB），volume 从 {vol} 升至 {needed_vol}')
        final_vol = needed_vol
        adjusted = True
    else:
        print(f'间距 OK: {gap:.1f} dB')

    print(f'FINAL_VOL={final_vol}')

    # 写入 segment_durations.json
    sd_path = 'segment_durations.json'
    if os.path.exists(sd_path):
        with open(sd_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        old_vol = data.get('meta', {}).get('bgm_volume', 'N/A')
        data.setdefault('meta', {})['bgm_volume'] = final_vol
        with open(sd_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f'segment_durations.json: bgm_volume {old_vol} → {final_vol}')

    sys.exit(1 if adjusted else 0)


if __name__ == '__main__':
    main()
