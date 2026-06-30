# Stage 6: 沉浸式视频制作（委托 HyperFrames）

当 `segment_durations.json` + 音频文件已存在且 `output.mp4` 不存在时触发。基于组件库装配 HTML 组合并渲染为视频。

## §6.1 项目初始化

```bash
# 创建日期目录（如不存在）+ 项目目录（纯英文路径）
mkdir -p "workspace/<YYYY>/<MM>/<DD>/<project-name>"
npx hyperframes init "workspace/<YYYY>/<MM>/<DD>/<project-name>" --example blank --non-interactive
```

项目目录结构为 `workspace/<YYYY>/<MM>/<DD>/<项目名>/`，日期格式为纯数字（如 `workspace/2026/05/18/github-trending/`）。详见 `clipforge.md` 的「项目目录结构」段。

## §6.2 读取 design.md + storyboard

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

## §6.3 音频嵌入

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

## §6.4 编写 HTML 组合（创意碎片化 + 组装确定化）

> **代码引擎生成 `creative/` 碎片骨架（每场景一个 `sNN.html`，含三层 div + phase 占位），LLM 逐场景填充视觉创意。组装脚本负责所有确定性结构：clip 包裹、data-start/duration、GSAP 时间线、phase opacity、audio 嵌入、DOCTYPE。**

## §6.5 碎片骨架生成 + 视觉上下文（代码引擎自动执行）

> `s6_prepare.sh` 一次性完成: phase 校准 → creative/ 碎片骨架生成 → 碎片验证 → 视觉上下文生成。

```bash
bash .claude/commands/clipforge/scripts/s6_prepare.sh --project-dir .
```

生成的 `creative/` 目录包含：
- `style.css` — 已预填 `:root` CSS 变量（从 design.md 提取配色），LLM 在此追加自定义组件 CSS
- `s01.html` ~ `sNN.html` — 每个场景一个碎片模板，含三层 div（bg/fx/content）+ phase 占位 + 旁白提示
- 单 phase 场景：无 phase div 包裹，直接填 layer-content
- 多 phase 场景：生成 `phase-1`/`phase-2` div，按旁白句子自动分配提示

> **LLM 永远不碰以下内容（组装脚本 `s6_assemble_html.py` 负责）：** clip 包裹、`data-start`/`data-duration`、GSAP timeline、phase opacity 切换、`<audio>` 嵌入、DOCTYPE/HEAD 结构。碎片中**只写三层 div 的内容**。

## §6.6 视觉节奏上下文（代码引擎自动执行）

> `s6_prepare.sh` 已自动生成 `visual_context.json`，创作前**必须读取**。

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

## §6.7 创意填充（LLM 自由创作）

> 碎片保证结构性正确，LLM 只需逐场景填充视觉内容。创作前读取 `visual_context.json`。

**LLM 逐个填充 `creative/sNN.html` 碎片文件，每个碎片只包含三层 div 的内容（bg/fx/content），不含 clip 包裹和 GSAP。**

> **⛔ bg 层铁律（2026-06-23 事故固化）：layer-bg 里写的内容会被组装脚本覆盖，bg 不是创作空间。**
> `s6_assemble.sh` 检测 `<!-- bg-component: NAME -->` 标记后，用 `components/bg/NAME.html` 的组件 DOM **整体覆盖** layer-bg 内一切——碎片里自写的 bg CSS/元素全部丢弃（从机制上强制 R-R-021，`s6_assemble_html.py:_inject_bg_component`）。
> - **bg 创作空间 = 选组件 + CSS 变量换色**：layer-bg 内只放一行 `<!-- bg-component: NAME -->`（NAME 从 `components/bg/` 选），换色靠 `creative/style.css` 的 `:root` CSS 变量
> - **选组件先确认视觉类型达标**：选中组件须含 ≥2 种视觉类型且非纯 glow+grid（R-R-009）。组件 `@ComponentMeta` 的 `visual_types` 字段已声明类型，gate 优先读它判定——选 `visual_types` 含 beams/contour/wave/noise/particles/geometry/vignette/dots/scan 的组件即安全；只含 {gradient, glow} 的会被误判淘汰。查全部组件达标：`python scripts/check_bg_components.py --check`
> - **fx/content 才是自由创作层**：layer-fx（特效动画）和 layer-content（文字卡片）由 LLM 自由发挥，不被覆盖

