#!/usr/bin/env python3
"""
BGM 音量校准：均值公式 + 动态分档峰值约束

用法: python scripts/bgm_gap_check.py <BGM_MEAN_dB> <BGM_MAX_dB> <NARR_MAX_dB>

输入:
  BGM_MEAN: bgm.wav 的 mean_volume (dB)
  BGM_MAX:  bgm.wav 的 max_volume (dB)
  NARR_MAX: narration.mp3 的 max_volume (dB)

输出:
  打印计算过程和 FINAL_VOL
  将 FINAL_VOL 写入 segment_durations.json 的 meta.bgm_volume

算法:
  1. 均值层：volume = 10^((narr_mean - mean_gap - bgm_mean) / 20)
     旁白均值固定（loudnorm I=-16 后 ≈ -17 dB），BGM 均值实测，
     mean_gap 按档位取值（平稳 BGM 压更低，避免持续铺底抢旁白）。
  2. 双层按 BGM 动态范围（peak_spread）分档，mean_gap / peak_gap 同档取值：
     - flat (≤12 dB):       氛围/lo-fi/钢琴，mean_gap=10, peak_gap=8  dB
     - balanced (12-14 dB): 轻流行/民谣，    mean_gap=9,  peak_gap=11 dB
     - beat-heavy (14-16):  电子/合成波，    mean_gap=9,  peak_gap=15 dB
     - dynamic (>16 dB):    交响/电影，      mean_gap=9,  peak_gap=14 dB
     取 min(均值层, 峰值层) 作为最终 volume。

前提: narration.mp3 已经过 loudnorm I=-16 标准化（均值约 -17 dB，峰值约 -1.5 dB）。
"""
import json
import math
import os
import sys


# ── 旁白基准 ──
NARR_MEAN_REF = -17.0  # loudnorm I=-16 标准化后的稳定均值

# ── 均值层基准（fallback：tier 未指定 mean_gap 时用） ──
MEAN_GAP_TARGET = 9.0  # BGM 有效均值比旁白均值低 9 dB（自然融合，不抢不弱）

# ── 动态分档：均值层 + 峰值层双层参数 ──
# peak_spread = bgm_max - bgm_mean（经 loudnorm 标准化后测量）
# spread 小 = 平稳柔和（氛围/钢琴）→ 持续等响铺底，mean_gap 加大压更低
# spread 大 = 重音猛烈（电子/交响）→ 有动态弱段让位，mean_gap 维持基准
PEAK_TIERS = [
    {"name": "flat",        "max_spread": 12,  "peak_gap": 8,  "mean_gap": 10, "desc": "氛围/lo-fi/钢琴"},
    {"name": "balanced",    "max_spread": 14,  "peak_gap": 11, "mean_gap": 9,  "desc": "轻流行/民谣"},
    {"name": "beat-heavy",  "max_spread": 16,  "peak_gap": 15, "mean_gap": 9,  "desc": "电子/合成波"},
    {"name": "dynamic",     "max_spread": 999, "peak_gap": 14, "mean_gap": 9,  "desc": "交响/电影"},
]

# ── 物理极限（HTML <audio> volume 范围） ──
VOLUME_FLOOR = 0.01
VOLUME_CEIL = 1.0


def db(val):
    """将线性值转为 dB"""
    if val <= 0:
        return -120
    return 20 * math.log10(val)


def classify_tier(peak_spread):
    """根据 peak_spread 匹配分档"""
    for tier in PEAK_TIERS:
        if peak_spread <= tier["max_spread"]:
            return tier
    return PEAK_TIERS[-1]


def calc_volume(bgm_mean, bgm_max, narr_mean, narr_max):
    """
    两层计算 + 动态分档：
    1. 均值层：算出目标 volume（固定 9dB 间距）
    2. 峰值层：根据 BGM 动态分档，用对应 peak_gap 计算 volume 上限
    返回 (final_vol, reason, tier_info)
    """
    peak_spread = bgm_max - bgm_mean
    tier = classify_tier(peak_spread)
    peak_gap_target = tier["peak_gap"]
    mean_gap_target = tier.get("mean_gap", MEAN_GAP_TARGET)  # 均值间距按档位取值

    # ── 第一层：均值公式（按档位 mean_gap） ──
    needed_atten = narr_mean - mean_gap_target - bgm_mean
    vol_mean = 10 ** (needed_atten / 20)
    vol_mean = round(max(VOLUME_FLOOR, min(VOLUME_CEIL, vol_mean)), 2)

    # ── 第二层：峰值公式（分档目标） ──
    needed_peak_atten = narr_max - peak_gap_target - bgm_max
    vol_peak = 10 ** (needed_peak_atten / 20)
    vol_peak = round(max(VOLUME_FLOOR, min(VOLUME_CEIL, vol_peak)), 2)

    # 取更严格约束
    if vol_peak < vol_mean:
        vol = vol_peak
        reason = f"峰值限制（{tier['name']}档, spread={peak_spread:.1f}dB, 目标{peak_gap_target}dB）"
    else:
        vol = vol_mean
        reason = "均值公式"

    # 触碰上限
    if vol >= VOLUME_CEIL:
        eff_mean = bgm_mean + db(vol)
        actual_gap = narr_mean - eff_mean
        reason = f"均值公式（触碰上限，实际间距 {actual_gap:.1f} dB > 目标 {mean_gap_target:.1f} dB，BGM 偏弱）"

    tier_info = {"name": tier["name"], "spread": round(peak_spread, 1), "peak_gap": peak_gap_target, "mean_gap": mean_gap_target}
    return vol, reason, tier_info


def main():
    if len(sys.argv) < 4:
        print("用法: python scripts/bgm_gap_check.py <BGM_MEAN_dB> <BGM_MAX_dB> <NARR_MAX_dB>")
        sys.exit(1)

    bgm_mean = float(sys.argv[1])
    bgm_max = float(sys.argv[2])
    narr_max = float(sys.argv[3])
    narr_mean = NARR_MEAN_REF

    # 计算
    final_vol, reason, tier_info = calc_volume(bgm_mean, bgm_max, narr_mean, narr_max)

    # 输出分析
    final_atten = db(final_vol)
    final_mean = bgm_mean + final_atten
    final_peak = bgm_max + final_atten

    print(f'BGM 原始: mean={bgm_mean:.1f} dB, max={bgm_max:.1f} dB')
    print(f'旁白基准: mean={narr_mean:.1f} dB, max={narr_max:.1f} dB')
    print(f'动态分档: {tier_info["name"]}（spread={tier_info["spread"]}dB, mean_gap={tier_info["mean_gap"]}dB, peak_gap={tier_info["peak_gap"]}dB）')
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
        meta['bgm_gap_target'] = tier_info["mean_gap"]
        meta['bgm_peak_tier'] = tier_info["name"]
        meta['bgm_peak_spread'] = tier_info["spread"]
        meta['bgm_mean_gap'] = tier_info["mean_gap"]
        meta['bgm_peak_gap'] = tier_info["peak_gap"]
        if old_vol != final_vol:
            print(f'segment_durations.json: bgm_volume {old_vol} → {final_vol}')
        else:
            print(f'segment_durations.json: bgm_volume={final_vol}（未变）')
        with open(sd_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)


if __name__ == '__main__':
    main()
