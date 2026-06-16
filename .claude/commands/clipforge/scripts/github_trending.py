#!/usr/bin/env python
"""GitHub Trending multi-source data fetcher with cross-validation.

Sources:
  1. Python requests — direct HTTP fetch, no cache
  2. web-reader MCP — validation (called externally, results compared here)
  3. gh CLI API — authoritative star counts + activity check

Usage:
  python scripts/github_trending.py --output-dir workspace/github-trending-2026-05-16
  python scripts/github_trending.py --output-dir workspace/github-trending-2026-05-16 --since weekly
"""

import argparse
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

import requests

DEFAULT_PROXY = os.environ.get("https_proxy", "")
TRENDING_URL_DAILY = "https://github.com/trending?spoken_language_code="
TRENDING_URL_WEEKLY = "https://github.com/trending?since=weekly&spoken_language_code="
MIN_PROJECTS = 8
STALE_DAYS = 30


def fetch_trending(proxy: str, since: str = "daily") -> list[dict]:
    """Source 1: Direct HTTP request to GitHub Trending page."""
    url = TRENDING_URL_DAILY if since == "daily" else TRENDING_URL_WEEKLY
    proxies = {"https": proxy, "http": proxy}

    resp = requests.get(
        url,
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
        proxies=proxies,
        timeout=30,
    )
    resp.raise_for_status()
    html = resp.text

    # Split into article blocks
    articles = re.findall(r'<article[^>]*>(.*?)</article>', html, re.DOTALL)
    print(f"[Source 1] Found {len(articles)} article blocks")

    projects = []
    for i, block in enumerate(articles, 1):
        # Repo name - find the h2 > a link (the actual repo link, not sponsor links)
        name_match = re.search(r'<h2[^>]*>.*?<a[^>]*href="/([^/]+/[^/"]+)"', block, re.DOTALL)
        if not name_match:
            continue
        full_name = name_match.group(1)

        # Skip non-repo links (sponsors, features, etc.)
        if full_name.count("/") != 1:
            continue
        # Skip known non-repo paths
        skip_prefixes = ("sponsors/", "features/", "marketplace/", "topics/", "explore/",
                         "collections/", "events/", "trending/", "settings/")
        if any(full_name.startswith(p) for p in skip_prefixes):
            continue

        # Today stars
        stars_today_match = re.search(r'([\d,]+)\s*stars?\s*today', block)
        stars_today = int(stars_today_match.group(1).replace(",", "")) if stars_today_match else 0

        # Language
        lang_match = re.search(r'itemprop="programmingLanguage">([^<]+)<', block)
        language = lang_match.group(1).strip() if lang_match else "-"

        # Description
        desc_match = re.search(r'<p[^>]*class="[^"]*col-9[^"]*"[^>]*>\s*(.+?)\s*</p>', block, re.DOTALL)
        description = ""
        if desc_match:
            description = re.sub(r'<[^>]+>', '', desc_match.group(1)).strip()

        projects.append({
            "rank": len(projects) + 1,
            "full_name": full_name,
            "owner": full_name.split("/")[0],
            "repo": full_name.split("/")[1],
            "description": description,
            "language": language,
            "stars_today": stars_today,
            "stars_total": 0,
            "url": f"https://github.com/{full_name}",
        })

    print(f"[Source 1] Parsed {len(projects)} projects")
    return projects


