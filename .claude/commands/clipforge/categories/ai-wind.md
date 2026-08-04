---
name: "AI 风向标"
description: "每日 AI 开源项目专项盘点视频（GitHub AI 子系列）"
id: "ai-wind"
---

<!-- CONFIG-START: 机器可解析的配置值，供 render_stage.py 和引擎模块加载 -->
audio:
  default_voice: "zh-CN-YunjianNeural"
  default_rate: "+25%"
  voice_override: true

narration:
  hook_example: "{M}月{D}日 GitHub 上 AI 项目又杀疯了，有个让 AI 自己干完整套活"
  topic_example: "今天的 AI 开源项目，方向是..."
  hook_json_example: "{M}月{D}日 GitHub 上 AI 项目又杀疯了，有个让 AI 自己干完整套活"
  cta_purpose: "AI 开源信息"
  word_count_range: [250, 380]
  hook_anchors:
    - "杀疯"
    - "杀入"
    - "冲上"
    - "实测"
    - "翻车"
    - "居然"
    - "砍掉"
    - "千星"
    - "万星"
    - "单日涨"
    - "自己干"
    - "全自动"
  metric_layer: "| 6. 星标增量 | 单日涨星数 | 强调色（紫/金） | \"+3941 ★\" |"
  contrarian_questions: |
    对每个 AI 项目回答以下问题，提取反直觉角度：
    1. **非常规手段**：是否用不常见的方法做常见的 AI 任务？
    2. **离线/本地替代**：是否在本地完成通常需要云端的大模型能力？
    3. **平民化 AI 能力**：是否让普通人能用上原本要专家/高配硬件的 AI？
    4. **领域跨界**：是否把 AI 用在了非传统场景？
  narration_txt_example: |
    {M}月{D}日 GitHub 上 AI 项目又杀疯了，有个让 AI 自己干完整套活
    第一个项目，{项目描述}
    {后续 AI 项目旁白}
    {结尾争议提问，如"这几个 AI 项目你最想试哪个"}
    关注我，下期见

delivery:
  hashtags: "#AI #开源 #人工智能 #GitHub #AI工具"
  cover_badge: "AI 风向标"
  cover_scene_label: "AI 开源风向"
  cover_data_examples: "+3973 最高涨星 / 198K 最高总星"
  hook_template_example: "{M}月{D}日涨星最猛的几个 AI 项目，有个让 AI 自己干活"
  tag_strategy: |
    | 核心圈标签 | #AI | 命中 AI 目标受众 |
    | 领域标签 | #开源 | 命中开源圈 |
    | 热点标签 | #人工智能 | 命中当前 AI 热点 |
    | 身份标签 | #GitHub | 命中开发者身份 |
    | 泛流量标签 | #AI工具 | 获取泛流量触达 |
  comment_template: |
    评论区格式：
    1. 项目英文名 + 一句话描述（每行一个）
    2. 不放完整链接，不提搜索，不提平台名
    3. 可附 owner/repo 路径

design:
  default_style: "暗色科技风（AI 电紫主题）"
  color_bias: "电紫为主（#A855F7 主色 + 深紫底），辅色青（#00D4FF）+ 暖点缀橙（#FF6B35）"

content:
  optional_deps: ["gh"]
  sensitive_keywords:
    finance: []
    extreme_words: ["病历", "处方", "确诊", "诊疗"]
    hype_numbers: []
    ai_deepfake: ["换脸", "脱衣", "伪造身份证"]   # AI 深伪类零容忍

shared_rules:
  data_example: "33K Star"
  hook_data_example: "{M}月{D}日涨星最猛的 AI 项目"
  hook_emotion_example: "{M}月{D}日 AI 项目直接杀疯了"
<!-- CONFIG-END -->

# AI 风向标分类配置

> GitHub AI 子系列：每日 AI 开源项目专项盘点。与综合「GitHub 每日热门」差异化——纯 AI 聚焦 + 独立 AI 数据源（ai_trending.py），AI 项目池更全更专。

## content

### data_source

当内容涉及 **AI 开源项目** 时，从 `ai_trending.py` 获取当日 AI 专项数据（已 AI 二次筛：topics 含 ai/llm/agent/machine-learning 等，或 description 含 AI 关键词）。

### data_commands

```bash
# AI 专项采集（主源全语言 trending → AI 二次筛 → 不足补 Python trending）
python scripts/ai_trending.py --output-dir "${PROJECT_DIR}" --date "${TODAY}" --since daily \
  --yesterday "workspace/${YESTERDAY_DATE_DIR}/ai-wind/raw_trending.json"

# avatar 下载（复用 github 管线脚本）
python scripts/fetch_avatars.py --project-dir "${PROJECT_DIR}"
```

输出 `raw_trending.json`（结构与综合 trending 一致，下游 gate/fetch_avatars/monthly 零改动），`source=ai_trending+gh_api`、`album=ai-wind`。

