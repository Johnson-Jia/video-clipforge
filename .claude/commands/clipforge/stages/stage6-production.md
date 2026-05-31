# Stage 6: 沉浸式视频制作（委托 HyperFrames）

当 `segment_durations.json` + 音频文件已存在且 `output.mp4` 不存在时触发。基于组件库装配 HTML 组合并渲染为视频。

## 6.1 项目初始化

```bash
# 创建日期目录（如不存在）+ 项目目录（纯英文路径）
mkdir -p "workspace/<YYYY>/<MM>/<DD>/<project-name>"
npx hyperframes init "workspace/<YYYY>/<MM>/<DD>/<project-name>" --example blank --non-interactive
```

项目目录结构为 `workspace/<YYYY>/<MM>/<DD>/<项目名>/`，日期格式为纯数字（如 `workspace/2026/05/18/github-trending/`）。详见 `clipforge.md` 的「项目目录结构」段。

## 6.2 读取 design.md + storyboard

Stage 2 已将视觉风格方向和故事板写入 `design.md`。**本阶段只读取，不重写。**

**读取字段和用途：**

| 字段 | 用途 |
|------|------|
| `style`, `mood` | 整体风格方向 |
| `color_direction` | 配色方案选择 |
| `storyboard.immersion_mode` | 沉浸模式 → 匹配 `stage6-components.md` 的配色速查表 |
| `storyboard.emotion_curve` | 6 拍情感强度 → 影响每个场景的视觉力度 |
| `storyboard.narrative_template` | 叙事模板 → 影响场景布局选择 |
| `storyboard.humor_style` | 幽默策略 → 是否添加 SpeechBubble 组件 |
| `storyboard.character_presence` | 角色出场 → 是否添加 CharOverlay 组件 |
| `narration_segments.json` 的 `visual_intent` | 每场景 × 每层的导演视觉意图（bg/fx/content 三层） |

**沉浸模式 → CSS 变量映射：** 从 `stage6-components.md` 的「沉浸模式配色速查」表获取具体色值，写入 `:root` CSS 变量。

```css
/* 示例：immersion_mode = "hyper-pace" */
:root {
  --bg-dark: #080818;
  --bg-mid: #001a33;
  --accent-warm: #00D4FF;
  --accent-cool: #0088CC;
  --text-primary: #ffffff;
  --text-secondary: #a0a0c0;
}
```

**色彩优先级规则（冲突时必须遵守）：**

当 `design.md` 的 `color_direction` 与 `immersion_mode` 配色速查表冲突时：
- **`color_direction` 优先。** `color_direction` 是 Stage 2 基于内容主题推导的定制配色，比 `immersion_mode` 的通用配色表更精准。
- `immersion_mode` 配色速查表作为**兜底默认值**，仅在 `color_direction` 未明确指定色值时生效。
- `immersion_mode` 的**风格方向**（暗度、饱和度、对比度特征）仍然有效，只是具体色值让位于 `color_direction`。
- 实践：先从 `immersion_mode` 查表获取 `:root` CSS 变量，再用 `color_direction` 中明确的色值覆盖对应变量。

**设计决策链：**
1. `immersion_mode` → `stage6-components.md` 配色速查 → `:root` CSS 变量（兜底）
2. `color_direction` → 覆盖 `:root` 中冲突的色值（优先）
3. 每个场景的**具体内容** → 读内容想画面（格言引导 + 反面清单兜底） → 背景层 + 特效层 + 内容层的视觉方案
4. `character_presence` + 每段 `character_expression` → CharOverlay 组件选择

## 6.3 音频嵌入

> **前置依赖：Stage 4 的 `segment_durations.json` 和音频文件必须已产出。**

HyperFrames 原生支持 `<audio>` 元素：自动发现、多轨混音、AAC 编码、MP4 封装。HTML 中嵌入音频后，`output.mp4` 直接包含完整音轨，无需 FFmpeg 手动合并。

### 嵌入方式

在 composition 根元素内添加 `<audio>` 元素：

```html
<div class="composition" data-composition-id="main"
     data-width="1080" data-height="1920" data-start="0" data-duration="TOTAL">
  <!-- 旁白音轨（track 1）：单条 narration.mp3，从 t=0 播放到结束 -->
  <audio data-track-index="1" data-volume="1" data-start="0"
         src="narration.mp3" preload="auto"></audio>

  <!-- BGM 音轨（track 2）：bgm.wav 循环播放，音量由 Stage 4 分析结果决定 -->
  <audio data-track-index="2" data-volume="0.06" data-start="0"
         src="bgm.wav" preload="auto" loop></audio>

  <!-- 场景 div ... -->
  <div class="clip s-hook" data-start="0" data-duration="4.2">...</div>
  <div class="clip s-solution" data-start="4.2" data-duration="7.8">...</div>
</div>
```

### 参数说明

| 属性 | 值 | 说明 |
|------|-----|------|
| `data-width` | `1080` | **必需**。视频宽度（px），HyperFrames 用此设置 viewport，缺少会导致 100% 黑帧 |
| `data-height` | `1920` | **必需**。视频高度（px），缺少会导致 100% 黑帧 |
| `data-start` (audio) | `0` | **必需**。音频起始时间，缺少会导致音频不播放 |
| `data-track-index` | `1`（旁白）/ `2`（BGM） | HyperFrames 按轨分组混音 |
| `data-volume` | 旁白 `1`，BGM 从 `segment_durations.json` 的 `meta.bgm_volume` 读取 | HyperFrames 混音时的音量系数 |
| `loop` | 仅 BGM 添加 | BGM 循环播放直到视频结束（安全兜底，Stage 4 已预对齐时长） |
| `preload="auto"` | 必须 | 确保 HyperFrames 预加载音频 |

