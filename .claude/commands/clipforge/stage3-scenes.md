# Stage 3: 场景拆解 + 旁白文案

当 `design.md` 已存在且 `narration_segments.json` 不存在时触发。拆解场景序列并撰写分段旁白文案。

| 模式 | 场景数 | 目标时长 |
|------|--------|---------|
| 标准模式 | 6-8 个 | 35-55 秒 |
| 单项目深度解析 | 7-8 个 | 45-60 秒 |
| 电影解读模式 | 不限 | 3-5 分钟 |

## 节奏铁律

| 规则 | 说明 |
|------|------|
| **黄金 3 秒** | hook 场景（前 3-5s）必须是纯钩子，不含任何信息性内容。正文从第 2 个场景开始 |
| 钩子句 ≤ 12 字 | 口语化、一击即中（数据震撼/反问/强对比/悬念） |
| 单个画面元素 ≤3 秒 | 每 2-3 秒必须有新的视觉变化（入场、切换、高亮） |
| 重点场景 6-8 秒 | 核心内容正常展开（一句话核心 + 一句话亮点 + 数据/细节） |
| 概括场景 3-4 秒 | 非重点内容快速带过 |
| 单场景上限 10 秒 | 即使重点介绍也不超过 10 秒 |

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

| 类型 | 用途 | 典型时长 |
|------|------|---------|
| **hook** | 开场钩子（痛点/反问/强对比） | 3-5s |
| **solution** | 引出产品/方案，核心卖点 | 5-7s |
| **features** | 功能展示、输入输出演示（内部元素快速切换） | 8-14s |
| **cta** | 号召行动，开源信息，地址 | 4-7s |
| **video_clip** | 电影片段播放（电影解读模式） | 10s-3min |
| **what** | 项目是什么，一句话核心定义（深度解析） | 5-7s |
| **how** | 原理解释，技术工作流程（深度解析） | 6-10s |
| **capabilities** | 核心能力/性能数据展示（深度解析） | 8-12s |
| **usecases** | 应用场景卡片展示（深度解析） | 7-10s |
| **tech** | 技术栈/硬件/架构（深度解析） | 5-8s |
| **privacy** | 隐私/安全/合规优势（深度解析，可选） | 5-7s |

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

```json
// narration_segments.json
[
  {"scene": "hook", "text": "今天涨星最快的项目是...", "estimated_duration": 4},
  {"scene": "topic1", "text": "第一个值得关注的...", "estimated_duration": 7},
  {"scene": "topic2", "text": "还有一个也很厉害...", "estimated_duration": 7},
  {"scene": "cta", "text": "关注我，每天更新...", "estimated_duration": 4}
]
```

同时生成 `narration.txt`（完整旁白，一行一段，顺序与场景一致）：
```
今天涨星最快的项目是...
第一个值得关注的...
还有一个也很厉害...
关注我，每天更新...
```


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
| 标准模式（5-6 个项目） | 25-55s | 200-350 字 |
| 深度解析模式 | 45-60s | 300-450 字 |

### 产出

1. 场景拆解表（YAML，含时间轴 + 每场景旁白段落）
2. `narration_segments.json`（分段旁白，每段对应一个场景）
3. `narration.txt`（完整旁白，一行一段，顺序与场景一致）

**交付物：** 展示场景表和旁白文案，用户确认后进入视频制作。

---

## Red Flags（停止信号）

| 信号 | 说明 |
|------|------|
| hook 场景旁白超 12 字 | _shared-rules §5 黄金 3 秒要求纯钩子 ≤12 字，超字会被划走 |
| hook 包含信息性内容 | 钩子必须是纯钩子（数据震撼/反问/强对比/悬念），不能是项目介绍 |
| 旁白含广告审查敏感词 | "必装"、"神器"、"最强"等会导致视频审核不通过（§1） |
| 画面文字包含英文非项目名/缩写 | "TRENDING TODAY"等违反中文为主规范（§2） |

## Common Rationalizations（常见借口反驳）

| 借口 | 事实 |
|------|------|
| "hook 多说点背景信息" | §5 黄金 3 秒要求纯钩子 ≤12 字。背景信息从第 2 个场景开始 |
| "用英文标题更酷" | §2 画面文字必须以中文为主，英文仅限项目名和技术缩写 |
| "hook 里说'这个项目太强了'" | §1 禁止"太强了"等极限用语，改用数据说话（"33K Star"） |
| "CTA 说'点赞关注一键三连'" | §1 禁止诱导互动，文案末尾自然提及即可 |