**碎片示例（多 phase 场景 `creative/s01.html`）：**
```html
<!-- 场景: hook | 时长: 20.0s -->
<div class="layer-bg">
  <!-- LLM 填充背景 -->
</div>
<div class="layer-fx">
  <!-- LLM 填充特效 -->
</div>
<div class="layer-content">
<div class="phase phase-1">
  <!-- phase-1 旁白: 开场钩子... -->
  <!-- LLM 填充 phase-1 视觉内容 -->
</div>
<div class="phase phase-2">
  <!-- phase-2 旁白: 数据引入... -->
  <!-- LLM 填充 phase-2 视觉内容 -->
</div>
</div>
```

**读取以下文件作为创作输入：**
- `creative/sNN.html` — 待填充的场景碎片（了解三层结构和 phase 布局）
- `creative/style.css` — 已有 CSS 变量和组件样式（在此追加自定义 CSS）
- `visual_context.json` — 视觉节奏上下文（不单调、不突兀的引导）
- `design.md` — 视觉风格方向、storyboard、配色方案
- `narration_segments.json` — 每段的旁白内容、情感标记、visual_phases
- `stage6-components.md` — 组件库参考（bg 层必须从中选用，fx/content 可自由创作）
- `shared/text-effects.md` — 文字特效配方库（content 层呼吸/渐变/跑马灯/3D 等，标题/数字必选特效）

如果 Stage 5 已制备素材，将 `assets/manifest.md` 中列出的文件路径作为 prompt 上下文传入 HyperFrames，让其在 HTML 中嵌入：

- **背景图**：用 `background-image: url(assets/xxx.jpg)` 设为场景背景，加 `background-size: cover` + 半透明遮罩层保证文字可读
- **图表 SVG**：用 `<img src="assets/chart.svg">` 嵌入，或 inline SVG 以便 GSAP 控制动画
- **图标 SVG**：用 `<img src="assets/icons/xxx.svg">` 或 CSS mask 方式嵌入
- **AI 生成图**：同背景图用法，适合定制化场景
- **技术架构图（深度解析模式）**：用 `<img src="assets/arch.svg">` 嵌入 Stage 5 制作的专业 SVG 架构图，配合旁白讲解。**取代 HTML/CSS 即兴架构图**（即兴画不够精美、不符合技术人画图方式）。架构场景的 layer-content 只放 `<img>` + 标题，不手画分层框
  - **前置确认**：嵌入前确认 `assets/arch.svg` 存在；若 stage5 被跳过导致缺失，回退用 HTML/CSS 即兴架构图（保证渲染不崩），并在交付标注「架构图降级（未用 SVG 素材）」

> 读取 `assets/manifest.md`，将素材文件名和用途写入 HyperFrames prompt。

### 组件装配流程

1. **参照模板**（HARD）:
   写 HTML 前，必须参照一个已验证的 HTML 模板。按以下优先级选择：
   - **首选**：同分类最近一个已成功渲染的项目的 `index.html`（`output.mp4` 存在且 > 500KB）
   - **备选**：`templates/golden-portrait.html`（首次运行或无历史项目时使用）
   - 以参照模板的 DOM 结构为骨架，只替换内容和配色。禁止凭空构思新的 DOM 层级结构。
2. **读取 `narration_segments.json`** — 每段的 `scene`、`text`（旁白内容）、`visual_phases`、`character_expression`、`humor_type`
3. **读取 `design.md` 的 `storyboard`** — 沉浸模式、叙事模板、情感曲线
4. **读取 `stage6-components.md`** — 视觉推导系统 + CSS 特效参考库 + 组件模板
5. **运行组件匹配** — 如果 `component_manifest.md` 不存在，执行 §6.10 的匹配流程生成
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
       - 读取匹配组件文件，确认其动画是否适合当前场景
    c) 匹配成功 → 使用该组件，按场景参数调整
    d) 匹配不到或现有组件不合适 → **创建新特效**：
       - 从内容自主推导视觉表达（不是查表）
       - 编写新特效的 HTML + CSS
       - 新特效必须遵守 `render-safety.md` 全部约束
    e) **新组件入库**：如果新特效质量高、可复用，封装为组件：
       - 创建 `components/fx/<name>.html`，包含 `@ComponentMeta` 头
       - 更新 `components/registry.yaml` 添加元数据
       - 向用户展示新组件 HTML 样例，由用户决定是否入库
