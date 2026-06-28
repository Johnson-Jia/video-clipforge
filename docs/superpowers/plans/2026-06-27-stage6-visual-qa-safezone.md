# Stage6 视觉 QA 反馈闭环 + 安全区渲染门禁 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 stage6 渲染后增加「视觉 QA 反馈闭环」(防布局断层,创意归 LLM)+「安全区渲染门禁」(防内容溢出,HARD 边界),不固定布局。

**Architecture:** 共享核心 `engine/lib/visual_qa.py`(PIL 像素分析,只产客观数据,不判断层)被两个消费者复用:`scripts/s6_visual_qa.py`(B,渲染后抽帧→报告+帧→回传 SubAgent 自审,非强制)和 `engine/gate.py::check_safezone_rendered`(A,安全区 HARD 门禁,独立抽帧不依赖 B)。哲学:代码到「客观数据」为止,断层/留白判断留给 LLM。

**Tech Stack:** Python 3.12, Pillow 11.3.0(已装), ffmpeg(管线已有), numpy(合成测试帧), pytest(单元测试)

**Spec:** `docs/superpowers/specs/2026-06-27-stage6-visual-qa-safezone-design.md`

---

## File Structure

| 文件 | 责任 | 类型 |
|---|---|---|
| `engine/lib/visual_qa.py` | PIL 像素分析核心:analyze_frame / check_safezone / extract_scene_frames | 新建 |
| `engine/tests/test_visual_qa.py` | analyze_frame / check_safezone 单元测试(合成帧) | 新建 |
| `engine/gate.py` | 新增 `check_safezone_rendered` 检查器 + 注册 GATE_CHECKERS | 改 |
| `engine/lib/models.py` | GateType enum 加 `safezone_rendered` | 改 |
| `skills/stage6-production.yaml` | gate.hard 加 `safezone_rendered` | 改 |
| `scripts/s6_visual_qa.py` | B:QA 阶段(抽帧→报告→回传 SubAgent) | 新建 |
| `stages/stage6-production.md` | SubAgent-3 渲染后 QA 自审指令(§6.8 后) | 改 |
| `shared/cron-template.md` | SubAgent-3 prompt 模板加 QA 步骤 | 改 |

约定:本计划中 `CF_DIR = .claude/commands/clipforge`(engine/ 和 scripts/ 的根)。所有 python 命令在 `CF_DIR` 下跑,加 `PYTHONIOENCODING=utf-8`。`engine/lib` 通过 `sys.path` 导入(参照 gate.py 现有方式)。

---

## Task 1: 共享核心 analyze_frame(TDD)

**Files:**
- Create: `CF_DIR/engine/lib/visual_qa.py`
- Create: `CF_DIR/engine/tests/test_visual_qa.py`
- Create: `CF_DIR/engine/tests/__init__.py`(空文件,确保包可导入)

- [ ] **Step 1: 写失败测试(test_analyze_frame_content_y + blank_band)**

Create `CF_DIR/engine/tests/test_visual_qa.py`:
```python
import numpy as np
from PIL import Image
import tempfile, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from lib.visual_qa import analyze_frame

def _make_frame(content_bands, width=1080, height=1920):
    """合成帧:黑底,在 content_bands=[(y0,y1),...] 画白条模拟内容行。"""
    img = np.zeros((height, width), dtype=np.uint8)
    for (y0, y1) in content_bands:
        img[y0:y1, :] = 255
    return Image.fromarray(img, "L")

def _save_tmp(img):
    f = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    f.close()
    img.save(f.name)
    return f.name

def test_content_y_range():
    path = _save_tmp(_make_frame([(200, 300), (800, 900)]))
    try:
        r = analyze_frame(path)
        assert r["content_y"] is not None
        assert 195 <= r["content_y"][0] <= 205   # 顶部内容 ≈200
        assert 895 <= r["content_y"][1] <= 905   # 底部内容 ≈900
    finally:
        os.unlink(path)

def test_blank_band_in_content_range():
    path = _save_tmp(_make_frame([(200, 300), (800, 900)]))
    try:
        r = analyze_frame(path)
        # 300-800 之间应有空白带(>50px)
        mid_bands = [b for b in r["blank_bands"] if b["y"] >= 300 and b["y"] < 800]
        assert any(b["height"] > 50 for b in mid_bands)
    finally:
        os.unlink(path)

def test_empty_frame():
    path = _save_tmp(_make_frame([]))
    try:
        r = analyze_frame(path)
        assert r["content_y"] is None
        assert r["blank_bands"] == []
    finally:
        os.unlink(path)
```

