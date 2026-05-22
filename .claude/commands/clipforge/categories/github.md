---
name: "GitHub 开源项目"
description: "GitHub Trending 热门项目盘点和深度解析视频"
id: "github"
---

# GitHub 分类配置

## content

### data_source

当内容涉及 **GitHub 开源项目** 时，**必须额外获取准确的实时统计数据**（Star、Fork、语言等），不能依赖 README 中的 badge 或猜测。

### 数据来源优先级

| 优先级 | 来源 | 方式 |
|--------|------|------|
| **1** | GitHub CLI (`gh`) | `gh api repos/{owner}/{repo} --jq '{stars, forks, language, description}'` — 数据最准确、最实时 |
| **2** | 智谱 MCP | 如果环境中有智谱 MCP 工具，调用获取项目完整信息 |
| **3** | Web 抓取主目录 | 用 WebReader 访问 `https://github.com/{owner}/{repo}` 从页面解析 Star 数 |

### GitHub CLI 安装引导

如果 `gh` 未安装，引导用户安装：

```bash
# Windows
winget install GitHub.cli
# macOS
brew install gh
# Linux
sudo apt install gh    # Debian/Ubuntu
sudo dnf install gh    # Fedora
```

安装后需登录：

```bash
gh auth login
```

> 也可以用 `gh auth login --with-token` 配合 Personal Access Token 免交互登录。

### 数据获取命令

```bash
# 获取项目核心数据
gh api repos/{owner}/{repo} --jq '{stars: .stargazers_count, forks: .forks_count, language: .language, description: .description, license: .license.spdx_id, open_issues: .open_issues_count}'

# 获取贡献者数量（--paginate 自动翻页获取完整数量）
# 注意：大型仓库可能触发 API 速率限制，此时可跳过此指标
gh api repos/{owner}/{repo}/contributors --paginate --jq '.[].id' | wc -l
```

> **注意：** README 页面（`/blob/main/README.md`）中的 Star badge 是图片或缓存数据，**不可靠**。`gh api` 返回的是 GitHub 实时数据，优先使用。

### selection_strategy — 标准模式（5-6 个项目）

从 trending 数据中选取 5-6 个项目，遵循以下优先级：

| 优先级 | 选取条件 | 预期数量 | 场景处理 |
|--------|---------|---------|---------|
| **1 — 新上榜** | 首次出现在 trending 榜单，或上次视频中未出现 | 2-3 个 | 正常展开介绍（6-8s） |
| **2 — 涨星加速** | 今日涨星速率明显加快（相比前几日） | 1-2 个 | 正常展开介绍 |
| **3 — 连续霸榜** | 前次视频已详细介绍，仍在榜上 | 1-2 个 | 快速带过（3-4s），提及增量即可 |
| **4 — 领域/语言补充** | 覆盖不同语言/领域，避免全同质 | 按需 | 视新上榜/老项目而定 |

**选取流程：**

1. 获取当日 trending 数据（`scripts/github_trending.py` 或 API）
2. **检查前次视频项目列表**：读取同类型最近一次视频的 `raw_trending.json` 或 `narration_segments.json`，识别哪些项目上次已介绍
3. **标记三类项目**：新上榜 / 涨星加速 / 连续霸榜
4. **组合选取 5-6 个**：优先新上榜和涨星加速，补入霸榜项目维持信息连续性
5. **调整 hook 文案**：如重复率 >50%，hook 改为强调"新增"（如"今天又冲上来三个新的"）；如以新项目为主，hook 强调"涨星"（如"今天涨星直接炸了"）

**前次视频不存在时**（首次制作）：直接取 TOP 5-6，按排名排序。

**重复率过高时**（>70%）：可减少项目数至 4-5 个，缩短总时长，或引入"周榜"/"月榜"视角切换。

### deep_research — 单项目深度调研

当视频只聚焦一个项目时，基础数据（Star/Fork/Language）不足以支撑 45-60 秒的深度内容。需要额外调研以下维度：

| 维度 | 调研内容 | 用途场景 |
|------|---------|---------|
| **核心原理** | 项目的技术原理是什么？用什么技术/算法/方法？ | `how` 场景 |
| **核心能力** | 有哪些关键功能和性能指标？准确率/精度/速度等 | `capabilities` 场景 |
| **应用场景** | 哪些行业/场景最需要这个项目？举 2-3 个具体例子 | `usecases` 场景 |
| **技术架构** | 用什么语言/框架写的？硬件需求？部署门槛？ | `tech` 场景 |
| **独特优势** | 和同类项目相比，独特卖点是什么？（隐私/性能/易用性） | `privacy`/`capabilities` 场景 |

**调研方法：**

