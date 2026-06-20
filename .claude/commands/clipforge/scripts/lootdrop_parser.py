"""loot-drop.io 失败案例详情页解析（SSR HTML → 结构化字段）。

供 fetch_lootdrop.py 调用，提取失败案例完整信息：
公司名/融资/地区/overview/6维分析/重建点子/相关失败。

详情页结构（SSR，requests 可抓）：
- <title>NAME | Failed Startup Case Study</title>
- <meta name="description" content="...burning $XM. NAME pioneered...">
- <h3 class="card-title">SECTION</h3>...</div><p class="card-text">CONTENT</p>（6维）
- Pivot Concept（master-timeline）到 Execution Plan 间为重建方案
- <article class="startup-card-v2" data-href="/startup/ID-slug">...<h3 class="card-v2-name">NAME</h3>
"""
from __future__ import annotations
import re

# 地区关键词（中国公司筛选依赖，首批中国起步）
REGION_KEYWORDS = [
    ("中国", ["china", "chinese", "beijing", "shanghai", "shenzhen",
              "guangzhou", "hangzhou", "alibaba", "tencent"]),
    ("美国", ["san francisco", "silicon valley", "new york", " usa",
              "u.s.", "american", "bezos"]),
    ("印度", ["india", "indian", "bangalore", "mumbai", "delhi"]),
    ("欧洲", ["europe", "european", "london", "berlin", "paris"]),
]

# 6维分析 section 标题 → 字段名
SECTION_KEYS = {
    "Failure Analysis": "failure_analysis",
    "Market Analysis": "market_analysis",
    "Startup Learnings": "startup_learnings",
    "Market Potential": "market_potential",
    "Difficulty": "difficulty",
    "Scalability": "scalability",
}


def infer_region(text: str) -> str:
    """从文本推断地区（中国公司筛选用）。无匹配返回 '其他'。"""
    if not text:
        return "其他"
    low = text.lower()
    for region, keywords in REGION_KEYWORDS:
        if any(k in low for k in keywords):
            return region
    return "其他"


def _strip_tags(s: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", s)).strip()


def parse_failure_detail(html: str, url: str = "") -> dict:
    """解析详情页 HTML → 结构化字段 dict。"""
    # 公司名（title）
    name = ""
    m = re.search(r"<title>(.+?)\s*\|\s*Failed Startup", html)
    if m:
        name = m.group(1).strip()

    # meta description（overview + 融资额）
    overview = ""
    m = re.search(r'<meta name="description" content="([^"]+)"', html)
    if m:
        overview = m.group(1)

    funding = ""
    m = re.search(r"burning \$([\d.,]+[KMB]?)", overview)
    if m:
        funding = f"${m.group(1)}"

    region = infer_region(overview)

    # 6维 section（card-title + card-text）
    fields = {key: "" for key in SECTION_KEYS.values()}
    for title, key in SECTION_KEYS.items():
        m = re.search(
            rf'<h3 class="card-title">\s*{re.escape(title)}\s*</h3>\s*</div>\s*'
            r'<p class="card-text">([^<]+)</p>', html)
        if m:
            fields[key] = m.group(1).strip()

    # Pivot Concept（重建点子）：Pivot Concept 到 Execution Plan 间文本去标签
    pivot = ""
    m = re.search(r"Pivot Concept</h3>(.*?)Execution Plan</h3>", html, re.DOTALL)
    if m:
        pivot = _strip_tags(m.group(1))

    # Related failures（card-v2: data-href + card-v2-name）
    related = []
    for m in re.finditer(
        r'data-href="(/startup/[^"]+)".*?<h3 class="card-v2-name">([^<]+)</h3>',
        html, re.DOTALL):
        related.append({"name": m.group(2).strip(), "url": m.group(1)})

    return {
        "name": name,
        "url": url,
        "funding": funding,
        "region": region,
        "overview": overview,
        **fields,
        "pivot_concept": pivot,
        "related": related,
    }
