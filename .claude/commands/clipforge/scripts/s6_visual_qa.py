#!/usr/bin/env python
"""Stage6 视觉 QA:渲染后抽帧 → PIL 分析 → visual_qa_report.json + qa_frames/*.png。
反馈给 SubAgent 自审(非门禁,非强制)。代码只产客观数据,断层判断归 LLM。
"""
import argparse, json, sys, os, re
from pathlib import Path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project-dir", required=True)
    args = ap.parse_args()
    project_dir = Path(args.project_dir)
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "engine"))
    from lib.visual_qa import (extract_scene_frames, analyze_frame, check_safezone,
                               PORTRAIT_BOUNDS, LANDSCAPE_BOUNDS)

    seg = project_dir / "segment_durations.json"
    if not seg.exists():
        print(f"[ERROR] 无 {seg}", file=sys.stderr)
        sys.exit(1)
    segs = json.loads(seg.read_text(encoding="utf-8")).get("segments", [])

    # 各场景中段时间点
    t = 0.0
    time_points = []
    for s in segs:
        dur = s.get("actual_duration", 0)
        time_points.append({"scene": s.get("scene", f"s{len(time_points)+1}"),
                            "t": round(t + dur / 2, 2)})
        t += dur

    # orientation: 行锚定 regex(与 gate.py check_safezone_rendered 一致,避免 prose 误匹配)
    orientation = "portrait"
    design = project_dir / "design.md"
    if design.exists() and re.search(r"^orientation:\s*landscape", design.read_text(encoding="utf-8"), re.M):
        orientation = "landscape"
    bounds = PORTRAIT_BOUNDS if orientation == "portrait" else LANDSCAPE_BOUNDS
    safe_h = bounds[1] - bounds[0]

    out_dir = project_dir / "qa_frames"
    frames = extract_scene_frames(str(project_dir / "output.mp4"), time_points, str(out_dir))

    scenes = []
    for f in frames:
        a = analyze_frame(f["path"])
        cy = a["content_y"]
        sz = check_safezone(cy, orientation)
        note = ""
        for b in a["blank_bands"]:
            if b["height"] > safe_h * 0.20:
                note = f"⭐ 空白带 y={b['y']} 高{b['height']}px (>20% 安全区 {safe_h}px),建议关注是否断层"
                break
        rel_path = os.path.relpath(f["path"], project_dir)
        scenes.append({"id": f["scene"], "frame": rel_path, "t": f["t"],
                       "content_y": cy,
                       "safezone": {"ok": sz["ok"], "overflow": sz["overflow"]},
                       "blank_bands": a["blank_bands"], "note": note})

    report = {"project_dir": str(project_dir), "output_mp4": "output.mp4",
              "orientation": orientation, "safezone_bounds": list(bounds), "scenes": scenes}
    out_report = project_dir / "visual_qa_report.json"
    out_report.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"QA 报告: {out_report}")
    print(f"帧目录: {out_dir} ({len(scenes)} 场景)")
    print("SubAgent: 读 visual_qa_report.json + 看 qa_frames/*.png,判断布局是否有断层/间距问题(创意归你),需要则调整重渲染")


if __name__ == "__main__":
    main()
