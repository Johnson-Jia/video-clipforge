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

### hashtags

- `#GitHub热门`
- `#程序员`
- `#开源`
- `#AI`
- `#科技`

### comment_template

```
评论区格式：
1. 项目英文名（每行一个）
2. "在 GitHub 搜项目名就能找到"
3. 不放完整链接
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