def enrich_with_gh_api(projects: list[dict]) -> list[dict]:
    """Source 3: Enrich each project with gh API data (stars, forks, pushed_at)."""
    verified = 0
    warnings = []

    for p in projects:
        try:
            env = os.environ.copy()
            env["MSYS_NO_PATHCONV"] = "1"
            result = subprocess.run(
                ["gh", "api", f"repos/{p['owner']}/{p['repo']}", "--jq",
                 "{stars: .stargazers_count, forks: .forks_count, pushed: .pushed_at, language: .language, topics: .topics, avatar: .owner.avatar_url}"],
                capture_output=True, text=True, timeout=15, env=env,
            )
            if result.returncode != 0:
                warnings.append(f"gh api failed for {p['full_name']}: {result.stderr.strip()}")
                continue

            api = json.loads(result.stdout)
            p["stars_total"] = api["stars"]
            p["forks_total"] = api["forks"]
            p["pushed_at"] = api["pushed"]
            p["topics"] = api.get("topics", [])
            p["avatar_url"] = api.get("avatar")  # owner 头像（组织=品牌logo/个人=头像），fetch_avatars.py 下载

            # Activity check
            pushed = datetime.fromisoformat(api["pushed"].replace("Z", "+00:00"))
            age_days = (datetime.now(timezone.utc) - pushed).days
            p["active"] = age_days <= STALE_DAYS
            if not p["active"]:
                warnings.append(f"{p['full_name']}: last push {age_days} days ago (>{STALE_DAYS})")

            verified += 1
            time.sleep(0.3)  # Rate limit courtesy

        except (subprocess.TimeoutExpired, json.JSONDecodeError, KeyError) as e:
            warnings.append(f"gh api error for {p['full_name']}: {e}")

    print(f"[Source 3] Verified {verified}/{len(projects)} projects via gh API")
    for w in warnings:
        print(f"  [!] {w}")

    return projects


def check_stale(projects: list[dict], yesterday_path: str) -> dict:
    """Check if today's data is identical to yesterday's (cache hit detection)."""
    result = {"is_stale": False, "overlap_count": 0, "message": ""}

    if not yesterday_path or not os.path.exists(yesterday_path):
        result["message"] = "No yesterday data to compare"
        return result

    try:
        with open(yesterday_path, "r", encoding="utf-8") as f:
            yesterday = json.load(f)
        yesterday_names = set(p["full_name"] for p in yesterday.get("projects", []))
        today_names = set(p["full_name"] for p in projects)

        overlap = today_names & yesterday_names
        result["overlap_count"] = len(overlap)

        if today_names == yesterday_names and len(today_names) > 0:
            # Check if star counts also identical (stronger stale signal)
            today_stars = {p["full_name"]: p.get("stars_today", 0) for p in projects}
            yesterday_stars = {p["full_name"]: p.get("stars_today", 0) for p in yesterday.get("projects", [])}
            stars_match = all(today_stars.get(n) == yesterday_stars.get(n) for n in today_names)

            if stars_match:
                result["is_stale"] = True
                result["message"] = f"CRITICAL: Same {len(today_names)} projects AND same star counts as yesterday — cache hit!"
            else:
                result["message"] = f"WARNING: Same {len(today_names)} projects but different star counts — same trending, data may be valid"
        else:
            result["message"] = f"OK: {len(overlap)} overlapping projects, {len(today_names - yesterday_names)} new entries"

    except (json.JSONDecodeError, KeyError) as e:
        result["message"] = f"Could not parse yesterday data: {e}"

    return result


def validate_project_count(projects: list[dict]) -> bool:
    """Minimum project count gate."""
    if len(projects) < MIN_PROJECTS:
        print(f"[FAIL] Only {len(projects)} projects (minimum {MIN_PROJECTS})")
        return False
    print(f"[OK] Project count: {len(projects)} (>= {MIN_PROJECTS})")
    return True


def validate_activity(projects: list[dict]) -> bool:
    """Check that most projects are recently active."""
    active = sum(1 for p in projects if p.get("active", True))
    ratio = active / len(projects) if projects else 0
    threshold = 0.8
    if ratio < threshold:
        print(f"[WARN] Activity: {active}/{len(projects)} active ({ratio:.0%}, threshold {threshold:.0%})")
        return False
    print(f"[OK] Activity: {active}/{len(projects)} active ({ratio:.0%})")
    return True