- [ ] **Step 2: 跑测试确认失败**

Run: `cd CF_DIR && PYTHONIOENCODING=utf-8 python -m pytest engine/tests/test_visual_qa.py -v`
Expected: FAIL (`ModuleNotFoundError: No module named 'lib.visual_qa'`)

- [ ] **Step 3: 实现 analyze_frame**

Create `CF_DIR/engine/lib/visual_qa.py`:
```python
"""Stage6 视觉 QA 共享核心:PIL 像素分析。
只产客观数据(content_y / blank_bands / row_density),不判断「是不是断层」——判断留给 LLM。
"""
from PIL import Image
import numpy as np


def analyze_frame(frame_path, content_threshold=0.05, pixel_threshold=100, min_blank_height=50):
    """分析单帧内容垂直分布。

    content_threshold: 行亮像素占比超过此值视为「内容行」(过滤 bg 零散粒子/光晕)
    pixel_threshold:   灰度 > 此值视为亮像素
    min_blank_height:  连续空白带 ≥此像素才记录(去噪)
    返回 dict: content_y [ymin,ymax] | blank_bands [{y,height}] | row_density [...] | width | height
    """
    img = np.array(Image.open(frame_path).convert("L"))
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
    if in_blank and (ymax + 1 - start) >= min_blank_height:
        blank_bands.append({"y": start, "height": ymax + 1 - start})

    return {"content_y": [ymin, ymax], "blank_bands": blank_bands,
            "row_density": row_density.tolist(), "width": int(w), "height": int(h)}
```

- [ ] **Step 4: 跑测试确认通过**

Run: `cd CF_DIR && PYTHONIOENCODING=utf-8 python -m pytest engine/tests/test_visual_qa.py -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add CF_DIR/engine/lib/visual_qa.py CF_DIR/engine/tests/test_visual_qa.py CF_DIR/engine/tests/__init__.py
git commit -m "feat(visual_qa): add analyze_frame PIL pixel distribution analysis"
```

---

## Task 2: check_safezone(TDD)

**Files:**
- Modify: `CF_DIR/engine/lib/visual_qa.py`(追加 check_safezone)
- Modify: `CF_DIR/engine/tests/test_visual_qa.py`(追加测试)

- [ ] **Step 1: 写失败测试**

追加到 `test_visual_qa.py`:
```python
from lib.visual_qa import check_safezone

def test_safezone_ok():
    assert check_safezone([200, 1600])["ok"] is True

def test_safezone_top_overflow():
    r = check_safezone([100, 1600])
    assert r["ok"] is False and r["overflow"] == "top"

def test_safezone_bottom_overflow():
    r = check_safezone([200, 1800])
    assert r["ok"] is False and r["overflow"] == "bottom"

def test_safezone_boundary_inclusive():
    assert check_safezone([180, 1700])["ok"] is True   # 边界值合规

def test_safezone_empty():
    r = check_safezone(None)
    assert r["ok"] is False

def test_safezone_landscape():
    r = check_safezone([60, 1860], orientation="landscape")
    assert r["ok"] is True
```

- [ ] **Step 2: 跑测试确认失败**

Run: `cd CF_DIR && PYTHONIOENCODING=utf-8 python -m pytest engine/tests/test_visual_qa.py -k safezone -v`
Expected: FAIL (`ImportError: cannot import name 'check_safezone'`)

- [ ] **Step 3: 实现 check_safezone**

追加到 `CF_DIR/engine/lib/visual_qa.py`:
```python
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
```

- [ ] **Step 4: 跑测试确认通过**

Run: `cd CF_DIR && PYTHONIOENCODING=utf-8 python -m pytest engine/tests/test_visual_qa.py -v`
Expected: 9 passed (3 + 6)

- [ ] **Step 5: Commit**

```bash
git add CF_DIR/engine/lib/visual_qa.py CF_DIR/engine/tests/test_visual_qa.py
git commit -m "feat(visual_qa): add check_safezone boundary check"
```

---

## Task 3: extract_scene_frames

**Files:**
- Modify: `CF_DIR/engine/lib/visual_qa.py`(追加 extract_scene_frames)

- [ ] **Step 1: 实现 extract_scene_frames**

追加到 `CF_DIR/engine/lib/visual_qa.py`:
```python
import os
import subprocess


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
```

- [ ] **Step 2: 烟雾测试(用 2026-06-27 真实 output.mp4)**