7. **逐场景填充 `creative/sNN.html`** — 将三层视觉内容写入对应碎片文件，CSS 组件样式写入 `creative/style.css`

### 场景 → 组件参考

> 参考映射，根据场景内容选择组件，允许跨场景复用和变体。

| 场景类型 | 常用组件 | 视觉方向参考 |
|---------|---------|------------|
| hook | HeroCard | 震撼开场：高力度视觉、聚焦元素 |
| 数据/规模 | DataViz, NumGrid, MarketBars | 数据呈现：结构化、清晰、有科技感 |
| 对比/竞争 | CompareSplit, ScoreCompare | 双视角：冷暖分割、对冲视觉 |
| 结论/摘要 | VerdictBox, RecStrip | 核心论点：border-left 高亮、分层推荐 |
| 影响分析 | Spectrum | 层级分布：色带渐变 + 垂直条形图 |
| 时间线/路径 | TimeLineFlow | 叙事推进：轨道感、节点连线 |
| 突出/揭示 | TextReveal | 悬念展示：渐进揭示、聚光灯效果 |
| 标准模式项目介绍 | ProjectFullCard | 单项目全屏 9 层信息（含 owner avatar） |
| CTA | TextReveal | 收束聚焦：温暖引导、行动号召 |

> **标准模式项目介绍场景：** 使用 ProjectFullCard 组件（`components/content/project_full_card.html`），一个项目占满一屏，9 层信息（排名/类别/项目名/avatar/描述/涨星进度条/topics/卖点/评语）。
>
> **数据源**：`narration_segments.json` 的 `selling_points`、`commentary` 字段 + content_ready.txt（`用途:` 行 → 填 `pfc-use` 顶部利益标签；`avatar:` 行 → 填中部 avatar）+ `raw_trending.json` 的 `avatar_path`/`stars_today`/`topics`。
>
> **⛔ 纵向分带铁律**：ProjectFullCard 必须 `justify-content: space-between` 三带（顶/中/底）填满 1920 安全区，**禁单列 `align-items:center; justify-content:center`**（旧布局垂直利用率仅 33%，元素挤中间）。owner avatar 圆形头像作中部带视觉锚点。
>
> **⛔ 项目名完整铁律**：项目名（owner/repo）**禁 `white-space:nowrap + overflow:hidden + text-overflow:ellipsis`**，必须完整显示——独占整行 `width:100%` + `word-break:break-word`（长名换行不省略）。短视频手机端省略号不可读（SkillSpect... 截断事故）。**此规则适用所有 content 层文字，不限于 ProjectFullCard**。
>
> **avatar 引用**：`<img src="assets/avatars/{owner}.png">`（fetch_avatars.py 在数据采集后下载）。**Stage6 创作碎片时**读 content_ready.txt 每个项目的 `avatar:` 行（或 raw_trending.json 的 `avatar_path`）：值为路径则填 `<img src="...">`，值为 `null`（下载失败）则**省略整个 `.pfc-avatar-wrap`**（含 ring + img，不可只删 img 留空 ring），中部带 flex 自适应不塌。涨星进度条 `.pfc-bar-fill` 宽度按 `stars_today` 相对当日最大值设百分比。

### 角色和幽默组件插入

- `character_expression` 非 null 的场景 → 添加 `CharOverlay` 组件（对应表情 SVG）
- `humor_type` 非 null 的场景 → 添加 `SpeechBubble` 组件（文案从 narration 提取幽默句）
- 角色定位：画面左下角，占 15-20%
- 气泡定位：画面右下角或角色上方

### 特效填充验证

