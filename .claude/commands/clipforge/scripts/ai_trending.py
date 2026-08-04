#!/usr/bin/env python
"""AI 风向标 — GitHub AI 开源项目专项采集器。

基于 github_trending.py，新增 AI 二次筛选（topics + description 关键词）。
输出 raw_trending.json（结构与 github_trending 一致，下游管线 gate/fetch_avatars/monthly 零改动）。

采集策略（三源交叉验证，沿用 github 分类 data_validation）：
  1. 主源：github.com/trending（daily 全语言）→ 爬取项目列表
  2. AI 二次筛：topics 含 AI 关键词 或 description 含 AI 关键词
  3. 补充源（主源 AI < MIN_AI）：github.com/trending/python（Python 是 AI 主语言）
  4. gh API enrichment（stars/forks/topics/avatar）+ 活跃度核验
  5. 真实性核验（authenticity_verification）由下游 stage1/content 阶段执行（复用 github 规则）

Usage:
  python scripts/ai_trending.py --output-dir workspace/test/ai-wind --date 2026-08-02 --since daily
  python scripts/ai_trending.py --output-dir <PROJECT_DIR> --yesterday <昨日 raw_trending.json>
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import github_trending as gt
import requests

# ── AI 筛选关键词（topics，小写匹配）──
AI_TOPICS = {
    "ai", "artificial-intelligence", "ai-agent", "ai-agents", "llm",
    "large-language-models", "large-language-model", "agent", "autonomous-agents",
    "machine-learning", "ml", "deep-learning", "neural-network", "neural-networks",
    "transformer", "transformers", "gpt", "chatgpt", "openai", "anthropic",
    "langchain", "langgraph", "rag", "generative-ai", "generative",
    "stable-diffusion", "diffusion", "diffusion-model", "huggingface",
    "pytorch", "tensorflow", "keras", "computer-vision", "cv",
    "nlp", "natural-language-processing", "speech-recognition",
    "text-to-speech", "tts", "speech-to-text", "speech-to-speech",
    "reinforcement-learning", "robotics", "ocr", "vision-language", "multimodal",
}

# ── AI 筛选关键词（description 正则，大小写敏感词边界）──
AI_DESC_PATTERNS = [
    r"\bAI\b", r"\bLLMs?\b", r"\bGPT\b", r"\bAgents?\b", r"\bTransformers?\b",
    r"\bgenerative[- ]ai\b", r"\bmachine[- ]learning\b", r"\bdeep[- ]learning\b",
    r"\bchatbot\b", r"\btext-to-(image|speech|video|3d)\b", r"\bspeech-to-(text|speech)\b",
    r"\bopen[- ]?source\s+(ai|llm|model)\b", r"\blocal\s+(ai|llm)\b",
    r"智能体", r"大模型", r"机器学习", r"深度学习", r"生成式",
]

MIN_AI_PROJECTS = 8      # 理想下限（< 时告警但继续）
FALLBACK_MIN = 5         # 硬下限（< 时 abort，不足以制作）


def is_ai_project(p: dict) -> bool:
    """判定是否 AI 项目：topics 命中 或 description 命中 AI 关键词。"""
    topics = {t.lower() for t in (p.get("topics") or [])}
    if topics & AI_TOPICS:
        return True
    desc = p.get("description") or ""
    for pat in AI_DESC_PATTERNS:
        if re.search(pat, desc, re.IGNORECASE):
            return True
    return False


def fetch_by_language(proxy: str, lang: str, since: str = "daily") -> list[dict]:
    """补充源：按语言抓 trending（Python 多 AI）。解析逻辑同 gt.fetch_trending，换 URL。"""
    url = f"https://github.com/trending/{lang}?since={since}&spoken_language_code="
    proxies = {"https": proxy, "http": proxy}
    resp = requests.get(
        url,
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
        proxies=proxies, timeout=30,
    )
    resp.raise_for_status()
    articles = re.findall(r'<article[^>]*>(.*?)</article>', resp.text, re.DOTALL)
    print(f"[补充源 {lang}] Found {len(articles)} article blocks")
    projects = []
    skip_prefixes = ("sponsors/", "features/", "marketplace/", "topics/", "explore/",
                     "collections/", "events/", "trending/", "settings/")
    for block in articles:
        name_match = re.search(r'<h2[^>]*>.*?<a[^>]*href="/([^/]+/[^/"]+)"', block, re.DOTALL)
        if not name_match:
            continue
        full = name_match.group(1)
        if full.count("/") != 1 or any(full.startswith(p) for p in skip_prefixes):
            continue
        stars_match = re.search(r'([\d,]+)\s*stars?\s*today', block)
        lang_match = re.search(r'itemprop="programmingLanguage">([^<]+)<', block)
        desc_match = re.search(r'<p[^>]*class="[^"]*col-9[^"]*"[^>]*>\s*(.+?)\s*</p>', block, re.DOTALL)
        projects.append({
            "full_name": full,
            "owner": full.split("/")[0],
            "repo": full.split("/")[1],
            "description": (re.sub(r'<[^>]+>', '', desc_match.group(1)).strip() if desc_match else ""),
            "language": (lang_match.group(1).strip() if lang_match else lang),
            "stars_today": (int(stars_match.group(1).replace(",", "")) if stars_match else 0),
            "stars_total": 0,
            "url": f"https://github.com/{full}",
        })
    return projects


def main():
    parser = argparse.ArgumentParser(description="AI 风向标 — GitHub AI 项目专项采集")
    parser.add_argument("--output-dir", required=True, help="输出目录")
    parser.add_argument("--yesterday", default="", help="昨日 raw_trending.json 路径（去重对照）")
    parser.add_argument("--proxy", default=gt.DEFAULT_PROXY, help="HTTP 代理")
    parser.add_argument("--since", choices=["daily", "weekly"], default="daily")
    parser.add_argument("--skip-gh", action="store_true", help="跳过 gh API enrichment")
    parser.add_argument("--date", default="", help="日期（默认今天）")
    args = parser.parse_args()

    date = args.date or datetime.now().strftime("%Y-%m-%d")
    os.makedirs(args.output_dir, exist_ok=True)

    print("=" * 60)
    print(f"AI 风向标 Fetcher — {date} ({args.since})")
    print("=" * 60)

    # ── 主源：全语言 trending ──
    all_projects = gt.fetch_trending(args.proxy, args.since)
    print(f"[主源] 全语言 trending: {len(all_projects)} 项目")

    # gh API enrichment（topics 在此获取，AI 筛选依赖 topics，故先 enrich 全部）
    if not args.skip_gh:
        all_projects = gt.enrich_with_gh_api(all_projects)
    else:
        print("[Source 3] Skipped (--skip-gh)")

    # ── AI 二次筛 ──
    ai_projects = [p for p in all_projects if is_ai_project(p)]
    print(f"[AI 筛] 主源 AI 项目: {len(ai_projects)}")

    # ── 补充源：Python trending（主源 AI 不足时）──
    if len(ai_projects) < MIN_AI_PROJECTS:
        print(f"[补充] AI 项目 < {MIN_AI_PROJECTS}，抓 Python trending 补充")
        try:
            py_projects = fetch_by_language(args.proxy, "python", args.since)
            existing = {p["full_name"] for p in ai_projects}
            py_new = [p for p in py_projects if p["full_name"] not in existing]
            if py_new and not args.skip_gh:
                py_new = gt.enrich_with_gh_api(py_new)
            py_ai = [p for p in py_new if is_ai_project(p)]
            print(f"[补充] Python trending 新增 AI: {len(py_ai)}")
            ai_projects.extend(py_ai)
        except Exception as e:
            print(f"[补充] Python trending 抓取失败: {e}（继续用主源）")

    # 去重 + 按 stars_today 降序重排 rank
    seen = set()
    deduped = []
    for p in ai_projects:
        if p["full_name"] not in seen:
            seen.add(p["full_name"])
            deduped.append(p)
    deduped.sort(key=lambda p: p.get("stars_today", 0), reverse=True)
    for i, p in enumerate(deduped, 1):
        p["rank"] = i
    ai_projects = deduped

    # ── 质量门禁 ──
    if len(ai_projects) < FALLBACK_MIN:
        print(f"[ABORT] AI 项目仅 {len(ai_projects)} (< {FALLBACK_MIN})，不足以制作")
        sys.exit(1)

    warnings = []
    if len(ai_projects) < MIN_AI_PROJECTS:
        print(f"[WARN] AI 项目 {len(ai_projects)} (< 理想 {MIN_AI_PROJECTS})，降级继续")
        warnings.append(f"AI 项目偏少 ({len(ai_projects)})")

    active = sum(1 for p in ai_projects if p.get("active", True))
    if active / len(ai_projects) < 0.8:
        print(f"[WARN] 活跃度 {active}/{len(ai_projects)} (<80%)")
        warnings.append("部分项目不活跃")
    print(f"[活跃] {active}/{len(ai_projects)} active")

    # stale check（与昨日 AI 数据对比）
    stale = gt.check_stale(ai_projects, args.yesterday)
    print(f"[STALE] {stale['message']}")
    if stale.get("is_stale"):
        warnings.append(stale["message"])

    # ── 输出（文件名 raw_trending.json，下游零改动；source 标 ai_trending）──
    gt.write_checklist(ai_projects, args.output_dir, date)
    output = {
        "date": date,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "source": "ai_trending+gh_api",
        "album": "ai-wind",
        "since": args.since,
        "cache_warning": stale.get("is_stale", False),
        "stale_message": stale.get("message", ""),
        "validation_warnings": warnings,
        "project_count": len(ai_projects),
        "projects": ai_projects,
    }
    out_path = os.path.join(args.output_dir, "raw_trending.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    print(f"[OK] AI 输出: {out_path} ({len(ai_projects)} 项目)")

    # ── Summary ──
    print(f"\n{'=' * 60}")
    print(f"[SUMMARY] {date} AI 风向标")
    print(f"  AI 项目: {len(ai_projects)}")
    print(f"  活跃: {active}/{len(ai_projects)}")
    print(f"  缓存: {'STALE!' if stale.get('is_stale') else 'Fresh'}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