### 电影解读模式

电影模式使用 `narration_new.mp3`（含静音填充），并在电影片段场景使用 `<video>` 元素（见 `shared/movie-clips` 的嵌入规则）。

### 对齐机制

**场景连续无间隔 + 旁白连续无间隔 → 单条 `narration.mp3` 天然与场景序列对齐。** 每个 scene div 的 `data-duration` 取自 `segment_durations.json` 的对应段落实测时长，画面时长 = 语音时长，零偏移计算。

HyperFrames 的 `resolveMediaDuration()` 还会用 ffprobe 自动检测 `<audio>` 时长，`mediaDurationFloor` 确保视频时间线不短于音频。

## 6.4 编写 HTML 组合（骨架 + 创意插槽模式）

> **核心思路：代码引擎生成 HTML 骨架（三层架构、composition 注册、audio 嵌入、GSAP 框架），LLM 只在创意插槽中自由编写 CSS/HTML/GSAP 代码。** 骨架保证结构性正确，LLM 保证视觉创意。

### §6.4-0 骨架生成（代码引擎自动执行）

> **这一步由代码引擎完成，LLM 不参与。** 输出为包含 `CREATIVE_SLOT` 标记的 HTML 骨架。

```bash
cd workspace/<YYYY>/<MM>/<DD>/<project-dir>

# 1. 生成 HTML 骨架 + 插槽清单
python .claude/commands/clipforge/scripts/generate_skeleton.py \
  --project-dir . \
  --output index_skeleton.html \
  --slots-json skeleton_slots.json

# 2. 验证骨架结构完整性
python .claude/commands/clipforge/scripts/validate_skeleton.py \
  --html index_skeleton.html
```

骨架包含：
- 完整 HTML 文档结构（DOCTYPE、head、body）
- 三层 div 架构（bg / fx / content），每层都有 `CREATIVE_SLOT` 标记
- `<audio>` 嵌入（旁白 + BGM，音量从 segment_durations.json 自动读取）
- GSAP timeline 初始化 + `window.__hf` 注册
- Phase 初始化和切换占位
- 每个 scene div 的 `id`、`data-start`、`data-duration` 已精确设置

### §6.4-1 视觉节奏上下文（代码引擎自动执行）

> **这一步由代码引擎完成。** 为每个场景生成视觉上下文 JSON，LLM 创作前**必须读取**。

```bash
# 生成视觉节奏上下文（emotion curve + 前序场景指纹 + 节奏引导）
python .claude/commands/clipforge/scripts/generate_visual_context.py \
  --project-dir . \
  --output visual_context.json
```

`visual_context.json` 为每个场景提供：

```json
{
  "scene_id": "s3",
  "emotion_curve_position": 0.22,
  "emotion_intensity": 0.55,
  "intensity_label": "平稳推进 — 视觉力度适中：保持节奏，可做小变化",
  "visual_theme": {
    "color_temperature": "cold-warm-contrast",
    "accent_colors": ["#00d4ff", "#ff6b35"],
    "immersion_mode": "hyper-pace"
  },
  "prev_scene_summary": {
    "scene_id": "s2",
    "dominant_colors": ["#FFD700", "#0a0a0f"],
    "bg_element_types": ["gradient", "glow", "noise"],
    "fx_types": ["canvas"]
  },
  "next_scene_summary": { "...": "..." },
  "rhythm_guidance": "推进阶段：视觉随内容展开\n前序场景主色: #FFD700\n → 保留一个色调族，其他维度制造差异"
}
```

**LLM 如何使用这些上下文：**
- `emotion_intensity` → 决定视觉力度（高=浓烈/低=收敛）
- `prev_scene_summary.dominant_colors` → 保留一个色调族（不突兀），替换其他色（不单调）
- `prev_scene_summary.bg_element_types` → 保留一种元素类型（连贯感），替换其余（新鲜感）
- `rhythm_guidance` → 直接的创作引导文字

### §6.4-2 创意填充（LLM 自由创作）

> **LLM 在此获得完全创作自由。** 骨架已经保证了结构性正确（三层、composition、audio、__hf），LLM 只需为每个插槽编写创意内容。创作前读取 `visual_context.json`，在自由创作中自然融入节奏感。

**LLM 输出的不是完整 HTML，而是创意内容——逐场景的 CSS + HTML + GSAP 动画。**

**读取以下文件作为创作输入：**
- `index_skeleton.html` — 骨架结构（了解有哪些插槽需要填充）
- `skeleton_slots.json` — 插槽清单（每个插槽的 scene_id、layer、类型）
- `visual_context.json` — 视觉节奏上下文（不单调、不突兀的引导）
- `design.md` — 视觉风格方向、storyboard、配色方案
- `narration_segments.json` — 每段的旁白内容、情感标记、visual_phases
- `stage6-components.md` — 组件库参考（可选，不是唯一来源）

如果 Stage 5 已制备素材，将 `assets/manifest.md` 中列出的文件路径作为 prompt 上下文传入 HyperFrames，让其在 HTML 中嵌入：

- **背景图**：用 `background-image: url(assets/xxx.jpg)` 设为场景背景，加 `background-size: cover` + 半透明遮罩层保证文字可读
- **图表 SVG**：用 `<img src="assets/chart.svg">` 嵌入，或 inline SVG 以便 GSAP 控制动画
- **图标 SVG**：用 `<img src="assets/icons/xxx.svg">` 或 CSS mask 方式嵌入
- **AI 生成图**：同背景图用法，适合定制化场景

> **素材交接方式：** 读取 `assets/manifest.md`，将每个素材的文件名和用途描述写入 HyperFrames 的 prompt。HyperFrames 不解析 manifest.md，由编排者负责桥接。