### selection_strategy — 标准模式（5-6 个 AI 项目）

从 `raw_trending.json`（已是 AI 项目集）选取 5-6 个，遵循优先级：

| 优先级 | 选取条件 | 预期数量 |
|--------|---------|---------|
| **1 — 钩子潜力** | 反直觉/颠覆性 AI 项目（如"让 AI 自己干几小时""本地跑大模型"） | 1-2 |
| **2 — 新上榜** | 首次出现在 AI 榜，或上次未介绍 | 2-3 |
| **3 — 涨星加速** | 单日涨星明显加快 | 1-2 |
| **4 — 跨 AI 子方向** | 覆盖 ≥3 不同方向（Agent / 大模型 / 语音 / 视觉 / AI工具） | 按需 |

**选题节奏**：
- 连续 2 期同子方向（如全是 Agent）→ 强制轮换（下期换大模型/语音/视觉）
- **超长 description 项目降权**：raw description >200 字符的项目（如含中英混排的安全/逆向类），内嵌原文锚点负担重且审核风险高，selection 时降权或剔除
- 分段数 ≤ 6（>6 段全播率下降）
- 与综合「GitHub 每日热门」当天 AI 项目降低重叠：优先选综合未展开的 AI 项目

### audience_filter — 受众可用性筛选

> **门槛：A 档（普通人可用的 AI 工具）约占一半（5 选 2-3、6 选 3-4）**。AI 榜大量是框架/SDK（B/C 档），纯库扎堆时泛受众完播低；但开发者向 AI 项目也是看点，按约一半配比。

| 档 | 判定信号 | 选取权重 |
|----|---------|---------|
| **A 普通可用** | AI 桌面 app / 浏览器即开 / Docker 一键 / 有 demo 网页 / 手机端 AI | 优先入选 |
| **B 半可用** | AI CLI 工具 / 需配置 / 需下模型 | 按需补入 |
| **C 开发者向** | AI 框架/SDK/中间件/训练代码，需写代码集成 | 降权，≤1/3 占比 |

**约束**：A 档约占一半；C 档 ≤1/3 不扎堆。C 档项目文案措辞「给做 AI 的开发者」，不伪装普通人能用。

### authenticity_verification — 项目真实性验证

> **⛔ 虚假项目零容忍。** AI 是刷榜重灾区（AI 项目易买 star）。每个入选项目必须通过 gh API 真实性核验。

验证方法与判定规则**沿用 github 分类 authenticity_verification**（账号年龄/星叉比/watcher/贡献集中度/仓库体积/README/提交活跃度/star 增长模式），HARD 条件触发即剔除并补选。

### preparation_rules — 内容整理规则

- 项目名保留英文（如 `microsoft/AI-For-Beginners`）
- 描述忠实翻译 `raw_trending.json` 的 `description` 字段，**内嵌原文** `（原: <英文 description>）`
- 每个项目附 `avatar: assets/avatars/{owner}.png` + `用途: <4-6字利益>`（从 AI 能力推导观众好处）
- AI 黑话翻译成利益（参考下方 jargon_translation）
- 按热度排序，开头用震撼数据做钩子

**⛔ 描述来源铁律（HARD）**：中文描述必须忠实翻译 raw description，禁止从 owner/repo 名推断。Stage 1 门禁 `description_fidelity_valid` 用子串匹配校验原文锚点。

### jargon_translation — AI 黑话→利益翻译表

| 黑话 | 观众语言（利益） |
|------|----------------|
| 大模型 / LLM | AI 大脑 / 能读懂人话的 AI |
| Agent / 智能体 | AI 自己干活 / 替你操作 |
| 本地推理 / 离线 | 数据不外传 / 不用联网 |
| 微调 / finetune | 调教成你专属的 AI |
| RAG / 知识库 | AI 读了你的资料再回答 |
| 开源模型 | 免费用的大模型 / 没版权限制 |
| 单日涨 X 星 | 突然爆火 / 火出圈 |
| 单卡 / 消费级显卡 | 普通电脑就能跑 |

### exclusion_list — 永久排除

沿用 github 分类 exclusion_list（`ruvnet/RuView` 等永久排除）。AI 深伪类（换脸/脱衣/伪造证件）零容忍剔除——`ai_deepfake` 敏感词门禁兜底。

### data_validation — 三源交叉验证

ai_trending.py 内置：主源 trending + web-reader 验证 + gh API 权威数据 + 昨日对比。沿用 github quality_gates（AI 项目 ≥5 硬下限，≥8 理想；活跃度 ≥80%）。

### monthly_inventory — 月度清单管理

每日 AI 数据采集后追加到 AI 风向标独立月度清单：
- **文件路径**：`workspace/sources/ai-wind/${MONTH}.md`（与 github-trending 月度清单分开）
- **追加格式**：日期标题 `### YYYY-MM-DD` + AI 项目表格（项目名 / Star / 今日+ / 语言 / 描述）
- **写入后验证**：当日日期标题已存在

