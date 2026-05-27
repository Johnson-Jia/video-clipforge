# Stage 3: 场景拆解 + 旁白文案

当 `design.md` 已存在且 `narration_segments.json` 不存在时触发。拆解场景序列、撰写分段旁白文案、注入情感标记和幽默元素。

> **导演思维驱动。** 执行前读取 `_director-toolkit`，每个场景用"导演的 5 个必答题"驱动视觉描述。用"视觉词汇表"写出具体的视觉指令，让 Stage 6 能直接理解和实现。

| 模式 | 场景数 | 目标时长 |
|------|--------|---------|
| 标准模式 | 6-8 个 | 45-55 秒 |
| 单项目深度解析 | 7-8 个 | 45-60 秒 |
| 电影解读模式 | 不限 | 3-5 分钟 |

## 标准模式 — 单项目全屏结构（8 层信息）

> **数据来源：** 爆款视频分析（05-19，11万播放）采用一屏一项目布局，每项目包含 8 层信息。对比同日另一视频（一屏多项目，5 层信息），播放量差 3 倍。

标准模式下，每个项目独占一个场景（6-8s），画面包含 8 层信息，从理性到感性全覆盖：

| 层级 | 内容 | 字色 | 示例 |
|------|------|------|------|
| 1. 类别标签 | 项目所属类别概括 | 浅蓝/辅助色 | "今日之星" / "反检测利器" / "WiFi 黑科技" |
| 2. 排名数字 | 大号排名编号 | 强调色（橙/金） | "1" / "2" / "3" |
| 3. 项目名 | 英文原名 | 白色 | "openhuman" / "RuView" |
| 4. 一句话描述 | 中文翻译 + 核心卖点 | 浅灰 | "个人 AI 超级大脑·完全私有化" |
| 5. 语言标签 | 技术栈药丸 | 辅助色徽章 | "Rust" / "Python" |
| 6. 星标增量 | 今日涨星数 | 强调色（橙/金） | "+3941 ★" |
| 7. 三词卖点 | 3 个关键词用间隔号连接 | 辅助色（蓝/青） | "私有部署·极速响应·本地运行" |
| 8. 感性评语 | 一句话感性总结 | 浅灰 | "一天涨近四千星，速度惊人" |

**8 层信息的生成规则：**
- **类别标签**：从项目功能中提取 4 字以内的概括，要有记忆点（不说"工具"，说"反检测利器"；不说"AI 项目"，说"个人大脑"）
- **三词卖点**：3 个词分别覆盖能力、性能、场景三个维度，用"·"分隔，每词 ≤6 字
- **感性评语**：用数据或感叹做情绪收尾，不超过 12 字。可以是数据惊叹（"近四千星，速度惊人"）或场景感慨（"家用 WiFi 就能实现"）

### 反直觉角度挖掘（每个项目必须执行）

对每个项目回答以下问题，提取反直觉角度：

1. **非常规手段**：是否用不常见的技术做常见的事？
2. **离线/本地替代**：是否在本地完成通常需要云端的功能？
3. **平民化专业能力**：是否让普通人能做专业级的事？
4. **领域跨界**：是否把 A 领域的技术用在了 B 领域？

挖掘结果写入 `contrarian_angle` 字段。如果项目有反直觉角度，优先用在：
- 旁白文案中的介绍句
- 发布文案中的钩子句
- 类别标签的命名

## 节奏铁律

> **数据来源（2026-05-27 抖音 58 条视频分析）：**
> - 5s 完播率 ≥44% → 平均 36,077 播放（11.6x 基线）
> - 5s 完播率 38-44% → 平均 12,290 播放（4.0x 基线）
> - 5s 完播率 <38% → 平均 3,102 播放（基线）
> - **5s 完播率是播放量最强预测因子。前 5 秒决定一切。**

| 规则 | 说明 |
|------|------|
| **黄金 3 秒** | hook 场景（前 3-5s）必须是纯钩子，不含任何信息性内容。正文从第 2 个场景开始 |
| **钩子模式优先级** | 反直觉/冲突（首选，平均 46K 播放）> 数字锚定（42K）> 信号注意（5K）。禁止疑问/互动模式（平均 1.2K） |
| 钩子句 ≤ 12 字 | 口语化、一击即中（数据震撼/反直觉/强对比），禁止平铺直叙式开场 |
| **前 5 秒零废话** | hook 场景内禁止项目名、功能描述、背景铺垫。只允许：震撼数据 / 反直觉陈述 / 强对比 |
| **视觉切换频率** | 遵守 `_shared-rules` §6 的分级规则：≤10s 单 phase，10-20s ≥2 phases，20-40s ≥3 phases，>40s 按 ⌈duration/14⌉ |
| 重点场景 6-8 秒 | 短视频核心内容（一句话核心 + 一句话亮点 + 数据/细节） |
| 概括场景 3-4 秒 | 非重点内容快速带过 |
| 长视频场景按 phase 拆分 | 时长 >15 秒的场景必须有 `visual_phases`，不足则 Stage 6 gate 拦截 |