### 组件装配流程

1. **读取 `narration_segments.json`** — 每段的 `scene`、`text`（旁白内容）、`visual_phases`、`character_expression`、`humor_type`
2. **读取 `design.md` 的 `storyboard`** — 沉浸模式、叙事模板、情感曲线
3. **读取 `stage6-components.md`** — 视觉推导系统 + CSS 特效参考库 + 组件模板
4. **读取 `segment_durations.json`** — 动画断点强制使用 actual_duration（非 estimated_duration）：
   - 用 `actual_duration` 计算 BP 断点数组（见 `visual-phasing.md`）
   - GSAP timeline 中所有时间偏移量基于 BP 断点，不使用任何预估时长
   - `data-duration` 属性直接使用 `actual_duration` 值
5. **运行组件匹配** — 如果 `component_manifest.md` 不存在，执行 §6.4a 的匹配流程生成
6. **设计视觉（每个场景独立创作）** — 读场景内容，像导演一样构思画面：
   - 这段内容在说什么？观众该感受到什么？什么视觉能强化这个感受？
   - 参考 `stage6-components.md` 的设计格言（5 条正面引导）
   - 对照反面清单（10 条红线），确保不踩雷
   - 用 CSS 特效参考库的工具实现你的构思
   - **不查表、不套公式、每个场景独立思考**
6a. **特效组件匹配/创建**（每个场景独立执行）：
    a) 读取 `narration_segments.json` 该场景的 `visual_intent`
    b) 根据内容情绪和视觉意图，在 `components/registry.yaml` 中搜索匹配的 fx 组件
       - 按 `emotion_range` 和 `tags` 粗筛
       - 读取匹配组件文件，确认其 GSAP 动画是否适合当前场景
    c) 匹配成功 → 使用该组件，按场景参数调整
    d) 匹配不到或现有组件不合适 → **创建新特效**：
       - 从内容自主推导视觉表达（不是查表）
       - 编写新特效的 HTML + CSS + GSAP 动画
       - 新特效必须遵守 `render-safety.md` 全部约束
       - 新特效必须有 GSAP 动画（持续 `repeat:-1` 或入场 `.from()`）
    e) **新组件入库**：如果新特效质量高、可复用，封装为组件：
       - 创建 `components/fx/<name>.html`，包含 `@ComponentMeta` 头
       - 更新 `components/registry.yaml` 添加元数据
       - 向用户展示新组件 HTML 样例，由用户决定是否入库
7. **装配 HTML** — 按 HyperFrames composition 结构组装

### 场景 → 组件参考

> **这是参考映射，不是固定分配。** 根据场景内容选择最合适的组件组合，允许跨场景复用和变体。

| 场景类型 | 常用组件 | 视觉方向参考 |
|---------|---------|------------|
| hook | HeroCard | 震撼开场：高力度视觉、聚焦元素 |
| 数据/规模 | DataViz, NumGrid, MarketBars | 数据呈现：结构化、清晰、有科技感 |
| 对比/竞争 | CompareSplit, ScoreCompare | 双视角：冷暖分割、对冲视觉 |
| 结论/摘要 | VerdictBox, RecStrip | 核心论点：border-left 高亮、分层推荐 |
| 影响分析 | Spectrum | 层级分布：色带渐变 + 垂直条形图 |
| 时间线/路径 | TimeLineFlow | 叙事推进：轨道感、节点连线 |
| 突出/揭示 | TextReveal | 悬念展示：渐进揭示、聚光灯效果 |
| 标准模式项目介绍 | ProjectFullCard | 单项目全屏 8 层信息 |
| CTA | TextReveal | 收束聚焦：温暖引导、行动号召 |

> **标准模式项目介绍场景：** 使用 ProjectFullCard 组件（`components/content/project_full_card.html`），一个项目占满一屏，包含 8 层信息。数据来自 `narration_segments.json` 的 `selling_points`、`commentary` 字段和 content 数据。

### 角色和幽默组件插入

- `character_expression` 非 null 的场景 → 添加 `CharOverlay` 组件（对应表情 SVG）
- `humor_type` 非 null 的场景 → 添加 `SpeechBubble` 组件（文案从 narration 提取幽默句）
- 角色定位：画面左下角，占 15-20%
- 气泡定位：画面右下角或角色上方

### 特效填充验证

> `director_gate.py` §6 检查 layer-fx 内容非空，`stage6_gate.sh` 检查空 layer-fx 数量。HTML 写完后直接运行门禁脚本即可。

### 视觉检查（对照反面清单）

> HTML 写完后，快速扫一遍 `stage6-components.md` 的 10 条反面清单，确保没有踩雷。无需额外检查流程——反面清单已经编码了所有已知的视觉质量问题。

### 导演自审（Layer 3 — HTML 写完后、渲染前必须执行）

> **目的**：像导演审看每日样片，逐场景检查 HTML 是否实现了导演决策。这是最后一道"导演看监视器"关卡。

读取 `shared/director-toolkit.md` 的"导演 5 个必答题"，逐 `.clip` 场景自审：

| # | 必答题 | 检查点 |
|---|--------|--------|
| Q1 | 核心情绪是什么？ | 旁白文本 → 情绪词 → HTML 配色/光晕是否匹配 |
| Q2 | 观众该感受到什么？ | `narration_segments.json` 情感标记 → 视觉力度是否对等 |
| Q3 | 什么视觉能放大？ | 情绪 → 视觉词汇（暖冷/明暗/动静）→ HTML 是否实现 |
| Q4 | 相邻场景反差够不够？ | 上下 `.clip` 的背景渐变/配色是否不同 |
| Q5 | 眼睛该被引导到哪里？ | 字号最大/颜色最亮的元素 = 旁白的信息重点？ |