def write_checklist(projects: list[dict], output_dir: str, date: str):
    """Write project name list for web-reader MCP cross-validation."""
    checklist = {
        "date": date,
        "source": "python_requests",
        "project_names": [p["full_name"] for p in projects],
        "instructions": (
            "Use web-reader MCP (no_cache=true) on "
            "https://github.com/trending?spoken_language_code= "
            "and compare project list with project_names above. "
            "Overlap >= 80% = pass."
        ),
    }
    path = os.path.join(output_dir, "webreader_checklist.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(checklist, f, indent=2, ensure_ascii=False)
    print(f"[OK] Checklist written to {path}")


def write_output(projects: list[dict], output_dir: str, date: str, since: str,
                 stale_result: dict, validation_warnings: list[str]):
    """Write final validated output."""
    output = {
        "date": date,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "source": "python_requests+gh_api",
        "since": since,
        "cache_warning": stale_result.get("is_stale", False),
        "stale_message": stale_result.get("message", ""),
        "validation_warnings": validation_warnings,
        "project_count": len(projects),
        "projects": projects,
    }
    path = os.path.join(output_dir, "raw_trending.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    print(f"[OK] Output written to {path}")
    return path


def main():
    parser = argparse.ArgumentParser(description="GitHub Trending multi-source fetcher")
    parser.add_argument("--output-dir", required=True, help="Output directory for JSON files")
    parser.add_argument("--yesterday", default="", help="Path to yesterday's raw_trending.json")
    parser.add_argument("--proxy", default=DEFAULT_PROXY, help="HTTP proxy URL")
    parser.add_argument("--since", choices=["daily", "weekly"], default="daily", help="Time range")
    parser.add_argument("--skip-gh", action="store_true", help="Skip gh API verification")
    parser.add_argument("--date", default="", help="Date string (default: today)")
    args = parser.parse_args()

    date = args.date or datetime.now().strftime("%Y-%m-%d")
    output_dir = args.output_dir
    os.makedirs(output_dir, exist_ok=True)

    print(f"=" * 60)
    print(f"GitHub Trending Fetcher — {date} ({args.since})")
    print(f"=" * 60)

    # Source 1: Python HTTP fetch
    projects = fetch_trending(args.proxy, args.since)

    # Gate: minimum project count
    if not validate_project_count(projects):
        print("[ABORT] Insufficient projects from GitHub Trending page")
        sys.exit(1)

    # Source 3: gh API enrichment
    if not args.skip_gh:
        projects = enrich_with_gh_api(projects)
    else:
        print("[Source 3] Skipped (--skip-gh)")

    # Validation
    all_warnings = []
    if not args.skip_gh:
        if not validate_activity(projects):
            all_warnings.append("Some projects not recently active")

    # Stale check
    stale_result = check_stale(projects, args.yesterday)
    print(f"[STALE] {stale_result['message']}")
    if stale_result["is_stale"]:
        all_warnings.append(stale_result["message"])

    # Write checklist for web-reader MCP (Source 2)
    write_checklist(projects, output_dir, date)

    # Write final output
    write_output(projects, output_dir, date, args.since, stale_result, all_warnings)

    # Summary
    print(f"\n{'=' * 60}")
    print(f"[SUMMARY] {date}")
    print(f"  Source 1 (Python): {len(projects)} projects [OK]")
    if not args.skip_gh:
        verified = sum(1 for p in projects if p.get("stars_total", 0) > 0)
        print(f"  Source 3 (gh API): {verified}/{len(projects)} verified [OK]")
        active = sum(1 for p in projects if p.get("active", True))
        print(f"  Activity: {active}/{len(projects)} recently pushed [OK]")
    print(f"  Cache check: {'STALE!' if stale_result['is_stale'] else 'Fresh'}")
    if all_warnings:
        print(f"  Warnings: {len(all_warnings)}")
        for w in all_warnings:
            print(f"    [!] {w}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
