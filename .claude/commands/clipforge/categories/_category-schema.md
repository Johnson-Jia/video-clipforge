---
id: "clipforge.categories.schema"
description: 分类配置文件格式规范 — 定义分类文件的 schema 和覆盖机制
version: "2.0.0"
type: SCHEMA
---

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
version: "2.0.0"
type: CATEGORY
category_id: "分类ID"
rules_lib_ref: "_rules-lib/global-rules.yaml"
patterns_ref: "_patterns/store.yaml"
---
```

### clipforge_fit — 内容类型适配度

标记该分类下不同内容类型与 ClipForge 流水线的适配程度：

```yaml
## meta
  clipforge_fit:
    project-listing: HIGH    # 项目盘点：标准流水线直接生产
    deep-dive: MEDIUM        # 深度解析：需要额外视觉设计（图表/对比）
    business-analysis: LOW   # 商业分析：需要图表/数据可视化组件支持
```

| 适配度 | 说明 | 视觉要求 |
|--------|------|---------|
| HIGH | 8 层卡片 + 快速切换完美匹配 | 标准组件即可 |
| MEDIUM | 需要额外视觉元素 | 至少 2 种：数据图表/对比表/数字动画/逻辑链 |
| LOW | 标准流水线不适配 | 必须搭配图表组件，否则建议转图文 |

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

#### Stage 3: narration — 场景与文案

```markdown
## narration

### hook_templates
钩子文案模板列表（如 ["今天涨星最快的N个项目", "这个项目直接霸榜了"]）

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
评论区模板（如"在 GitHub 搜项目名"）

### cover_badge
封面徽章文案（如"GitHub 今日热门"）

### cover_scene_label
封面场景标签（如"今日GitHub榜单"）
```

#### shared-rules 覆盖（可选）

```markdown
## shared-rules

### url_validation（可选）
本分类特有的数据验证规范（如 GitHub 双源交叉验证）

### content_safety_override（可选）
对通用内容安全规范的补充或覆盖
```

### boundary_overrides（四原子架构新增）

分类特有的 Boundary 规则，覆盖或补充通用阶段规则：

```yaml
## boundary_overrides
rules:
  - id: "R-{CATEGORY}-001"
    type: FORBIDDEN_ACTION | FORBIDDEN_METHOD | FORBIDDEN_SPEECH | FORBIDDEN_LOGIC
    pattern: "分类特有的禁止行为"
    positive: "正向重述"
    guardrail: "校验方式"
    severity: HARD | SOFT
    class: SAFETY | EXPERIENTIAL
    scope: SKILL
```

### gate_overrides（四原子架构新增）

分类特有的门禁标准：

```yaml
## gate_overrides
hard:
  - gate: "gate_name"
    check: "检查方式"
soft:
  - gate: "gate_name"
    threshold: 0.7
```

### trace_overrides（四原子架构新增）

分类特有的 Trace 采集点：

```yaml
## trace_overrides
additional_capture:
  - "分类特有的采集项"
```

### patterns_ref（四原子架构新增）

关联的经验模式（从 `_patterns/store.yaml` 引用）：

```yaml
## patterns_ref
  - id: "P-001"
    applies_to: "stage3-scenes"
  - id: "P-002"
    applies_to: "stage3-scenes, stage7-delivery"
```

## 设计原则

1. **覆盖而非重写。** 分类配置只声明与通用规则不同的部分。通用 stage 文件的规则始终作为基线。
2. **分类配置由 SubAgent 在执行时读取。** SubAgent prompt 中会包含"读取 `categories/{id}.md` 获取分类配置"的指令。
3. **一个分类一个文件。** 不要跨分类引用，每个文件自包含。
4. **分类 ID 用英文小写。** 文件名 = 分类 ID = cron 文件中的引用键。
5. **四原子对齐。** 分类配置可声明 boundary_overrides / gate_overrides / trace_overrides / patterns_ref，与四原子架构对齐。

## 如何添加新分类

1. 复制本文件作为模板参考
2. 创建 `categories/{id}.md`，填写该分类的覆盖规则
3. 创建对应的 cron 编排文件（如 `commands/{id}-daily.md`）
4. 测试：手动 `/clipforge` 指定分类，验证各 stage 正确读取分类配置