Run:
```bash
cd CF_DIR && PYTHONIOENCODING=utf-8 python -c "
import sys; sys.path.insert(0,'engine')
from lib.visual_qa import extract_scene_frames, analyze_frame, check_safezone
pd='D:/AI-Agent/video-clipforge/workspace/2026/06/27/github-trending'
frames=extract_scene_frames(pd+'/output.mp4',[{'scene':'s2','t':11}],pd+'/qa_frames_test')
a=analyze_frame(frames[0]['path'])
print('content_y:',a['content_y'])
print('safezone:',check_safezone(a['content_y']))
"
```
Expected: `content_y: [约200-250, 约1690]` / `safezone: {'ok': True, ...}`(2026-06-27 视频已修在安全区)

- [ ] **Step 3: 清理烟雾测试产物 + Commit**

```bash
rm -rf CF_DIR/../workspace/2026/06/27/github-trending/qa_frames_test
git add CF_DIR/engine/lib/visual_qa.py
git commit -m "feat(visual_qa): add extract_scene_frames ffmpeg helper"
```

---

## Task 4: gate 安全区门禁 check_safezone_rendered(TDD)

**Files:**
- Modify: `CF_DIR/engine/lib/models.py`(GateType enum 加成员)
- Modify: `CF_DIR/engine/gate.py`(加检查器 + 注册 GATE_CHECKERS)
- Modify: `CF_DIR/skills/stage6-production.yaml`(gate.hard 加 safezone_rendered)

- [ ] **Step 1: GateType enum 加成员**

读 `CF_DIR/engine/lib/models.py`,找到 `class GateType` (line 33 附近),在 `video_bitrate_valid = "video_bitrate_valid"` (line 50) 附近加一行:
```python
    safezone_rendered = "safezone_rendered"
```

- [ ] **Step 2: 写 check_safezone_rendered 检查器**

在 `CF_DIR/engine/gate.py` 的 `check_video_bitrate_valid` 函数定义后追加(参照其它 check_ 函数签名 `(project_dir: Path, params: dict) -> tuple[bool, str]`):
```python
def check_safezone_rendered(project_dir: Path, params: dict) -> tuple[bool, str]:
    """渲染后内容必须在安全区内(竖屏 y∈[180,1700] / 横屏 y∈[60,1860])。
    优先读 visual_qa_report.json(B 产出);不存在则自抽帧(解耦,门禁不依赖 QA 是否跑过)。
    """
    import json, sys, os
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from lib.visual_qa import extract_scene_frames, analyze_frame, check_safezone

    output_mp4 = project_dir / "output.mp4"
    if not output_mp4.exists():
        return (True, "skip(output.mp4 不存在,渲染前检查)")  # 渲染门禁仅在 output 存在时生效

    # orientation
    orientation = "portrait"
    design = project_dir / "design.md"
    if design.exists() and "orientation: landscape" in design.read_text(encoding="utf-8").lower():
        orientation = "landscape"

    report_path = project_dir / "visual_qa_report.json"
    if report_path.exists():
        scenes = json.loads(report_path.read_text(encoding="utf-8")).get("scenes", [])
    else:
        # 自抽帧:读 segment_durations 算各场景中段时间点
        seg_path = project_dir / "segment_durations.json"
        if not seg_path.exists():
            return (True, "skip(无 segment_durations.json,无法定位场景时间点)")
        segs = json.loads(seg_path.read_text(encoding="utf-8")).get("segments", [])
        t = 0.0
        time_points = []
        for s in segs:
            dur = s.get("actual_duration", 0)
            time_points.append({"scene": s.get("scene", "s"), "t": t + dur / 2})
            t += dur
        out_dir = project_dir / ".qa_frames_gate"
        frames = extract_scene_frames(str(output_mp4), time_points, str(out_dir))
        scenes = []
        for f in frames:
            cy = analyze_frame(f["path"])["content_y"]
            scenes.append({"id": f["scene"], "content_y": cy})
        import shutil
        shutil.rmtree(out_dir, ignore_errors=True)

    for sc in scenes:
        res = check_safezone(sc.get("content_y"), orientation)
        if not res["ok"]:
            return (False, f"{sc.get('id')}: 内容溢出安全区 {res['overflow']} "
                    f"(content_y={sc.get('content_y')}, bounds={res['bounds']})")
    return (True, f"全部 {len(scenes)} 场景内容在安全区内")
```

- [ ] **Step 3: 注册到 GATE_CHECKERS**

在 `CF_DIR/engine/gate.py` 找 `GATE_CHECKERS[GateType.fx_animation_present] = check_fx_animation_present` (line 1669 附近)后追加一行:
```python
GATE_CHECKERS[GateType.safezone_rendered] = check_safezone_rendered
```