## design

### default_style

暗色科技风（AI 电紫主题）。背景深紫渐变（`#0a0a14` → `#1a0a2e`），主色电紫 `#A855F7`，辅青 `#00D4FF`，暖点缀橙 `#FF6B35`。双光晕（紫+青），字体无衬线粗体。

**⛔ text-shadow 规则**：极淡 drop `text-shadow: 0 2px 6px rgba(30,41,59,0.08)`，禁发光 `0 0 Xpx`。

**⛔ 渐变文字配色**：`background-clip:text` 禁白色端点，用同色系高饱和（紫 `#A855F7→#C084FC→#E9D5FF` / 青 `#00D4FF→#60A5FA→#93C5FD`）。

### color_bias

电紫为主，辅青+暖橙形成对比。AI 科技光晕效果。

## narration

### hook_templates

> 多项目盘点钩子：反直觉/冲突 + 数字锚定（沿用 github 数据，AI 主题）。

**优先级 1 — 反直觉/冲突**（AI 项目有非常规能力时首选）：
- "有个 AI 工具把模型输入砍掉了95%，效果没变"
- "不用联网，本地就能跑大模型"
- "让 AI 自己干完一整天的活"

**优先级 2 — 动作+数字+利益**：
- "{M}月{D}日 N 个 AI 项目杀入榜单，一半能让 AI 替你干活"

**⛔ hook 具象度**（c5s 防退化）：≤15 字 + 具象数字/冲突词，禁抽象/堆叠/元铺垫。gate `check_hook_pattern_verified` HARD 拦截。反例：禁"几个猛项目/方向挺杂/替你跑全流程"等抽象表达。

### special_rules

- **数据优先于描述**：用 Star/涨星说话，不用"太强了"
- **反直觉角度**：每个 AI 项目挖至少一个反直觉点（非常规手段/离线替代/平民化/跨界），写入 `contrarian_angle`
- **AI 术语翻译**：旁白/画面用利益语言，禁裸报黑话（参考 jargon_translation）

### ending_question

正文零提问，结尾 1 个二选一**中性互动**（"这几个 AI 项目你最想试哪个"类），禁站队对抗。问题类型轮换，禁连续两期同句式。

### word_count_range

标准模式：250-380 字。

## audio

### default_voice

`zh-CN-YunjianNeural` +25%（AI 风向标固定，不查通用声音表）。

### voice_override

true

## narrative

### default_template
默认 `contrast-arc`（AI 项目盘点悬念揭晓弧）。

### character_presence
true — AI 风向标启用码力角色。

### immersion_mapping
AI 项目 100% → 默认 `hyper-pace` 沉浸模式（快速剪辑 + 密集粒子 + 霓虹电紫 #A855F7），强化 AI 科技感。匹配规则：AI 项目占比 >50% 即用 hyper-pace（本分类恒满足）。

## delivery

### hashtags

`#AI #开源 #人工智能 #GitHub #AI工具`

### cover_badge

"AI 风向标"

### cover_scene_label

"AI 开源风向"

### comment_template

项目英文名 + 一句话描述 + `owner/repo` 路径，不放链接/搜索/平台名。

## shared-rules

### url_validation

ai_trending.py 内置三源交叉验证（主源 requests + web-reader MCP `no_cache:true` + gh API 权威）。AI 项目数 ≥5 硬门禁，与昨日完全相同则告警缓存。

### Red Flags（AI 风向标特定）

| 信号 | 说明 |
|------|------|
| AI 深伪类项目（换脸/脱衣/伪造身份证） | 零容忍剔除，触发平台违规 + 违法。ai_deepfake 门禁兜底 |
| 描述/旁白出现商业 AI 品牌（GPT Plus/ChatGPT 订阅等付费产品） | 用类别词"大语言模型/AI 助手"，不点付费产品名 |
| 从 owner/repo 名推断 AI 功能 | 描述必须忠实 raw description（如 owner=ailab 不代表功能） |
| content_ready.txt 出现 raw 中不存在的项目 | 杜撰，stage1 门禁拦截 |
| 与综合当天 AI 项目完全重复 | 独立源天然降低重叠；stage0.5 新鲜度预警会标注 |
| 医疗 AI 项目（病历/诊断） | "病历/处方/确诊/诊疗"触发医疗资质审核，中性化或剔除 |

### Common Rationalizations

| 借口 | 事实 |
|------|------|
| "AI 框架技术新颖，必须深入讲原理" | 泛受众听不懂框架原理，翻译成"能让 AI 做什么"的利益 |
| "这个换脸项目是技术 demo，讲技术不违法" | 换脸/脱衣无论技术多新都违规违法，零容忍 |
| "本地大模型太复杂，跳过活跃度检查" | AI 项目刷榜重灾，真实性核验不可跳 |
