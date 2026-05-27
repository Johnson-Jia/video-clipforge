---
name: "GitHub 开源项目"
description: "GitHub Trending — 标签、评论区、封面、数据验证"
id: "github"
section: "delivery"
version: "2.1.0"
type: CATEGORY
category_id: "github"
---

# GitHub 分类配置 — 交付

> **消费方：** SubAgent-4（delivery → cleanup）

## delivery

### hashtags — 平台差异化标签

#### 抖音标签（泛流量导向，5 个）
- `#GitHub热门` `#程序员` `#开源` `#AI` `#科技`

#### 视频号标签（职业导向，5 个）
- `#GitHub` `#开源项目` `#AI` `#程序员` `#技术管理`

#### 小红书标签（搜索SEO导向，8-10 个）
- `#GitHub` `#开源项目推荐` `#程序员必看` `#AI工具推荐` `#编程效率`
- `#开发者工具` `#开源项目合集` `#GitHub每日热门` `#代码工具` `#科技分享`

#### 标签使用规则
- 抖音：5 个标签，泛流量 + 精准各半
- 视频号：5 个标签，偏职业导向
- 小红书：8-10 个标签，搜索热词优先（长尾流量）

### comment_template — 平台差异化评论区

#### 抖音评论区
```
项目英文名（每行一个）
"在 GitHub 搜项目名就能找到"
```

#### 视频号评论区
```
项目英文名 + 一句话定位（每行一个）
"觉得有用就转发给团队看看 👆"
```

#### 小红书评论区
```
项目英文名 + Star 数 + 适合人群（每行一个）
"整理不易，建议收藏 💾 用到的时候方便找"
```

### cover_badge

"GitHub 今日热门"

### cover_scene_label

"今日GitHub榜单"

## shared-rules

### url_validation

当从网络 URL 获取 GitHub 数据作为视频素材时，**必须通过至少两个独立数据源交叉验证**，防止缓存、过期或错误数据进入视频。

| 规则 | 说明 |
|------|------|
| 至少两个数据源 | 一个 MCP/Web 工具 + 一个脚本直连（Python requests / curl 等） |
| 交叉比对 ≥ 80% | 两个数据源的核心数据（项目名、标题等）交集 ≥ 80% |
| web-reader 必须禁缓存 | 使用 `mcp__web_reader__webReader` 时设置 `no_cache: true` |
| 数据量门禁 | 数据项数量必须 ≥ 8 个项目，否则停止执行 |
| 与前次对比 | 与前一次数据比对，完全相同则告警缓存命中 |

**实施方式：**

- **优先写脚本**：用 Python `requests` 或 `curl` 直接 HTTP 抓取，绕过所有中间层缓存
- **MCP 做验证**：用 web-reader 等工具作为第二数据源交叉确认
- **已有脚本的场景**（如 `.claude/commands/clipforge/scripts/github_trending.py`）：直接运行脚本，按脚本输出的校验报告确认数据质量
- **无现成脚本的场景**：临场写一个轻量脚本或用 `curl` + `jq` 抓取验证

### Red Flags（GitHub 特定）

| 信号 | 说明 | 规则 ID |
|------|------|---------|
| URL 数据未交叉验证 | 至少两个独立数据源，缓存/过期数据会进入视频 | R-GITHUB-001 |
| 数据量 < 最低阈值 | 项目数少于 8 个时停止，数据不足无法支撑标准模式视频 | R-GITHUB-002 |
| web-reader 未禁缓存 | 必须设置 `no_cache: true`，否则可能获取过期数据 | R-GITHUB-003 |
| 与前次数据完全相同 | 说明命中缓存，需刷新数据源 | R-GITHUB-004 |

### Common Rationalizations（GitHub 特定）

| 借口 | 事实 |
|------|------|
| "这些数据看起来合理" | 看起来合理 ≠ 数据准确。要求至少两个独立数据源交叉验证 |
| "README badge 显示的 Star 数够用了" | README badge 是图片或缓存数据，不可靠。必须用 `gh api` 获取实时数据 |
| "跳过数据验证，直接开始" | 错误 Star 数进入视频 → 观众评论区纠正 → 伤害频道可信度 |
| "之前的项目列表不用检查" | 不检查重复 → 连续两期视频介绍同样的项目 → 观众流失 |
