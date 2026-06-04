#!/usr/bin/env python3
"""
BGM 全段验证：在使用前扫描整段音乐，检测并移除静音片段。

用法: python scripts/bgm_validate.py [bgm_file]

功能:
  1. 用 ffmpeg silencedetect 扫描全文静音段（< -40 dB 持续 >= 2 秒）
  2. 移除头尾静音
  3. 内部静音段：选取最长的连续有声区域
  4. 覆盖原文件，原文件备份为 bgm_orig.wav

退出码: 0=OK 或已清理, 1=不可恢复的问题
"""
import os
import re
import subprocess
import sys


SILENCE_THRESH_DB = -40
SILENCE_MIN_DUR = 2.0
NUL = "NUL" if sys.platform == "win32" else "/dev/null"


def get_duration(filepath):
    r = subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
         "-of", "csv=p=0", filepath],
        capture_output=True, text=True,
    )
    return float(r.stdout.strip())


def detect_silence(filepath):
    """返回静音段列表 [(start, end), ...]，文件末尾静音的 end=None"""
    cmd = [
        "ffmpeg", "-i", filepath,
        "-af", f"silencedetect=n={SILENCE_THRESH_DB}dB:d={SILENCE_MIN_DUR}",
        "-f", "null", NUL,
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)

    silences = []
    for line in r.stderr.split("\n"):
        m = re.search(r"silence_start:\s*([\d.]+)", line)
        if m:
            silences.append({"start": float(m.group(1)), "end": None})
        m = re.search(r"silence_end:\s*([\d.]+)", line)
        if m and silences and silences[-1]["end"] is None:
            silences[-1]["end"] = float(m.group(1))

    return silences


def find_content_regions(silences, total_dur):
    """从静音段反推出连续有声区域 [(start, end), ...]"""
    regions = []
    cursor = 0.0

    for s in silences:
        s_start = s["start"]
        s_end = s["end"] if s["end"] is not None else total_dur
        if s_start > cursor + 0.1:
            regions.append((cursor, s_start))
        cursor = s_end

    if cursor < total_dur - 0.1:
        regions.append((cursor, total_dur))

    return regions


def extract_region(filepath, start, end, output):
    subprocess.run(
        ["ffmpeg", "-y", "-i", filepath,
         "-ss", str(start), "-to", str(end),
         "-c:a", "pcm_s16le", output],
        capture_output=True, text=True,
    )


def main():
    bgm_file = sys.argv[1] if len(sys.argv) > 1 else "bgm.wav"

    if not os.path.exists(bgm_file):
        print(f"ERROR: {bgm_file} 不存在")
        sys.exit(1)

    total_dur = get_duration(bgm_file)
    print(f"BGM: {bgm_file} ({total_dur:.1f}s)")

    # 扫描静音段
    silences = detect_silence(bgm_file)

    if not silences:
        print("OK: 无静音段，BGM 完整")
        sys.exit(0)

    # 打印检测结果
    print(f"检测到 {len(silences)} 个静音段:")
    for i, s in enumerate(silences):
        end_str = f"{s['end']:.1f}s" if s["end"] is not None else "文件末尾"
        dur = (s["end"] if s["end"] else total_dur) - s["start"]
        print(f"  #{i+1}: {s['start']:.1f}s ~ {end_str} ({dur:.1f}s)")

    # 找出有声区域
    regions = find_content_regions(silences, total_dur)

    if not regions:
        print("ERROR: 整段 BGM 都是静音，无法使用")
        sys.exit(1)

    print(f"有声区域 {len(regions)} 段:")
    for i, (rs, re_) in enumerate(regions):
        print(f"  #{i+1}: {rs:.1f}s ~ {re_:.1f}s ({re_-rs:.1f}s)")

    # 选择最长有声区域
    best = max(regions, key=lambda r: r[1] - r[0])
    best_dur = best[1] - best[0]

    if best_dur < 10:
        print(f"WARNING: 最长有声区域仅 {best_dur:.1f}s，BGM 可能不适合使用")

    # 检查是否需要裁剪
    covers_start = best[0] < 1.0
    covers_end = best[1] > total_dur - 1.0
    is_only_region = len(regions) == 1

    if is_only_region and covers_start and covers_end:
        print("OK: 静音段仅在头尾边缘，无需裁剪")
        sys.exit(0)

    # 裁剪到最长有声区域
    print(f"裁剪到最长区域: {best[0]:.1f}s ~ {best[1]:.1f}s ({best_dur:.1f}s)")

    backup = "bgm_orig.wav"
    if not os.path.exists(backup):
        import shutil
        shutil.copy2(bgm_file, backup)
        print(f"原始文件备份: {backup}")

    extract_region(bgm_file, best[0], best[1], "bgm_cleaned.wav")

    # 验证裁剪后文件
    cleaned_dur = get_duration("bgm_cleaned.wav")
    if cleaned_dur < 1.0:
        print("ERROR: 裁剪后文件异常，恢复原始文件")
        os.remove("bgm_cleaned.wav")
        sys.exit(1)

    os.replace("bgm_cleaned.wav", bgm_file)
    print(f"OK: 已清理，{total_dur:.1f}s → {cleaned_dur:.1f}s")


if __name__ == "__main__":
    main()
