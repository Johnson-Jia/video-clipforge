---
name: "GitHub 开源项目"
description: "GitHub Trending 热门项目盘点和深度解析视频"
id: "github"
---

<!-- CONFIG-START: 机器可解析的配置值，供 render_stage.py 和引擎模块加载 -->
audio:
  default_voice: "zh-CN-YunjianNeural"
  default_rate: "+25%"
  voice_override: true

narration:
  hook_example: "{M}月{D}日涨星最快的几个项目，直接炸了"
  topic_example: "这周 GitHub 涨星最快的项目是..."
  hook_json_example: "{M}月{D}日涨星最快的几个项目，直接炸了"
  cta_purpose: "开源信息"
  word_count_range: [250, 380]
  hook_anchors:
    - "涨星最快"
    - "N 个项目"
    - "天涨近"
    - "千星"
    - "万星"
    - "单日涨"
    - "最高涨星"
    - "涨星最多"
  metric_layer: "| 6. 星标增量 | 单日涨星数 | 强调色（橙/金） | \"+3941 ★\" |"
  contrarian_questions: |
    对每个项目回答以下问题，提取反直觉角度：
    1. **非常规手段**：是否用不常见的技术做常见的事？
    2. **离线/本地替代**：是否在本地完成通常需要云端的功能？
    3. **平民化专业能力**：是否让普通人能做专业级的事？
    4. **领域跨界**：是否把 A 领域的技术用在了 B 领域？
  narration_txt_example: |
    {M}月{D}日涨星最快的几个项目，直接炸了
    第一个项目，{项目描述}
    {后续项目旁白}
    关注我，下期见
  weekly_narration_txt_example: |
    第22周周榜（5月26日-6月1日），最高一周涨了近X千星
    {分类1的项目描述}
    {后续分类}
    第22周周榜就到这，关注GitHub星探，下周见

delivery:
  hashtags: "#GitHub热门 #程序员 #开源 #AI #科技"
  cover_badge: "GitHub 热门项目"
  cover_scene_label: "GitHub 榜单速览"
  cover_data_examples: "+3973 最高涨星 / 198K 最高总星"
  hook_template_example: "{M}月{D}日涨星最猛的 6 个项目，AI 占了一半"
  tag_strategy: |
    | 核心圈标签 | #GitHub | 命中目标受众 |
    | 领域标签 | #开源 | 命中开源圈 |
    | 热点标签 | #AI | 命中当前热点圈层 |
    | 身份标签 | #程序员 | 命中职业身份圈 |
    | 泛流量标签 | #科技 | 获取泛流量触达 |
  comment_template: |
    评论区格式：
    1. 项目英文名（每行一个）
    2. "在 GitHub 搜项目名就能找到"
    3. 不放完整链接

design:
  default_style: "暗色科技风"
  color_bias: "冷色为主（深蓝/深紫），强调色用暖色（橙色/金色）"

content:
  optional_deps: ["gh"]

shared_rules:
  data_example: "33K Star"
  hook_data_example: "{M}月{D}日涨星最猛的 N 个项目"
  hook_emotion_example: "{M}月{D}日涨星直接炸了"
<!-- CONFIG-END -->

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
| **1 — 钩子潜力** | 项目具有反直觉/颠覆性特征（如"WiFi 做空间感知不用摄像头"），能在文案中形成强钩子 | 1-2 个 | 正常展开 + 优先分配反直觉钩子句 |
| **2 — 新上榜** | 首次出现在 trending 榜单，或上次视频中未出现 | 2-3 个 | 正常展开介绍（6-8s） |
| **3 — 涨星加速** | 单日涨星速率明显加快（相比前几日） | 1-2 个 | 正常展开介绍 |
| **4 — 连续霸榜** | 前次视频已详细介绍，仍在榜上 | 1-2 个 | 快速带过（3-4s），提及增量即可 |
| **5 — 跨圈补充** | 覆盖不同语言/领域，确保 ≥3 个不同方向（AI/安全/硬件/工具/科研等） | 按需 | 视新上榜/老项目而定 |

**选取流程：**

1. 获取当日 trending 数据（`.claude/commands/clipforge/scripts/github_trending.py` 或 API）
2. **检查前次视频项目列表**：读取同类型最近一次视频的 `raw_trending.json` 或 `narration_segments.json`，识别哪些项目上次已介绍
3. **标记三类项目**：新上榜 / 涨星加速 / 连续霸榜
4. **组合选取 5-6 个**：优先新上榜和涨星加速，补入霸榜项目维持信息连续性
5. **调整 hook 文案**：如重复率 >50%，hook 改为强调"新增"（如"又冲上来三个新的"）；如以新项目为主，hook 用具体数字锚定（如"涨星最高的一个项目，单日近四千"）；如涨星爆发，可用情绪化表达（如"涨星直接炸了"）

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
2. **继续流程不中断**：数据缺失不应阻塞视频制作，可在旁白中用定性描述替代精确数字（如"这个项目最近涨星很快"替代"+500 Star"）
3. **记录告警**：在 `design.md` 末尾记录 `> ⚠️ GitHub 数据获取失败，使用估算值`，供后续阶段知晓数据可靠性

