#!/usr/bin/env python3
"""
导演门禁 — 渲染帧视觉分析（渲染后运行）

用法: python scripts/frame_analysis.py [项目目录]
  项目目录默认为当前目录

检查项:
  1. 帧间视觉差异（相邻帧亮度差 ≥ 阈值 = 场景切换）
  2. 全片色彩多样性（U/V 通道方差）
  3. 暗帧比例（亮度 < 12 的帧占比）
  4. 总体亮度分布

退出码: 0=通过, 1=视觉问题

依赖: ffmpeg/ffprobe（必需）
"""

import subprocess
import sys
import os
import json
import re

# Windows GBK console cannot encode Unicode symbols (✓✗⚠)
if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if sys.stderr and hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')


def get_duration(video_path):
    result = subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
         "-of", "csv=p=0", video_path],
        capture_output=True, text=True
    )
    return float(result.stdout.strip())


def analyze_frame_brightness(video_path, timestamp):
    """用 ffmpeg showinfo 提取指定时间戳帧的 Y 均值（亮度）"""
    result = subprocess.run(
        ["ffmpeg", "-ss", str(timestamp), "-i", video_path,
         "-frames:v", "1", "-vf", "showinfo", "-f", "null", "-"],
        capture_output=True, text=True, timeout=10
    )
    # 提取 mean Y 值
    match = re.search(r'mean:\[(\d+)', result.stderr)
    if match:
        return int(match.group(1))
    return None


def analyze_frame_color(video_path, timestamp):
    """用 ffmpeg signalstats 提取帧的色彩通道均值"""
    result = subprocess.run(
        ["ffmpeg", "-ss", str(timestamp), "-i", video_path,
         "-frames:v", "1", "-vf", "signalstats=stat=tout+vrep+brng",
         "-f", "null", "-"],
        capture_output=True, text=True, timeout=10
    )
    # 提取 YAV 元数据
    stats = {}
    for key in ["YAVG", "UAVG", "VAVG", "SATAVG"]:
        match = re.search(rf'lavfi\.signalstats\.{key}=(\d+\.?\d*)', result.stderr)
        if match:
            stats[key] = float(match.group(1))
    return stats