> `director_gate.py` §6 检查 layer-fx 内容非空，`stage6_gate.sh` 检查空 layer-fx 数量。HTML 写完后直接运行门禁脚本即可。

### 视觉检查（对照反面清单）

> HTML 写完后，扫一遍 `stage6-components.md` 的 10 条反面清单。

### 导演自审（创意轨自检 — HTML 写完后、渲染前的 LLM Q1-Q5，非脚本门禁；与 director_gate[Layer 1] 区分）

> 逐场景检查 HTML 是否实现了导演决策。

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

## §6.8 组装与验证（代码引擎自动执行）

LLM 填充完所有 `creative/sNN.html` 碎片后，`s6_assemble.sh` 一次性完成: 碎片完整性验证 → 碎片组装 index.html → 导演门禁：

```bash
bash .claude/commands/clipforge/scripts/s6_assemble.sh --project-dir .
```

组装脚本自动处理的确定性内容（LLM 无需关心）：
- 每个 `creative/sNN.html` 碎片被 `<div class="clip" id="sNN" data-start="..." data-duration="...">` 包裹
- `data-start` 按累计时长精确设置，`data-duration` 取自 `segment_durations.json`
- GSAP timeline 自动生成：场景硬切（前场景 opacity 0 / 当前场景 1）+ phase 切换（按 `phase_timings.json` 句子锚点）
- `<audio>` 元素嵌入（旁白 + BGM，BGM 音量从 segment_durations.json 自动读取）
- DOCTYPE / HEAD / `<style>`（基础层 CSS + creative/style.css）/ body 结构

如果 gate 检查失败，仅修复对应 `creative/sNN.html` 碎片的失败部分（不需要重写整个 HTML）。修复后重新运行 `s6_assemble.sh` 重新组装。

**创意自由度声明：**
- LLM 可以自由发明任何 CSS 效果（渐变、动画、滤镜、混合模式...）
- LLM 可以使用 Canvas/WebGL 编写全新特效
- LLM 可以引用组件库中的组件作为基础并修改
- **bg 层强制使用组件库**（R-R-021 HARD）：每个场景必须从 `components/bg/` 选用 1 个 bg 组件，保留 `<!-- bg-component: NAME -->` 标记。允许换色（CSS 变量/色值替换）、叠加背景图片，禁止自行编写 bg CSS
- **bg 亮度底线**（gate: frame_analysis.py §4）：bg 组件底色亮度 L ≥ 12%（hsl 第三参数），装饰元素（线条/光晕/粒子）alpha ≥ 0.12。底色过暗或装饰 alpha 过低 → 渲染平均亮度 < 25/255 → frame_analysis warn/fail。暗调场景（危机/破产）通过降低装饰密度实现"暗"，底色仍需 L ≥ 12%
- fx/content 层的组件库仍是工具箱和灵感来源，不强制

## §6.9 渲染后视觉 QA 自审（LLM 创意轨,非门禁）

output.mp4 渲染完成后,运行视觉 QA 抽帧分析,**让你看见自己的渲染结果**再决定布局要不要改:

python scripts/s6_visual_qa.py --project-dir <PROJECT_DIR>

读 `visual_qa_report.json` + 看 `qa_frames/*.png`:
- **安全区**:每场景 content_y 应在 [180,1700](竖屏)/[60,1860](横屏)。溢出会被后续 stage6 门禁 HARD 拦截,这里先自查。
- **断层/间距**(创意判断归你):看 blank_bands 和帧截图,判断空白带是「有意留白」还是「布局断层」。项目名与头像、各元素间距是否舒适,由你决定。不满意就调整 creative/sNN.html 碎片重渲染。

⛔ 代码只产客观数据(content_y / blank_bands 坐标),不替你下「是不是断层」的判断——布局审美归 LLM。这一步是非强制自审,但强烈建议:你终于能看见渲染结果了。