**对标 `narration_segments.json`**：

- `visual_phases[n].focus` → HTML 有对应内容元素？
- `visual_phases[n].key_data` → 画面数据完整呈现？
- 相邻场景配色雷同 → 调整背景渐变
- hook 缺乏冲击力 → 加强光晕/字号/对比度

**发现偏差立即修复。自审不通过的禁止渲染。**

### §6.4-3 组装与验证（代码引擎自动执行）

LLM 完成所有插槽的创意内容后，由代码引擎组装为最终 HTML：

```bash
cd workspace/<YYYY>/<MM>/<DD>/<project-dir>

# 1. 注入创意内容到骨架
python .claude/commands/clipforge/scripts/inject_creative.py \
  --skeleton index_skeleton.html \
  --creative creative_output.json \
  --output index.html

# 2. 验证所有插槽已填充
python .claude/commands/clipforge/scripts/validate_skeleton.py \
  --html index.html --strict

# 3. 运行导演门禁（重用现有 gate 检查）
python3 .claude/commands/clipforge/scripts/director_gate.py .
```

如果 gate 检查失败，仅修复失败的部分（不需要重写整个 HTML）。修复后重新注入或直接编辑 `index.html`。

**LLM 输出格式（两种任选）：**

**格式 A：结构化 JSON**
```json
[
  {"slot_id": "s1-css", "content": "#s1 .layer-bg { background: radial-gradient(...); }"},
  {"slot_id": "s1-bg-html", "content": "<div class='nebula'>...</div>"},
  {"slot_id": "s1-fx-html", "content": "<canvas id='particles-s1'>...</canvas>"},
  {"slot_id": "s1-content-html", "content": "<h1 style='font-size:100px;...'>震撼标题</h1>"},
  {"slot_id": "s1-gsap", "content": "tl.from('#s1 h1', {scale:0.85, opacity:0, duration:0.15, ease:'power3.out'}, 0);"}
]
```

**格式 B：带标记的代码片段（更自由）**
```html
<!-- CREATIVE_SLOT:s1-bg-html -->
<div style="position:absolute;inset:0;background:radial-gradient(ellipse at 30% 70%, rgba(75,0,130,0.8), transparent);">
  <div style="position:absolute;width:300px;height:300px;border-radius:50%;filter:blur(40px);"></div>
</div>
<!-- END_SLOT:s1-bg-html -->

<!-- CREATIVE_SLOT:s1-gsap -->
tl.from('#s1 h1', {scale: 0.85, opacity: 0, duration: 0.15, ease: 'power3.out'}, 0);
<!-- END_SLOT:s1-gsap -->
```

**创意自由度声明：**
- LLM 可以自由发明任何 CSS 效果（渐变、动画、滤镜、混合模式...）
- LLM 可以使用 Canvas/WebGL 编写全新特效
- LLM 可以引用组件库中的组件作为基础并修改
- LLM 也可以完全不使用组件库，从零创作
- 组件库是"工具箱和灵感来源"，不是约束

## 6.4a 特效工坊（组件匹配 + 新特效创建）

> **两阶段触发：**
> 1. §6.4 step 5 负责运行组件匹配 — 如果 `component_manifest.md` 不存在，执行下方匹配流程
> 2. 本节负责处理 `new` 条目 — 如果已生成的 manifest 含 `new` 标记，启动工坊创建新特效；否则跳过

### 匹配流程

1. **读取 visual_intent** — 从 `narration_segments.json` 中每个场景的 `visual_intent` 字段获取导演意图
2. **读取 registry.yaml** — 加载 `components/registry.yaml` 组件注册表
3. **粗筛** — 按 layer/tags/emotion_range/complexity 过滤候选组件（匹配方式：AI 语义理解，允许词形变体如 warm↔warmth、excitement↔energy）
4. **精排** — AI 语义理解：读取 visual_intent + 候选组件 description + 相邻场景已选组件，选择最佳匹配
5. **回退规则（按层）：**
   - **bg 层**：bg 组件本质是渐变+光晕，通过调色即可覆盖绝大多数场景。粗筛为空时，按 `color_hint` 色温方向选最近的 bg 组件（暖色→light_field，冷色→gradient_mesh），**不标记 `new`**
   - **fx 层**：粗筛为空时先考虑 fx:null（不使用特效），仅当场景明确需要动态装饰且无候选时才标记 `new`
   - **content 层**：粗筛为空时，回退到 §6.4 "场景→组件参考" 表的经验映射
6. **处理 null 场景** — `visual_intent` 为 null 的短场景（≤4s），manifest 中写 `auto`，表示 AI 自主推导，不指定组件
7. **输出 component_manifest.md** — 每个场景 × 每层 = 使用组件 + 来源(library/new/auto) + 参数变体

### 新特效创建（手动模式）

当匹配标记为 `new` 时：

1. **读取该场景的 visual_intent** — 情感内核 + 视觉意图
2. **读取已匹配的 library 组件** — 确保新特效与已有方案协调
3. **AI 推导新特效** — 生成 CSS/Canvas/Three.js 实现
4. **生成样本 HTML** — 独立可运行文件，写入 `fx_workshop/` 目录

### 样本预览

- **纯 CSS 特效** → 浏览器直接打开样本 HTML
- **Canvas/Three.js 特效** → `npx hyperframes render` 渲染为短视频片段
- 用户标记：使用/不使用 + 入库/不入库
- 不满意可重新推导（最多 3 轮）

### 入库流程