## 场景模板

```yaml
scenes:
  - id: hook
    type: hook           # hook / solution / features / cta
    duration: 4s         # 预估时长，最终由 TTS 实际时长决定
    content: "核心钩子文字"
    narration_segment: "这周 GitHub 涨星最快的项目是..."  # 本场景旁白（一句/一段）
    mood: urgent
  - id: solution
    type: solution
    duration: 7s
    content: "..."
    narration_segment: "第一个项目..."
    mood: energetic
  - id: features
    type: features
    duration: 12s
    content: "..."
    narration_segment: "还有个项目也很厉害..."
    mood: confident
  - id: cta
    type: cta
    duration: 7s
    content: "..."
    narration_segment: "关注我，每天更新..."
    mood: inspiring
```

> **`start` 自动累加：** 场景按顺序排列，`start` = 前面所有场景 `duration` 之和，无需手动填写。调整某个场景的 `duration` 时，后续场景的 `start` 自动更新。

## 场景类型

场景类型定义了每个场景的叙事用途，时长由内容密度决定，不套固定值：

| 类型 | 用途 |
|------|------|
| **hook** | 开场钩子（痛点/反问/强对比） |
| **solution** | 引出产品/方案，核心卖点 |
| **features** | 功能展示、输入输出演示 |
| **cta** | 号召行动，开源信息 |
| **video_clip** | 电影片段播放（电影解读模式） |
| **what** | 项目是什么，一句话核心定义（深度解析） |
| **how** | 原理解释，技术工作流程（深度解析） |
| **capabilities** | 核心能力/性能数据展示（深度解析） |
| **usecases** | 应用场景卡片展示（深度解析） |
| **tech** | 技术栈/硬件/架构（深度解析） |
| **privacy** | 隐私/安全/合规优势（深度解析，可选） |

### 单项目深度解析 — 8 场景模板

当只聚焦一个项目时，使用以下 8 场景结构替代标准 4-5 场景模板。每个场景专注一个维度，层层递进：

```yaml
scenes:
  - id: hook
    type: hook
    duration: 4s
    narration_segment: "用震撼数据或反问开场，制造好奇心"
    mood: urgent

  - id: what
    type: what
    duration: 6s
    narration_segment: "一句话说明项目是什么、解决什么问题"
    mood: energetic

  - id: how
    type: how
    duration: 8s
    narration_segment: "解释核心原理，用通俗易懂的类比"
    mood: confident

  - id: capabilities
    type: capabilities
    duration: 10s
    narration_segment: "列出核心能力指标，用具体数据说话"
    mood: energetic

  - id: usecases
    type: usecases
    duration: 9s
    narration_segment: "描绘 2-3 个典型应用场景，让人产生代入感"
    mood: inspiring

  - id: tech
    type: tech
    duration: 7s
    narration_segment: "技术栈、硬件需求、部署门槛"
    mood: confident

  - id: privacy
    type: privacy
    duration: 6s
    narration_segment: "隐私/安全/合规方面的独特优势（如项目无此维度可省略）"
    mood: confident

  - id: cta
    type: cta
    duration: 4s
    narration_segment: "号召行动，关注更新"
    mood: inspiring
```

### video_clip 场景（电影解读模式）

当制作电影/影视解读视频时，使用 `video_clip` 类型嵌入电影原片片段。此类场景的旁白为空（`null`），播放期间由电影原音替代旁白。

```yaml
# 电影解读模式：video_clip 场景
- id: wives_video
  type: video_clip        # 电影片段播放
  duration: 144s          # 预估总时长（Stage 5 提取后将用实际测量值覆盖此预估值）
  source_clips:           # 源视频片段列表
    - file: "video/P14_xxx.mp4"
      start: "0:00"       # 开始时间码
      end: "0:24"         # 结束时间码（"end" = 到文件结尾）
    - file: "video/P5_xxx.mp4"
      start: "1:10"
      end: "end"
  xfade: 0.5              # 片段间交叉溶解时长（可选，默认 0.5s）
  narration_segment: null  # 电影片段期间无旁白
```

**关键规则：**
- `video_clip` 场景的 `narration_segment` **必须为 `null`**，Stage 4 会自动填充与片段等长的静音
- 多个 `source_clips` 由 Stage 5 自动拼接，xfade 转场消除硬切
- HTML 中用 `<video>` 元素嵌入，必须是 composition 根元素的直接子元素
- 电影解读模式总时长可达 **3-5 分钟**，场景数量不限
- 文案总字数按实际旁白场景计算，不含 `video_clip` 场景
- **`duration` 是粗估值。** Stage 5 提取片段后会产出 `clip_durations.json`（实际测量值），Stage 6 用实际值设置 `data-duration`。Stage 3 的 `duration` 仅用于内容规划时的参考

