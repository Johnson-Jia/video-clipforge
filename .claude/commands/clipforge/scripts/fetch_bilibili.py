#!/usr/bin/env python3
"""B站视频数据自动拉取 —— 调创作中心接口拿全量稿件数据,产出 CSV。

绕过创作中心前端"每次10条"限制:接口A 翻页拿全量 bvid+基础字段,
接口B 按 bvid 分批拿深度字段,合并后复刻 parse_bilibili_csv 列结构。

用法:
  python fetch_bilibili.py --self-test     # 纯函数自测(用 testdata fixture,不需 cookie)
  python fetch_bilibili.py --dry-run       # 调真实接口,打印,不写文件(需 cookie)
  python fetch_bilibili.py                 # 全量拉取并写出 CSV(需 cookie)

cookie: 完整 Cookie 字符串存 workspace/sources/视频数据/.bili-cookie(gitignore)。
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib import request as urlrequest
from urllib.error import HTTPError, URLError

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

SCRIPT_DIR = Path(__file__).resolve().parent
TESTDATA = SCRIPT_DIR / "testdata"
sys.path.insert(0, str(SCRIPT_DIR.parent))  # clipforge（engine.lib.data_paths）
from engine.lib.data_paths import VIDEO_DATA_DIR as DATA_DIR  # 四级回退(env>git>config>cwd)
COOKIE_FILE = DATA_DIR / ".bili-cookie"

REFERER = "https://member.bilibili.com/york/data-center-web/dataCenter/video?tmid=&bvid=&tab="
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36")
CST = timezone(timedelta(hours=8))


# ── 数值解析(容错:str/int/空) ──────────────────────────────────────────────────

def _num(v, default: int = 0) -> int:
    """'4'/4/''/None -> int。用于绝对值(播放/点赞/评论...)。"""
    if v in (None, "", "-", "--"):
        return default
    try:
        return int(float(str(v).strip().replace(",", "")))
    except (ValueError, TypeError):
        return default


def _ratio(v, div: float = 10000.0):
    """4420 -> 0.442(÷10000)。空/0/未就绪 -> None。用于率字段。"""
    if v in (None, "", "-", "--", 0):
        return None
    try:
        return round(float(v) / div, 6)
    except (ValueError, TypeError):
        return None


def _ts_to_date(ts) -> str:
    """时间戳 -> 'YYYY年MM月DD日'(东八区)。None/0 -> ''。"""
    if not ts:
        return ""
    try:
        return datetime.fromtimestamp(int(ts), CST).strftime("%Y年%m月%d日")
    except (ValueError, TypeError, OSError):
        return ""


# ── 解析 ───────────────────────────────────────────────────────────────────────

def parse_index_page(data: dict) -> list[dict]:
    """archive/index 一页 -> [{bvid,title,pubtime,plays,likes,comments,
    followers_gained,completion_rate}]。优先 real_stat(新稿件 stat 为 null)。"""
    out = []
    for x in (data.get("data") or {}).get("list") or []:
        st = x.get("real_stat") or x.get("stat") or {}
        out.append({
            "bvid": x.get("bvid", ""),
            "title": x.get("title", ""),
            "pubtime": _ts_to_date(x.get("pubtime")),
            "plays": _num(st.get("play")),
            "likes": _num(st.get("likes")),
            "comments": _num(st.get("reply")),
            "followers_gained": _num(st.get("fans")),
            "avg_play_progress": _ratio(st.get("full_play_ratio")),
        })
    return out


# 接口B stat 绝对值字段: api键 -> record键
_ABS_KEYS = {
    "like": "likes", "comment": "comments", "dm": "danmaku",
    "fav": "saves", "coin": "coins", "share": "shares",
    "total_new_attention_cnt": "followers_gained",
}
# 接口B stat 率字段(÷10000): api键 -> record键
_RATE_KEYS = {
    "crash_rate": "bounce_3s_rate", "interact_rate": "interaction_rate",
    "play_viewer_rate": "visitor_play_ratio", "full_play_ratio": "avg_play_progress",
}


def parse_compare_page(data: dict) -> dict[str, dict]:
    """archive_diagnose/compare 一批 -> {bvid: {深度字段}}。
    跳过 stat.not_ready_field 列出的未就绪字段。"""
    out = {}
    for x in (data.get("data") or {}).get("list") or []:
        bvid = x.get("bvid", "")
        st = x.get("stat") or {}
        not_ready = set(st.get("not_ready_field") or [])
        rec = {}
        for src, dst in _ABS_KEYS.items():
            rec[dst] = None if src in not_ready else _num(st.get(src))
        for src, dst in _RATE_KEYS.items():
            rec[dst] = None if src in not_ready else _ratio(st.get(src))
        out[bvid] = rec
    return out


def merge(index_items: list[dict], compare_stats: dict) -> list[dict]:
    """合并:index 给基础+元数据,compare 深度字段(就绪,非None)覆盖。"""
    merged = []
    for it in index_items:
        rec = dict(it)
        for k, v in (compare_stats.get(it["bvid"]) or {}).items():
            if v is not None:
                rec[k] = v
        merged.append(rec)
    return merged


# CSV 列索引(对齐 collect_performance.py 的 parse_bilibili_csv): 索引 -> record键
CSV_COLS = {
    0: "title", 1: "pubtime", 2: "plays", 3: "visitor_play_ratio",
    8: "bounce_3s_rate", 11: "interaction_rate", 14: "followers_gained",
    17: "likes", 19: "comments", 21: "danmaku", 23: "saves",
    25: "coins", 27: "shares", 29: "avg_play_progress",
}
CSV_WIDTH = 30


def to_csv_row(rec: dict) -> list[str]:
    """record -> 30 列 CSV 行(关键列按 CSV_COLS 索引,其余空)。"""
    row = [""] * CSV_WIDTH
    for idx, key in CSV_COLS.items():
        v = rec.get(key)
        row[idx] = "" if v is None else str(v)
    return row


def chunk(seq: list, n: int) -> list[list]:
    return [seq[i:i + n] for i in range(0, len(seq), n)]


def total_pages(total: int, ps: int) -> int:
    return max(1, (total + ps - 1) // ps)


# ── HTTP ───────────────────────────────────────────────────────────────────────

class AuthError(Exception):
    """cookie 过期/未登录(code -101)。"""


def _api_get(url: str, cookie: str, timeout: int = 15) -> dict:
    req = urlrequest.Request(url, headers={
        "User-Agent": UA, "Referer": REFERER, "Cookie": cookie,
        "Accept": "application/json, text/plain, */*",
    })
    last_err = None
    for attempt in range(3):
        try:
            with urlrequest.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            if data.get("code") == -101:
                raise AuthError("cookie 过期或未登录(code -101),请重新复制完整 Cookie 到 "
                                f"{COOKIE_FILE}")
            return data
        except AuthError:
            raise
        except (HTTPError, URLError, TimeoutError) as e:
            last_err = e
            time.sleep(0.5 * (attempt + 1))
    raise RuntimeError(f"请求失败(重试3次): {url} -> {last_err}")


def fetch_index_page(cookie: str, pn: int, ps: int = 20) -> dict:
    return _api_get(
        "https://member.bilibili.com/x/web/data/archive/index"
        f"?pn={pn}&ps={ps}&scene=archive_compare&order=0&tmid=", cookie)


def fetch_compare(cookie: str, bvids: list[str]) -> dict:
    return _api_get(
        "https://member.bilibili.com/x/web/data/archive_diagnose/compare"
        f"?compare_bvids={','.join(bvids)}&size=10&tmid=", cookie)


def read_cookie() -> str:
    if not COOKIE_FILE.exists():
        raise SystemExit(
            f"未找到 cookie 文件 {COOKIE_FILE}\n"
            "获取:浏览器登录 B站 → DevTools → Network → 任一 member.bilibili.com/x/ 请求 → "
            "复制完整 Cookie 请求头 → 整段粘贴到该文件。")
    cookie = COOKIE_FILE.read_text(encoding="utf-8").strip()
    if not cookie:
        raise SystemExit(f"cookie 文件为空: {COOKIE_FILE}")
    return cookie


# ── 主流程 ─────────────────────────────────────────────────────────────────────

def run(cookie: str) -> list[dict]:
    """全量拉取:接口A 翻页拿 bvid+基础 → 接口B 分批拿深度 → 合并。"""
    all_items, pn = [], 1
    while True:
        page = fetch_index_page(cookie, pn)
        items = parse_index_page(page)
        all_items.extend(items)
        total = (page.get("data") or {}).get("pager", {}).get("total", 0)
        pages = total_pages(total, 20)
        print(f"[A] pn={pn}/{pages} +{len(items)} (total={total})")
        if pn >= pages or not items:
            break
        pn += 1
        time.sleep(0.5)

    bvids = [x["bvid"] for x in all_items if x["bvid"]]
    batches = chunk(bvids, 10)
    compare_stats: dict = {}
    for i, batch in enumerate(batches, 1):
        cmp = fetch_compare(cookie, batch)
        compare_stats.update(parse_compare_page(cmp))
        print(f"[B] batch {i}/{len(batches)} +{len(batch)} bvids")
        time.sleep(0.5)

    return merge(all_items, compare_stats)


def write_csv(records: list[dict], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        for rec in records:
            w.writerow(to_csv_row(rec))


def _self_test() -> None:
    idx = json.loads((TESTDATA / "bili_index_p1.json").read_text(encoding="utf-8"))
    cmp = json.loads((TESTDATA / "bili_compare.json").read_text(encoding="utf-8"))
    items = parse_index_page(idx)
    stats = parse_compare_page(cmp)
    recs = merge(items, stats)

    # index: real_stat 优先(stat:null 用 real_stat;stat 有值时 real_stat 覆盖)
    assert len(items) == 3
    assert items[0]["bvid"] == "BV11Rju65EAs"
    assert items[0]["plays"] == 291, f"real_stat play 期望 291, 实际 {items[0]['plays']}"
    assert items[1]["plays"] == 916, f"real_stat 应覆盖 stat(511), 实际 {items[1]['plays']}"
    assert abs(items[1]["avg_play_progress"] - 0.442) < 1e-9, "full_play_ratio ÷10000"
    assert items[0]["avg_play_progress"] is None, "空 full_play_ratio -> None"
    assert items[1]["pubtime"].startswith("2026年"), f"pubtime 格式: {items[1]['pubtime']}"

    # compare: 全就绪稿件(第2条)
    s2 = stats["BV1sCJg6pEKA"]
    assert s2["likes"] == 21 and s2["comments"] == 3 and s2["saves"] == 44
    assert s2["coins"] == 2 and s2["shares"] == 5 and s2["danmaku"] == 0
    assert s2["followers_gained"] == 4, "total_new_attention_cnt"
    assert abs(s2["bounce_3s_rate"] - 0.3566) < 1e-9, "crash_rate 3566 ÷10000"
    assert abs(s2["visitor_play_ratio"] - 0.4649) < 1e-9, "play_viewer_rate 4649"
    # compare: not_ready 稿件(第1条)率字段为 None,绝对值就绪
    s1 = stats["BV11Rju65EAs"]
    assert s1["bounce_3s_rate"] is None, "crash_rate 在 not_ready_field"
    assert s1["avg_play_progress"] is None, "full_play_ratio 在 not_ready_field"
    assert s1["likes"] == 13, "like 不在 not_ready -> 就绪"

    # merge: compare 就绪字段覆盖 index
    r1 = next(r for r in recs if r["bvid"] == "BV1sCJg6pEKA")
    assert r1["likes"] == 21, "compare likes 覆盖 index"
    assert r1["saves"] == 44, "深度字段来自 compare"

    # CSV
    row = to_csv_row(recs[1])
    assert len(row) == 30, f"CSV 列数 30, 实际 {len(row)}"
    assert row[0] == recs[1]["title"], "col0 title"
    assert row[2] == "916", f"col2 plays, 实际 {row[2]}"
    assert row[17] == "21", f"col17 likes, 实际 {row[17]}"

    assert chunk([1, 2, 3, 4, 5], 2) == [[1, 2], [3, 4], [5]]
    assert total_pages(72, 20) == 4
    assert total_pages(0, 20) == 1

    print(f"self-test OK: {len(items)} items, csv 30 cols, "
          f"sample bvid={items[0]['bvid']} plays={items[0]['plays']}")


def main():
    ap = argparse.ArgumentParser(description="B站视频数据自动拉取")
    ap.add_argument("--self-test", action="store_true", help="纯函数自测(不需 cookie)")
    ap.add_argument("--dry-run", action="store_true", help="调真实接口,打印,不写文件")
    args = ap.parse_args()

    if args.self_test:
        _self_test()
        return

    cookie = read_cookie()
    records = run(cookie)
    print(f"\n共 {len(records)} 条稿件")

    if args.dry_run:
        for r in records[:3]:
            print(f"  {r['bvid']} plays={r['plays']} likes={r.get('likes')} "
                  f"completion={r.get('completion_rate')} saves={r.get('saves')}")
        return

    today = datetime.now(CST).strftime("%Y-%m-%d")
    out = DATA_DIR / today / "哔哩哔哩近期稿件对比.csv"
    write_csv(records, out)
    print(f"写出: {out}")
    print("下一步: /evolve-daily 或 /clipforge-feedback")


if __name__ == "__main__":
    main()
