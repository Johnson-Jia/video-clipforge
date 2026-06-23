#!/usr/bin/env python3
"""bg 组件库自检：visual_types 声明 vs 分类器正则识别一致性。

防止组件库新增/修改组件后，@ComponentMeta 的 visual_types 声明与 gate 分类器
正则识别漂移（2026-06-23 diamond_lattice 误判为 glow+grid 三件套事故根因）。

用法：
  python check_bg_components.py --check   # 报告漂移（声明 vs 正则不一致的组件），不一致 exit 1
  python check_bg_components.py --fix     # 根据正则识别更新 visual_types 声明
"""
import argparse
import re
import pathlib
import sys

CF = pathlib.Path(__file__).resolve().parent.parent  # clipforge 技能目录
sys.path.insert(0, str(CF / "engine"))
from gate import _classify_bg_element_types  # noqa: E402

BG_DIR = CF / "components" / "bg"


def get_dom_types(html: str) -> set[str]:
    """提取组件 DOM（bg-component 标记后、去注释）跑正则分类器。"""
    m = re.search(r"bg-component:\s*\S+\s*-->(.*)", html, re.DOTALL)
    dom = re.sub(r"<!--.*?-->", "", m.group(1) if m else html, flags=re.DOTALL)
    return _classify_bg_element_types(dom)


def get_declared_types(html: str) -> list[str]:
    """读 @ComponentMeta 的 visual_types 声明。"""
    meta = re.search(r"@ComponentMeta\b.*?/ComponentMeta", html, re.DOTALL)
    if not meta:
        return []
    vt = re.search(r"visual_types:\s*\[([^\]]*)\]", meta.group(0))
    if not vt:
        return []
    return [t.strip() for t in vt.group(1).split(",") if t.strip()]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true", help="报告漂移")
    ap.add_argument("--fix", action="store_true", help="按正则识别更新声明")
    args = ap.parse_args()
    if not args.check and not args.fix:
        args.check = True

    drift: list[tuple[str, list[str], list[str]]] = []
    files = sorted(BG_DIR.glob("*.html"))
    for f in files:
        html = f.read_text(encoding="utf-8")
        dom_types = get_dom_types(html)
        declared = get_declared_types(html)
        name = f.stem
        if args.fix:
            if dom_types and set(declared) != dom_types:
                vt_line = f"visual_types: [{', '.join(sorted(dom_types))}]"
                if declared:
                    html = re.sub(r"visual_types:\s*\[[^\]]*\]", vt_line, html)
                else:
                    html = re.sub(r"(\n/ComponentMeta)", f"\n{vt_line}\\1", html, count=1)
                f.write_text(html, encoding="utf-8")
                print(f"FIXED {name:20s} → {sorted(dom_types)}")
            else:
                print(f"OK    {name:20s} → {sorted(dom_types)}")
        if set(declared) != dom_types:
            drift.append((name, declared, sorted(dom_types)))

    if args.check:
        if drift:
            print(f"\n⚠️ {len(drift)} 个组件 visual_types 声明与正则识别不一致：")
            for name, declared, domt in drift:
                print(f"  {name}: 声明={declared} vs 正则={domt}")
            sys.exit(1)
        print(f"\n✅ {len(files)} 个组件 visual_types 声明与正则一致")


if __name__ == "__main__":
    main()
