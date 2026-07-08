#!/usr/bin/env python3
"""goldminer 历史扫描 — 防重复跑相同企业。

扫描 workspace/**/goldminer/content_ready.txt，提取每期主角企业 + 行业，
聚合到 workspace/evolution/goldminer_done.json。selection 前必跑，避开已做企业。

用法:
  python scripts/goldminer_history.py                              # 扫描 + 写 done.json + 摘要
  python scripts/goldminer_history.py --report                      # 打印历史摘要 + 重复检测
  python scripts/goldminer_history.py --check "Magic Ears"          # 查某企业是否做过（exit 0=做过 / 1=没做过）
  python scripts/goldminer_history.py --filter-candidates RAW.json  # 过滤候选 raw_failures.json，输出未做过清单
"""
from __future__ import annotations
import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")  # Windows GBK 终端中文兜底
except Exception:
    pass

SCRIPT_DIR = Path(__file__).resolve().parent
CLIPFORGE_DIR = SCRIPT_DIR.parent
sys.path.insert(0, str(CLIPFORGE_DIR))
from engine.lib.data_paths import WORKSPACE_ROOT  # noqa: E402

WS = WORKSPACE_ROOT / "workspace"
DONE_FILE = WORKSPACE_ROOT / "workspace" / "evolution" / "goldminer_done.json"


def normalize_keys(name: str) -> set[str]:
    """企业名 → 标准化 key 集合（中文 key + 英文 key），用于跨语言别名匹配。

    覆盖同一企业中英文名互匹配（根因：学吧100/Xueba100 漏匹配事故）：
      "魔力耳朵 Magic Ears" -> {"魔力耳朵", "magicears"}
      "学吧100（Xueba100）" -> {"学吧100", "100xueba100"}
      "Xueba100"           -> {"xueba100"}  # 与上面 "100xueba100" 互包含 → 匹配
    """
    n = (name or "").split("|")[0].strip()
    n = re.sub(r"[（(].*?[)）]", " ", n)  # 括号转空格，保留英文别名
    keys = set()
    cn = re.sub(r"[A-Za-z\s\-.]+", "", n).strip()  # 中文 + 数字
    en = re.sub(r"[一-鿿（）()\s\-.]+", "", n).strip().lower()  # 英文 + 数字
    if cn:
        keys.add(cn)
    if en:
        keys.add(en)
    if not keys:
        keys.add(n.lower().strip())
    return keys


def keys_match(a: set[str], b: set[str]) -> bool:
    """两个 key 集合是否有任一元素互相包含（覆盖中英文别名 + 简写）。"""
    for x in a:
        for y in b:
            if x and y and (x in y or y in x):
                return True
    return False


def parse_episodes() -> list[dict]:
    """扫描所有 goldminer content_ready.txt → episode 列表（按日期升序）。"""
    episodes = []
    for cr in sorted(WS.glob("**/goldminer/content_ready.txt")):
        parts = cr.parts
        try:
            idx = parts.index("workspace")
            date = f"{parts[idx+1]}-{parts[idx+2]}-{parts[idx+3]}"
        except (ValueError, IndexError):
            continue
        try:
            txt = cr.read_text(encoding="utf-8")
        except Exception:
            continue
        m = re.search(r"【主角】([^\n]+)", txt)
        if not m:
            continue
        fields = [f.strip() for f in m.group(1).split("|")]
        company_raw = fields[0] if fields else "?"
        episodes.append({
            "date": date,
            "company": company_raw,
            "company_keys": normalize_keys(company_raw),
            "region": fields[1] if len(fields) > 1 else "",
            "funding": fields[2] if len(fields) > 2 else "",
            "industry": fields[3] if len(fields) > 3 else "",
            "industry_key": next(iter(normalize_keys(fields[3])), "") if len(fields) > 3 else "",
        })
    return episodes


def fuzzy_match(name: str, episodes: list[dict]) -> list[dict]:
    """企业名模糊匹配历史（key 集合任一互包含）。"""
    cand = normalize_keys(name)
    return [ep for ep in episodes if keys_match(cand, ep["company_keys"])]