### data_validation — 三源交叉验证

数据采集时必须通过至少两个独立数据源交叉验证：

| 数据源 | 方式 | 用途 |
|--------|------|------|
| Python 脚本（主） | `scripts/github_trending.py --output-dir DIR --date DATE --since daily\|weekly` | 无缓存直连抓取，输出 `raw_trending.json` |
| web-reader MCP（验证） | `mcp__web_reader__webReader`，url: `https://github.com/trending`，**必须 `no_cache: true`** | 交叉确认主数据源 |
| 昨日数据（比对） | 读取前一天 `raw_trending.json`（如果存在） | 检测缓存命中 |

**验证规则**：
- 主数据源与验证源项目名交集 >= 80% → 通过
- daily 模式：与昨日数据完全相同 → 告警缓存命中，停止执行
- weekly 模式：Weekly 页面与日榜交集 >= 60% 为正常

### quality_gates — 数据质量门禁

以下任一条件不满足则**停止执行并报错**：

| 条件 | daily | weekly |
|------|-------|--------|
| 最低项目数 | >= 8 | >= 15 |
| 与昨日不完全相同（如存在） | 必须 | — |
| 活跃度（30 天内有更新） | >= 80% | >= 80% |

### monthly_inventory — 月度清单管理

每日数据抓取后立即写入月度清单（在 DAG 长流程之前，避免 context 压缩丢失）：

- **文件路径**：`workspace/sources/github-trending/${MONTH}.md`（如 `2026-05.md`）
- **追加格式**：日期标题 `### YYYY-MM-DD` + 项目表格（项目名 / Star / 今日涨幅 / 语言 / 描述）
- **写入后验证**：必须确认当日日期标题已存在

### weekly_mode — 周汇总模式规则

当内容模式为"周汇总"时（weekly trending 或知乎文章），适用以下规则：

**选取与分组**：
- 选取 12-15 个项目（按周涨幅排序）
- 按编程语言/领域分组，每组 3-4 个项目
- 不同分类可用不同色彩区分（AI 冷色系、前端暖色系等），整体保持协调

**场景与文案**：
- 场景数 6-7 个：hook → 分类1 → 分类2 → 分类3 → 分类4 → 趋势总结 → CTA
- 字数 300-450 字，时长 45-60 秒

**周次标注（必选）**：
- hook 开头必须带"第N周"或日期范围（如"5月26日-6月1日"），不得只用"本周"
- CTA 结尾带周次（如"第22周周榜就到这，关注GitHub星探，下周见"）
- SubAgent prompt 中会注入 `week_context.txt`，读取后自然嵌入旁白

**数据标注**：
- 仅在 Weekly 页面出现但不在日榜中的项目标注为"本周新上榜"
- 从日榜数据中提取各项目"连续上榜天数"作为持续热门标签

### preparation_rules — 内容整理规则

将原始数据整理为中文短视频素材时遵循：

- 项目名保留英文（如 `facebook/react`）
- 描述翻译成中文（简洁口语化）
- 按热度排序
- 开头用震撼数据做钩子（如"一天涨近四千星"）

## design

### default_style

暗色科技风。背景以深蓝/深紫渐变为基底，强调色偏橙蓝（`#FF8C32` 橙 + `#4DA8DA` 蓝），双光晕（暖冷色调），字体无衬线粗体。

### color_bias

冷色为主（深蓝/深紫），强调色用暖色（橙色/金色）形成对比。科技感光晕效果。

## narration

### hook_templates

> **数据来源（2026-05-27 三平台分析）：** 抖音 58 条视频标题模式与播放量强相关。反直觉/冲突模式平均 46,596 播放（8x 基线），数字钩子模式平均 42,783 播放（8x），直接叙述模式平均 5,363（基线），疑问/互动模式平均 1,195（最低）。

**优先级排序（从高到低）：**

| 优先级 | 模式 | 平均播放 | 模板 | 适用条件 |
|--------|------|---------|------|---------|
| **1** | 反直觉/冲突 | 46,596 | "用 WiFi 信号感知人体，完全不用摄像头" | 项目有非常规技术/跨界应用 |
| **2** | 数字钩子 | 42,783 | "{M}月{D}日涨星最快的 N 个项目" / "一天涨近 X 千星" | 有震撼数据可锚定 |
| **3** | 信号/注意 | 5,093 | "这个项目直接霸榜了" / "注意这个新项目" | 无反直觉角度也无震撼数据时 |
| **4** | 直接叙述 | 5,363 | "来看这 N 个开源项目" | **避免使用** — 播放量基线 |
| **5** | 疑问/互动 | 1,195 | "你知道这个项目吗？" | **禁止使用** — 播放量最低 |

