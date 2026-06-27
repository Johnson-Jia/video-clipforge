"""Stage6 视觉 QA 共享核心:PIL 像素分析。
只产客观数据(content_y / blank_bands / row_density),不判断「是不是断层」——判断留给 LLM。
"""
import os
import subprocess

from PIL import Image
import numpy as np


def analyze_frame(frame_path, content_threshold=0.05, pixel_threshold=100, min_blank_height=50):
    """分析单帧内容垂直分布。

    content_threshold: 行亮像素占比超过此值视为「内容行」(过滤 bg 零散粒子/光晕)
    pixel_threshold:   灰度 > 此值视为亮像素
    min_blank_height:  连续空白带 ≥此像素才记录(去噪)
    返回 dict: content_y [ymin,ymax] | blank_bands [{y,height}] | row_density [...] | width | height
    """
    with Image.open(frame_path) as im:
        img = np.array(im.convert("L"))
    h, w = img.shape
    bright_per_row = (img > pixel_threshold).sum(axis=1)
    row_density = (bright_per_row / w).astype(float)
    content_rows = np.where(row_density > content_threshold)[0]

    if len(content_rows) == 0:
        return {"content_y": None, "blank_bands": [], "row_density": row_density.tolist(),
                "width": int(w), "height": int(h)}

    ymin, ymax = int(content_rows[0]), int(content_rows[-1])
    # 仅在内容范围 [ymin,ymax] 内找空白带(中间断层),忽略上下纯背景
    blank_bands = []
    in_blank = False
    start = ymin
    for y in range(ymin, ymax + 1):
        if row_density[y] <= content_threshold:
            if not in_blank:
                in_blank = True
                start = y
        else:
            if in_blank:
                in_blank = False
                if y - start >= min_blank_height:
                    blank_bands.append({"y": start, "height": y - start})

    return {"content_y": [ymin, ymax], "blank_bands": blank_bands,
            "row_density": row_density.tolist(), "width": int(w), "height": int(h)}


PORTRAIT_BOUNDS = (180, 1700)   # 竖屏 1080×1920:上180 下220
LANDSCAPE_BOUNDS = (60, 1860)   # 横屏 1920×1080:上60 下60


def check_safezone(content_y, orientation="portrait"):
    """判断内容 y 范围是否在安全区内(客观事实)。
    返回 {ok, bounds, y_min, y_max, overflow}。overflow: "top"/"bottom"/"empty"/None
    """
    bounds = PORTRAIT_BOUNDS if orientation == "portrait" else LANDSCAPE_BOUNDS
    if content_y is None:
        return {"ok": False, "bounds": bounds, "y_min": None, "y_max": None, "overflow": "empty"}
    ymin, ymax = content_y
    overflow = None
    if ymin < bounds[0]:
        overflow = "top"
    elif ymax > bounds[1]:
        overflow = "bottom"
    return {"ok": overflow is None, "bounds": bounds,
            "y_min": ymin, "y_max": ymax, "overflow": overflow}


def extract_scene_frames(output_mp4, time_points, out_dir):
    """ffmpeg 按时间点抽帧。
    time_points: [{"scene": sid, "t": seconds}, ...]
    返回同结构 list,每项加 "path"。
    """
    os.makedirs(out_dir, exist_ok=True)
    results = []
    for tp in time_points:
        path = os.path.join(out_dir, f"{tp['scene']}.png")
        subprocess.run(
            ["ffmpeg", "-y", "-ss", str(tp["t"]), "-i", output_mp4,
             "-frames:v", "1", "-loglevel", "error", path],
            check=True,
        )
        results.append({**tp, "path": path})
    return results