> **⛔ 顺序铁律（防 qa_frames 残留）**：§6.9 QA 在 **stage6 渲染后、cleanup 之前**。流程：渲染 → §6.9 QA（产 qa_frames）→ stage7 delivery → **cleanup（清 qa_frames，管线终点）**。**cleanup 之后禁止再跑 `s6_visual_qa.py`**——会重新产 qa_frames 残留（cleanup 已清过，2026-06-30 goldminer 事故）。交付前若需复查布局，读已保留的 `visual_qa_report.json`（在 RETAIN 白名单）即可，不重新抽帧。

## §6.10 特效工坊（组件匹配 + 新特效创建）

> **两阶段触发：**
> 1. §6.7 负责运行组件匹配 — 如果 `component_manifest.md` 不存在，执行下方匹配流程
> 2. 本节负责处理 `new` 条目 — 如果已生成的 manifest 含 `new` 标记，启动工坊创建新特效；否则跳过

### 匹配流程

1. **读取 visual_intent** — 从 `narration_segments.json` 中每个场景的 `visual_intent` 字段获取导演意图
2. **读取 registry.yaml** — 加载 `components/registry.yaml` 组件注册表
3. **粗筛** — 按 layer/tags/emotion_range/complexity 过滤候选组件（匹配方式：AI 语义理解，允许词形变体如 warm↔warmth、excitement↔energy）
4. **精排** — AI 语义理解：读取 visual_intent + 候选组件 description + 相邻场景已选组件，选择最佳匹配
5. **回退规则（按层）：**
   - **bg 层**：bg 组件本质是渐变+光晕，通过调色即可覆盖绝大多数场景。粗筛为空时，按 `color_hint` 色温方向选最近的 bg 组件（暖色→light_field，冷色→gradient_mesh），**不标记 `new`**
   - **fx 层**：粗筛为空时先考虑 fx:null（不使用特效），仅当场景明确需要动态装饰且无候选时才标记 `new`
   - **content 层**：粗筛为空时，回退到 §6.7 "场景→组件参考" 表的经验映射
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

## §6.11 视觉分镜（Visual Phasing）

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
   - **HARD，gate: scene_ids_match**
   - **门禁自动校验**：`gate.py` 的 `scene_ids_match` 检查器会交叉验证 HTML 与 segments 的映射
6. 根元素必须有 `data-start="0"`
7. **`data-start` 和 `data-duration` 使用秒（不是毫秒）**
8. **`window.__hf` 必须定义 + GSAP timeline 必须注册**（完整代码模板见 `shared/render-safety.md` §1.13）
   - **HARD，gate: hyperframes_api_valid**
   - **门禁自动校验**：`gate.py` 的 `hf_api_present` 检查器会扫描 index.html 中的 `window.__hf` 声明、`duration` 字段和 `seek` 函数
9. **GSAP 初始化模板（唯一允许的写法，R-S6-026 HARD，gate: gsap_pattern）**:

```html
<script src="https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.5/gsap.min.js"></script>
<script>
window.__timelines = {};
var tl = gsap.timeline({ paused: true });

// 内容入场: tl.from() 只用 scale/x/y，禁止 opacity
tl.from('#s1-title', {scale:0.85, duration:0.15, ease:'power3.out'}, 0);

// FX 动画: tl.to() 允许 repeat:-1 + yoyo:true，允许 opacity
tl.to('#s1-ring', {scale:1.15, duration:3, ease:'sine.inOut', repeat:-1, yoyo:true}, 0);

window.__hf = {
  duration: TOTAL_DURATION,
  seek: function(t) { tl.time(t, false); }
};
window.__timelines["main"] = tl;
</script>
```

禁止模式（R-S6-026 HARD）:
  - `DOMContentLoaded` / `addEventListener('DOMContentLoaded')` 包裹 GSAP 代码
  - `for (var key in window.__timelines)` 循环 seek
  - `tl.fromTo()` 任何使用场景（用 `tl.from()` + `tl.to()` 替代）
  - `tl.from()` / `tl.to()` 中对**内容元素**使用 `opacity` 属性（`tl.from({opacity:0})` 导致 HyperFrames seek 时内容不可见）
  - **fx 元素的 `tl.to({opacity:..., repeat:-1, yoyo:true})` 不受此限制**