**具体模板：**

**优先级 1 — 反直觉/冲突**（首选，必须有反直觉角度时使用）
- "用 {非常规手段} 做 {常见事}，{颠覆性结果}"
- "{常见问题}，但这个项目用 {意外方法} 解决了"
- "不用 {常见依赖}，也能做到 {专业级能力}"

**优先级 2 — 数字钩子**（有震撼数据时使用）
- "{M}月{D}日涨星最快的 N 个项目，最高一天涨近 X 千星"
- "{M}月{D}日 N 个项目，AI 占了一半"
- "这个项目，单日涨星 X 千"

**优先级 3 — 信号/注意**（兜底，无上述条件时）
- "这个项目直接霸榜了"
- "N 个新项目冲上来了"

> **选择规则：** 优先级 1 可用时必须用优先级 1。无反直觉角度时用优先级 2。每日 hook 不得与前一天相同或高度相似。"炸了""霸榜"等表达可用，但不能连续两天使用。

### special_rules

- **老项目不重复展开**：连续霸榜的项目只用一句话提及增量（"上次说的 XX 又涨了两千星"），不重复介绍功能
- **数据优先于描述**：用 Star 数、涨星数等数据说话，不用"太强了"等主观评价
- **反直觉角度挖掘**：每个项目必须挖掘至少一个"反直觉/颠覆常识"的角度。判断方法：
  - 该项目是否用非常规技术做常规事？（如 WiFi 信号代替摄像头）
  - 该项目是否在离线/本地完成通常需要云端的事？（如离线 TTS）
  - 该项目是否让普通人能做专业级的事？（如家用路由器做空间感知）
  - 挖掘结果写入 `narration_segments.json` 的 `contrarian_angle` 字段，用于旁白和发布文案

### word_count_range

标准模式：250-380 字。深度解析模式：300-450 字。

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

"GitHub 热门项目"

### cover_scene_label

"GitHub 榜单速览"

### zhihu_article — 知乎文章模式

当输出为知乎文章（非视频）时，遵循以下规则：

**文章结构**：
```markdown
# YYYY年M月第N周 GitHub 热门开源项目盘点

> 一句话导语（本周趋势概括）

## 本周趋势速览
| 趋势 | 说明 |
|------|------|
| 最大赢家 | 涨星最多的项目 + 数据 |
| 新面孔 | 首次上榜的项目 |
| 持续热门 | 连续多周上榜的项目 |

## 项目详细解读
（按分类分组，每组 2-4 个项目）

### 分类名称（如"AI & 智能体"）

#### N. owner/repo

**项目简介：** 2-3 句话说明项目是做什么的、解决什么问题。

**核心亮点：**
- 亮点1（具体功能/特性）
- 亮点2（性能/架构优势）
- 亮点3（适用场景）

**快速上手：** 安装/使用命令

**适合人群：** XX方向开发者

> Star: XX,XXX | Fork: X,XXX | 协议: MIT | 语言: Python | 本周涨幅: +X,XXX

## 本周总结
- 2-3 句话总结本周开源趋势
- 推荐 1-2 个最值得关注的项目及理由
```

**写作要求**：
1. **深度优先** — 每个项目至少 150 字解读，不是简单罗列
2. **实用导向** — 尽量包含安装命令、使用示例、适用场景
3. **数据说话** — 用 Star 数、Fork 数、Issues 数量化项目热度
4. **中性客观** — 描述功能和特点，不使用"最强"、"必装"等极限词
5. **搜索友好** — 标题和正文包含"GitHub"、"开源"、"项目"等搜索高频词
6. **不点名商业产品/品牌** — 不提 GPT、DeepSeek 等品牌名，用"大语言模型"、"AI 助手"等类别词。但项目名本身包含品牌名（如 DeepSeek-TUI）可如实引用
7. **项目链接可放** — 知乎不像抖音限制 URL，每个项目标题直接超链接到 GitHub
8. **数据来源透明** — 文章末尾注明数据来源，标注周涨幅以 Weekly 页面为准

**分类策略**：

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

### zhihu_cover_template — 知乎封面模板

**设计规范**：
- 尺寸：1920×1080（16:9 横版，知乎文章封面标准比例）
- 风格：GitHub Dark 主题（`#0d1117` 底色 + `#00e5a0` 强调色 + `#f0883e` 星标色）
- 字体：Inter / JetBrains Mono / PingFang SC

**封面布局**：
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

**实现**：在项目目录创建 `cover.html`，用 Puppeteer 或 HyperFrames 截图生成 `cover.png`。

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
