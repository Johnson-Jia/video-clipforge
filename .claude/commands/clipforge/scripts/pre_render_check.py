#!/usr/bin/env python3
"""渲染前依赖检查 — 扫描 index.html 引用的文件是否全部存在。

用法: python scripts/pre_render_check.py [--project-dir DIR]
退出码: 0=通过, 1=有缺失依赖
"""
import re
import sys
import json
from pathlib import Path


def main():
    project_dir = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    html_file = project_dir / "index.html"

    if not html_file.exists():
        print(f"FAIL: index.html 不存在")
        sys.exit(1)

    content = html_file.read_text(encoding="utf-8", errors="ignore")
    failures = []

    # 1. 检查 HTML 中引用的外部文件
    refs = re.findall(r'src="([^"]*\.(mp3|wav|mp4|png|jpg|jpeg|svg|gif|webp))"', content)
    for ref, _ in refs:
        if ref.startswith(("http://", "https://", "//")):
            continue
        if not (project_dir / ref).exists():
            failures.append(f"引用文件不存在: {ref}")

    # 2. composition 根元素必须有 data-width 和 data-height
    if not re.search(r'data-width="\d+"', content):
        failures.append("composition 根元素缺少 data-width")
    if not re.search(r'data-height="\d+"', content):
        failures.append("composition 根元素缺少 data-height")

    # 3. bgm.wav 必须存在（如果 HTML 引用了）
    if 'src="bgm.wav"' in content and not (project_dir / "bgm.wav").exists():
        failures.append("bgm.wav 被 HTML 引用但不存在")

    # 4. narration.mp3 必须存在
    if 'src="narration.mp3"' in content and not (project_dir / "narration.mp3").exists():
        failures.append("narration.mp3 被 HTML 引用但不存在")

    # 5. segment_durations.json 中 bgm_volume > 0
    sd_file = project_dir / "segment_durations.json"
    if sd_file.exists():
        try:
            sd = json.loads(sd_file.read_text(encoding="utf-8"))
            vol = sd.get("meta", {}).get("bgm_volume")
            if vol is not None and vol <= 0:
                failures.append(f"bgm_volume={vol} <= 0（BGM 静音）")
        except (json.JSONDecodeError, KeyError):
            pass

    if failures:
        for f in failures:
            print(f"FAIL: {f}")
        sys.exit(1)

    print(f"PASS: 渲染前依赖检查通过（{len(refs)} 个文件引用已验证）")


if __name__ == "__main__":
    main()
