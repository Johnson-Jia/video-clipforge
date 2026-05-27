---
name: "GitHub 开源项目"
description: "GitHub Trending — 数据获取、选取策略、设计风格、旁白规则、叙事模板"
id: "github"
section: "content-design-narration"
version: "2.1.0"
type: CATEGORY
category_id: "github"
rules_lib_ref: "_rules-lib/global-rules.yaml"
patterns_ref: "_patterns/store.yaml"
---

# GitHub 分类配置 — 内容 + 设计 + 旁白

> **消费方：** SubAgent-1（env-check → content → design → narration）

## Boundary Overrides — 分类特有规则

### 数据获取规则（覆盖通用 Stage 1 规则）
1. **双源交叉验证** — 至少两个数据源交叉验证，项目名交集 ≥ 80% ← `R-GITHUB-001` [HARD/EXPERIENTIAL]
   ↳ 校验：脚本输出和 web-reader 输出的项目名交集 ≥ 80%
2. **数据量门禁** — 获取项目数 ≥ 8 ← `R-GITHUB-002` [HARD/EXPERIENTIAL]
   ↳ 校验：项目列表长度 ≥ 8
3. **web-reader 禁缓存** — 使用 web-reader 时必须设置 no_cache: true ← `R-GITHUB-003` [HARD/EXPERIENTIAL]
4. **与前次对比** — 获取数据后必须与上一次视频的项目列表对比 ← `R-GITHUB-004` [HARD/EXPERIENTIAL]
   ↳ 校验：对比记录存在

### 选取策略规则
5. **标准模式选取 5-6 个项目** — 按钩子潜力 > 新上榜 > 涨星加速 > 连续霸榜 > 跨圈补充排序 ← `R-GITHUB-005` [HARD/EXPERIENTIAL]
6. **重复率控制** — 与前次视频项目重复率 > 70% 时，减少至 4-5 个项目 ← `R-GITHUB-006` [SOFT/EXPERIENTIAL]

### 数据质量规则
7. **数据优先于描述** — 展示具体数据（Star 数、涨星量）而非主观描述 ← `R-GITHUB-007` [SOFT/EXPERIENTIAL]
8. **反直觉角度挖掘** — 每个项目检查 4 个反直觉维度，写入 contrarian_angle 字段 ← `R-GITHUB-008` [SOFT/EXPERIENTIAL]
   ↳ 关联 Pattern: P-002（反直觉描述）

## Gate Overrides — 分类特有门禁

### 合规门禁（覆盖通用 Stage 1 门禁）
- [ ] `data_quantity` — ≥ 8 个项目（R-GITHUB-002）
- [ ] `cross_source_validation` — 双源交叉验证 ≥ 80% 交集（R-GITHUB-001）
- [ ] `web_reader_no_cache` — web-reader 设置了 no_cache: true（R-GITHUB-003）
- [ ] `previous_comparison` — 与前次视频列表对比完成（R-GITHUB-004）

## Pattern References — 关联经验模式

从 `_patterns/store.yaml` 中引用以下模式：
- `P-001`（量化钩子）— 适用于 Stage 3 hook 场景
- `P-002`（反直觉描述）— 适用于 Stage 3 旁白 + Stage 7 文案
- `P-003`（8层全屏卡片）— 适用于 Stage 6 标准模式项目展示
- `P-004`（5标签跨圈）— 适用于 Stage 7 抖音文案标签
- `P-005`（45-55秒甜区）— 适用于 Stage 3 时长控制

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
| **1 — 钩子潜力** | 项目具有反直觉/颠覆性特征（如"WiFi 做空间感知不用摄像头"），能在文案中形成强钩子 | 1-2 个 | 正常展开 + 优先分配反直觉钩子句 |
| **2 — 新上榜** | 首次出现在 trending 榜单，或上次视频中未出现 | 2-3 个 | 正常展开介绍（6-8s） |
| **3 — 涨星加速** | 今日涨星速率明显加快（相比前几日） | 1-2 个 | 正常展开介绍 |
| **4 — 连续霸榜** | 前次视频已详细介绍，仍在榜上 | 1-2 个 | 快速带过（3-4s），提及增量即可 |
| **5 — 跨圈补充** | 覆盖不同语言/领域，确保 ≥3 个不同方向（AI/安全/硬件/工具/科研等） | 按需 | 视新上榜/老项目而定 |

**选取流程：**

1. 获取当日 trending 数据（`.claude/commands/clipforge/scripts/github_trending.py` 或 API）
2. **检查前次视频项目列表**：读取同类型最近一次视频的 `raw_trending.json` 或 `narration_segments.json`，识别哪些项目上次已介绍
3. **标记三类项目**：新上榜 / 涨星加速 / 连续霸榜
4. **组合选取 5-6 个**：优先新上榜和涨星加速，补入霸榜项目维持信息连续性
5. **调整 hook 文案**：如重复率 >50%，hook 改为强调"新增"（如"今天又冲上来三个新的"）；如以新项目为主，hook 用具体数字锚定（如"今天涨星最高的一个项目，单日近四千"）；如涨星爆发，可用情绪化表达（如"今天涨星直接炸了"）

**前次视频不存在时**（首次制作）：直接取 TOP 5-6，按排名排序。