```bash
# 1. 获取 README（最核心的技术信息来源）
gh api repos/{owner}/{repo}/readme --jq '.content' | base64 -d

# 2. 获取项目 topics（分类和关键词）
gh api repos/{owner}/{repo} --jq '{topics: .topics, language: .language}'

# 3. 获取最近 release 信息（新功能/版本号）
gh api repos/{owner}/{repo}/releases --jq '.[0] | {tag_name, body}'

# 4. 浏览项目目录结构（了解架构规模）
gh api repos/{owner}/{repo}/contents/ --jq '.[].name'
```

对于 README 内容较长的项目，重点提取：
- **Architecture / How it works** 段落 → 原理
- **Features / Capabilities** 段落 → 核心能力
- **Use Cases / Applications** 段落 → 应用场景
- **Requirements / Installation** 段落 → 部署门槛
- **Benchmark / Performance** 段落 → 性能数据

**信息密度要求：**

| 场景 | 需要的信息密度 |
|------|--------------|
| `what` | 一句话精确定义（不说"一个工具"，而是"用 WiFi 电波感知人体的开源项目"） |
| `how` | 1-2 句通俗原理解释（类比 > 术语），让人"恍然大悟" |
| `capabilities` | 3+ 个具体数据/指标（"准确率 100%"、"精度 ±1 BPM"、"支持 N 人追踪"） |
| `usecases` | 2-3 个有画面感的场景（"养老院不用摄像头就能监测老人跌倒"） |
| `tech` | 具体的技术栈和硬件需求（"几个 ESP32 芯片"、"Rust 编写"、"58K Star"） |

### fallback — 全部来源失败时的处理

如果三个优先级来源全部失败（`gh` 未安装 + 智谱 MCP 不可用 + Web 抓取被限流），执行以下兜底：

1. **标记数据为估算值**：在内容中使用"约"、"左右"等措辞标注 Star 数（如"约 30K Star"），来源标注为"README badge（非实时数据）"
2. **继续流程不中断**：数据缺失不应阻塞视频制作，可在旁白中用定性描述替代精确数字（如"这个项目最近涨星很快"替代"今天 +500 Star"）
3. **记录告警**：在 `design.md` 末尾记录 `> ⚠️ GitHub 数据获取失败，使用估算值`，供后续阶段知晓数据可靠性

## design

### default_style

暗色科技风。背景以深蓝/深紫渐变为基底，强调色偏橙蓝（`#FF8C32` 橙 + `#4DA8DA` 蓝），双光晕（暖冷色调），字体无衬线粗体。

### color_bias

冷色为主（深蓝/深紫），强调色用暖色（橙色/金色）形成对比。科技感光晕效果。

## narration

### hook_templates

- "今天涨星最快的 N 个项目"
- "这个项目，直接霸榜了"
- "N 个新项目冲上来了"
- "涨星直接炸了"

### special_rules

- **老项目不重复展开**：连续霸榜的项目只用一句话提及增量（"上次说的 XX 又涨了两千星"），不重复介绍功能
- **数据优先于描述**：用 Star 数、涨星数等数据说话，不用"太强了"等主观评价

### word_count_range

标准模式：200-350 字。深度解析模式：300-450 字。

## audio

### default_voice

`zh-CN-YunjianNeural`

### default_rate

`+25%`

### voice_override

true — GitHub 系列视频固定使用 YunjianNeural +25%，不需要查通用声音选择表。

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
- **已有脚本的场景**（如 `scripts/github_trending.py`）：直接运行脚本，按脚本输出的校验报告确认数据质量
- **无现成脚本的场景**：临场写一个轻量脚本或用 `curl` + `jq` 抓取验证

### Red Flags（GitHub 特定）

| 信号 | 说明 |
|------|------|
| URL 数据未交叉验证 | 至少两个独立数据源，缓存/过期数据会进入视频 |
| 数据量 < 最低阈值 | 项目数少于 8 个时停止，数据不足无法支撑标准模式视频 |
| web-reader 未禁缓存 | 必须设置 `no_cache: true`，否则可能获取过期数据 |
| 与前次数据完全相同 | 说明命中缓存，需刷新数据源 |

### Common Rationalizations（GitHub 特定）

| 借口 | 事实 |
|------|------|
| "这些数据看起来合理" | 看起来合理 ≠ 数据准确。要求至少两个独立数据源交叉验证 |
| "README badge 显示的 Star 数够用了" | README badge 是图片或缓存数据，不可靠。必须用 `gh api` 获取实时数据 |
| "跳过数据验证，直接开始" | 错误 Star 数进入视频 → 观众评论区纠正 → 伤害频道可信度 |
| "之前的项目列表不用检查" | 不检查重复 → 连续两期视频介绍同样的项目 → 观众流失 |