9b. **延迟入场动画必须 `.set()` 初始化**（R-S6-027 HARD，gate: delayed_animation_init）:
   HyperFrames 通过 GSAP timeline seek 驱动每帧。当 `.from()` 的时间偏移 > 0 时，seek 到动画触发前的帧时，**元素保持 DOM 原位（可见）**——`.from()` 的"起始值"仅在动画区间生效，seek 到 t < 动画开始时间时不起作用。

   **必须**在 timeline 开始处用 `.set()` 将延迟入场元素初始化为离屏状态，再用 `.to()` 入场：

   ```javascript
   // ✅ 正确：.set() 初始化离屏 + .to() 入场
   s2.set('#card-2', { x: 1100 })    // seek t=0 时完全在画布外
     .to('#card-2', { x: 0, duration: 0.7, ease: 'power3.out' }, 5.5)

   // ❌ 错误：偏移不够 — x:200 时卡片一半仍然可见
   s2.set('#card-2', { x: 200 })

   // ❌ 错误：仅 .from() — seek 到场景起始帧时 card-2 在 DOM 原位可见
   s2.from('#card-2', { x: 200, duration: 0.7 }, 5.5)
   ```

   **判定规则**：`.from()` / `.to()` 的第三个参数（时间位置）> 2s 时，同 timeline 中必须存在对应选择器的 `.set()` 调用。t≤2s 的入场动画不需要 `.set()`（元素在场景开始后极短时间内就进入动画区间，seek 预显示不可察觉）。

   **偏移量硬标准**（HARD，gate: delayed_animation_init）：`.set()` 的偏移量必须足以将元素完全推出画布：
   - **水平偏移**（x/translateX）：竖屏 ≥ 1080px，横屏 ≥ 1920px
   - **垂直偏移**（y/translateY）：竖屏 ≥ 1920px，横屏 ≥ 1080px
   - **缩放隐藏**（scale: 0）：视为完全隐藏，不适用偏移量标准
   - **透明度隐藏**（opacity: 0）：视为完全隐藏，不适用偏移量标准

   不满足偏移量的 `.set()` 等同于无 `.set()`——元素一半可见。

### CSS 规则

> **CSS 渲染安全规则全部在 `shared/render-safety.md` §1 中定义。** 以下仅列 Stage 6 独有规则，不重复渲染安全内容。

10. **`.clip` 必须铺满全画幅**：`position:absolute; inset:0`（与 `.composition` 同尺寸 1080×1920）。`.clip` 只做时间定位（data-start/data-duration），**不做空间裁剪**。安全区内缩由 `.phase` 的 padding 负责（见 `shared/render-safety.md` §1.5）。如果 `.clip` 有 top/right/bottom/left 偏移，背景层会被限制在 clip 内，clip 外显示黑色 → 四面黑边。
11. **DOM 三层直系铁律**（R-S6-025 HARD，gate: no_scene_wrap）:
   `.clip` 的直接子元素必须且仅包含 `.layer-bg` + `.layer-fx` + `.layer-content`。
   禁止任何中间包裹层（`scene-wrap`、额外 `div` 容器等）。内容容器使用 `.phase`（`position:absolute; inset:0; padding:安全区; display:flex; flex-direction:column; justify-content:center; opacity:1`）。
12. **⛔ 禁止在 `.grad-text` 元素上使用 `background:` 简写**（R-S6-021 HARD）。CSS `background` 简写会重置 `background-clip` 回 `border-box`，导致 `.grad-text` 的 `background-clip:text` 失效，渐变变成纯色背景块、`color:transparent` 隐藏文字——只看到色块看不到字。**正确：`background-image:linear-gradient(...)`，错误：`background:linear-gradient(...)`**。竖屏横屏均适用。
13. **⛔ `background-clip:text` 渐变文字禁止搭配黑色 `text-shadow`**（R-S6-023 HARD）。`text-shadow: rgba(0,0,0,...)` 叠加在透明填充的渐变文字上会产生黑色光晕，压低文字亮度。渐变文字应使用同色系发光（如暖渐变用 `rgba(249,168,37,0.5)`，冷渐变用 `rgba(0,212,255,0.5)`）。纯色文字的黑色 `text-shadow` 不受此限制。

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

