#!/usr/bin/env python3
"""s6_assemble_html.py — 从 creative/ 碎片 + 时间数据自动拼装完整 index.html。

LLM 只负责写 creative/ 目录下的碎片文件（style.css + 每场景 sNN.html）。
脚本负责所有确定性逻辑：clip 包裹、data-start/duration、GSAP 时间线、
phase 初始 opacity、audio 嵌入、DOCTYPE/HEAD 结构。

设计原则（双轨铁律，确定轨由脚本全自动）：
- 时间轴连续性、场景硬切、phase opacity 切换全部由数据驱动生成
- LLM 永远不碰 GSAP、不碰 data-start、不碰 clip 包裹
- 这彻底解决：API 超时（碎片化）+ GSAP 手写易错 + 重名 scene_id 冲突

用法:
  python scripts/s6_assemble_html.py --project-dir workspace/2026/06/11/xxx
  python scripts/s6_assemble_html.py --project-dir . --output index.html
  python scripts/s6_assemble_html.py --project-dir . --validate   # 仅校验碎片完整性
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# 让脚本 import engine.lib（读 config 等），parents[1] = clipforge 目录
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


# fx 层装饰动画约定 class（LLM 在碎片 layer-fx 子元素上用这些 class，
# assemble 自动注入对应 GSAP 动画。元素颜色/位置/大小由内联 style 自由控制）
FX_ANIM_CLASSES = {"fx-pulse", "fx-drift", "fx-spin", "fx-blink"}

# bg 组件库目录（s6_assemble 根据 <!-- bg-component: NAME --> 标记自动注入）
COMPONENTS_BG_DIR = Path(__file__).resolve().parent.parent / "components" / "bg"


# ──────────────────────────────────────────────────────────────────────────
# 基础 CSS（固定，LLM 不碰）— 三层架构 + FX 原语（phase 可见性由 GSAP 控制，CSS 永不设 opacity:0）
# ──────────────────────────────────────────────────────────────────────────
BASE_CSS = """/* === ClipForge 基础层（自动生成，勿手改）=== */
*{margin:0;padding:0;box-sizing:border-box;}
body{background:#000;color:#fff;overflow:hidden;width:1080px;height:1920px;}
#root{position:relative;width:1080px;height:1920px;overflow:hidden;}
.clip{position:absolute;top:0;left:0;width:1080px;height:1920px;overflow:hidden;}
.layer-bg{position:absolute;top:0;left:0;width:100%;height:100%;z-index:1;pointer-events:none;}
.layer-fx{position:absolute;top:0;left:0;width:100%;height:100%;z-index:2;pointer-events:none;}
.layer-content{position:relative;z-index:3;height:100%;color:#fff;font-size:48px;}
.phase{position:absolute;top:0;left:0;width:100%;height:100%;display:flex;flex-direction:column;align-items:center;justify-content:center;padding:180px 90px 220px 90px;}
/* 兜底：.phase 内文本居中容器的直接块级子元素水平居中（根治 max-width 块缺 margin:0 auto 导致整块偏左；text-align 只居中行内内容不居中块盒子）*/
.phase [style*="text-align:center"] > div,.phase [style*="text-align: center"] > div{margin-left:auto;margin-right:auto;}
audio{display:none;}
.fx-glow{position:absolute;border-radius:50%;filter:blur(80px);pointer-events:none;}
.fx-line{position:absolute;height:1px;pointer-events:none;}
.fx-dot{position:absolute;border-radius:50%;pointer-events:none;}
/* === fx 原语库（CSS animation 循环态，0%帧可见/移动型，HyperFrames 安全）===
   LLM 在 .layer-fx 内用 <div class="fx-xxx"> 直接引用，无需写 CSS；
   颜色默认半透明白，可 inline 覆盖（style="background:var(--accent-warm)"）。
   情绪→原语：ambient→aura / focus→ring,pulse-ring / calm→particle / tech→scan,stream,grid /
   climax→beam / shock→bolt / energy→orbit。R-R-008 要求 ≥2 种不同 fx class。 */
@keyframes fxAura{0%,100%{opacity:.45;transform:scale(1)}50%{opacity:.8;transform:scale(1.1)}}
@keyframes fxRingExp{0%,100%{opacity:.3;transform:scale(.92)}50%{opacity:.65;transform:scale(1.25)}}
@keyframes fxFloat{0%,100%{transform:translateY(0);opacity:.6}50%{transform:translateY(-22px);opacity:1}}
@keyframes fxScanMove{0%,100%{top:18%}50%{top:82%}}
@keyframes fxBeamSweep{0%{left:-60%;opacity:0}10%,90%{opacity:.6}50%{left:50%}100%{left:120%;opacity:0}}
@keyframes fxStreamFall{0%{top:-50%;opacity:0}15%{opacity:.5}100%{top:120%;opacity:0}}
@keyframes fxBolt{0%,88%,100%{opacity:0}90%,94%{opacity:.85}91%{opacity:.2}}
@keyframes fxGridPulse{0%,100%{opacity:.06}50%{opacity:.14}}
@keyframes fxOrbit{from{transform:rotate(0) translateX(160px) rotate(0)}to{transform:rotate(360deg) translateX(160px) rotate(-360deg)}}
@keyframes fxPulseRing{0%{transform:scale(.4);opacity:.6}100%{transform:scale(2.2);opacity:0}}
.fx-aura{position:absolute;border-radius:50%;filter:blur(70px);animation:fxAura 4.5s ease-in-out infinite;}
.fx-ring{position:absolute;border-radius:50%;border:2px solid rgba(255,255,255,.5);animation:fxRingExp 5s ease-in-out infinite;}
.fx-particle{position:absolute;width:10px;height:10px;border-radius:50%;background:rgba(255,255,255,.7);animation:fxFloat 4s ease-in-out infinite;}
.fx-scan{position:absolute;left:0;width:100%;height:3px;background:linear-gradient(90deg,transparent,rgba(255,255,255,.6),transparent);opacity:.5;animation:fxScanMove 6s ease-in-out infinite;}
.fx-beam{position:absolute;top:40%;width:80%;height:50px;background:linear-gradient(90deg,transparent,rgba(255,255,255,.5),transparent);filter:blur(6px);mix-blend-mode:screen;animation:fxBeamSweep 5s ease-in-out infinite;}
.fx-stream{position:absolute;width:3px;height:35%;background:linear-gradient(180deg,transparent,rgba(255,255,255,.6),transparent);animation:fxStreamFall 3s linear infinite;}
.fx-bolt{position:absolute;inset:0;opacity:0;background:radial-gradient(circle at 50% 30%,rgba(255,255,255,.4),transparent 60%);animation:fxBolt 5s steps(1) infinite;}
.fx-grid{position:absolute;inset:0;background-image:linear-gradient(rgba(255,255,255,.1) 1px,transparent 1px),linear-gradient(90deg,rgba(255,255,255,.1) 1px,transparent 1px);background-size:50px 50px;animation:fxGridPulse 8s ease-in-out infinite;}
.fx-orbit{position:absolute;top:50%;left:50%;width:12px;height:12px;margin:-6px;border-radius:50%;background:rgba(255,255,255,.8);box-shadow:0 0 10px rgba(255,255,255,.5);animation:fxOrbit 6s linear infinite;}
.fx-pulse-ring{position:absolute;top:calc(50% - 100px);left:calc(50% - 100px);width:200px;height:200px;margin:0;border-radius:50%;border:2px solid rgba(255,255,255,.5);animation:fxPulseRing 3s ease-out infinite;}
/* === LLM 自定义组件层（来自 creative/style.css）=== */
"""


def _parse_bg_component(component_path: Path) -> tuple[str, list[str], list[str]]:
    """解析 bg 组件文件，返回 (dom_html, keyframes_css_list, visual_types)。

    组件文件三层结构：
    1. <!-- @ComponentMeta ... --> — 元数据（含 visual_types 声明）
    2. <!-- @keyframes ... --> — CSS 动画，提取注入 index.html <style>
    3. DOM HTML — 实际元素，注入 layer-bg
    """
    content = component_path.read_text(encoding="utf-8").strip()

    # 提取 @keyframes：扫描 <!-- --> 注释块，收集含 @keyframes 的
    keyframes: list[str] = []
    for m in re.finditer(r"<!--\s*(.*?)\s*-->", content, re.DOTALL):
        block = m.group(1).strip()
        if "@keyframes" in block:
            keyframes.append(block)

    # 提取 @ComponentMeta 的 visual_types 声明（供 gate R-R-009 优先读取，防分类器正则误判）
    visual_types: list[str] = []
    meta_match = re.search(r"@ComponentMeta\b.*?/ComponentMeta", content, re.DOTALL)
    if meta_match:
        vt_match = re.search(r"visual_types:\s*\[([^\]]*)\]", meta_match.group(0))
        if vt_match:
            visual_types = [t.strip() for t in vt_match.group(1).split(",") if t.strip()]

    # DOM = 去掉所有注释后的纯 HTML
    dom = re.sub(r"<!--.*?-->", "", content, flags=re.DOTALL).strip()
    return dom, keyframes, visual_types


def _find_layer_bg_range(html: str) -> tuple[int, int]:
    """定位 layer-bg div 的精确字符范围（正确处理嵌套 div）。

    Returns: (start, end) 含整个 <div class="layer-bg">...</div>；找不到返回 (-1, -1)
    """
    start_match = re.search(r'<div\s+class="layer-bg"[^>]*>', html)
    if not start_match:
        return -1, -1
    start = start_match.start()
    pos = start_match.end()
    depth = 1
    while depth > 0 and pos < len(html):
        next_open = html.find("<div", pos)
        next_close = html.find("</div>", pos)
        if next_close == -1:
            break
        if next_open != -1 and next_open < next_close:
            depth += 1
            pos = next_open + 4
        else:
            depth -= 1
            if depth == 0:
                return start, next_close + 6
            pos = next_close + 6
    return start, pos


def _inject_bg_component(frag_html: str, sid: str) -> tuple[str, list[str]]:
    """根据碎片 layer-bg 中的 <!-- bg-component: NAME --> 标记注入组件 DOM。

    机制：从 components/bg/NAME.html 加载组件，用组件 DOM 覆盖 layer-bg 内所有内容。
    LLM 在碎片里写的任何 bg CSS 都会被组件覆盖——从机制上消除自写 bg。
    无标记/组件不存在/无 DOM → 原样返回（不破坏流程，留给 gate 拦截）。

    Returns: (modified_html, keyframes_css_list)
    """
    marker_match = re.search(r"<!--\s*bg-component:\s*(\S+)\s*-->", frag_html)
    if not marker_match:
        return frag_html, []
    comp_name = marker_match.group(1)
    comp_path = COMPONENTS_BG_DIR / f"{comp_name}.html"
    if not comp_path.exists():
        print(f"[WARN] {sid}: bg-component '{comp_name}' 不存在于 {COMPONENTS_BG_DIR}", file=sys.stderr)
        return frag_html, []
    dom, keyframes, visual_types = _parse_bg_component(comp_path)
    if not dom:
        print(f"[WARN] {sid}: bg-component '{comp_name}' 解析后无 DOM 内容", file=sys.stderr)
        return frag_html, []
    start, end = _find_layer_bg_range(frag_html)
    if start < 0:
        return frag_html, []
    marker = marker_match.group(0)
    # 注入 data-bg-types 声明：gate _classify_bg_element_types 优先读取，正则作 fallback。
    # 声明优先避免分类器正则追不上组件库的实际 CSS 写法（2026-06-23 diamond_lattice 误判事故）
    types_attr = f' data-bg-types="{",".join(visual_types)}"' if visual_types else ""
    new_bg = f'<div class="layer-bg"{types_attr}>\n{marker}\n{dom}\n</div>'
    return frag_html[:start] + new_bg + frag_html[end:], keyframes


def load_json(path: Path) -> dict | list:
    """加载 JSON，不存在返回空容器。"""
    if not path.exists():
        return {} if path.suffix == ".json" else []
    return json.loads(path.read_text(encoding="utf-8"))


def parse_fx_classes(frag_html: str) -> set[str]:
    """提取碎片 layer-fx 层中出现的 fx 动画 class（约定见 FX_ANIM_CLASSES）。

    只扫描 layer-fx 到 layer-content 之间的片段，避免误读 bg/content 层。
    """
    classes: set[str] = set()
    fx_open = re.search(r'class="[^"]*layer-fx[^"]*"', frag_html)
    if not fx_open:
        return classes
    rest = frag_html[fx_open.end():]
    next_layer = re.search(r'class="[^"]*layer-content[^"]*"', rest)
    fx_chunk = rest[: next_layer.start()] if next_layer else rest
    for cls_str in re.findall(r'class="([^"]+)"', fx_chunk):
        for c in cls_str.split():
            if c in FX_ANIM_CLASSES:
                classes.add(c)
    return classes


def build_clips(segments: list, creative_dir: Path) -> tuple[str, float, list[str], dict, list[str]]:
    """读取每个场景的创意碎片，包裹 clip div。

    Returns: (clips_html, total_duration, missing_scenes, fx_info, bg_keyframes)
        fx_info: {sid: set(fx 动画 class)}，供 build_gsap 注入装饰动画
        bg_keyframes: 所有场景 bg 组件的 @keyframes CSS（去重），注入 <style>
    """
    clips: list[str] = []
    missing: list[str] = []
    fx_info: dict[str, set[str]] = {}
    bg_keyframes_seen: dict[str, None] = {}
    cumulative = 0.0

    for idx, seg in enumerate(segments, 1):
        sid = f"s{idx:02d}"
        frag_path = creative_dir / f"{sid}.html"

        if not frag_path.exists() or frag_path.stat().st_size == 0:
            missing.append(sid)
            # 占位空骨架，保证时间轴连续（渲染时该场景空白，不阻断流程）
            body = (
                '<div class="layer-bg"></div>\n'
                '<div class="layer-fx"></div>\n'
                '<div class="layer-content"></div>'
            )
            fx_info[sid] = set()
        else:
            body = frag_path.read_text(encoding="utf-8").strip()
            # B: bg 组件注入——用组件 DOM 覆盖碎片 layer-bg（LLM 自写 bg 失效）
            body, kfs = _inject_bg_component(body, sid)
            for kf in kfs:
                bg_keyframes_seen[kf] = None
            fx_info[sid] = parse_fx_classes(body)

        dur = float(seg.get("actual_duration", seg.get("duration", 0)))
        clip = (
            f'<div class="clip" id="{sid}" '
            f'data-start="{cumulative:.2f}" data-duration="{dur:.2f}">\n'
            f"{body}\n"
            f"</div>"
        )
        clips.append(clip)
        cumulative += dur

    return "\n\n".join(clips), cumulative, missing, fx_info, list(bg_keyframes_seen.keys())


def build_gsap(segments: list, phase_timings: dict, total_duration: float,
               fx_info: dict | None = None, narration_segs: list | None = None) -> str:
    """从时间数据自动生成 GSAP timeline。

    完全确定性：场景过渡 = 累计 start（按 transition 字段）；phase 切换 = global_start + start_offset；
    fx 装饰动画按约定 class 注入；运镜相机动画按 camera_move 字段注入。LLM 永不手写这段，根除 phase opacity 漏恢复。
    """
    n = len(segments)
    ids = [f"#s{i+1:02d}" for i in range(n)]
    fx_info = fx_info or {}
    narration_segs = narration_segs or []

    # 累计起止时间
    starts: list[float] = []
    cum = 0.0
    for s in segments:
        starts.append(cum)
        cum += float(s.get("actual_duration", s.get("duration", 0)))

    lines: list[str] = ["var tl = gsap.timeline({ paused: true });"]

    # 初始化：隐藏除第一个外的所有场景
    if n > 1:
        quoted = ", ".join(f"'{i}'" for i in ids[1:])
        lines.append(f"tl.set([{quoted}], {{opacity:0}}, 0);")
    lines.append(f"tl.set('{ids[0]}', {{opacity:1}}, 0);")

    # 场景过渡（按 transition 字段：硬切/叠化/淡入/淡出/黑场）
    from scripts.cinematic import transition_to_phase
    for i in range(1, n):
        t = starts[i]
        prev_sid = f"s{i:02d}"
        cur_sid = f"s{i+1:02d}"
        # transition 属"前镜→当前镜"过渡，读当前镜（narration_segs 索引 i）
        ns_seg = narration_segs[i] if i < len(narration_segs) else None
        tr = (ns_seg.get("transition") if isinstance(ns_seg, dict) else None) or "硬切"
        for stmt in transition_to_phase(prev_sid, cur_sid, t, tr):
            lines.append(stmt + ";")

    # Phase 切换（phase_timings.json 句子锚点校准，精度 ±50ms）
    scenes = phase_timings.get("scenes", []) if isinstance(phase_timings, dict) else []
    for sc in scenes:
        seg_idx = sc.get("segment_index", 0)
        base = sc.get(
            "global_start",
            starts[seg_idx] if seg_idx < len(starts) else 0.0,
        )
        sid = f"s{seg_idx + 1:02d}"
        # Phase 初始化：场景开始时隐藏 phase-2+（CSS 默认 opacity:1，
        # 若不初始化，切点前所有 phase 叠加显示）。切点 GSAP 再设回 1。
        phases_in_scene = sorted({p.get("phase", 1) for p in sc.get("phases", [])})
        if len(phases_in_scene) > 1:
            extra = ", ".join(
                f"'#{sid} .phase-{ph}'" for ph in phases_in_scene if ph > 1
            )
            if extra:
                lines.append(f"tl.set([{extra}], {{opacity:0}}, {base:.2f});")
        for p in sc.get("phases", []):
            if p.get("phase", 1) > 1:
                t = base + p["start_offset"]
                pn = p["phase"]
                lines.append(
                    f"tl.set('#{sid} .phase-{pn}', {{opacity:1}}, {t:.2f});"
                )
                lines.append(
                    f"tl.set('#{sid} .phase-{pn-1}', {{opacity:0}}, {t:.2f});"
                )

    # fx 层装饰动画（确定性注入：LLM 只需在碎片用约定 class）
    # repeat 按场景时长动态算（HyperFrames lint 禁止 repeat:-1 无限循环）：
    #   repeat = floor(scene_dur / cycle) - 1
    FX_ANIM = {
        # class: (动画属性, 单循环时长, yoyo, ease)
        "fx-pulse": ("scale:1.18", 2.4, True, "sine.inOut"),
        "fx-drift": ("y:-30", 3.2, True, "sine.inOut"),
        "fx-spin": ("rotation:360", 9, False, "none"),
        "fx-blink": ("opacity:0.25", 1.6, True, "sine.inOut"),
    }
    for i, s in enumerate(segments):
        sid = f"s{i+1:02d}"
        scene_start = starts[i]
        scene_dur = float(s.get("actual_duration", s.get("duration", 0)))
        for cls in sorted(fx_info.get(sid, set())):
            if cls in FX_ANIM:
                props, cycle, yoyo, ease = FX_ANIM[cls]
                repeat = max(0, int(scene_dur // cycle) - 1)
                yoyo_str = ",yoyo:true" if yoyo else ""
                lines.append(
                    f"tl.to('#{sid} .{cls}', {{{props},duration:{cycle},"
                    f"repeat:{repeat}{yoyo_str},ease:'{ease}'}}, {scene_start:.2f});"
                )

    # 运镜相机动画（按 camera_move 字段，对 .scene-content 注入 GSAP）
    from scripts.cinematic import camera_move_to_gsap
    for i, s in enumerate(segments):
        sid = f"s{i+1:02d}"
        scene_start = starts[i]
        scene_dur = float(s.get("actual_duration", s.get("duration", 0)))
        ns_seg = narration_segs[i] if i < len(narration_segs) else None
        cm = (ns_seg.get("camera_move") if isinstance(ns_seg, dict) else None) or "固定"
        stmt = camera_move_to_gsap(sid, cm, scene_start, scene_dur)
        if stmt:
            lines.append(stmt + ";")

    # HyperFrames 注册
    lines.append("window.__timelines=window.__timelines||{};")
    lines.append('window.__timelines["main"]=tl;')
    lines.append(
        f"window.__hf={{duration:{total_duration:.2f},"
        f"seek:function(ms){{tl.seek(ms/1000);}}}};"
    )

    return "\n".join(lines)


# 字体 family 名 → Google Fonts URL 的 family 参数。
# 字重用 ; 分隔；单字重字体不带 :wght@。新增字体需在此表登记。
GOOGLE_FONT_MAP = {
    # 标题展示体
    "Ma Shan Zheng": "Ma+Shan+Zheng",
    "Noto Serif SC": "Noto+Serif+SC:wght@500;700;900",
    "ZCOOL XiaoWei": "ZCOOL+XiaoWei",
    "ZCOOL QingKe HuangYou": "ZCOOL+QingKe+HuangYou",
    "JetBrains Mono": "JetBrains+Mono:wght@400;700;800",
    "Inter": "Inter:wght@400;700;900",
    # 正文 / 数据
    "Noto Sans SC": "Noto+Sans+SC:wght@300;400;500;700",
}


# family → [(相对路径, weight)]。前缀 assets/ 或 cache/，resolve_font_files 运行时解析。
# 字体文件不入 git（.gitignore），由三级回退获取（SRC_MAP/本地/下载）。
_FONT_SRCS = {
    "Ma Shan Zheng": [("assets/MaShanZheng-400.ttf", 400)],
    "Noto Serif SC": [("assets/SourceHanSerifSC-Heavy.woff2", 900), ("assets/SourceHanSerifSC-Regular.woff2", 400)],
    "Noto Sans SC": [("cache/noto-sans-sc/400-normal.woff2", 400), ("cache/noto-sans-sc/700-normal.woff2", 700)],
    "JetBrains Mono": [("cache/jetbrains-mono/700-normal.woff2", 700), ("cache/jetbrains-mono/400-normal.woff2", 400)],
    "Inter": [("cache/inter/900-normal.woff2", 900), ("cache/inter/400-normal.woff2", 400)],
}


def resolve_font_files(family, assets, cache, downloader=None):
    """三级回退解析 family → [(path, weight)]：SRC_MAP → CLIPFORGE_FONTS_DIR 本地 → 自动下载。

    用户配 CLIPFORGE_FONTS_DIR（如 E:\\字体）→ 本地字体直接用、不下载；
    克隆者无本地 → downloader 从 Google Fonts 下载到 cache（首次渲染自动）。
    字体不入 git，仓库不膨胀 + 环境自包含。
    """
    import os
    # 1. SRC_MAP（assets / 已配置 cache）
    found = []
    for rel, weight in _FONT_SRCS.get(family, []):
        if rel.startswith("assets/"):
            p = assets / rel[len("assets/"):]
        else:
            p = cache / rel[len("cache/"):]
        if p.exists():
            found.append((p, weight, ""))
    if found:
        return found
    # 2. 字体目录（env > config.json，参照工作目录回退——data_paths.get_fonts_dir）
    from engine.lib.data_paths import get_fonts_dir
    local_dir = get_fonts_dir()
    if local_dir:
        local = _find_local_fonts(local_dir, family)
        if local:
            return local
    # 3. 自动下载到 cache（克隆者 fallback）
    if downloader and family in GOOGLE_FONT_MAP:
        return downloader(family, cache)
    return []


def _find_local_fonts(local_dir, family):
    """在本地目录按 family 名关键词模糊匹配 woff2/woff/ttf，返回 [(path, weight)]。"""
    d = Path(local_dir)
    if not d.exists():
        return []
    key = family.replace(" ", "").lower()
    matches = []
    for f in d.rglob("*"):
        if f.suffix.lower() not in (".woff2", ".woff", ".ttf"):
            continue
        name = f.stem.lower().replace(" ", "").replace("-", "").replace("_", "")
        if key in name or name in key:
            matches.append((f, _infer_weight(f.name), ""))
    return matches


def _infer_weight(name):
    """从文件名推断 CSS weight（数字/关键词），默认 400。"""
    import re
    m = re.search(r'(\d{3})', name)
    if m:
        w = int(m.group(1))
        if 100 <= w <= 900:
            return w
    low = name.lower()
    if any(k in low for k in ("black", "heavy")):
        return 900
    if "bold" in low:
        return 700
    if "medium" in low:
        return 500
    if "light" in low:
        return 300
    return 400


def _parse_google_fonts_css(css):
    """解析 Google Fonts CSS → [(weight, url, unicode_range)]。

    中文字体分段（同 weight 多 unicode-range 切片），保留所有切片不覆盖。
    旧逻辑 dest 用 {weight}-normal.woff2 导致同 weight 多切片互相覆盖，只留 1 个 → 缺字。
    """
    results = []
    for block in re.finditer(r'@font-face\s*\{([^}]+)\}', css):
        text = block.group(1)
        w = re.search(r'font-weight:\s*(\d+)', text)
        s = re.search(r'src:\s*url\((https://[^)]+\.woff2)\)', text)
        u = re.search(r'unicode-range:\s*([^;]+);', text)
        if w and s:
            results.append((int(w.group(1)), s.group(1), (u.group(1).strip() if u else "")))
    return results


def _ensure_font_in_cache(family, cache):
    """从 Google Fonts 下载 family 的 woff2 切片到 cache/family/，返回 [(path, weight, unicode_range)]。

    中文字体分段（同 weight 多 unicode-range 切片），唯一命名 weight-idx 避免覆盖。
    克隆者首次渲染自动下载。网络失败 → 返回空（调用方降级 fallback 字体）。
    """
    import urllib.request
    import re
    if family not in GOOGLE_FONT_MAP:
        return []
    cache_sub = cache / family.lower().replace(" ", "-")
    css_url = f"https://fonts.googleapis.com/css2?family={GOOGLE_FONT_MAP[family]}&display=swap"
    try:
        req = urllib.request.Request(css_url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })
        css = urllib.request.urlopen(req, timeout=15).read().decode("utf-8")
        results = []
        cache_sub.mkdir(parents=True, exist_ok=True)
        for idx, (weight, url, unicode_range) in enumerate(_parse_google_fonts_css(css)):
            dest = cache_sub / f"{weight}-{idx}-normal.woff2"
            if not dest.exists():
                data = urllib.request.urlopen(url, timeout=30).read()
                dest.write_bytes(data)
            results.append((dest, weight, unicode_range))
        return results
    except Exception:
        return []


def build_font_faces(creative_dir: Path, script_dir: Path) -> str:
    """生成 @font-face（三级回退：assets/本地/下载），替代 Google Fonts <link>。

    HyperFrames 0.6.109+ 把 google_fonts_import 升级为 lint error。本地 @font-face +
    具体 font-family 让 lint 通过。字体来源三级回退（resolve_font_files）：
    assets/fonts → $CLIPFORGE_FONTS_DIR（用户本地，如 E:\\字体）→ 自动下载到 hyperframes cache。
    """
    fonts_path = creative_dir / "fonts.json"
    if not fonts_path.exists():
        return ""
    try:
        fonts = json.loads(fonts_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return ""

    import os
    cache = Path(os.path.expanduser("~/.cache/hyperframes/fonts"))
    assets = script_dir.parent / "assets" / "fonts"
    parts = []
    seen = set()
    for layer in ("title", "body", "data"):
        family = fonts.get(layer, {}).get("family", "")
        if family and family not in seen:
            for path, weight, unicode_range in resolve_font_files(family, assets, cache,
                                                     downloader=_ensure_font_in_cache):
                abs_path = str(path).replace("\\", "/")
                ext = path.suffix.lower().lstrip(".")
                fmt = {"woff2": "woff2", "woff": "woff", "ttf": "truetype"}.get(ext, "woff2")
                ur = f" unicode-range: {unicode_range};" if unicode_range else ""
                parts.append(
                    f"@font-face {{ font-family: '{family}'; font-weight: {weight}; "
                    f"src: url('file:///{abs_path}') format('{fmt}');{ur} }}")
            seen.add(family)
    return "\n".join(parts) + "\n"


def assemble(project_dir: Path) -> tuple[str, list[str]]:
    """拼装完整 index.html，返回 (html, missing_scenes)。"""
    creative_dir = project_dir / "creative"

    # 加载确定性数据
    dur_data = load_json(project_dir / "segment_durations.json")
    segments = (
        dur_data.get("segments", []) if isinstance(dur_data, dict) else dur_data
    )
    if not segments:
        print("[FAIL] segment_durations.json 无 segments 数据", file=sys.stderr)
        sys.exit(1)

    phase_timings = load_json(project_dir / "phase_timings.json")

    # 加载电影级字段（shot_size/camera_move/transition，来自 stage3 narration_segments.json）
    narration_segs = []
    ns_path = project_dir / "narration_segments.json"
    if ns_path.exists():
        try:
            narration_segs = json.loads(ns_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            narration_segs = []

    # 读取 LLM 自定义 CSS（可选）
    custom_css = ""
    custom_css_path = creative_dir / "style.css"
    if custom_css_path.exists():
        custom_css = custom_css_path.read_text(encoding="utf-8").strip()

    # 构建 clips + GSAP（B: build_clips 现同时注入 bg 组件并收集 keyframes）
    clips_html, total_duration, missing, fx_info, bg_keyframes = build_clips(segments, creative_dir)
    gsap_js = build_gsap(segments, phase_timings, total_duration, fx_info, narration_segs)
    bg_keyframes_css = "\n\n".join(bg_keyframes) if bg_keyframes else ""

    # 读取 BGM 音量（已在 tts/bgm 管线算好）
    bgm_volume = (
        dur_data.get("meta", {}).get("bgm_volume", 0.15)
        if isinstance(dur_data, dict)
        else 0.15
    )

    fonts_link = build_font_faces(creative_dir, Path(__file__).resolve().parent)

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=1080,height=1920">
<style>
{fonts_link}
{BASE_CSS}
{custom_css}
/* === bg 组件 @keyframes（自动注入，来自 components/bg/）=== */
{bg_keyframes_css}
</style>
</head>
<body>
<div id="root" data-composition-id="main" data-start="0" data-duration="{total_duration:.2f}" data-width="1080" data-height="1920">
<audio id="narration" src="narration.mp3" data-volume="1" data-track="1" data-start="0"></audio>
<audio id="bgm" src="bgm.wav" data-volume="{bgm_volume}" data-track="2" data-start="0"></audio>

{clips_html}

</div>
<script src="https://cdn.jsdelivr.net/npm/gsap@3/dist/gsap.min.js"></script>
<script>
{gsap_js}
</script>
</body>
</html>"""

    # var(--font-x) → 具体字体名（HyperFrames 0.6.109+ lint 不解析 CSS var()）
    fonts_path = creative_dir / "fonts.json"
    if fonts_path.exists():
        try:
            _fonts = json.loads(fonts_path.read_text(encoding="utf-8"))
            for layer in ("title", "body", "data"):
                family = _fonts.get(layer, {}).get("family", "")
                if family:
                    html = html.replace(f"var(--font-{layer})", f"'{family}'")
        except (json.JSONDecodeError, OSError):
            pass

    return html, missing


def validate(project_dir: Path) -> int:
    """校验 creative/ 目录碎片完整性。"""
    creative_dir = project_dir / "creative"
    dur_data = load_json(project_dir / "segment_durations.json")
    segments = (
        dur_data.get("segments", []) if isinstance(dur_data, dict) else dur_data
    )
    n = len(segments)

    if not creative_dir.exists():
        print(f"[FAIL] creative/ 目录不存在", file=sys.stderr)
        return 1

    missing = []
    empty = []
    for idx in range(1, n + 1):
        sid = f"s{idx:02d}"
        frag = creative_dir / f"{sid}.html"
        if not frag.exists():
            missing.append(sid)
        elif frag.stat().st_size == 0:
            empty.append(sid)

    style_css = creative_dir / "style.css"
    style_status = "OK" if style_css.exists() and style_css.stat().st_size > 0 else "MISSING"

    print(f"=== creative/ 碎片校验 ===")
    print(f"  场景数: {n}")
    print(f"  style.css: {style_status}")
    if missing:
        print(f"  [FAIL] 缺失 {len(missing)} 个碎片: {', '.join(missing)}")
    if empty:
        print(f"  [WARN] 空碎片 {len(empty)} 个: {', '.join(empty)}")
    if not missing and not empty:
        print(f"  [OK] 全部 {n} 个碎片完整")

    return 1 if missing else 0


def main() -> None:
    parser = argparse.ArgumentParser(
        description="ClipForge 创意碎片拼装器（自动生成 index.html）"
    )
    parser.add_argument("--project-dir", required=True, help="项目目录")
    parser.add_argument("--output", default=None, help="输出路径（默认 <project>/index.html）")
    parser.add_argument("--validate", action="store_true", help="仅校验 creative/ 完整性")
    args = parser.parse_args()

    project_dir = Path(args.project_dir).resolve()

    if args.validate:
        sys.exit(validate(project_dir))

    html, missing = assemble(project_dir)

    if missing:
        print(f"[WARN] {len(missing)} 个场景碎片缺失，已用空骨架占位: {', '.join(missing)}", file=sys.stderr)

    output_path = Path(args.output) if args.output else project_dir / "index.html"
    output_path.write_text(html, encoding="utf-8")

    print(f"[OK] Assembled: {output_path}")
    print(f"  场景数: {html.count('class=\"clip\"')}")
    print(f"  Phase 元素: {html.count('class=\"phase phase-')}")


if __name__ == "__main__":
    main()