def build_done_data(episodes: list[dict]) -> dict:
    companies = defaultdict(list)
    industries = defaultdict(list)
    for ep in episodes:
        primary = next(iter(ep["company_keys"]), ep["company"])
        companies[primary].append({"date": ep["date"], "company": ep["company"]})
        if ep["industry_key"]:
            industries[ep["industry_key"]].append(
                {"date": ep["date"], "company": ep["company"], "industry": ep["industry"]}
            )
    return {
        "scan_date": datetime.now().strftime("%Y-%m-%d"),
        "total_episodes": len(episodes),
        "episodes": [{k: (sorted(v) if k == "company_keys" else v) for k, v in ep.items()} for ep in episodes],
        "companies_done": dict(companies),
        "industries_done": dict(industries),
    }


def cmd_report(episodes: list[dict]) -> None:
    print(f"goldminer 历史 ({len(episodes)} 期)")
    print("=" * 70)
    for ep in episodes:
        print(f"  {ep['date']} | {ep['company'][:26]:28} | {ep['industry'][:22]}")
    print("=" * 70)
    # 重复企业：两两 key 集合匹配
    dups = []
    for i, a in enumerate(episodes):
        for b in episodes[i + 1:]:
            if keys_match(a["company_keys"], b["company_keys"]):
                dups.append((a, b))
    if dups:
        print("[!] 重复企业:")
        for a, b in dups:
            print(f"    {a['company'][:20]} ({a['date']}) == {b['company'][:20]} ({b['date']})")
    ind_cnt = Counter([e["industry_key"] for e in episodes if e["industry_key"]])
    multi = {k: v for k, v in ind_cnt.items() if v > 1}
    if multi:
        print("[!] 同行业多做:")
        for k, cnt in multi.items():
            eps = [e for e in episodes if e["industry_key"] == k]
            print(f"    {eps[0]['industry'][:18]} x{cnt}: {[e['date']+'/'+e['company'][:10] for e in eps]}")


def cmd_check(name: str, episodes: list[dict]) -> int:
    matches = fuzzy_match(name, episodes)
    if matches:
        print(f"[DONE] '{name}' 已做过 {len(matches)} 次:")
        for m in matches:
            print(f"    {m['date']} | {m['company']} | {m['industry']}")
        return 0  # 做过
    print(f"[FRESH] '{name}' 未做过 (keys={sorted(normalize_keys(name))})")
    return 1  # 没做过


def cmd_filter(raw_file: str, episodes: list[dict]) -> tuple[list, list]:
    data = json.loads(Path(raw_file).read_text(encoding="utf-8"))
    cases = data.get("cases", [])
    fresh, dup = [], []
    for c in cases:
        matches = fuzzy_match(c.get("name", ""), episodes)
        if matches:
            dup.append({"name": c["name"], "done_date": matches[0]["date"], "funding": c.get("funding")})
        else:
            fresh.append(c)
    print(f"候选 {len(cases)} 个: 未做过 {len(fresh)} / 已做过 {len(dup)}")
    if dup:
        print("[已做过] 不可选:")
        for d in dup:
            print(f"    {d['name']} ({d['funding']}) -> {d['done_date']}")
    if fresh:
        print("[未做过] 可选:")
        for c in fresh:
            fa = (c.get("failure_analysis") or "")[:60]
            print(f"    {c['name']} | {c.get('region')} | {c.get('funding')} | {fa}")
    return fresh, dup


def main():
    ap = argparse.ArgumentParser(description="goldminer 历史扫描防重复")
    ap.add_argument("--report", action="store_true", help="打印历史摘要 + 重复检测")
    ap.add_argument("--check", help="查某企业是否做过（exit 0=做过 / 1=没做过）")
    ap.add_argument("--filter-candidates", help="过滤候选 raw_failures.json，输出未做过清单")
    args = ap.parse_args()

    episodes = parse_episodes()

    if args.check:
        sys.exit(cmd_check(args.check, episodes))
    if args.filter_candidates:
        cmd_filter(args.filter_candidates, episodes)
        return
    if args.report:
        cmd_report(episodes)
        return

    data = build_done_data(episodes)
    DONE_FILE.parent.mkdir(parents=True, exist_ok=True)
    DONE_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"写出: {DONE_FILE} ({len(episodes)} 期)")
    cmd_report(episodes)


if __name__ == "__main__":
    main()