用户勾选入库的特效：
1. 复制到 `components/{layer}/` 正式目录
2. 补充 @ComponentMeta 元数据（如果 AI 未自动生成）
3. 更新 `registry.yaml` 添加新条目

### 自动模式

自动模式下跳过预览，AI 直接选择并使用。值得复用的特效写入 `components/auto_candidates/{layer}/`，下次手动模式时提示用户审阅。

### component_manifest.md 格式

```markdown
# Component Manifest — <project-name>

## Scene: s1-hook
- **bg**: gradient_mesh (library) — color_hint: warm gold
- **fx**: particle_burst (library) — emotion: excitement
- **content**: hero_card (library) — params: {title_size: 120px}

## Scene: s2-solution
- **bg**: light_field (library) — color_hint: cool blue
- **fx**: code_rain (new) — emotion: tension, tech
- **content**: project_full_card (library) — params: {rank: 1}
```

## 6.4b 视觉分镜（Visual Phasing）

> **当场景时长 >15 秒时必须使用。** 完整规范见 `clipforge/shared/visual-phasing`。

### 降级触发条件

以下任一情况发生时，从 HyperFrames 委托模式降级为自行编写 HTML：

| 触发条件 | 判断方式 |
|---------|---------|
| HyperFrames 技能不可用 | Skill 工具调用 `/hyperframes` 失败或找不到技能 |
| 技能调用超时/报错 | Skill 调用返回错误，或渲染命令 `npx hyperframes` 执行失败 |
| lint 检查不通过 | 产出的 HTML 运行 `npx hyperframes lint` 报错且无法快速修复 |

降级时向用户说明原因，然后继续执行。降级自行编写时，**严格遵守以下规则**：

### 内容规则

> **以下全部规则同样适用于 HyperFrames 委托模式产出的 HTML。**

- **内容安全规范**遵守 `clipforge/shared/shared-rules` 全部条款。
- **渲染安全规范**遵守 `clipforge/shared/render-safety` 全部条款（Stage 6 必读）。

### 结构规则

1. `window.__timelines` 是 `{}` 不是 `[]`
2. timeline 必须 `{ paused: true }`
3. 注册 key 匹配根元素的 `data-composition-id`
4. **`data-composition-id` 只在根元素上**，scene div 不要加
5. **每个场景包裹 div 必须有 `id="sN"`**（如 `id="s1"`、`id="s19"`）
   - `id` 取自 `narration_segments.json` 的 `scene` 字段前缀（如 `"s1-hook"` → `id="s1"`）
   - GSAP 动画使用 `#sN .xxx` 选择器，缺少 `id` 则动画静默丢失
   - **事故教训（2026-05-28）：s1/s19 缺少 id，导致首尾两个最重要场景的动画全部丢失**
   - **门禁自动校验**：`gate.py` 的 `scene_ids_match` 检查器会交叉验证 HTML 与 segments 的映射
6. 根元素必须有 `data-start="0"`
7. **`data-start` 和 `data-duration` 使用秒（不是毫秒）**
8. **`window.__hf` 必须定义 + GSAP timeline 必须注册**
   - 缺少 `__hf` 会导致 HyperFrames 渲染在 62% 处崩溃（45s 超时白屏）
   - `window.__timelines = {};`（空对象）会导致空白渲染
   - **事故教训（2026-05-28 + service-as-software）：遗漏 __hf 是最高频渲染致命错误**
   - 必须在 `</body>` 前添加：
     ```html
     <script src="https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.5/gsap.min.js"></script>
     <script>
     window.__timelines = {};
     const tl = gsap.timeline({paused: true});
     // ... 场景动画 ...

     // ★ 必须在 </script> 前注入 __hf — 从 segment_durations.json 计算总时长
     const totalDuration = /* sum of all segment actual_duration */;
     window.__hf = { duration: totalDuration, seek: function(t) { tl.time(t, false); } };
     window.__timelines["main"] = tl;
     </script>
     ```
   - **门禁自动校验**：`gate.py` 的 `hf_api_present` 检查器会扫描 index.html 中的 `window.__hf` 声明、`duration` 字段和 `seek` 函数

### CSS 规则

> **CSS 渲染安全规则全部在 `shared/render-safety.md` §1 中定义。** 以下仅列 Stage 6 独有规则，不重复渲染安全内容。

9. **`.clip` 必须铺满全画幅**：`position:absolute; inset:0`（与 `.composition` 同尺寸 1080×1920）。`.clip` 只做时间定位（data-start/data-duration），**不做空间裁剪**。安全区内缩由 `.scene-wrap` 或组件的 padding 负责（见 `shared/render-safety.md` §1.3）。如果 `.clip` 有 top/right/bottom/left 偏移，背景层会被限制在 clip 内，clip 外显示黑色 → 四面黑边。

### 视觉设计规则（必须遵守）

#### 视觉密度要求（分级规则）

| 场景类型 | 最低元素数 | 说明 |
|---------|-----------|------|
| 内容场景（项目介绍等） | ≥ 5 | 排名 + 名称 + 数据 + 描述 + 标签（+ 卖点/角色 可选） |
| Hook/CTA | ≥ 3 | 主标题 + 装饰 + 标识（不强凑，保持极简冲击力） |
| 高潮场景 | ≥ 5 | 额外添加视觉强化元素（特效爆发 + 数据强调） |

每个场景的元素计数不包含背景装饰（光晕、网格等），只计入 `.layer-content` 中的可读/可交互元素。

#### hook 场景 — 黄金 3 秒视觉

hook 必须满足全部要求：信息极简（≤3 元素）、字号最大（主标题 ≥100px）、对比最强、光晕加倍（2 个大光晕 ≥画面 50%）、发光效果、配色优雅（≤3 色）、布局精致（留白 ≥30%）、**首帧即冲击**（首个文字动画 t=0 启动、duration ≤ 0.15s，禁止任何延迟）。

