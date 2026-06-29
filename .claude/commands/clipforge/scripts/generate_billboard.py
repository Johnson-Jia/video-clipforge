#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""generate_billboard.py — 生成 GitHub 每日热门榜单图 HTML（GitHub 星探频道标识 + 暗色风）。

用法:
  python generate_billboard.py --data billboard_data.json --output billboard.html

读 billboard_data.json（含 date/channel/title/subtitle/avatar_path/items），
头像转 base64 内嵌，生成自包含 HTML。再用 Chrome 截图得到 PNG。

billboard_data.json schema:
{
  "date": "2026-06-24",
  "channel": "GitHub 星探",
  "title": "GitHub 今日榜单",
  "subtitle": "热门开源项目",
  "avatar_path": "workspace/covers/科技兔头像.png",   # 相对项目根（clone 友好，禁绝对路径）
  "items": [
    {"rank":1,"name":"owner/repo","lang":"Python","desc":"中文描述","stars":"15,523","today":"+3,590","medal":"gold"}
  ]
}
medal 可选: gold/silver/bronze（前3高亮），其余留空。
"""
import argparse
import base64
import json
import os
import sys

# 项目根 = scripts/ 上 4 级（scripts→clipforge→commands→.claude→项目根）
# 用于把相对 avatar_path 解析为绝对，clone 到任意目录都能工作
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(SCRIPT_DIR))))


CSS = """
* { margin:0; padding:0; box-sizing:border-box; }
body { width:1080px; height:1920px; background:#0d1117; font-family:'Microsoft YaHei','PingFang SC','Segoe UI',sans-serif; color:#c9d1d9; overflow:hidden; }
.wrap { width:1080px; height:1920px; padding:52px 44px 40px; display:flex; flex-direction:column;
  background: radial-gradient(ellipse at 50% 0%, rgba(88,166,255,0.12), transparent 55%), #0d1117; }
.header { display:flex; align-items:center; justify-content:space-between; padding-bottom:26px; border-bottom:1px solid #30363d; }
.brand { display:flex; align-items:center; gap:22px; }
.avatar { width:110px; height:110px; border-radius:50%; border:3px solid #58a6ff; object-fit:cover; box-shadow:0 0 18px rgba(88,166,255,0.45); }
.channel { font-size:28px; color:#58a6ff; font-weight:800; letter-spacing:3px; }
.h-title { font-size:60px; font-weight:800; color:#f0f6fc; letter-spacing:2px; margin-top:4px; }
.h-sub { font-size:26px; color:#8b949e; margin-top:5px; letter-spacing:1px; }
.date-pill { background:rgba(88,166,255,0.15); border:1px solid rgba(88,166,255,0.5); color:#58a6ff;
  padding:14px 26px; border-radius:999px; font-size:30px; font-weight:700; font-family:'Consolas',monospace; }
.list { flex:1; display:flex; flex-direction:column; justify-content:space-between; gap:10px; padding-top:28px; padding-bottom:10px; }
.item { display:flex; align-items:center; gap:20px; background:#161b22; border:1px solid #30363d; border-radius:16px; padding:22px 26px; }
.rank { width:66px; height:66px; flex-shrink:0; border-radius:12px; display:flex; align-items:center; justify-content:center;
  font-size:38px; font-weight:800; font-family:'Consolas',monospace; background:#21262d; color:#8b949e; }
.item.gold .rank { background:linear-gradient(135deg,#ffd700,#ffa500); color:#1a1a00; }
.item.silver .rank { background:linear-gradient(135deg,#e8e8e8,#a8a8a8); color:#1a1a1a; }
.item.bronze .rank { background:linear-gradient(135deg,#e3b341,#b8860b); color:#1a1a00; }
.mid { flex:1; min-width:0; }
.name { font-size:34px; font-weight:700; color:#f0f6fc; font-family:'Consolas','Microsoft YaHei',monospace;
  white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.name .lang { font-size:22px; font-weight:400; color:#8b949e; margin-left:12px; }
.desc { font-size:27px; color:#8b949e; margin-top:6px; line-height:1.3; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.stats { flex-shrink:0; text-align:right; }
.stars { font-size:30px; font-weight:700; color:#e3b341; font-family:'Consolas',monospace; }
.today { font-size:24px; color:#3fb950; font-weight:700; font-family:'Consolas',monospace; margin-top:4px; }
.footer { text-align:center; padding-top:18px; border-top:1px solid #30363d; color:#6e7681; font-size:24px; letter-spacing:1px; }
/* 紧凑布局：items > 12（如周榜 Top 15-20）自动启用，缩小 avatar/padding/字号容纳 20 项；日榜 10 项不受影响 */
.wrap.compact .header { padding-bottom:10px; }
.wrap.compact .avatar { width:76px; height:76px; border-width:2px; box-shadow:0 0 12px rgba(88,166,255,0.4); }
.wrap.compact .channel { font-size:23px; letter-spacing:2px; }
.wrap.compact .h-title { font-size:40px; margin-top:3px; }
.wrap.compact .h-sub { font-size:19px; margin-top:2px; }
.wrap.compact .date-pill { font-size:23px; padding:10px 20px; }
.wrap.compact .list { gap:4px; padding-top:12px; padding-bottom:4px; }
.wrap.compact .item { padding:8px 16px; gap:12px; border-radius:12px; }
.wrap.compact .rank { width:42px; height:42px; font-size:24px; border-radius:9px; }
.wrap.compact .name { font-size:24px; }
.wrap.compact .name .lang { font-size:16px; margin-left:8px; }
.wrap.compact .desc { font-size:18px; margin-top:2px; line-height:1.25; }
.wrap.compact .stars { font-size:22px; }
.wrap.compact .today { font-size:17px; margin-top:1px; }
.wrap.compact .footer { padding-top:8px; font-size:18px; }
"""


def item_html(it):
    medal = it.get("medal", "")
    cls = ("item " + medal).strip()
    return (
        f'<div class="{cls}"><div class="rank">{it["rank"]}</div>'
        f'<div class="mid"><div class="name">{it["name"]}<span class="lang">{it.get("lang","")}</span></div>'
        f'<div class="desc">{it["desc"]}</div></div>'
        f'<div class="stats"><div class="stars">{it["stars"]}&#9733;</div>'
        f'<div class="today">{it["today"]}</div></div></div>'
    )


def render_screenshot(html_path, png_path, width=1080, height=1920, dsf=1):
    """playwright 截图 HTML → PNG。dsf=1 出 1080×1920（手机查看/社交分享最佳），
    dsf=2 出 2160×3840 retina（桌面/打印/高清存档）。"""
    from playwright.sync_api import sync_playwright
    url = "file:///" + os.path.abspath(html_path).replace("\\", "/")
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": width, "height": height}, device_scale_factor=dsf)
        page.goto(url)
        page.wait_for_timeout(1500)
        page.screenshot(path=png_path, full_page=False)
        browser.close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True, help="billboard_data.json 路径")
    ap.add_argument("--output", required=True, help="输出 HTML 路径")
    ap.add_argument("--render", action="store_true", help="生成 HTML 后用 playwright 截图为 PNG")
    ap.add_argument("--png", help="PNG 输出路径（默认 = output 同名 .png）")
    args = ap.parse_args()

    d = json.load(open(args.data, encoding="utf-8"))
    avatar_b64 = ""
    av = d.get("avatar_path")
    if av:
        try:
            if not os.path.isabs(av):
                av = os.path.join(PROJECT_ROOT, av)  # 相对路径 → 相对项目根（clone 友好）
            avatar_b64 = base64.b64encode(open(av, "rb").read()).decode()
        except Exception as e:
            print(f"WARN: 头像读取失败 {e}", file=sys.stderr)

    items = d.get("items", [])
    items_str = "\n".join(item_html(it) for it in items)
    avatar_html = (
        f'<img class="avatar" src="data:image/png;base64,{avatar_b64}">'
        if avatar_b64 else ""
    )
    body = (
        '<div class="wrap' + (' compact' if len(items) > 12 else '') + '">'
        '<div class="header"><div class="brand">'
        f'{avatar_html}<div>'
        f'<div class="channel">{d.get("channel","")}</div>'
        f'<div class="h-title">{d.get("title","")}</div>'
        f'<div class="h-sub">{d.get("subtitle","")}</div>'
        '</div></div>'
        f'<div class="date-pill">{d.get("date","")}</div>'
        '</div>'
        f'<div class="list">{items_str}</div>'
        f'<div class="footer">按涨星排序 · Top {len(items)}</div>'
        '</div>'
    )
    html = (
        '<!DOCTYPE html><html lang="zh"><head><meta charset="utf-8">'
        f"<style>{CSS}</style></head><body>{body}</body></html>"
    )
    open(args.output, "w", encoding="utf-8").write(html)
    print(f"HTML 已生成: {args.output} ({len(items)} 项, 头像={'有' if avatar_b64 else '无'})")
    if args.render:
        png_path = args.png or os.path.splitext(args.output)[0] + ".png"
        render_screenshot(args.output, png_path)
        print(f"PNG 已截图: {png_path}")


if __name__ == "__main__":
    main()