def main():
    project_dir = sys.argv[1] if len(sys.argv) > 1 else "."
    video_path = os.path.join(project_dir, "output.mp4")

    if not os.path.exists(video_path):
        video_alt = os.path.join(project_dir, "final.mp4")
        if os.path.exists(video_alt):
            video_path = video_alt
        else:
            print("ERROR: 无 output.mp4 或 final.mp4")
            sys.exit(1)

    PASS = 0
    FAIL = 0
    WARN = 0

    def ok(msg):
        nonlocal PASS
        PASS += 1
        print(f"  \033[32m✓ {msg}\033[0m")

    def fail(msg):
        nonlocal FAIL
        FAIL += 1
        print(f"  \033[31m✗ {msg}\033[0m")

    def warn(msg):
        nonlocal WARN
        WARN += 1
        print(f"  \033[33m⚠ {msg}\033[0m")

    print("=" * 50)
    print("  导演门禁 — 渲染帧视觉分析")
    print(f"  视频: {video_path}")
    print("=" * 50)

    duration = get_duration(video_path)
    print(f"  时长: {duration:.1f}s")

    # 均匀抽取帧（最多 20 帧）
    NUM_FRAMES = min(20, max(8, int(duration / 3)))
    interval = duration / (NUM_FRAMES + 1)

    print(f"\n── 1. 帧间视觉差异（{NUM_FRAMES} 帧采样）──")

    brightness_data = []
    color_data = []
    dark_frames = 0

    for i in range(1, NUM_FRAMES + 1):
        t = interval * i
        brightness = analyze_frame_brightness(video_path, t)
        color = analyze_frame_color(video_path, t)

        if brightness is not None:
            brightness_data.append({"time": t, "Y": brightness})
            if brightness < 12:
                dark_frames += 1

        if color:
            color_data.append({"time": t, **color})

    if not brightness_data:
        fail("无法提取帧亮度数据")
        sys.exit(1)

    # 计算相邻帧亮度差异
    diffs = []
    for i in range(1, len(brightness_data)):
        diff = abs(brightness_data[i]["Y"] - brightness_data[i - 1]["Y"])
        diffs.append(diff)

    if diffs:
        avg_diff = sum(diffs) / len(diffs)
        max_diff = max(diffs)
        min_diff = min(diffs)

        # 阈值：相邻帧亮度差 < 3 = 视觉无变化
        static_pairs = sum(1 for d in diffs if d < 3)

        if avg_diff < 3:
            fail(f"帧间平均亮度差 {avg_diff:.1f}（几乎无变化，画面可能过于静态）")
        elif avg_diff < 8:
            warn(f"帧间平均亮度差 {avg_diff:.1f}（变化较小，视觉切换可能不够明显）")
        else:
            ok(f"帧间平均亮度差 {avg_diff:.1f}（视觉切换充分）")

        if min_diff == 0 and len(diffs) > 2:
            # 检查是否有连续多个帧完全相同
            static_streaks = 0
            current_streak = 0
            for d in diffs:
                if d < 3:
                    current_streak += 1
                    static_streaks = max(static_streaks, current_streak)
                else:
                    current_streak = 0
            if static_streaks >= 3:
                fail(f"连续 {static_streaks + 1} 帧视觉无变化（可能场景停留过长）")
        else:
            ok(f"最大亮度差 {max_diff}，最小 {min_diff}")

    # ── 2. 色彩多样性 ──
    print("\n── 2. 色彩多样性 ──")
    if len(color_data) >= 5:
        y_values = [c["YAVG"] for c in color_data if "YAVG" in c]
        u_values = [c["UAVG"] for c in color_data if "UAVG" in c]
        v_values = [c["VAVG"] for c in color_data if "VAVG" in c]

        def variance(vals):
            if len(vals) < 2:
                return 0
            mean = sum(vals) / len(vals)
            return sum((x - mean) ** 2 for x in vals) / len(vals)

        y_var = variance(y_values)
        u_var = variance(u_values)
        v_var = variance(v_values)

        if u_var < 1 and v_var < 1:
            fail(f"色彩几乎无变化: U方差={u_var:.1f} V方差={v_var:.1f}（画面可能偏单色）")
        elif u_var < 3 and v_var < 3:
            warn(f"色彩变化偏小: U方差={u_var:.1f} V方差={v_var:.1f}（视觉多样性不足）")
        else:
            ok(f"色彩多样性: U方差={u_var:.1f} V方差={v_var:.1f}")
    else:
        warn("色彩数据不足，跳过多样性检查")

    # ── 3. 暗帧检测 ──
    print("\n── 3. 暗帧检测 ──")
    dark_ratio = dark_frames / len(brightness_data) if brightness_data else 0
    if dark_frames == 0:
        ok("无暗帧（亮度全部正常）")
    elif dark_ratio < 0.1:
        warn(f"暗帧: {dark_frames}/{len(brightness_data)}（{dark_ratio:.0%}，少量可接受）")
    else:
        fail(f"暗帧过多: {dark_frames}/{len(brightness_data)}（{dark_ratio:.0%}，可能有黑屏问题）")

    # ── 4. 总体亮度分布 ──
    print("\n── 4. 亮度分布 ──")
    if brightness_data:
        y_vals = [b["Y"] for b in brightness_data]
        avg_y = sum(y_vals) / len(y_vals)
        max_y = max(y_vals)
        min_y = min(y_vals)

        if avg_y < 15:
            fail(f"平均亮度过低: {avg_y:.0f}/255（接近黑屏，bg 组件可能太暗或未生效）")
        elif avg_y < 25:
            warn(f"平均亮度偏低: {avg_y:.0f}/255（建议提高 bg 装饰层 alpha）")
        elif avg_y > 200:
            warn(f"平均亮度偏高: {avg_y:.0f}/255（整体画面可能过亮）")
        else:
            ok(f"平均亮度: {avg_y:.0f}/255（范围 {min_y}~{max_y}）")

    # ── 汇总 ──
    print("\n" + "=" * 50)
    print(f"  帧分析: {PASS} 通过  {FAIL} 失败  {WARN} 警告")
    print("=" * 50)

    if FAIL > 0:
        print(f"\n\033[31m  帧分析未通过 — 视觉设计需要调整\033[0m")
        sys.exit(1)
    else:
        print(f"\n\033[32m  帧分析通过\033[0m")
        sys.exit(0)


if __name__ == "__main__":
    main()
