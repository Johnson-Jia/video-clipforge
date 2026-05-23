#!/usr/bin/env python3
"""
BGM 峰值间距校验

用法: python scripts/bgm_gap_check.py <BGM_MAX_dB> <NARR_MAX_dB> <BGM_VOL>

输入:
  BGM_MAX:  bgm.wav 的 max_volume (dB)
  NARR_MAX: narration.mp3 的 max_volume (dB)
  BGM_VOL:  查表得到的推荐 volume 值

输出:
  打印间距分析结果和 FINAL_VOL（如果需要调整）
  退出码: 0=OK, 1=需要调整

工作目录必须在项目目录下。
"""
import math, sys

def main():
    if len(sys.argv) < 4:
        print("用法: python scripts/bgm_gap_check.py <BGM_MAX_dB> <NARR_MAX_dB> <BGM_VOL>")
        sys.exit(1)

    bgm_max = float(sys.argv[1])
    narr_max = float(sys.argv[2])
    vol = float(sys.argv[3])

    attenuated = bgm_max + 20 * math.log10(vol)
    gap = narr_max - attenuated
    print(f'BGM 衰减后峰值: {attenuated:.1f} dB')
    print(f'旁白峰值: {narr_max:.1f} dB')
    print(f'间距: {gap:.1f} dB (目标 15~20 dB)')

    if gap < 15:
        needed_vol = 10 ** ((narr_max - 17 - bgm_max) / 20)
        needed_vol = math.floor(needed_vol * 100) / 100
        if needed_vol < 0.01: needed_vol = 0.01
        print(f'WARNING: BGM 太响（间距 {gap:.1f} dB < 15 dB），volume 从 {vol} 降至 {needed_vol}')
        print(f'FINAL_VOL={needed_vol}')
        sys.exit(1)
    elif gap > 22:
        needed_vol = 10 ** ((narr_max - 17 - bgm_max) / 20)
        needed_vol = math.ceil(needed_vol * 100) / 100
        if needed_vol > 0.50: needed_vol = 0.50
        print(f'WARNING: BGM 太小听不到（间距 {gap:.1f} dB > 22 dB），volume 从 {vol} 升至 {needed_vol}')
        print(f'FINAL_VOL={needed_vol}')
        sys.exit(1)
    else:
        print(f'间距 OK: {gap:.1f} dB')
        print(f'FINAL_VOL={vol}')
        sys.exit(0)

if __name__ == '__main__':
    main()