## 撰写旁白文案（分段模式）

场景拆解的同时，撰写旁白文案。**每个场景必须对应一段独立的旁白文字**，存为 `narration.txt`（一行一个场景）和 `narration_segments.json`。

### 分段旁白（必须遵守）

**核心原则：一个场景 = 一段旁白 = 一个独立 TTS 片段。**

旁白按场景分段，每段独立生成 TTS。Stage 4 会为每段测量实际时长，Stage 6 用实际时长设置 `data-duration`。这确保画面与语音精确同步。

`narration_segments.json` 格式：

```json
[
  {
    "scene": "hook",
    "text": "今天涨星最快的几个项目，直接炸了",
    "estimated_duration": 4,
    "emotion": "grab",
    "emotion_intensity": 0.3,
    "humor_type": null,
    "character_expression": null,
    "selling_points": null,
    "commentary": null,
    "contrarian_angle": null,
    "visual_phases": []
  },
  {
    "scene": "topic1",
    "text": "第一个项目，这个框架跑起来比我外卖还快",
    "estimated_duration": 7,
    "emotion": "build",
    "emotion_intensity": 0.5,
    "humor_type": "analogy",
    "character_expression": "cool",
    "selling_points": "极速响应·本地运行·隐私优先",
    "commentary": "一天涨了三千星，开发者用脚投票",
    "contrarian_angle": "完全离线运行的大语言模型，不需要显卡",
    "visual_phases": []
  },
  {
    "scene": "market",
    "type": "capabilities",
    "text": "全球可穿戴AI设备市场正处于高速增长期，2025年市场规模约845亿美元...",
    "estimated_duration": 38,
    "emotion": "reveal",
    "emotion_intensity": 0.6,
    "humor_type": null,
    "character_expression": "cool",
    "selling_points": null,
    "commentary": null,
    "contrarian_angle": null,
    "visual_phases": [
      {
        "focus": "全球市场规模与增长",
        "visual_type": "data",
        "key_data": ["845亿美元(2025)", "1767亿美元(2030)", "年复合增长15.9%"],
        "layout_hint": { "density": "compact" }
      },
      {
        "focus": "中国市场出货量",
        "visual_type": "data",
        "key_data": ["腕戴7390万台", "智能手表5061万台", "智能手环2329万台"]
      },
      {
        "focus": "渗透率与确定性",
        "visual_type": "highlight",
        "key_data": ["35%成年人已使用", "渗透率快速增长", "确定性极高的赛道"],
        "layout_hint": { "density": "generous" }
      }
    ]
  },
  {
    "scene": "cta",
    "text": "关注我，每天更新",
    "estimated_duration": 4,
    "emotion": "summon",
    "emotion_intensity": 0.4,
    "humor_type": null,
    "character_expression": null,
    "selling_points": null,
    "commentary": null,
    "contrarian_angle": null,
    "visual_phases": []
  }
]
```

**新增字段说明：**

| 字段 | 类型 | 说明 |
|------|------|------|
| `emotion` | string | 6 拍节拍名: grab/build/reveal/climax/settle/summon |
| `emotion_intensity` | float | 0-1，对应 design.md 的 emotion_curve |
| `humor_type` | string/null | `analogy`（类比）/ `sarcasm`（反差吐槽）/ `trivia`（冷知识梗）/ null |
| `character_expression` | string/null | `shock`/`think`/`cool`/`explode`/`tease`/`moved`/null |
| `selling_points` | string/null | 三词卖点（仅标准模式项目场景），格式："词1·词2·词3"，每词 ≤6 字 |
| `commentary` | string/null | 感性评语（仅标准模式项目场景），≤12 字，数据惊叹或场景感慨 |
| `contrarian_angle` | string/null | 反直觉角度（仅标准模式项目场景），用于旁白钩子和发布文案 |
| `visual_phases` | array | **视觉分镜（时长 >15s 时必填）**。每项含 `focus`(内容焦点)、`visual_type`(视觉类型)、`key_data`(画面数据/关键词列表)、`layout_hint`(可选，布局微调)。时长 ≤15s 的场景可传空数组 `[]` |

### visual_phases 类型定义