**重复率过高时**（>70%）：可减少项目数至 4-5 个，缩短总时长，或引入"周榜"/"月榜"视角切换。

### weekly_strategy — 周榜优化策略（数据驱动）

> **数据诊断**：周榜在抖音播放量仅为日榜的 9%（均 1,815 vs 20,276），视频号 70%，小红书 33%。
> 核心问题：信息密度过高（10-17 个项目），标题缺乏紧迫感和数据钩子。

#### 标题策略
- ❌ 禁止："本周 GitHub 最火开源项目盘点"（无数据钩子，无紧迫感）
- ✅ 必须包含具体数字："本周涨星最猛的 5 个项目，最高的涨了 N 万星"
- ✅ 必须有"本周之最"的单一故事线，不是分类罗列
- ✅ 用"本周最炸裂/最反直觉/最实用"等超级latives制造期待

#### 场景结构（精选 TOP 5，不是 10-17）

| 场景 | 角度 | 时长 | 说明 |
|------|------|------|------|
| hook | "本周之最"数据钩子 | 5s | "本周 N 个项目，涨星最高的飙了 N 万" |
| 第1名 | 本周最炸裂 | 10s | 最大涨星/最多关注的单一项目 |
| 第2名 | 本周最反直觉 | 10s | 最出人意料的项目 |
| 第3名 | 本周最实用 | 10s | 最能解决实际问题的项目 |
| 第4-5名 | 快速盘点 | 8s | 2个项目快速带过 |
| CTA | 关注引导 | 3s | |

**目标**：总时长 50-55s，5 个项目精选 + 每个项目配"周涨星数"数据卡片

#### 与日榜的差异化
- 日榜强调"今天发生了什么"（紧迫性）
- 周榜强调"这周最值得关注的"（精选感）
- 周榜的 hook 必须用周维度数据（"本周涨了 N 万星"），不用日维度
- 周榜每个项目增加"连续 N 天上榜"或"本周新上榜"标记

#### 数据卡片设计
周榜的项目卡片需增加日榜没有的信息：
- 周涨星总数（vs 日榜的日涨星）
- 连续上榜天数
- 本周排名变化（↑/↓/new）

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
- "今天 N 个项目，最高一天涨近 X 千星"
- "今天涨星直接炸了"

> **每日 hook 不得与前一天相同或高度相似。** 从不同角度轮换切入（数据锚定、新项目数、领域趋势、连续霸榜、情绪表达等），避免连续多天使用同一种话术风格。"炸了""霸榜"等表达可用，但不能天天用。

### special_rules

- **老项目不重复展开**：连续霸榜的项目只用一句话提及增量（"上次说的 XX 又涨了两千星"），不重复介绍功能
- **数据优先于描述**：用 Star 数、涨星数等数据说话，不用"太强了"等主观评价
- **反直觉角度挖掘**：每个项目必须挖掘至少一个"反直觉/颠覆常识"的角度。判断方法：
  - 该项目是否用非常规技术做常规事？（如 WiFi 信号代替摄像头）
  - 该项目是否在离线/本地完成通常需要云端的事？（如离线 TTS）
  - 该项目是否让普通人能做专业级的事？（如家用路由器做空间感知）
  - 挖掘结果写入 `narration_segments.json` 的 `contrarian_angle` 字段，用于旁白和发布文案

### word_count_range

标准模式（日榜）：250-380 字。周榜模式：280-350 字（精选 5 个，每个更充分）。深度解析模式：350-500 字（论述更完整）。

## narrative

### default_template

当未明确匹配时，默认使用 `contrast-arc` 模板。

### humor_rules

- 用生活类比而非直白吐槽（"这个 PR 就像在火锅里加了冰淇淋"）
- 开发者文化梗优先（"据说这个 bug 的工龄比实习生还长"）
- 避免低俗、人身攻击、政治敏感
- 吐槽力度：中等偏轻（"涨星比发际线退得快"可以，"这代码写得像💩"不行）
- 每期视频至少 30% 的段落包含幽默元素（旁白或视觉）

### character_presence

true — GitHub 系列视频启用码力角色。

### immersion_mapping

根据内容标签自动选择沉浸模式：

| 内容标签 | 沉浸模式 | 视觉风格 |
|---------|---------|---------|
| AI / LLM / Agent | `hyper-pace` | 快速剪辑 + 密集粒子 + 霓虹 #00D4FF |
| 小众宝藏 / 新发现 | `hidden-gem` | 渐进揭示 + 温暖光效 + 复古 #FFB800 |
| 重大更新 / 里程碑 | `mega-update` | 3D 场景 + 大气粒子 + 暗色 #7B2FBE |
| 对比 / VS / 评测 | `versus` | 分屏对比 + 脉冲能量 + 硬朗 #FF3B30 |
| 开发者故事 / 历程 | `story-time` | 插画风 + 柔和过渡 + 暖色 #34C759 |
| 有趣工具 / 有意思 | `fun-tool` | 彩色弹跳 + 幽默角色 + 亮色 |

匹配规则：按 `content_ready.txt` 中项目的主要分类标签匹配。AI 类项目 >50% 时用 `hyper-pace`；首屏出现"对比"关键词用 `versus`；其余按默认 `contrast-arc`。
