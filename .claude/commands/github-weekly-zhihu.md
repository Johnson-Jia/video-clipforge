---
name: github-weekly-zhihu
description: 每周一自动汇总上周 GitHub Trending 数据，生成高质量知乎文章。完成后自动续期定时任务。
---

# GitHub 每周热门 → 知乎深度文章（全自动）

> **全自动执行，不需要人工确认。** 文章项目仅执行数据采集 + 内容撰写 + 封面生成，不涉及视频 DAG 流水线。状态通过文件系统检测。

## 前置：日期 & 目录

```bash
TODAY=$(date +%Y-%m-%d)
MONTH=$(date +%Y-%m)
DATE_DIR="$(date +%Y)/$(date +%m)/$(date +%d)"
OUTPUT_DIR="workspace/${DATE_DIR}/github-zhihu"
```

> **代理：** 如果本机需要代理才能访问 GitHub，请在执行前设置 `https_proxy` / `http_proxy` 环境变量。

## Step 1: 三源交叉验证数据采集

> **核心原则：周涨幅以 GitHub Weekly Trending 页面为准（覆盖完整 7 天），本地日榜数据作为补充（识别连续多天热门项目）。**

### 数据源 1：GitHub Weekly Trending 页面（主数据源）

用 Python 脚本抓取 GitHub Weekly Trending 页面，获取完整 7 天的周涨幅数据：

```bash
TODAY=$(date +%Y-%m-%d)
DATE_DIR="$(date +%Y)/$(date +%m)/$(date +%d)"
VERIFY_DIR="workspace/${DATE_DIR}/github-weekly-verify"
mkdir -p "${VERIFY_DIR}"

python .claude/commands/clipforge/scripts/github_trending.py \
  --output-dir "${VERIFY_DIR}" \
  --date "${TODAY}" \
  --since weekly
```

脚本输出 `raw_trending.json`，包含 15 个项目及**周涨幅（stars_today 字段在 weekly 模式下为周涨幅）**。

**额外验证：用 HTTP 直连提取周涨幅数据**（脚本可能不捕获周涨幅字段）：

```bash
python -c "
import requests, re
from bs4 import BeautifulSoup

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
resp = requests.get('https://github.com/trending?since=weekly&spoken_language_code=', headers=headers, timeout=30)
resp.raise_for_status()

soup = BeautifulSoup(resp.text, 'html.parser')
articles = soup.select('article.Box-row')
for art in articles:
    h2 = art.select_one('h2 a')
    name = h2.get_text(strip=True).replace('\n', '').replace(' ', '') if h2 else 'N/A'
    star_span = art.select_one('span.d-inline-block.float-sm-right')
    weekly_stars = 'N/A'
    if star_span:
        text = star_span.get_text(strip=True)
        m = re.search(r'([\d,]+)\s*stars', text)
        if m:
            weekly_stars = m.group(1)
    print(f'{name}|{weekly_stars}')
"
```

### 数据源 2：本地月度清单（日榜趋势）

读取 `workspace/sources/github-trending/${MONTH}.md`，提取**上周一到昨天**的所有日期条目。

**重要：排除缓存重复数据**。如果连续两天的项目列表完全相同（项目名、每日★数一致），则后一天为 CDN 缓存命中，标记为无效数据不纳入统计。

从日榜数据中提取：
- 各项目的每日★数（累计为日榜涨幅，仅作参考，不作为周涨幅依据）
- 连续上榜天数（作为"持续热门"标签依据）

### 数据源 3：zread.ai 历史数据（备选验证）

zread.ai 提供 GitHub Trending 的历史数据。由于该网站使用 Next.js SSR，数据在客户端渲染，需要特殊处理：