| visual_type | 画面表现 | 适用时机 |
|------------|---------|---------|
| `hero` | 大标题 + 关键数字 + 光晕 | 新概念引入、核心结论 |
| `list` | 逐条出现的要点卡片 | 功能列表、原因列举、特征描述 |
| `data` | 数字计数动画 + 进度条/柱状图 | 市场数据、增长率、规模 |
| `compare` | 双栏对比（左 vs 右） | 方案对比、优劣对比、前后对比 |
| `timeline` | 步骤节点依次出现 | 路线图、发展流程、时间线 |
| `highlight` | 核心结论放大 + 强调色背景 | 段落总结、核心观点强调 |

### visual_phases 规则

1. **计数规则**：时长 ≤15s → 可省略（`[]`）；16-25s → ≥2 phases；26-40s → ≥3 phases；>40s → ⌈duration/14⌉ phases
2. **相邻 phase 的 visual_type 不应重复**（保持视觉多样性）
3. **key_data 是画面上必须展示的数据/关键词**，Stage 6 根据 visual_type 选择组件模板展示这些数据
4. **focus 是该 phase 的内容主题**，Stage 6 据此生成画面标题
5. **Phase 不足视为 Stage 3 未完成**，Stage 6 gate 会拦截
6. **layout_hint.density** 可选，控制元素间距密度：`compact`（条目多/时间紧）、`standard`（默认）、`generous`（元素少/强调留白）。不指定时 Stage 6 从 visual_type 自动推导

同时生成 `narration.txt`（完整旁白，一行一段，顺序与场景一致）：
```
今天涨星最快的几个项目，直接炸了
第一个项目，这个框架跑起来比我外卖还快
这个项目一周涨了五千星，比我的发际线退得还快
关注我，每天更新
```

## 双线幽默引擎

读取 `design.md` 的 `storyboard.humor_style` 确定幽默策略。

### 幽默原则

- 每 3-4 个段落至少注入 1 次幽默（analogy 类比 / sarcasm 反差吐槽 / trivia 冷知识梗）
- 幽默只在 build/reveal/settle 节拍使用，grab/climax/summon 保持严肃
- 幽默不改变核心信息，只是表达方式的调剂
- 遵守分类配置的 humor_rules（如有）

### 角色表情

`character_expression` 非 null 的段落，Stage 6 会渲染对应表情的码力角色。表情跟随情感自然匹配，不需要查表——数据震撼用 shock、分析思考用 think、展示酷功能用 cool、高潮爆发用 explode、调侃用 tease、感人用 moved。

## 情感节拍映射

从 `design.md` 的 `storyboard.beat_mapping` 确定每个场景属于哪个节拍，写入 `emotion` 字段：

| 节拍 | 旁白语速建议 | 幽默强度 | 角色出场 |
|------|-------------|---------|---------|
| grab | 快（+10%） | 无 | 无 |
| build | 中（+5%） | 低 | think/cool |
| reveal | 中快（+10%） | 中 | shock/cool |
| climax | 快（+15%） | 无 | explode |
| settle | 慢（-5%） | 高 | tease/moved |
| summon | 中（默认） | 低 | 无 |

### 情感变速标记

每段的 `emotion` 字段指导 Stage 4 的 TTS 语速偏移（grab/climax 偏快，settle 偏慢，build/reveal/summon 基准）。Stage 3 只标记 emotion，不设置具体 rate 值。Stage 4 读取 emotion 字段后应用偏移。

### 文案要求

- 每句不超过 15 个字（口语节奏）
- 去掉书面语气词（"因此"、"综上所述"）
- 用短句、反问句、感叹句增加节奏感
- **不出现具体网址/URL**（抖音审查敏感，链接放评论区）
- **不重复已有内容**：与前面场景重复的内容用一句话概括，不展开
- 总字数控制在 **200-350 字**（标准模式）或 **300-450 字**（深度解析模式）

### 措辞/画面/CTA 规范

> **遵守 `clipforge/_shared-rules` 全部条款**（§1 措辞、§2 画面文字、§3 CTA 时间、§4 内容安全）。已在执行前读取，无需在此重复。

### 时长估算

按语速 `+25%` 粗算：**每秒约 7-8 个汉字**。

| 模式 | 目标时长   | 建议字数 |
|------|--------|---------|
| 标准模式（5-6 个项目） | 45-55s | 250-380 字 |
| 深度解析模式 | 45-60s | 300-450 字 |

### 产出

1. 场景拆解表（YAML，含时间轴 + 每场景旁白段落 + 情感标记）
2. `narration_segments.json`（分段旁白，含 emotion/humor_type/character_expression）
3. `narration.txt`（完整旁白，一行一段，顺序与场景一致）

**交付物：** 展示场景表和旁白文案（含情感标记和幽默元素），用户确认后进入音频制作。

---

## 约束声明

> 本阶段的结构化约束（HARD/SOFT 规则 + Guard Red Flags）由引擎注入提供。执行前运行 `python engine/inject.py --skill stage3-scenes` 获取完整约束 prompt。