**禁止模式**：glow+grid 三件套（线性渐变 + 1-2 个模糊光圆 + grid-bg）作为唯一 bg 方案。这是 R-R-009 HARD 门禁。

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

> 渲染前品质检查清单见 `shared/quality-checklist.md`。

### 动画规则

14. 入场动画时长 **0.3-0.7 秒**（"快入+静止"模式）
15. stagger 间隔 **0.2-0.3 秒**
16. easing: `power3.out` 用于入场
17. 场景间由框架 transitions 处理，不手动 exit
18. **动画设计原则：** 每个场景的动画在 1 秒内完成入场，之后保持最终状态静止直到 `data-duration` 结束。
19. **hook 场景 A/V 同步铁律：** hook（s1）的首个文字动画必须从 t=0 启动，duration ≤ 0.15s，用 `scale` 代替 `y` 位移（缩放冲击感更强）。示例：`tl.from('#s1 h1', {scale:0.85, duration:0.15, ease:'power3.out'}, 0)`。副标题在 0.15s 启动，0.2s 内完成。确保旁白发声（t≈0.1s）时文字已可见，消除"先声后画"的脱节感。
20. **fx 动画密度**：每个场景的 `.layer-fx` 中，每个特效元素至少有 1 个 GSAP 动画调用。不限动画类型——脉冲、漂浮、旋转、闪烁、扫描、缩放、位移动画都可以。纯静态 fx 元素（div 在 timeline 中无 GSAP 目标）视为违规。

### 字体规则

21. **字体由 design.md 驱动**：Stage 2 在 design.md 的 `fonts` 字段声明三层字体（title/body/data + voice 气质链接 Q1）。`s6_prepare_creative.py` 自动提取并注入 CSS 变量到 `style.css` 的 `:root`（`--font-title` / `--font-body` / `--font-data` / `--title-weight`），`s6_assemble_html.py` 自动拼接 Google Fonts `<link>` 注入 HEAD。**场景 HTML 用 `font-family: var(--font-title)` 等引用，禁止硬编码字体名**（封面有独立字体规则，不复用 `fonts`）。字体气质↔情感映射见 `shared/director-toolkit` 第 2 层「字体气质」，技术参数见 `shared/font-palette`
22. **中文渲染验证**：CJK 字体首次加载 2-5 秒。渲染首帧前确认 `<link>` 已就位；加载失败时 fallback 链自动降级到 PingFang SC / Microsoft YaHei，不阻塞渲染

### 渲染规则

23. 渲染传目录路径（`.`），不传文件路径
24. 渲染前确保 `lint` 通过
25. **渲染后白屏/空白检查**：`frame_analysis.py`（Layer 2）自动执行暗帧和亮度检测，`stage6_gate.sh` 调用

## §6.12 画布方向

方向由 `design.md` 的 `orientation` 字段决定：

| orientation 值 | 画布尺寸 | 说明 |
|---------------|---------|------|
| `portrait` 或未设置 | 1080×1920 | 默认竖屏 |
| `landscape` | 1920×1080 | 横屏 |

读取方法：解析 `design.md` 中 `orientation:` 行的值。无此字段按 portrait 处理。

方向判定：根组合 `data-width` / `data-height` — `h > w` 为竖屏，`w > h` 为横屏。字号、padding、布局按方向自动切换（详见 `director-toolkit.md` 和 `render-safety.md §1.5`）。

### 横屏视觉增强（强制性）

横屏（1920×1080）比竖屏有 1.78 倍的水平空间，但也更容易显得空和单调。以下规则横屏视频**必须遵守**：

1. **每个场景必须有 fx 层动画**（R-R-008/013 HARD）。横屏空间大，纯静态 bg 会显得廉价。每个场景至少 2 个有 GSAP 动画的 fx 元素（粒子、光束、脉冲、扫描线、漂浮物等）。
2. **标题文字使用渐变或高对比配色**。纯白文字在横屏宽幅画面上显得平淡。推荐技法：
   - `linear-gradient(90deg, #color1, #color2)` + `background-clip:text` + `transparent fill-color`
   - 标题 ≥56px 时渐变效果最佳
   - 渐变色从场景主题色推导（暖色场景用金→橙，冷色场景用青→紫）