- [ ] **Step 4: 加到 stage6 gate.hard**

读 `CF_DIR/skills/stage6-production.yaml`,找 `gate:` 段下的 `hard:` 列表(含 `video_bitrate_valid` 等),追加:
```yaml
      - safezone_rendered
```

- [ ] **Step 5: 端到端验证(用 2026-06-27 已修视频,应通过)**

Run: `cd CF_DIR && PYTHONIOENCODING=utf-8 python engine/gate.py --skill stage6-production --project-dir "D:/AI-Agent/video-clipforge/workspace/2026/06/27/github-trending"`
Expected: `hard_passed: true`,输出含「全部 N 场景内容在安全区内」

- [ ] **Step 6: 构造溢出验证(应 HARD 失败)**

临时改 `workspace/2026/06/27/github-trending/visual_qa_report.json`(若不存在,先跑 Task 5 的 s6_visual_qa.py 生成;或手写一个 content_y=[30,1850] 的假场景)制造溢出,重跑 Step 5。
Expected: `hard_passed: false`,含 `R-... safezone_rendered ... 溢出`。验证后还原。

- [ ] **Step 7: Commit**

```bash
git add CF_DIR/engine/lib/models.py CF_DIR/engine/gate.py CF_DIR/skills/stage6-production.yaml
git commit -m "feat(gate): add check_safezone_rendered HARD gate for stage6"
```

---

## Task 5: s6_visual_qa.py(B 反馈阶段)

**Files:**
- Create: `CF_DIR/scripts/s6_visual_qa.py`

- [ ] **Step 1: 实现 s6_visual_qa.py**

Create `CF_DIR/scripts/s6_visual_qa.py`:
```python
#!/usr/bin/env python
"""Stage6 视觉 QA:渲染后抽帧 → PIL 分析 → visual_qa_report.json + qa_frames/*.png。
反馈给 SubAgent 自审(非门禁,非强制)。代码只产客观数据,断层判断归 LLM。
"""
import argparse, json, sys, os
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
        time_points.append({"scene": s.get("scene", f"s{len(time_points)+1}"), "t": round(t + dur / 2, 2)})
        t += dur

    orientation = "portrait"
    design = project_dir / "design.md"
    if design.exists() and "orientation: landscape" in design.read_text(encoding="utf-8").lower():
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
                       "content_y": cy, "safezone": {"ok": sz["ok"], "overflow": sz["overflow"]},
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
```

- [ ] **Step 2: 端到端跑(2026-06-27 视频)**

Run: `cd CF_DIR && PYTHONIOENCODING=utf-8 python scripts/s6_visual_qa.py --project-dir "D:/AI-Agent/video-clipforge/workspace/2026/06/27/github-trending"`
Expected: 生成 `visual_qa_report.json` + `qa_frames/s*.png`(7 场景),每场景 safezone ok,可能标出之前修复的断层位置。

- [ ] **Step 3: 检查报告内容**

Run: `cd "D:/AI-Agent/video-clipforge" && PYTHONIOENCODING=utf-8 python -X utf8 -c "import json; d=json.load(open('workspace/2026/06/27/github-trending/visual_qa_report.json')); [print(s['id'], s['content_y'], s['safezone']['ok'], s['note'][:40]) for s in d['scenes']]"`
Expected: 各场景 content_y 在 [180,1700],safezone ok=True。

- [ ] **Step 4: Commit**

```bash
git add CF_DIR/scripts/s6_visual_qa.py
git commit -m "feat(s6): add visual QA feedback stage (anti-断层, LLM 自审)"
```

---

## Task 6: stage6 流程整合(SubAgent-3 跑 QA 自审)

**Files:**
- Modify: `CF_DIR/stages/stage6-production.md`(§6.8 后加 §6.9 QA)
- Modify: `CF_DIR/shared/cron-template.md`(SubAgent-3 prompt 加 QA)

- [ ] **Step 1: stage6-production.md 加 §6.9 视觉 QA 自审**

