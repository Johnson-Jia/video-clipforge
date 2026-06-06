# 分类配置文件格式规范

> 每个分类一个 `.md` 文件，放在 `clipforge/categories/` 下。文件名即分类 ID（如 `github.md`、`comics.md`）。

## 必须包含的字段

每个分类配置文件用 YAML front matter 声明元信息，正文按 stage 分段描述覆盖规则。

### Front Matter

```yaml
---
name: "分类中文名"
description: "一句话描述"
id: "分类ID（与文件名一致，如 github、comics）"
---
```

### Stage 覆盖段

每个 stage 覆盖段是可选的。**不覆盖的 stage 不写**，通用 stage 文件的规则自动生效。

#### Stage 1: content — 内容获取

```markdown
## content

### data_source
数据获取方式描述（如"GitHub Trending API"、"漫画网站爬取"）

### data_commands
数据获取的具体命令或脚本

### selection_strategy
内容选取策略（如何从原始数据中筛选内容）

### deep_research（可选）
单项目/单内容深度调研的方法和维度

### fallback
数据获取全部失败时的兜底策略
```

#### Stage 2: design — 风格推导

```markdown
## design

### default_style
默认风格方向（如"暗色科技风"、"暖色治愈风"）

### color_bias
配色偏好（如"冷色为主、强调色偏橙蓝"）
```

#### 跨阶段: orientation — 画布方向（Stage 2 读取写入，Stage 3 可回写）

```markdown
## orientation

### orientation_hint（可选）
画布方向强制指定。不设置时默认 portrait。
值：`portrait` | `landscape`
说明：Stage 2 读取此值直接写入 design.md（orientation_source=category_hint）。
```

#### Stage 3: narration — 场景与文案

```markdown
## narration

### hook_templates
钩子文案模板列表（如 ["{M}月{D}日涨星最快的N个项目", "这个项目直接霸榜了"]）

### special_rules
分类特殊文案规则（如"老项目不重复展开"、"角色名必须标注配音"）

### word_count_range
推荐文案字数范围（如"200-350 字"）
```

#### Stage 4: audio — 音频

```markdown
## audio

### default_voice
默认 TTS 声音（如"zh-CN-YunjianNeural"）

### default_rate
默认语速（如"+25%"）

### voice_override
是否覆盖通用声音选择表（true/false）
```

#### Stage 7: delivery — 交付

```markdown
## delivery

### hashtags
固定标签列表（如 ["#GitHub热门", "#程序员", "#开源"]）

### comment_template
评论区模板（如"项目名 + 一句话描述 + owner/repo 路径"）

### cover_badge
封面徽章文案（如"GitHub 热门项目"）

### cover_scene_label
封面场景标签（如"GitHub 榜单速览"）
```

#### 跨阶段: narrative — 叙事策略（Stage 3/6 引用）

```markdown
## narrative

### default_template
默认叙事模板

### humor_rules
幽默引擎规则（类比/反差吐槽/冷知识梗的启用策略）

### character_presence
角色表现设定（虚拟主持人的表情/语态风格）

### immersion_mapping
沉浸感映射规则（情感节拍与视觉节奏的对应关系）
```

#### shared-rules 覆盖（可选）

```markdown
## shared-rules

### url_validation（可选）
本分类特有的数据验证规范（如 GitHub 双源交叉验证）

### content_safety_override（可选）
对通用内容安全规范的补充或覆盖
```

## CONFIG 段（机器可解析配置）

在 front matter 和正文之间，新增 `CONFIG-START` / `CONFIG-END` 标记的 YAML 段。这段内容由 `engine/render_stage.py` 和引擎模块解析，用于**确定性替换**通用 stage 文件中的模板变量。