#### 背景：多元素组合（≥3 种视觉类型）

每个场景的 bg 层必须包含 **至少 3 种不同类型的视觉元素**（含渐变底色，仅 glow+grid 组合不满足要求）。允许的类型：

| 类型 | 实现方式 | 组件参考 |
|------|---------|---------|
| 渐变底色 | `linear-gradient` / `radial-gradient` | gradient_mesh |
| 噪点纹理 | SVG `feTurbulence` | noise_field |
| 等高线 | `repeating-radial-gradient` | contour_lines |
| 光束射线 | `repeating-conic-gradient` + 旋转 | radial_beams |
| 网格+扫描线 | `background-image` + `@keyframes scanLine` | scan_grid |
| 暗角聚光 | `radial-gradient` 暗角 + 中心辉光 | vignette_glow |
| 波纹扩散 | `repeating-radial-gradient` + 扩散环 | wave_ripple |
| 光晕装饰 | `filter:blur()` 球体 | light_field |

**视觉风格分组**：20 个场景的视频至少有 4-5 种不同的 bg 风格组（如：暖色渐变+噪点、冷色等高线、暖色光束、冷色网格、暗角聚光）。相邻场景禁止使用相同的渐变色值组合。

**禁止模式**：glow+grid 三件套（线性渐变 + 1-2 个模糊光圆 + grid-bg）作为唯一 bg 方案。这是 R-R-011 HARD 门禁。

#### 场景独立配色

| 场景类型 | 强调色方向 |
|---------|-----------|
| hook | 暖色（金/琥珀/橙） |
| solution/top | 暖色 → 冷色过渡 |
| features/more | 冷色（翠绿/青） |
| CTA | 暖色主调 + 冷色辅 |

#### 项目卡片设计

展示项目的卡片必须包含：排名数字（竖屏≥52px/横屏≥40px）、项目名（等宽 竖屏≥42px/横屏≥32px）、中文描述（竖屏≥36px/横屏≥32px）、语言标签（药丸 竖屏≥28px/横屏≥24px）、星数（右对齐 竖屏≥36px/横屏≥32px）。

#### CTA 场景

CTA 必须：中心光晕 + 大标题（竖屏 96px+ / 横屏 72px+）+ 副标题（竖屏 36px+ / 横屏 32px+）+ 3-4 个标签药丸。

#### 整体品质检查

渲染前对照清单：背景三层（bg ≥2 种视觉元素类型，禁止纯 glow+grid 三件套）、fx 层非空（R-R-008 HARD）、相邻场景 bg 风格可区分（R-R-012 HARD）、光晕、卡片三栏、配色区分、CTA 完整、字号达标、安全区、居中（flexbox）、`__hf`（duration + seek）、场景 id 映射、GSAP timeline、音频、无 anim-in、无 HTML 实体、scene-wrap padding、视觉密度、无多余 composition、**`.clip` 必须是 `inset:0`（禁止 top/right/bottom/left 偏移 → 黑边）**。

### 动画规则

10. 入场动画时长 **0.3-0.7 秒**（"快入+静止"模式）
11. stagger 间隔 **0.2-0.3 秒**
12. easing: `power3.out` 用于入场
13. 场景间由框架 transitions 处理，不手动 exit
14. **动画设计原则：** 每个场景的动画在 1 秒内完成入场，之后保持最终状态静止直到 `data-duration` 结束。
15. **hook 场景 A/V 同步铁律：** hook（s1）的首个文字动画必须从 t=0 启动，duration ≤ 0.15s，用 `scale` 代替 `y` 位移（缩放冲击感更强）。示例：`tl.from('#s1 h1', {scale:0.85, opacity:0, duration:0.15, ease:'power3.out'}, 0)`。副标题在 0.15s 启动，0.2s 内完成。确保旁白发声（t≈0.1s）时文字已可见，消除"先声后画"的脱节感。
15. **fx 动画密度**：每个场景的 `.layer-fx` 中，每个特效元素至少有 1 个 GSAP 动画调用。不限动画类型——脉冲、漂浮、旋转、闪烁、扫描、缩放、位移动画都可以。纯静态 fx 元素（div 在 timeline 中无 GSAP 目标）视为违规。

### 字体规则

15. 优先使用 HyperFrames 内置字体映射
16. **中文渲染**：先渲染一帧验证，异常时用 `font-family: 'Inter', 'PingFang SC', 'Microsoft YaHei', sans-serif`

### 渲染规则

17. 渲染传目录路径（`.`），不传文件路径
18. 渲染前确保 `lint` 通过
19. **渲染后白屏/空白检查**：`frame_analysis.py`（Layer 2）自动执行暗帧和亮度检测，`stage6_gate.sh` 调用

## 6.5 画布方向

默认输出**竖屏（1080×1920）**。用户明确要求横屏时输出 **横屏（1920×1080）**。

方向判定：根组合 `data-width` / `data-height` — `h > w` 为竖屏，`w > h` 为横屏。所有字号、padding、布局按方向自动切换（详见 `director-toolkit.md` 排版表和 `render-safety.md §1.3`）。

### 横屏视觉增强（强制性）

横屏（1920×1080）比竖屏有 1.78 倍的水平空间，但也更容易显得空和单调。以下规则横屏视频**必须遵守**：