```bash
# 方法 1：探测 API 端点（已知端点返回 HTML，非 JSON）
curl -sL "https://zread.ai/api/trending/weekly" | head -100

# 方法 2：web-reader MCP（设置 no_cache: true）
# 使用 mcp__web_reader__webReader 工具，url: https://zread.ai/trending, no_cache: true

# 方法 3：如果 Chrome MCP 可用，用浏览器渲染后提取
# 使用 mcp__plugin_superpowers-chrome_chrome__use_browser 工具

# 如果三种方法都无法提取数据（常见于 Next.js SSR），跳过此数据源
# 记录跳过原因：\"zread.ai Next.js SSR 客户端渲染，静态抓取无法获取数据\"
```

### 数据合并与验证规则

1. **主排名以 GitHub Weekly 页面为准**：周涨幅、项目排名全部使用 Weekly 页面数据
2. **日榜数据作为补充**：标注项目"连续 N 天日榜"信息，用于趋势分析
3. **交叉比对**：Weekly 页面项目与日榜项目的交集 ≥ 60% 为正常（Weekly 覆盖 7 天，日榜仅覆盖采集到的天数）
4. **新增项目标注**：仅在 Weekly 页面出现但不在日榜中的项目标注为"本周新上榜"
5. **数据质量门禁**：Weekly 页面项目数 ≥ 15，否则停止执行并报错

### 合并后输出

- 项目列表（含周涨幅、总★、语言、描述、topics）
- 日榜持续性信息（连续上榜天数）
- 交叉验证报告（数据源一致性）

## Step 2: 数据增强 — 获取项目详情

对每个项目，用 `gh` API 获取补充信息：

```bash
gh api repos/{owner}/{repo} --jq '{topics: .topics, license: .license.spdx_id, created: .created_at, pushed: .pushed_at, open_issues: .open_issues_count, watchers: .watchers_count}'
```

- **topics**：用于文章分类标签
- **license**：开源协议信息
- **pushed_at**：项目活跃度指标
- **open_issues**：社区参与度参考

## Step 3: 撰写知乎文章

### 文章结构

```markdown
# YYYY年M月第N周 GitHub 热门开源项目盘点

> 一句话导语（本周趋势概括，如"AI Agent 框架持续霸榜，游戏引擎异军突起"）

## 本周趋势速览

| 趋势 | 说明 |
|------|------|
| 最大赢家 | 涨星最多的项目 + 数据 |
| 新面孔 | 首次上榜的项目 |
| 持续热门 | 连续多周上榜的项目 |

## 项目详细解读

（按分类分组，每组 2-4 个项目）

### 分类名称（如"AI & 智能体"）

#### 1. owner/repo

**项目简介：** 2-3 句话说明项目是做什么的、解决什么问题。

**核心亮点：**
- 亮点1（具体功能/特性）
- 亮点2（性能/架构优势）
- 亮点3（适用场景）

**快速上手：**
```bash
# 安装/使用命令（从 README 提取）
```

**适合人群：** XX方向开发者 / XX领域从业者

> Star: XX,XXX | Fork: X,XXX | 协议: MIT | 语言: Python | 本周涨幅: +X,XXX

---

（重复以上格式）

## 本周总结

- 2-3 句话总结本周开源趋势
- 推荐 1-2 个最值得关注的项目及理由

## 相关阅读

- 上周盘点：[链接]
- GitHub Trending 月度清单
```

### 写作要求

1. **深度优先** — 每个项目至少 150 字解读，不是简单罗列
2. **实用导向** — 尽量包含安装命令、使用示例、适用场景
3. **数据说话** — 用 Star 数、Fork 数、Issues 数量化项目热度
4. **中性客观** — 描述功能和特点，不使用"最强"、"必装"等极限词
5. **搜索友好** — 标题和正文包含"GitHub"、"开源"、"项目"等搜索高频词
6. **不点名商业产品/品牌** — 不提 GPT、DeepSeek 等品牌名，用"大语言模型"、"AI 助手"等类别词。但项目名本身包含品牌名（如 DeepSeek-TUI）可如实引用
7. **项目链接可放** — 知乎不像抖音限制 URL，每个项目标题直接超链接到 GitHub
8. **数据来源透明** — 文章末尾注明数据来源（"GitHub Weekly Trending + 每日 Trending 本地记录交叉验证"），标注周涨幅以 Weekly 页面为准