```markdown
<!-- CONFIG-START: 机器可解析的配置值 -->
audio:
  default_voice: "zh-CN-YunjianNeural"
  default_rate: "+25%"

narration:
  hook_example: "{M}月{D}日涨星最快的几个项目，直接炸了"
  hook_anchors:
    - "涨星最快"
    - "千星"
  metric_layer: "| 6. 星标增量 | 单日涨星数 | 强调色 | \"+3941 ★\" |"

delivery:
  hashtags: "#GitHub热门 #程序员 #开源"
  cover_badge: "GitHub 热门项目"
<!-- CONFIG-END -->
```

### 可用字段参考

| 段 | 字段 | 类型 | 说明 |
|----|------|------|------|
| `audio` | `default_voice` | string | TTS 声音名称（如 `zh-CN-YunjianNeural`） |
| `audio` | `default_rate` | string | TTS 语速（如 `+25%`） |
| `audio` | `voice_override` | bool | true=固定此音色，不查通用声音表 |
| `narration` | `hook_example` | string | 钩子文案示例 |
| `narration` | `topic_example` | string | 正文示例 |
| `narration` | `hook_json_example` | string | JSON 示例中的 hook 文案 |
| `narration` | `cta_purpose` | string | CTA 场景用途描述 |
| `narration` | `word_count_range` | [int, int] | 文案字数范围 |
| `narration` | `hook_anchors` | list[str] | hook 数字锚定关键词（供 gate.py 检测） |
| `narration` | `metric_layer` | string | 8 层信息表的领域专用层（markdown 表格行） |
| `narration` | `contrarian_questions` | string | 反直觉角度挖掘问题（多行文本） |
| `narration` | `narration_txt_example` | string | narration.txt 示例（多行文本） |
| `delivery` | `hashtags` | string | 标签（空格分隔） |
| `delivery` | `cover_badge` | string | 封面徽章文案 |
| `delivery` | `cover_scene_label` | string | 封面场景标签 |
| `delivery` | `cover_data_examples` | string | 封面数据卡片示例 |
| `delivery` | `hook_template_example` | string | 文案模板钩子示例 |
| `delivery` | `tag_strategy` | string | 标签策略表格（多行 markdown） |
| `delivery` | `comment_template` | string | 评论区模板 |
| `design` | `default_style` | string | 默认风格方向 |
| `design` | `color_bias` | string | 配色偏好 |
| `orientation` | `orientation_hint` | string | 画布方向强制指定（portrait/landscape） |
| `content` | `optional_deps` | list[str] | 分类专有可选依赖 |
| `shared_rules` | `data_example` | string | 数据示例 |
| `shared_rules` | `hook_data_example` | string | 钩子数据示例 |
| `shared_rules` | `hook_emotion_example` | string | 钩子情绪示例 |

### 模板指令语法

通用 stage 文件中使用三种指令：

| 指令 | 语法 | 用途 |
|------|------|------|
| 简单替换 | `{{section.field\|默认值}}` | 替换单值，无分类时用默认值 |
| 块注入 | `{{INJECT:section.field}}` | 注入多行内容（表格、列表等） |
| 条件块 | `{{IF:section.field}}...{{ENDIF}}` | 仅分类有此字段时显示 |

## 设计原则

1. **覆盖而非重写。** 分类配置只声明与通用规则不同的部分。通用 stage 文件的规则始终作为基线。
2. **配置合并由代码完成。** `engine/render_stage.py` 在执行前将 CONFIG 段的值确定性替换到通用 stage 模板中。LLM 读到的是已合并的完整文件，无需自行做配置路由。
3. **一个分类一个文件。** 不要跨分类引用，每个文件自包含。
4. **分类 ID 用英文小写。** 文件名 = 分类 ID = cron 文件中的引用键。

## 如何添加新分类

1. 运行 `/clipforge-category-setup`，引导式创建分类配置 + 可选定时代时任务
2. 或手动：复制本文件作为模板参考，创建 `categories/{id}.md`
3. 测试：手动 `/clipforge` 指定分类，验证各 stage 正确读取分类配置
