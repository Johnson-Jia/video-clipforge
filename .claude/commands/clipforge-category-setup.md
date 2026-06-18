---
name: clipforge-category-setup
description: 交互式引导创建新的 ClipForge 内容分类配置文件。逐步收集信息，生成 categories/{id}.md 并验证。
---

# /clipforge-category-setup — 分类配置引导

引导创建新的分类配置文件 `categories/{id}.md`，包含 CONFIG 段（机器解析）和 markdown body（LLM 可读指南）。

## 前置准备

1. 读取 `categories/_category-schema.md` 获取完整字段规范
2. 读取 `categories/github.md` 作为参考示例
3. 列出 `categories/` 目录已有分类（排除 `_` 前缀的元文件），展示给用户

---

## 步骤 1：基本信息

用 AskUserQuestion 收集以下信息（3 个问题分一组）：

**问题 1 — 分类 ID**
- 说明：英文小写，将成为文件名（如 medical、finance、comics）
- 校验：只允许小写字母、数字、连字符

**问题 2 — 分类名称**
- 说明：中文显示名（如"医疗健康"、"金融财经"、"漫画解说"）

**问题 3 — 一句话描述**
- 说明：这个分类做什么类型的内容

收集后，检查 `categories/{id}.md` 是否已存在。如存在，询问是否覆盖。

---

## 步骤 2：内容来源

用 AskUserQuestion 收集（2 个问题）：

**问题 4 — 数据来源**
- 说明：内容从哪来？描述获取方式（如"医学期刊 API + 网页抓取"、"财经新闻 RSS"、"手动输入 PDF"）
- 这是分类的核心特征，直接影响 content 段的所有内容

**问题 5 — 内容节奏**
- 选项：
  - A) **多条盘点**（5-6 个项目轮播，每条 6-8 秒，类似 GitHub Trending）
  - B) **单条深度**（1 个主题深入讲解 45 秒-3 分钟）
  - C) **混合模式**（2-3 个主题，每条 15-20 秒）
- 影响：`narration.word_count_range` 和 body 段的选取策略

---

## 步骤 3：风格偏好

用 AskUserQuestion 收集（3 个问题）：

**问题 6 — 音色偏好**
- 选项：
  - A) **叙事感（默认）** — YunjianNeural +25%，适合大部分内容
  - B) **沉稳专业** — YunxiangNeural +15%，适合严肃领域
  - C) **轻快活泼** — XiaoxiaoNeural +20%，适合轻松娱乐

**问题 7 — 视觉风格**
- 选项：
  - A) **暗色科技风**（默认）— 深蓝/深紫渐变，强调色暖色
  - B) **暖色治愈风** — 奶油色/暖灰，强调色柔粉/浅金
  - C) **清新简约** — 白底/浅灰，强调色翠绿/天蓝

**问题 8 — 标签与封面**
- 让用户输入：
  - 核心标签（空格分隔，如 `#医疗 #健康 #科普`）
  - 封面徽章文案（如"医学前沿速递"、"财经热点"）

---

## 步骤 4：生成配置文件

根据收集的信息，按以下规则生成完整的 `categories/{id}.md`：

### 4.1 生成 CONFIG 段

用户提供的值直接填入。用户未提供的字段使用默认值：

```yaml
<!-- CONFIG-START: 机器可解析的配置值 -->
audio:
  default_voice: "{用户选择或 zh-CN-YunjianNeural}"
  default_rate: "{用户选择或 +25%}"
  voice_override: false

narration:
  hook_example: "基于领域生成的 hook 示例"
  topic_example: "基于领域生成的正文示例"
  hook_json_example: "同 hook_example"
  cta_purpose: "引导互动"
  word_count_range: [250, 380]     # 多条盘点模式
  hook_anchors: []                  # 基于领域推导 3-5 个关键词
  metric_layer: ""                  # 基于领域生成或留空
  contrarian_questions: ""          # 基于领域生成
  narration_txt_example: ""         # 基于领域生成

delivery:
  hashtags: "{用户提供}"
  cover_badge: "{用户提供}"
  cover_scene_label: "{同 cover_badge}"
  cover_data_examples: ""
  hook_template_example: ""
  tag_strategy: ""
  comment_template: ""

design:
  default_style: "{用户选择或 暗色科技风}"
  color_bias: "{用户选择或 冷色为主，强调色用暖色}"

content:
  optional_deps: []

shared_rules:
  data_example: ""
  hook_data_example: ""
  hook_emotion_example: ""
<!-- CONFIG-END -->
```

### 4.2 生成 Markdown Body

基于用户提供的领域信息，参考 github.md 的结构，生成以下段落的详细内容：

**content 段**（必须生成）：
- `data_source` — 用户描述的数据来源 + 具体获取命令
- `selection_strategy` — 基于内容节奏选项推导选取规则
- `fallback` — 数据获取失败时的兜底策略

**design 段**：
- `default_style` — 来自用户选择
- `color_bias` — 来自用户选择