### 分类策略

根据项目 topics 和描述自动归类：

| 分类关键词 | 分类名 |
|-----------|--------|
| ai, ml, llm, deep-learning | AI & 机器学习 |
| web, frontend, react, vue | 前端开发 |
| api, server, backend, database | 后端 & 基础设施 |
| devops, ci/cd, kubernetes, docker | DevOps & 云原生 |
| game, 3d, engine | 游戏开发 |
| education, learning, course | 学习资源 |
| security, privacy | 安全 |
| mobile, ios, android | 移动开发 |
| 其他 | 开发工具 |

## Step 4: 生成文章封面图

用 HTML + Puppeteer 渲染一张知乎文章封面图（横版 1920×1080）。

### 封面设计规范

- **尺寸**：1920×1080（16:9 横版，知乎文章封面标准比例）
- **风格**：延续 GitHub Dark 主题（`#0d1117` 底色 + `#00e5a0` 强调色 + `#f0883e` 星标色）
- **字体**：Inter / JetBrains Mono / PingFang SC

### 封面内容结构

```
┌──────────────────────────────────────────┐
│  [网格背景 + 渐变光晕]                      │
│                                          │
│  YYYY年M月第N周                            │
│  GitHub 热门开源项目盘点                    │
│                                          │
│  ┌─────┐  ┌─────┐  ┌─────┐              │
│  │TOP1 │  │TOP2 │  │TOP3 │   ← 涨星前三  │
│  │★数  │  │★数  │  │★数  │              │
│  └─────┘  └─────┘  └─────┘              │
│                                          │
│  本周热度 N★ | X 个项目 | Y 个分类         │
└──────────────────────────────────────────┘
```

### 实现步骤

1. 在 `${OUTPUT_DIR}/` 下创建 `cover.html`，用纯 HTML/CSS 绘制封面布局
2. 用 Puppeteer 截图生成 `cover.png`：

```bash
node -e "
const puppeteer = require('puppeteer');
(async () => {
  const browser = await puppeteer.launch({ headless: 'new' });
  const page = await browser.newPage();
  await page.setViewport({ width: 1920, height: 1080, deviceScaleFactor: 2 });
  await page.goto('file:///${OUTPUT_DIR}/cover.html'.replace(/\\\\/g, '/'));
  await new Promise(r => setTimeout(r, 1000));
  await page.screenshot({ path: '${OUTPUT_DIR}/cover.png', type: 'png' });
  await browser.close();
  console.log('cover.png generated');
})();
"
```

3. 如果 Puppeteer 不可用，备选方案：

```bash
# 备选：用 HyperFrames 渲染
cd ${OUTPUT_DIR}
npx hyperframes init --force 2>/dev/null || true
# 将 cover.html 复制为 index.html，用 hyperframes render
npx hyperframes render --output cover.mp4
ffmpeg -y -i cover.mp4 -vf "select=eq(n\,0)" -vframes 1 -update 1 cover.png
```

4. 确认 `cover.png` 已生成且尺寸正确

### 封面 HTML 模板