1. **每个场景必须有 fx 层动画**（R-R-008/013 HARD）。横屏空间大，纯静态 bg 会显得廉价。每个场景至少 2 个有 GSAP 动画的 fx 元素（粒子、光束、脉冲、扫描线、漂浮物等）。
2. **标题文字使用渐变或高对比配色**。纯白文字在横屏宽幅画面上显得平淡。推荐技法：
   - `linear-gradient(90deg, #color1, #color2)` + `background-clip:text` + `transparent fill-color`
   - 标题 ≥56px 时渐变效果最佳
   - 渐变色从场景主题色推导（暖色场景用金→橙，冷色场景用青→紫）
3. **bg 层不可只用纯色渐变**。横屏画幅更大，纯色渐变 bg 在 H.264 编码后呈现为平坦色块。必须叠加纹理元素（等高线、光束、扫描线、噪点等），与竖屏 bg 层质量标准一致。
4. **相邻场景 bg 必须有可区分的视觉差异**（R-R-012 HARD），横屏尤甚——同质化在宽幅画面上更明显。

### 动画设计原则（HyperFrames 时长模型）

采用"快入+静止"动画策略：入场 0.3-0.7s，之后静止到场景结束。

字号参考（与 director-toolkit.md 排版表对齐）：

| 层级 | 竖屏 (1080×1920) | 横屏 (1920×1080) |
|------|-----------------|-----------------|
| impact | 120-220px | 88-160px |
| title | 64-96px | 56-80px |
| body | 36-48px | 32-44px |
| annotation | 28-36px | 24-32px |

### 竖屏垂直居中规则

> **居中已内置到 `.phase` CSS 中**：`.phase` 统一使用 `display:flex;flex-direction:column;justify-content:center`，所有 phase 内容自动垂直居中。不需要在 `.scene-wrap` 或 inline style 上手动添加 flex 居中。

**禁止在 `.scene-wrap` 上加 flex 居中**：Phase 模式下 `.phase` 是 `position:absolute`，不参与 `.scene-wrap` 的 flex 布局，在 scene-wrap 上加 flex 无效。

**禁止紧贴顶部**：不能用 `top: 80px` 等小值。场景内容容器禁止 `position: absolute` + 小 top 值。

### 布局推导（两级体系）

**垂直方向强制居中**（`.phase` flex 内置），水平方向由布局推导决定：

#### Level 1：visual_type → 布局框架

每个 phase 的布局从 `narration_segments.json` 的 `visual_phases[].visual_type` 推导，不套固定模板。完整规格表见 `stage6-components.md` 的「布局推导体系」章节。

**水平对齐推导规则：**

| visual_type | 水平对齐 | 说明 |
|------------|---------|------|
| hero | 全部居中 | 标题 + 数字 + 副标题，间距 generous |
| list | 标题居中，条目区 width:85% 内部左对齐 | 序号 + 文字条目 |
| data | 标题居中，数据行 width:85% | label-value 行 |
| compare | flex-direction:row，双栏各 flex:1 | 左冷右暖对比色 |
| timeline | 标题居中，步骤区 width:85% 内部左对齐 | 时间标签 + 文字 |
| highlight | 全部居中 | 大号文字 + 可选徽章 |

#### Level 2：内容字数 → 元素尺寸

primary/标题元素根据文本长度缩放：≤4 字 = 1.0×，5-8 字 = 0.85×，9-14 字 = 0.7×，15-24 字 = 0.55×，≥25 字 = 0.45×。具体基准字号见 `stage6-components.md`。

#### 密度控制

- `visual_phases[].layout_hint.density` 可微调间距（compact ×0.7 / standard ×1.0 / generous ×1.3）
- 不指定时从 visual_type 自动推导：hero/highlight → generous，list/timeline → standard，data/compare → compact

#### 渲染顺序原则

- 水平：从左到右（排名 → 名称 → 数据）
- 垂直：从上到下（标签 → 标题 → 描述 → 卖点）
- 不强制所有元素居中，让内容和 visual_type 决定最美观的布局

### 平台安全区域

**竖屏（1080×1920）：**
- 顶部危险区：上 180px
- 底部危险区：下 220px
- 水平安全边距：左 80px / 右 80px
- 安全内容区：180px ~ 1700px（垂直），80px ~ 1000px（水平）
- padding：`180px 80px 220px 80px`

**横屏（1920×1080）：**
- 顶部危险区：上 60px
- 底部危险区：下 60px
- 水平安全边距：左 120px / 右 120px
- 安全内容区：60px ~ 1020px（垂直），120px ~ 1800px（水平）
- padding：`60px 120px 60px 120px`

## 6.6 渲染

### 渲染前检查（必须执行）

```bash
cd workspace/<YYYY>/<MM>/<DD>/<project-dir>

# 1. 确认音频文件存在
ls -la narration.mp3 bgm.wav

# 2. 导演门禁 — HTML 设计意图验证（Layer 1）
python3 .claude/commands/clipforge/scripts/director_gate.py .
# 未通过则修复 HTML 后重新执行，不得跳过

# 3. 移除所有非 index.html 的 composition 文件
for f in cover.html index_with_bgm.html cover.html.bak; do
  [ -f "$f" ] && mv "$f" "$f.renderbak"
done
```

### 渲染命令

```bash
npx hyperframes lint
npx hyperframes render . --output output.mp4 --video-bitrate 5M
```

### 渲染后恢复

```bash
for f in cover.html index_with_bgm.html; do
  [ -f "$f.renderbak" ] && mv "$f.renderbak" "$f"
done
rm -f cover.html.bak.renderbak index_with_bgm.html.renderbak
```

### 渲染后音频验证

```bash
ffprobe -v quiet -show_streams -select_streams a output.mp4 | grep codec_name
ffmpeg -i output.mp4 -af "volumedetect" -f null /dev/null 2>&1 | grep volume
```

## 6.7 单次渲染 + ffmpeg 合成

