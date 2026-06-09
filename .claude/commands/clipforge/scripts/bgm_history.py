#!/usr/bin/env python3
"""
BGM 使用历史查询与记录

用法:
  # 查询最近 N 天用过的 BGM（逗号分隔输出）
  python scripts/bgm_history.py --recent 5

  # 记录一条使用记录
  python scripts/bgm_history.py --record --bgm "bold-energetic-3.mp3" --project "github-trending"

  # 检查某首 BGM 是否可用（最近 N 天未使用）
  python scripts/bgm_history.py --check "bold-energetic-3.mp3" --recent 5
"""
import json
import os
import sys
from datetime import datetime, timedelta

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CLIPFORGE_DIR = os.path.join(SCRIPT_DIR, "..")
LOG_PATH = os.path.normpath(os.path.join(CLIPFORGE_DIR, "..", "..", "..", "workspace", "bgm", "usage_log.json"))


def _normalize(p):
    return os.path.abspath(p)


def load_log():
    p = _normalize(LOG_PATH)
    if os.path.exists(p):
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save_log(data):
    p = _normalize(LOG_PATH)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def recent_used(days=5):
    """返回最近 N 天用过的 BGM 文件名集合"""
    log = load_log()
    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    return {entry["bgm"] for entry in log if entry.get("date", "") >= cutoff}


def record(bgm_file, project):
    """记录一条使用"""
    log = load_log()
    entry = {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "project": project,
        "bgm": os.path.basename(bgm_file),
    }
    log.append(entry)
    save_log(log)
    print(f"Recorded: {entry['date']} / {entry['project']} / {entry['bgm']}")


def check_available(bgm_file, days=5):
    """检查 BGM 是否在最近 N 天未被使用"""
    bgm_name = os.path.basename(bgm_file)
    used = recent_used(days)
    if bgm_name in used:
        print(f"BLOCKED: {bgm_name} used in last {days} days")
        return False
    print(f"OK: {bgm_name} available")
    return True


def main():
    import argparse
    parser = argparse.ArgumentParser(description="BGM usage history")
    parser.add_argument("--recent", type=int, help="Show BGMs used in last N days")
    parser.add_argument("--record", action="store_true", help="Record a usage entry")
    parser.add_argument("--bgm", type=str, help="BGM filename")
    parser.add_argument("--project", type=str, default="unknown", help="Project name")
    parser.add_argument("--check", type=str, help="Check if a BGM is available")
    parser.add_argument("--days", type=int, default=5, help="Lookback window (default 5)")
    args = parser.parse_args()

    if args.record:
        if not args.bgm:
            print("ERROR: --record requires --bgm")
            sys.exit(1)
        record(args.bgm, args.project)
    elif args.check:
        check_available(args.check, args.days)
    elif args.recent:
        used = recent_used(args.recent)
        if used:
            print(",".join(sorted(used)))
        else:
            print("(none)")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