3. **bg 层不可只用纯色渐变**。横屏画幅更大，纯色渐变 bg 在 H.264 编码后呈现为平坦色块。必须叠加纹理元素（等高线、光束、扫描线、噪点等），与竖屏 bg 层质量标准一致。
4. **相邻场景 bg 必须有可区分的视觉差异**（R-R-010 HARD），横屏尤甚——同质化在宽幅画面上更明显。

### 动画设计原则（HyperFrames 时长模型）

采用"快入+静止"动画策略：入场 0.3-0.7s，之后静止到场景结束。

字号参考见 `director-toolkit.md` 字号层级表。

### 竖屏垂直居中规则（R-S6-028 HARD）

**内容容器必须垂直居中**——无论使用什么 class 名。内容容器（承载主要文字/卡片的 div）必须包含以下 CSS：

```css
display: flex;
flex-direction: column;
justify-content: center;
```

**常见错误**：只有 `display:flex; flex-direction:column;` 但缺少 `justify-content:center`——内容会从顶部开始排列，视觉偏上。

**禁止紧贴顶部**：不能用 `top: 80px` 等小值。场景内容容器禁止 `position: absolute` + 小 top 值。

### 布局推导（两级体系）

**垂直方向强制居中**（内容容器 `justify-content:center`），水平方向由布局推导决定：

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

**竖屏安全区 padding：** `180px 90px 220px 90px`（完整平台安全区域表见 `render-safety.md` §1.5）

**横屏（1920×1080）：**
- 顶部危险区：上 60px
- 底部危险区：下 60px
- 水平安全边距：左 120px / 右 120px
- 安全内容区：60px ~ 1020px（垂直），120px ~ 1800px（水平）
- padding：`60px 120px 60px 120px`

## §6.13 渲染管线（全自动）

> `s6_render.sh` 一次性完成: 渲染前检查 → 导演门禁 → BGM 音量注入 → renderbak 隔离 → HyperFrames lint + render → renderbak 恢复 → output_no_bgm 合成 → 音频验证 → 完成门禁。

```bash
bash .claude/commands/clipforge/scripts/s6_render.sh --project-dir .
```

**如果任何检查失败，修复问题后重新执行，不得跳过。**

### 文件逻辑

```
output.mp4        = 视频 + 旁白 + BGM（HyperFrames 渲染）
output_no_bgm.mp4 = output.mp4 的视频 + narration.mp3 的音频（ffmpeg 合成）
final.mp4         = cover.png + output.mp4（Stage 7 拼接）
final_no_bgm.mp4  = cover.png + output_no_bgm.mp4（Stage 7 拼接）
```

> 封面帧拼接由 Stage 7 的 `s7_delivery.sh` 统一处理，Stage 6 不负责。
> **禁止**从 output.mp4 提取音频轨（只有 1 条混合轨，BGM 无法分离）。

## §6.14 无 BGM 版本合成（output_no_bgm.mp4）

> 由 `s6_render.sh` Step 10 触发，调用 `scripts/build_no_bgm.sh` 执行合成。

**合成规则：**
- 输入：`output.mp4` 的**视频轨**（`-an`）+ `narration.mp3` 的**音频轨**（`-vn`）
- 输出：`output_no_bgm.mp4`（仅含旁白，无 BGM）
- **禁止**：从 `output.mp4` 提取音频轨（只有 1 条混合轨，BGM 不可分离，见 §6.13）
- 验证：产出 `output_no_bgm.mp4`，Stage 7 前置检查依赖此文件（见 stage7-delivery.md §7.1）

---

## 约束声明

**Iron Law:** 渲染前未移除 cover.html = 渲染必冲突。GSAP timeline 未注册 = 全片空白。output_no_bgm.mp4 未从 narration.mp3 合成（§6.14）= 双版本输出失败。

> 本阶段的结构化约束（HARD/SOFT 规则 + Guard Red Flags）由引擎注入提供。执行前运行 `python engine/inject.py --skill stage6-production` 获取完整约束 prompt。