> **HyperFrames 只渲染一次 output.mp4（旁白 + BGM 混合）。** output_no_bgm.mp4 由 ffmpeg 从 output.mp4 视频轨 + narration.mp3（纯旁白源文件）合成，无需二次渲染。

### 渲染前准备

```bash
cd workspace/<YYYY>/<MM>/<DD>/<project-dir>

# 从 segment_durations.json 读取 BGM 音量，写入 HTML
BGM_VOL=$(python -c "import json; print(json.load(open('segment_durations.json'))['meta'].get('bgm_volume', 0.15))")

# BGM 音量预检
if [ "$(echo "$BGM_VOL < 0.10" | bc 2>/dev/null || echo "0")" -eq 1 ]; then
    echo "BLOCKED: bgm_volume=${BGM_VOL} < 0.10，BGM 不可听。回退 Stage 4 重新校准。"
    exit 1
fi
if [ "$(echo "$BGM_VOL > 0.50" | bc 2>/dev/null || echo "0")" -eq 1 ]; then
    echo "BLOCKED: bgm_volume=${BGM_VOL} > 0.50，BGM 过响。回退 Stage 4 重新校准。"
    exit 1
fi
echo "OK: bgm_volume=${BGM_VOL}"

sed -i "s/id=\"bgm\" data-volume=\"[^\"]*\"/id=\"bgm\" data-volume=\"${BGM_VOL}\"/" index.html
echo "HTML BGM data-volume set to ${BGM_VOL}"
```

### 渲染（仅一次）

```bash
# ── 渲染: 完整 HTML → output.mp4（旁白 + BGM）──
npx hyperframes render . --output output.mp4 --video-bitrate 5M
```

### 合成 output_no_bgm.mp4（ffmpeg，不渲染）

> **禁止**从 output.mp4 提取音频轨（只有 1 条混合轨，BGM 无法分离）。
> **必须**用 narration.mp3（纯旁白源文件）作为音频源。

```bash
# ── output_no_bgm.mp4 = output.mp4 视频轨 + narration.mp3 音频轨 ──
ffmpeg -y -i output.mp4 -i narration.mp3 \
  -map 0:v -map 1:a \
  -c:v copy -c:a aac -b:a 128k \
  -shortest \
  output_no_bgm.mp4
```

### 文件逻辑

```
output.mp4      = 视频 + 旁白 + BGM（HyperFrames 渲染）
output_no_bgm.mp4 = output.mp4 的视频 + narration.mp3 的音频（ffmpeg 合成）
final.mp4      = cover.png + output.mp4
final_no_bgm.mp4 = cover.png + output_no_bgm.mp4
```

## 6.8 封面帧拼接

> **ffmpeg concat filter 拼接封面帧 + 正片视频，不碰音频。**

```bash
cd workspace/<YYYY>/<MM>/<DD>/<project-dir>

# ── 创建封面帧（1帧 H264）──
ffmpeg -y -loop 1 -i cover.png -c:v libx264 -b:v 5M -t 0.0333 \
  -pix_fmt yuv420p -r 30 cover_clip.mp4

# ── 拼接：封面帧 + 正片 ──
# final.mp4 = cover + output.mp4（含 BGM）
ffmpeg -y -i cover_clip.mp4 -i output.mp4 \
  -filter_complex "[0:v][1:v]concat=n=2:v=1:a=0[outv]" \
  -map "[outv]" -map 1:a \
  -c:v libx264 -b:v 5M -c:a copy \
  final.mp4

# final_no_bgm.mp4 = cover + output_no_bgm.mp4（仅旁白）
ffmpeg -y -i cover_clip.mp4 -i output_no_bgm.mp4 \
  -filter_complex "[0:v][1:v]concat=n=2:v=1:a=0[outv]" \
  -map "[outv]" -map 1:a \
  -c:v libx264 -b:v 5M -c:a copy \
  final_no_bgm.mp4

# ── 清理临时文件 ──
rm -f cover_clip.mp4
```

### BGM 音量

> BGM 音量由 Stage 4 的 `bgm_gap_check.py` 自动查表校准，值存储在 `segment_durations.json` 的 `meta.bgm_volume`。渲染前从该文件读取并写入 HTML `data-volume`。

### 致命约束

| 约束 | 违反后果 |
|------|---------|
| **output_no_bgm.mp4 必须用 narration.mp3 合成** | 用 `-map 0:a:0` 从 output.mp4 提取只得到混合轨，BGM 无法消除 |
| **ffmpeg 只做封面帧拼接，不碰 output.mp4/output_no_bgm.mp4 的音频** | concat filter 只拼接视频流，音频从源文件直接 copy |
| **BGM 音量在渲染前写入 HTML** | 渲染后无法修改 HyperFrames 已混入的 BGM 音量 |

> **封面帧仅增加 1/30 秒（~33ms），对音画同步无感知影响。** `cover.png` 仍作为独立封面图上传平台。

## 6.9 Stage 6 完成门禁

```bash
# ── Stage 6 完成门禁 ──
bash .claude/commands/clipforge/scripts/stage6_gate.sh

# ── 渲染帧视觉分析（Layer 2）──
python3 .claude/commands/clipforge/scripts/frame_analysis.py .
```

**如果任何检查失败，修复问题后重新执行，不得跳过。**

---

## 约束声明

**Iron Law:** 渲染前未移除 cover.html = 渲染必冲突。GSAP timeline 未注册 = 全片空白。output_no_bgm.mp4 未从 narration.mp3 合成 = 双版本输出失败。

> 本阶段的结构化约束（HARD/SOFT 规则 + Guard Red Flags）由引擎注入提供。执行前运行 `python engine/inject.py --skill stage6-production` 获取完整约束 prompt。
