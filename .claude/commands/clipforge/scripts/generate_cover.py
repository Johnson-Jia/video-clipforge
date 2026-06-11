"""封面生成脚本 — 从 cover_params.json + Jinja2 模板生成 cover.html

LLM 只需提供内容参数 + 3 个核心色值（accent_warm / accent_cool / bg_dark），
脚本自动派生完整调色板（soft / rgb / mid / bottom 等），填充模板生成 HTML。

用法:
  python scripts/generate_cover.py --project-dir workspace/2026/06/04/github-trending/
  python scripts/generate_cover.py --project-dir ... --render  # 同时渲染 cover.png
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def hex_to_rgb(hex_color: str) -> str:
    hex_color = hex_color.lstrip("#")
    if len(hex_color) != 6:
        raise ValueError(f"Invalid hex color: #{hex_color}")
    r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
    return f"{r},{g},{b}"


def lighten(hex_color: str, factor: float = 0.2) -> str:
    hex_color = hex_color.lstrip("#")
    r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
    r = min(255, int(r + (255 - r) * factor))
    g = min(255, int(g + (255 - g) * factor))
    b = min(255, int(b + (255 - b) * factor))
    return f"#{r:02X}{g:02X}{b:02X}"


def darken(hex_color: str, factor: float = 0.15) -> str:
    hex_color = hex_color.lstrip("#")
    r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
    r = max(0, int(r * (1 - factor)))
    g = max(0, int(g * (1 - factor)))
    b = max(0, int(b * (1 - factor)))
    return f"#{r:02X}{g:02X}{b:02X}"


DEFAULT_COLORS = {
    "accent_warm": "#FF8C32",
    "accent_cool": "#6CB4EE",
    "bg_dark": "#080820",
    "glow_warm_opacity": "0.18",
    "glow_cool_opacity": "0.10",
}


def derive_palette(user_colors: dict) -> dict:
    colors = {**DEFAULT_COLORS, **user_colors}

    accent_warm = colors["accent_warm"]
    accent_cool = colors["accent_cool"]
    bg_dark = colors["bg_dark"]

    colors.setdefault("accent_warm_soft", lighten(accent_warm, 0.2))
    colors.setdefault("accent_warm_rgb", hex_to_rgb(accent_warm))
    colors.setdefault("accent_cool_soft", lighten(accent_cool, 0.15))
    colors.setdefault("accent_cool_rgb", hex_to_rgb(accent_cool))
    colors.setdefault("bg_mid", darken(lighten(bg_dark, 0.08), 0.05))
    colors.setdefault("bg_bottom", darken(bg_dark, 0.1))
    colors.setdefault("text_white", "#FFFFFF")
    colors.setdefault("text_muted", "#8899BB")
    colors.setdefault("card_bg", "rgba(20,20,50,0.85)")

    return colors


def _validate_seg(seg: dict, path: str, errors: list[str]) -> None:
    """Validate a single title segment dict."""
    if not isinstance(seg, dict) or "text" not in seg or "style" not in seg:
        errors.append(f"{path} needs 'text' and 'style' fields")
    elif seg["style"] not in ("white", "accent", "cool"):
        errors.append(f"{path}.style must be 'white', 'accent', or 'cool', got '{seg['style']}'")


def normalize_title(title: list) -> list:
    """Normalize title to nested format: [[seg, ...], [seg, ...]].

    Accepts two formats:
      New (nested):  [[{"text":"A","style":"white"}], [{"text":"B","style":"accent"},{"text":"C","style":"cool"}]]
      Old (flat):     [{"text":"A","style":"white"}, {"text":"B","style":"accent"}]

    Old format auto-wraps each segment into its own line (backward compatible).
    """
    if not title:
        return title
    # Detect old format: first element is a dict (not a list)
    if isinstance(title[0], dict):
        return [[seg] for seg in title]
    return title


def validate_params(params: dict) -> list[str]:
    errors = []
    if "date" not in params:
        errors.append("missing 'date' (e.g. '2026年6月4日')")
    if "title" not in params or not params["title"]:
        errors.append("missing 'title' array")
    else:
        for i, item in enumerate(params["title"]):
            if isinstance(item, list):
                # New nested format: line of segments
                for j, seg in enumerate(item):
                    _validate_seg(seg, f"title[{i}][{j}]", errors)
            elif isinstance(item, dict):
                # Old flat format: single segment
                _validate_seg(item, f"title[{i}]", errors)
            else:
                errors.append(f"title[{i}] must be a dict or list of dicts")
    if "cards" not in params or not params["cards"]:
        errors.append("missing 'cards' array (1-3 cards)")
    elif len(params["cards"]) > 3:
        errors.append(f"too many cards: {len(params['cards'])} (max 3)")
    for i, card in enumerate(params.get("cards", [])):
        if "num" not in card or "label" not in card:
            errors.append(f"cards[{i}] needs 'num' and 'label' fields")
    return errors


def render_cover_png(cover_html: Path, output_png: Path, orientation: str) -> bool:
    import platform
    npx_cmd = "npx.cmd" if platform.system() == "Windows" else "npx"
    tmpdir = tempfile.mkdtemp(prefix="cover-render-")
    try:
        shutil.copy(cover_html, Path(tmpdir) / "index.html")
        result = subprocess.run(
            [npx_cmd, "hyperframes", "render", ".", "--output", "cover_temp.mp4", "--video-bitrate", "5M"],
            cwd=tmpdir, capture_output=True, encoding="utf-8", errors="replace", timeout=120,
        )
        if result.returncode != 0:
            print(f"HyperFrames render failed: {result.stderr[-500:]}", file=sys.stderr)
            return False

        scale = "1080:1920" if orientation == "portrait" else "1920:1080"
        subprocess.run([
            "ffmpeg", "-y", "-i", f"{tmpdir}/cover_temp.mp4",
            "-vf", f"select=eq(n\\,0),scale={scale}:flags=lanczos",
            "-vframes", "1", "-update", "1", str(output_png),
        ], capture_output=True, encoding="utf-8", errors="replace", timeout=30)
        return output_png.exists()
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def main():
    parser = argparse.ArgumentParser(description="Generate cover.html from params + template")
    parser.add_argument("--project-dir", required=True, help="Project directory path")
    parser.add_argument("--params-file", default="cover_params.json", help="Params JSON filename (relative to project-dir)")
    parser.add_argument("--render", action="store_true", help="Also render cover.png via HyperFrames")
    args = parser.parse_args()

    project_dir = Path(args.project_dir)
    params_file = project_dir / args.params_file

    if not params_file.exists():
        print(f"ERROR: {params_file} not found. Create cover_params.json first.", file=sys.stderr)
        sys.exit(1)

    with open(params_file, encoding="utf-8") as f:
        params = json.load(f)

    errors = validate_params(params)
    if errors:
        print("ERROR: Invalid params:", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        sys.exit(1)

    colors = derive_palette(params.get("colors", {}))
    params["colors"] = colors

    # Normalize title to nested format (old flat format → each seg = own line)
    params["title"] = normalize_title(params.get("title", []))
    params.setdefault("orientation", "portrait")
    params.setdefault("scene_label", "")
    params.setdefault("badge", "")
    params.setdefault("data_subtitle", "")

    orientation = params["orientation"]
    if orientation not in ("portrait", "landscape"):
        print(f"ERROR: Invalid orientation '{orientation}', must be 'portrait' or 'landscape'", file=sys.stderr)
        sys.exit(1)

    try:
        from jinja2 import Environment, FileSystemLoader
    except ImportError:
        print("ERROR: jinja2 not installed. Run: pip install jinja2", file=sys.stderr)
        sys.exit(1)

    template_dir = Path(__file__).parent / "templates"
    env = Environment(loader=FileSystemLoader(str(template_dir)))
    template_name = f"cover-{orientation}.html.j2"
    template = env.get_template(template_name)

    html = template.render(**params)

    output = project_dir / "cover.html"
    output.write_text(html, encoding="utf-8")
    print(f"cover.html generated ({orientation}, {len(params['cards'])} cards)")

    if args.render:
        cover_png = project_dir / "cover.png"
        if render_cover_png(output, cover_png, orientation):
            print(f"cover.png rendered ({cover_png.stat().st_size // 1024} KB)")
        else:
            print("WARNING: cover.png render failed, render manually", file=sys.stderr)


if __name__ == "__main__":
    main()
