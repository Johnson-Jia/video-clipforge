#!/usr/bin/env python3
"""screencast.py — Playwright 屏录生成器（tutorial 屏录素材）。

录 web 内容（教程页 / demo HTML 报告 / web demo）为横屏 mp4 片段，供 tutorial 混合制作
（ClipForge 视觉片段 + Playwright 屏录片段 + 自己配音 + 剪映合成，见 categories/tutorial.md 片段制作指引）。

A 方案定位：屏录素材生成器——不是整片自动，是产出 demo 片段供用户合成。

用法:
  # 录教程页（缓慢滚动展示）
  python scripts/screencast.py --url "file:///D:/AI-Agent/ai-landing-tutorial/index.html" --output screencast-intro.mp4 --duration 15

  # 录 HTML 报告展示（如 ai-metrics 报告）
  python scripts/screencast.py --url "file:///D:/AI-Agent/ai-landing-tutorial/demos/ai-metrics/report.html" --output ai-metrics.mp4 --duration 20 --actions "scroll:5000,wait:3"

  # 录 web demo（点击导航 + 停留）
  python scripts/screencast.py --url "http://localhost:8000/demo" --output demo.mp4 --duration 12 --actions "click:.btn-start,wait:2,scroll:2000"

  # 调试（可见浏览器）
  python scripts/screencast.py --url ... --output ... --headed

actions DSL（逗号分隔）:
  scroll:像素距离     平滑滚动（默认 3000）
  wait:秒            停留展示（默认 2）
  click:CSS选择器    点击元素后等 0.8s
  type:选择器=文本   输入文本

CLI demo（如 python main.py）：先用 Claude Code 跑命令生成 HTML 报告，再用本脚本录报告页。

依赖: playwright（pip install playwright && playwright install chromium）+ ffmpeg（webm→mp4，ClipForge 已装）
"""
from __future__ import annotations
import argparse
import asyncio
import shutil
import subprocess
import sys
from pathlib import Path


async def record_one(url: str, output: Path, duration: float, width: int, height: int,
                     actions: list[str], headless: bool = True) -> int:
    """录单个 URL → mp4。返回 0 成功 / 1 失败。"""
    from playwright.async_api import async_playwright

    tmp_dir = output.parent / f".{output.stem}_sc_tmp"
    tmp_dir.mkdir(parents=True, exist_ok=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless)
        context = await browser.new_context(
            viewport={"width": width, "height": height},
            record_video_dir=str(tmp_dir),
            record_video_size={"width": width, "height": height},
        )
        page = await context.new_page()
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(800)  # 首屏渲染稳定

            for act in actions:
                kind, _, params = act.partition(":")
                kind = kind.strip().lower()
                if kind == "scroll":
                    dist = int(params) if params.strip() else 3000
                    steps = max(20, abs(dist) // 100)
                    for _ in range(steps):
                        await page.evaluate(f"window.scrollBy(0, {dist // steps})")
                        await page.wait_for_timeout(40)
                elif kind == "wait":
                    secs = float(params) if params.strip() else 2.0
                    await page.wait_for_timeout(int(secs * 1000))
                elif kind == "click":
                    try:
                        await page.click(params.strip(), timeout=5000)
                        await page.wait_for_timeout(800)
                    except Exception as e:
                        print(f"[WARN] click '{params}' 失败: {e}", file=sys.stderr)
                elif kind == "type":
                    sel, _, text = params.partition("=")
                    try:
                        await page.type(sel.strip(), text.strip())
                        await page.wait_for_timeout(500)
                    except Exception as e:
                        print(f"[WARN] type '{sel}' 失败: {e}", file=sys.stderr)
                elif kind == "next":
                    # next:N = 翻 N 页（ArrowRight + slide 动画 0.6s/页），不内部 wait
                    # 配合前置 wait:S 控制每页停留（per-page 不同时长，配合 tutorial_narrate.py 自动配音对齐）
                    times = int(params.strip()) if params.strip() else 1
                    for _ in range(times):
                        await page.keyboard.press("ArrowRight")
                        await page.wait_for_timeout(600)  # slide 切换/动画

            # 补足剩余 duration（actions 用时不可控，这里保证最低录制时长）
            await page.wait_for_timeout(int(max(0.5, duration) * 1000))
        finally:
            await context.close()  # 视频落盘（必须在 browser.close 前）
            await browser.close()

    # tmp_dir 里的 webm → mp4
    webm_files = list(tmp_dir.glob("*.webm"))
    if not webm_files:
        print("[FAIL] 未找到录制 webm（页面加载失败？）", file=sys.stderr)
        return 1
    webm = webm_files[0]

    if shutil.which("ffmpeg"):
        try:
            subprocess.run(
                ["ffmpeg", "-y", "-i", str(webm), "-c:v", "libx264", "-preset", "fast",
                 "-crf", "20", "-pix_fmt", "yuv420p", str(output)],
                check=True, capture_output=True,
            )
            print(f"[OK] {output} ({duration}s, {width}x{height})")
        except subprocess.CalledProcessError as e:
            # ffmpeg 失败，保留 webm 兜底
            fallback = output.with_suffix(".webm")
            shutil.copy(webm, fallback)
            print(f"[WARN] ffmpeg 转码失败，保留 webm: {fallback}", file=sys.stderr)
            print(f"       stderr: {e.stderr.decode(errors='ignore')[:200]}", file=sys.stderr)
    else:
        fallback = output.with_suffix(".webm")
        shutil.copy(webm, fallback)
        print(f"[OK] {fallback} (无 ffmpeg，保留 webm)")

    shutil.rmtree(tmp_dir, ignore_errors=True)
    return 0


def main() -> None:
    ap = argparse.ArgumentParser(description="Playwright 屏录生成器（tutorial 屏录素材）")
    ap.add_argument("--url", required=True, help="待录 URL（http:// 或 file:///）")
    ap.add_argument("--output", required=True, help="输出 mp4 路径")
    ap.add_argument("--duration", type=float, default=10.0, help="录制时长（秒，默认 10）")
    ap.add_argument("--width", type=int, default=1920, help="画布宽（横屏 1920，默认）")
    ap.add_argument("--height", type=int, default=1080, help="画布高（横屏 1080，默认）")
    ap.add_argument("--actions", default="scroll",
                    help="动作序列（逗号分隔：scroll:距离,wait:秒,click:选择器,type:选择器=文本）。默认 scroll")
    ap.add_argument("--headed", action="store_true", help="可见浏览器（调试用）")
    args = ap.parse_args()

    actions = [a.strip() for a in args.actions.split(",") if a.strip()]
    output = Path(args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)

    sys.exit(asyncio.run(record_one(
        args.url, output, args.duration, args.width, args.height, actions, headless=not args.headed
    )))


if __name__ == "__main__":
    main()
