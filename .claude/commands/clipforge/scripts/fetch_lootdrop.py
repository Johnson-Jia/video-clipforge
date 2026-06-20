#!/usr/bin/env python3
"""loot-drop.io 失败案例抓取 — 创业淘金者数据源。

从 sitemap.xml 拿案例 URL 清单（robots Allow /），requests 抓详情页(SSR)，
lootdrop_parser 解析完整字段。中国公司优先（首批起步，infer_region 筛选）。

用法:
  python scripts/fetch_lootdrop.py --output-dir workspace/.../ --region 中国 --limit 3
"""
from __future__ import annotations
import argparse
import json
import re
import sys
from pathlib import Path

import requests

SCRIPT_DIR = Path(__file__).resolve().parent
CLIPFORGE_DIR = SCRIPT_DIR.parent
sys.path.insert(0, str(CLIPFORGE_DIR))
from scripts.lootdrop_parser import parse_failure_detail  # noqa: E402

BASE = "https://www.loot-drop.io"
SITEMAP = f"{BASE}/sitemap.xml"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; ClipForge-lootdrop/1.0)"}


def fetch_sitemap_urls(scan_limit=80):
    """从 sitemap.xml 拿 /startup/ URL 清单（最新在前，id 递减）。"""
    resp = requests.get(SITEMAP, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    paths = re.findall(r"(/startup/\d+-[a-z0-9-]+)", resp.text)
    seen, urls = set(), []
    for p in paths:
        if p not in seen:
            seen.add(p)
            urls.append(f"{BASE}{p}")
    return urls[:scan_limit]


def fetch_detail(url):
    """抓单个详情页(SSR) → parse_failure_detail。失败返回 None。"""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=30)
        resp.raise_for_status()
        return parse_failure_detail(resp.text, url=url)
    except Exception as e:
        print(f"  [!] 抓取失败 {url}: {e}")
        return None


def select_cases(urls, region=None, limit=5):
    """扫 sitemap URL 抓详情，按地区筛选选 limit 个。"""
    selected = []
    scanned = 0
    for url in urls:
        if len(selected) >= limit:
            break
        scanned += 1
        d = fetch_detail(url)
        if not d or not d["name"]:
            continue
        if region and d["region"] != region:
            continue
        selected.append(d)
        print(f"  [+] {d['name']} | {d['region']} | {d['funding']} | "
              f"related={len(d['related'])}")
    print(f"  扫描 {scanned} 个详情页，选中 {len(selected)} 个"
          f"{f'（{region}）' if region else ''}")
    return selected


def main():
    ap = argparse.ArgumentParser(description="loot-drop.io 失败案例抓取")
    ap.add_argument("--output-dir", required=True)
    ap.add_argument("--region", default=None,
                    help="筛选地区（中国/美国/印度/欧洲）。默认全部")
    ap.add_argument("--limit", type=int, default=3, help="选中案例数")
    ap.add_argument("--scan-limit", type=int, default=80,
                    help="sitemap 扫描上限（地区筛选时遍历）")
    args = ap.parse_args()

    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)

    print("=== fetch sitemap ===")
    urls = fetch_sitemap_urls(scan_limit=args.scan_limit)
    print(f"  sitemap 案例 URL: {len(urls)}")

    region = args.region if args.region and args.region != "全部" else None
    print(f"=== 抓取详情（region={region or '全部'}, limit={args.limit}）===")
    cases = select_cases(urls, region=region, limit=args.limit)

    out_file = out / "raw_failures.json"
    out_file.write_text(json.dumps({
        "source": "loot-drop.io",
        "region_filter": region or "全部",
        "case_count": len(cases),
        "cases": cases,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"写出: {out_file} ({len(cases)} 案例)")


if __name__ == "__main__":
    main()