**narration 段**：
- `hook_templates` — 基于领域生成 3-5 个钩子模板
- `special_rules` — 基于领域特性推导 2-3 条特殊规则
- `word_count_range` — 来自内容节奏选项

**audio 段**：
- `default_voice` / `default_rate` / `voice_override` — 来自用户选择

**delivery 段**：
- `hashtags` / `cover_badge` / `cover_scene_label` — 来自用户输入
- `comment_template` — 基于领域生成评论区模板

**shared-rules 段**（仅在用户有特殊数据验证需求时生成）：
- `url_validation` — 如果数据来源涉及网页抓取

### 4.3 关键推导规则

LLM 在生成时必须遵循：

1. **hook_anchors**：从领域关键词中推导 3-5 个数字锚定词。如医疗领域："最新研究"、"治愈率"、"副作用"、"临床试验"；财经领域："涨幅"、"市值"、"收益率"、"突破"
2. **metric_layer**：基于领域数据特征生成表格行。如医疗："| 6. 临床数据 | 治愈率/有效率 | 强调色 | \"92% 治愈率\" |"
3. **contrarian_questions**：基于领域生成 3-4 个反直觉挖掘问题
4. **word_count_range**：多条盘点 → [250, 380]；单条深度 → [300, 950]（≤3min）；混合 → [280, 400]
5. **不包含** `narrative` 段的 `humor_rules`、`character_presence`、`immersion_mapping` — 这些是 GitHub 专有功能

---

## 步骤 5：预览与确认

1. 在终端输出完整的 `categories/{id}.md` 文件内容
2. 用 AskUserQuestion 询问用户：
   - "以上是生成的配置文件，是否确认写入？"
   - 选项：确认写入 / 需要修改 / 取消

如用户选择"需要修改"，询问具体要改哪些部分，修改后重新预览。

---

## 步骤 6：写入与验证

用户确认后：

1. 写入 `categories/{id}.md`

2. 运行验证：
```bash
source "$HOME/.claude/commands/clipforge/shared/clipforge-env.sh" 2>/dev/null || source "$(git rev-parse --show-toplevel 2>/dev/null)/.claude/commands/clipforge/shared/clipforge-env.sh"
python engine/render_stage.py --stage stages/stage4-audio.md --category {id}
```
检查输出无"未替换变量"警告（`leftover_variables` 为空列表）。

3. 如验证通过，展示成功信息。

---

## 步骤 7：生成定时任务（可选）

用 AskUserQuestion 询问用户：
- "是否需要创建定时任务（cron）实现自动化执行？"
- 选项：创建定时任务 / 跳过

如用户选择创建，按以下流程生成：

### 7.1 读取参考文件

1. 读取 `shared/cron-template.md` 获取通用 DAG 编排骨架
2. 读取当前分类的 `categories/{id}.md` 获取领域特定规则

### 7.2 收集定时配置

用 AskUserQuestion 收集（2 个问题）：

**问题 A — 执行频率**
- A) 每日
- B) 每周
- C) 自定义 cron 表达式

**问题 B — 任务名称**
- 说明：英文小写，将成为命令文件名（如 `{id}-daily`）
- 校验：只允许小写字母、数字、连字符

### 7.3 生成 cron 文件

基于 `shared/cron-template.md` 骨架 + `categories/{id}.md` 领域规则，生成自包含的 cron 命令文件。

生成规则：
- 文件写入 `.claude/commands/{任务名称}.md`
- frontmatter 包含 `name` 和 `description`
- 内容按 cron-template.md 的步骤顺序组织：前置 → 数据采集 → 内容整理 → DAG 编排 → 自续期 → 输出
- 数据采集和内容整理的具体规则内联写入（从分类文件中复制，非引用）
- DAG 编排的 SubAgent 差异项表格完整填入
- 文件末尾包含输出汇报模板

> **关键**：cron 文件是自包含的 LLM prompt。所有执行规则必须内联，不使用跨文件引用（`按 xxx.md → yyy 执行`）。LLM 在 cron 自动执行时上下文有限，跨文件查找不可靠。

### 7.4 注册定时任务

生成文件后，用 CronCreate 注册定时任务：
- 每日：`0 {hour} * * *`（询问具体时间，避开整点）
- 每周：`0 {hour} * * {day}`（询问星期几）
- 自定义：按用户提供的 cron 表达式

prompt 内容为：`/{任务名称}`

注册成功后，更新 memory 的 `cron-schedules.md`，添加新任务的 cron 表达式和 Job ID（供 `cron-renew` 读取）。

### 7.5 更新 .gitignore

确认 `.gitignore` 已包含新 cron 文件的排除规则。如果文件名不匹配现有通配符模式（`*-daily-*.md`、`*-weekly-*.md`），手动添加排除规则。

---

## 完成后提示

告知用户：

1. 分类配置已写入 `categories/{id}.md`
2. 手动检查配置文件，补充/修改不准确的字段
3. 用 `/clipforge` 指定分类测试制作一条视频
4. 如已生成定时任务，告知 cron 表达式和 Job ID