在 `CF_DIR/stages/stage6-production.md` 的 §6.8(组装与验证,line 313)渲染 output.mp4 之后、最终 stage6 门禁之前,插入新节:
```markdown
## §6.9 渲染后视觉 QA 自审（LLM 创意轨,非门禁）

output.mp4 渲染完成后,运行视觉 QA 抽帧分析,**让你看见自己的渲染结果**再决定布局要不要改:

bash .claude/commands/clipforge/scripts/s6_visual_qa.sh --project-dir . # 或直接 python scripts/s6_visual_qa.py --project-dir <PROJECT_DIR>

读 `visual_qa_report.json` + 看 `qa_frames/*.png`:
- **安全区**:每场景 content_y 应在 [180,1700](竖屏)/[60,1860](横屏)。溢出会被后续 stage6 门禁 HARD 拦截,这里先自查。
- **断层/间距**(创意判断归你):看 blank_bands 和帧截图,判断空白带是「有意留白」还是「布局断层」。项目名与头像、各元素间距是否舒适,由你决定。不满意就调整 creative/sNN.html 碎片重渲染。

⛔ 代码只产客观数据(content_y / blank_bands 坐标),不替你下「是不是断层」的判断——布局审美归 LLM。这一步是非强制自审,但强烈建议:你终于能看见渲染结果了。
```

- [ ] **Step 2: cron-template.md SubAgent-3 prompt 加 QA 指令**

在 `CF_DIR/shared/cron-template.md` 的 SubAgent-3(§5)门禁指令段(「完成 creative 碎片 + assemble + 渲染后,必须执行门禁校验」之前),插入:
```markdown
**渲染后视觉 QA 自审（门禁前,非强制但强烈建议）**:
渲染 output.mp4 后,运行 `python scripts/s6_visual_qa.py --project-dir <PROJECT_DIR>`。读 visual_qa_report.json 的 blank_bands + 看 qa_frames/*.png 帧截图,判断布局是否有断层/间距问题(创意判断归你)。不满意则调整 creative/ 碎片重渲染;满意则继续门禁。这一步让你「看见」渲染结果再迭代。
```

- [ ] **Step 3: Commit**

```bash
git add CF_DIR/stages/stage6-production.md CF_DIR/shared/cron-template.md
git commit -m "docs(stage6): integrate visual QA self-review into SubAgent-3 flow"
```

---

## Task 7: 回归 + 架构演进双层验证

**Files:** 无新建(验证任务)

- [ ] **Step 1: 回归 — 2026-06-27 视频跑全链**

Run:
```bash
cd CF_DIR
PYTHONIOENCODING=utf-8 python scripts/s6_visual_qa.py --project-dir "D:/AI-Agent/video-clipforge/workspace/2026/06/27/github-trending"
PYTHONIOENCODING=utf-8 python engine/gate.py --skill stage6-production --project-dir "D:/AI-Agent/video-clipforge/workspace/2026/06/27/github-trending"
```
Expected: QA 报告 5 项目场景 safezone ok;gate hard_passed=true。

- [ ] **Step 2: 单元测试全跑**

Run: `cd CF_DIR && PYTHONIOENCODING=utf-8 python -m pytest engine/tests/test_visual_qa.py -v`
Expected: 9 passed。

- [ ] **Step 3: 双层验证 — 推演核实(subagent)**

派 subagent 读真实文件,推演:① s6_visual_qa.py 输出被 SubAgent-3 读到 ② gate check_safezone_rendered 在 stage6-production skill 的 hard 列表生效 ③ B 的报告与 A 的门禁解耦(A 自抽帧兜底)。每结论附 file:line。

- [ ] **Step 4: 双层验证 — 真实视频重做(隔离 test 目录)**

用真实 GitHub 内容在 `workspace/test/<场景>/github-trending/` 跑 `/clipforge`(test 目录被 freshness/evolution 排除,见 feedback-test-isolation),验证:SubAgent-3 渲染后跑 QA 自审 → 若布局断层则据反馈调整 → gate 安全区门禁生效。确认改造端到端防止断层+溢出。

- [ ] **Step 5: 沉淀 memory + Commit**

更新 memory:`feedback-pfc-safezone-overflow` 加「已引擎化:gate check_safezone_rendered HARD + s6_visual_qa 反馈闭环」。Commit 所有改动。

---

## Self-Review(plan 自审)

- **Spec 覆盖**:① analyze_frame→Task1 ② check_safezone→Task2 ③ extract_scene_frames→Task3 ④ B(s6_visual_qa)→Task5 ⑤ A(gate门禁)→Task4 ⑥ 流程整合→Task6 ⑦ 测试+双层验证→Task7。✓ 全覆盖。
- **占位符**:无 TBD/TODO;每步含实际代码或确切命令(除 Task5 Step1 有一处已标注的笔误提醒)。
- **类型一致**:`analyze_frame` 返回 dict 含 content_y/blank_bands/row_density,Task4/Task5 消费者用的字段名一致;`check_safezone` 返回 ok/overflow 一致;GateType.safezone_rendered 在 models.py/gate.py/skills yaml 三处一致。
- **scope**:单一子系统(stage6 渲染后 QA+门禁),适合单实施计划。