```html
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;700;900&family=JetBrains+Mono:wght@400;700&display=swap');
  * { margin: 0; padding: 0; box-sizing: border-box; }
  html, body { width: 1920px; height: 1080px; overflow: hidden;
    font-family: 'Inter', 'PingFang SC', 'Microsoft YaHei', sans-serif;
    background: #0d1117; }
  .wrap { width: 1920px; height: 1080px; display: flex; flex-direction: column;
    align-items: center; justify-content: center; position: relative; }
  .grid-bg { position: absolute; width: 100%; height: 100%;
    background-image: linear-gradient(rgba(0,229,160,0.06) 1px, transparent 1px),
      linear-gradient(90deg, rgba(0,229,160,0.06) 1px, transparent 1px);
    background-size: 40px 40px; }
  .glow { position: absolute; width: 800px; height: 800px; border-radius: 50%;
    background: radial-gradient(circle, rgba(0,229,160,0.06), transparent 70%); }
  .week-label { font-size: 36px; color: #00e5a0; font-weight: 700; z-index:1; }
  .title { font-size: 72px; color: #ffffff; font-weight: 900; margin-top: 20px;
    letter-spacing: 4px; z-index:1; }
  .cards { display: flex; gap: 40px; margin-top: 60px; z-index:1; }
  .card { width: 360px; padding: 30px; background: rgba(22,27,34,0.9);
    border: 1px solid rgba(0,229,160,0.15); border-radius: 16px;
    text-align: center; }
  .card-name { font-family: 'JetBrains Mono', monospace; font-size: 28px;
    color: #58a6ff; font-weight: 700; }
  .card-stars { font-family: 'JetBrains Mono', monospace; font-size: 42px;
    color: #f0883e; font-weight: 900; margin-top: 10px; }
  .card-unit { font-size: 20px; color: #8b949e; margin-top: 4px; }
  .stats { font-size: 28px; color: #8b949e; margin-top: 50px; z-index:1; }
  .stats span { color: #00e5a0; font-weight: 700; }
</style>
</head>
<body>
<div class="wrap">
  <div class="grid-bg"></div>
  <div class="glow" style="top:-200px; left:-200px;"></div>
  <div class="glow" style="bottom:-200px; right:-200px;"></div>
  <div class="week-label">{{WEEK_LABEL}}</div>
  <div class="title">GitHub 热门开源项目盘点</div>
  <div class="cards">
    <div class="card">
      <div class="card-name">{{TOP1_NAME}}</div>
      <div class="card-stars">{{TOP1_STARS}}</div>
      <div class="card-unit">★ 本周热度</div>
    </div>
    <div class="card">
      <div class="card-name">{{TOP2_NAME}}</div>
      <div class="card-stars">{{TOP2_STARS}}</div>
      <div class="card-unit">★ 本周热度</div>
    </div>
    <div class="card">
      <div class="card-name">{{TOP3_NAME}}</div>
      <div class="card-stars">{{TOP3_STARS}}</div>
      <div class="card-unit">★ 本周热度</div>
    </div>
  </div>
  <div class="stats">本周热度 <span>{{TOTAL_STARS}}</span>★ · <span>{{PROJECT_COUNT}}</span> 个项目 · <span>{{CATEGORY_COUNT}}</span> 个分类</div>
</div>
</body>
</html>
```

模板中的占位符在运行时用实际数据替换。

## Step 5: 保存文章 + 项目清理

> **文章项目不使用视频 DAG 流水线。** 仅保留核心产出物，清理中间产物。

```bash
mkdir -p ${OUTPUT_DIR}
```

将文章保存为：
- `${OUTPUT_DIR}/article.md` — Markdown 原文（可直接粘贴到知乎编辑器）
- `${OUTPUT_DIR}/cover.png` — 文章封面图（Step 4 生成）

保存完成后，立即执行 `clipforge/_cleanup-rules` 清理中间产物，保留核心产出物（article.md、cover.png、content.md、raw_trending.json）。磁盘占用应 < 5 MB。

## Step 6: 自续期

执行 `clipforge/_cron-renew` 定时任务自续期模式，任务关键词为 `github-weekly-zhihu`。

## 输出

完成后汇报：
```
📝 GitHub 每周知乎文章已生成
周次：YYYY-MM-DD 这周
文件：workspace/<YYYY>/<MM>/<DD>/github-zhihu/article.md
封面：workspace/<YYYY>/<MM>/<DD>/github-zhihu/cover.png
项目数：X 个（分 X 类）
文章字数：约 XXXX 字
定时任务续期：✅ Job ID xxxxx
```
