"""从 cover.html 提取封面色值，给无 cover_params.json 的历史视频补 cover 标注。

历史视频多用手写 cover.html（无 cover_params.json），导致 cover 维度无法分析。
本脚本从 cover.html 提取 hex 色值，按 HSL 色相分类 warm（红橙黄）/cool（青蓝），
生成简化 cover_params.json（colors.accent_warm/accent_cool），供 _read_cover_attrs
解析 color_bias。确定性提取真实 CSS 色值，非编造。

用法：cd .claude/commands/clipforge && python scripts/backfill_cover.py
"""
from __future__ import annotations
import json
import re
import sys
from pathlib import Path
from datetime import datetime, timezone

CLIPFORGE_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(CLIPFORGE_ROOT))
from engine.lib.data_paths import WORKSPACE_ROOT as PROJECT_ROOT  # 四级回退(env>git>config>cwd)
WORKSPACE = PROJECT_ROOT / "workspace"


def _hex_warm_cool(hex_str: str) -> str:
    """hex → 'warm'/'cool'/'neutral'（基于 HSL 色相，过滤黑/白/灰底色）。"""
    h = hex_str.lstrip('#')
    if len(h) != 6:
        return 'neutral'
    try:
        r, g, b = int(h[0:2], 16) / 255, int(h[2:4], 16) / 255, int(h[4:6], 16) / 255
    except ValueError:
        return 'neutral'
    mx, mn = max(r, g, b), min(r, g, b)
    l = (mx + mn) / 2
    if l < 0.12 or l > 0.95:        # 跳过纯黑背景 / 纯白
        return 'neutral'
    d = mx - mn
    if d < 0.18:                    # 灰色无色相
        return 'neutral'
    if mx == r:
        hue = ((g - b) / d) % 6
    elif mx == g:
        hue = (b - r) / d + 2
    else:
        hue = (r - g) / d + 4
    hue *= 60
    if hue < 70 or hue >= 320:      # 红橙黄
        return 'warm'
    if 160 <= hue < 280:            # 青蓝
        return 'cool'
    return 'neutral'                # 绿/紫


def _extract_cover_from_html(html_path: Path) -> dict | None:
    html = html_path.read_text(encoding='utf-8', errors='ignore')
    hexes = set(re.findall(r'#([0-9A-Fa-f]{6})', html))
    if not hexes:
        return None
    warms = [h for h in hexes if _hex_warm_cool(h) == 'warm']
    cools = [h for h in hexes if _hex_warm_cool(h) == 'cool']
    if not warms and not cools:
        return None

    def _sat(h):
        r, g, b = int(h[0:2], 16) / 255, int(h[2:4], 16) / 255, int(h[4:6], 16) / 255
        return max(r, g, b) - min(r, g, b)

    warm_rep = max(warms, key=_sat) if warms else None   # 最饱和作代表色
    cool_rep = max(cools, key=_sat) if cools else None
    return {"warm": warm_rep, "cool": cool_rep}


def main():
    backfilled = 0
    skipped = 0
    no_html = 0
    for pf in sorted(WORKSPACE.rglob("performance.json")):
        proj = pf.parent
        cp_file = proj / "cover_params.json"
        if cp_file.exists():
            skipped += 1            # 已有（实时生成/已 backfill），不覆盖
            continue
        html_file = proj / "cover.html"
        if not html_file.exists():
            no_html += 1
            continue
        extracted = _extract_cover_from_html(html_file)
        if not extracted:
            continue
        payload = {
            "source": "html_extract",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "colors": {
                "accent_warm": f"#{extracted['warm']}" if extracted['warm'] else "",
                "accent_cool": f"#{extracted['cool']}" if extracted['cool'] else "",
            },
        }
        cp_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        backfilled += 1
    print(f"cover backfill: {backfilled} 个从 cover.html 提取 | {skipped} 已有跳过 | {no_html} 无 cover.html")


if __name__ == "__main__":
    main()
