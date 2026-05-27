---
name: stage6-production
description: 沉浸式视频制作 — HTML 组合 + HyperFrames 渲染 + 双版本输出
version: "1.0.0"
type: EXECUTIVE
rigor: STRICT
dependencies: ["clipforge.stage4-audio"]
---

# Stage 6: 沉浸式视频制作（委托 HyperFrames）

> 当 `segment_durations.json` + 音频文件已存在且 `output.mp4` 不存在时触发。基于组件库装配 HTML 组合并渲染为视频。

## Intent
> 编写 HTML 组合并渲染竖屏视频，含旁白和 BGM。
> 成功标准：双版本输出（output.mp4 + output_no_bgm.mp4）、渲染安全通过、GSAP timeline 注册、音频验证通过。

## Boundary — 行为准则

### 必须遵守（HARD 规则 · 正向重述）

1. **渲染前移除非 index.html 文件** — 将 cover.html 等含 `data-composition-id` 的文件临时重命名为 `.renderbak` ← `R-STAGE6-001` / `R-RENDER-007`
   ↳ 校验：渲染前项目目录中仅 index.html 含 `data-composition-id`
2. **注册 GSAP timeline** — `window.__timelines["main"] = tl`，tl 为 GSAP timeline({paused:true}) ← `R-STAGE6-002` / `R-RENDER-009`
   ↳ 校验：`window.__timelines["main"]` 非空
3. **用 narration.mp3 合成 no_bgm 版本** — `output_no_bgm.mp4 = output.mp4 视频轨 + narration.mp3 音频轨`（ffmpeg -map 0:v -map 1:a） ← `R-STAGE6-003`
   ↳ 校验：volumedetect 差值 > 3dB
4. **BGM 音量渲染前写入 HTML** — 从 `segment_durations.json` 的 `meta.bgm_volume` 读取并写入 `data-volume` ← `R-STAGE6-004`
   ↳ 校验：HTML 中 BGM 的 `data-volume` 与 JSON 一致
5. **产出双版本** — output.mp4（含 BGM）+ output_no_bgm.mp4（仅旁白），缺一不可 ← `R-STAGE6-005`
   ↳ 校验：两个文件都存在且非空
6. **使用 stage6-components.md 作为装配参考** — 组件库是 HTML 装配的唯一参考来源 ← `R-STAGE6-006`
7. **Canvas/Three.js 使用 seek 驱动时间** — 不使用 requestAnimationFrame，Three.js 使用 `__hfThreeTime` ← `R-STAGE6-007` / `R-RENDER-015` / `R-STAGE6-008`
8. **封面帧 anullsrc 使用 48kHz** — 确保与正片 48kHz 一致 ← `R-STAGE6-010`
9. **data-start 和 data-duration 使用秒** — 不使用毫秒 ← `R-STAGE6-011`
10. **window.__timelines 是 {} 不是 []** ← `R-STAGE6-012`
11. **timeline 必须 { paused: true }** ← `R-STAGE6-013`
12. **data-composition-id 只在根元素** — scene div 不加此属性 ← `R-STAGE6-014`
13. **根元素必须有 data-start="0"** ← `R-STAGE6-015`
14. **遵守渲染安全全部规则** — `_render-safety.md` §1-§2 的所有规则（R-RENDER-001~015） ← 引用
15. **遵守视觉切换频率** — Phase 断点与旁白话题转换对齐，禁止时间均分 ← `R-GLOBAL-016` / `R-GLOBAL-017`

### 建议参考（SOFT 规则 + 偏好）
- 角色覆盖层限制 15-20%，仅在角落，不遮挡核心内容（SOFT）← `R-STAGE6-009`
- 使用 HyperFrames 委托模式渲染，降级时自行编写 HTML（HIGH）
- 每个场景独立创作视觉，不套固定模板（MEDIUM）
- 对照 `stage6-components-ref.md` 的 10 条反面清单自检（MEDIUM）
- 导演自审（Layer 3）在渲染前执行（MEDIUM）

## Guard — 认知守卫

| 当你产生这个念头 | 现实是 | 触发行为 |
|---|---|---|
| "anullsrc 用 44100 也行" | 封面 44.1kHz vs 正片 48kHz → TS 拼接后音频异常 | 修改为 48kHz |
| "CSS 动画更简单" | CSS opacity:0 入场动画在 HyperFrames 中永远不执行 | 改用 GSAP .from() |
| "&amp; 是标准 HTML" | 无头浏览器对实体字符解析不可靠 | 改用 Unicode |
| "不用 padding" | 缺少 padding 导致内容区域塌陷 | 添加安全区 padding |
| "GSAP 会自动注册" | 空 __timelines={} 导致全片空白 | 显式注册 timeline |
| "绝对路径也能找到" | 只认项目目录内相对路径 | 确保文件在同级目录 |
| "cover.html 不影响" | 含 data-composition-id 的 HTML 都会导致冲突 | 渲染前移除 |
| "用 -map 0:a:0 提取旁白" | HyperFrames 输出只有 1 条混合音频轨 | 用 narration.mp3 合成 |
| "双次渲染更安全" | 单次渲染 + ffmpeg 合成更高效 | 遵循 §6.7 流程 |
| "Canvas 用 rAF 更流畅" | HyperFrames seek 驱动，rAF 不同步 | 使用 seek 驱动 |
| "Three.js 用 performance.now()" | seek 回放时不回溯 | 使用 __hfThreeTime |
| "角色大点更可爱" | CharOverlay 限制 15-20%，仅在角落 | 缩小角色尺寸 |
| "组件太多不需要都读" | stage6-components.md 是装配的唯一参考 | 完整读取组件索引，按需读取组件文件和 stage6-components-ref.md |
| "白屏可能是正常的" | 检查 window.__hf 和 data-duration | 排查并修复 |

### Spirit vs Letter

| 规则 | 模式 | 真实意图 |
|---|---|---|
| R-STAGE6-003 | SPIRIT | 确保 no_bgm 版本是纯旁白音频，BGM 可被用户自定义替换 |
| R-STAGE6-002 | SPIRIT | 确保 HyperFrames 有可执行的 timeline，不渲染空帧 |
| R-RENDER-006 | SPIRIT | 防止多层累计 padding 导致内容区域严重压缩 |

## Gate — 通过标准

### 流程门禁（自动化检查，不通过 = 驳回，max_retries: 2）
- [ ] `render_safety` — director_gate.py + stage6_gate.sh 全部通过
- [ ] `dual_output` — output.mp4 和 output_no_bgm.mp4 都存在且非空
- [ ] `gsap_timeline` — window.__timelines["main"] 已注册且非空
- [ ] `audio_verification` — post-render volumedetect: BGM 未泄露到 no_bgm 版本（差值 > 3dB）

### 质量门禁（创意评价，不通过 = 记录但放行，evaluator: HUMAN）
- `visual_quality`: 评分 ≥ 0.7（人类评价：视觉冲击力、信息层次、配色创意、与内容的契合度）

### STRICT 模式特有机制

本阶段标记为 `rigor: STRICT`，除标准门禁外还有以下增强机制：

- **首次人工复核**：新上线或重大修改后的前 5 次执行，即使流程/合规门禁全部通过，也需人工确认产出质量后才标记为 PASSED
- **归因审计**：每次归因产出 Delta Rule 时，记录完整审计日志（证据链 + 置信度推导）
- **模式入库确认**：正向闭环产出的经验模式在写入 Pattern Store 前需人工确认

## Trace — 采集点
- **执行开始**：记录 design.md 的 immersion_mode、场景数、总时长
- **HTML 编写**：记录使用的组件列表、Phase 数量、特效类型
- **渲染过程**：记录渲染次数、失败原因、路径切换
- **门禁结果**：记录 director_gate / stage6_gate / frame_analysis 结果
- **执行结束**：记录 gate_report，写入 `{project_dir}/trace/stage6-{timestamp}.yaml`

## 操作指令

### 6.1 项目初始化

```bash
# 创建日期目录（如不存在）+ 项目目录（纯英文路径）
mkdir -p "workspace/<YYYY>/<MM>/<DD>/<project-name>"
npx hyperframes init "workspace/<YYYY>/<MM>/<DD>/<project-name>" --example blank --non-interactive
```

项目目录结构为 `workspace/<YYYY>/<MM>/<DD>/<项目名>/`，日期格式为纯数字（如 `workspace/2026/05/18/github-trending/`）。详见 `clipforge.md` 的「项目目录结构」段。

### 6.2 读取 design.md + storyboard

Stage 2 已将视觉风格方向和故事板写入 `design.md`。**本阶段只读取，不重写。**

**读取字段和用途：**

| 字段 | 用途 |
|------|------|
| `style`, `mood` | 整体风格方向 |
| `color_direction` | 配色方案选择 |
| `storyboard.immersion_mode` | 沉浸模式 → 匹配 `stage6-components-ref.md` 的配色速查表 |
| `storyboard.emotion_curve` | 6 拍情感强度 → 影响每个场景的视觉力度 |
| `storyboard.narrative_template` | 叙事模板 → 影响场景布局选择 |
| `storyboard.humor_style` | 幽默策略 → 是否添加 SpeechBubble 组件 |
| `storyboard.character_presence` | 角色出场 → 是否添加 CharOverlay 组件 |

**沉浸模式 → CSS 变量映射：** 从 `stage6-components-ref.md` 的「沉浸模式配色速查」表获取具体色值，写入 `:root` CSS 变量。

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
1. `immersion_mode` → `stage6-components-ref.md` 配色速查 → `:root` CSS 变量（兜底）
2. `color_direction` → 覆盖 `:root` 中冲突的色值（优先）
3. 每个场景的**具体内容** → 读内容想画面（格言引导 + 反面清单兜底） → 背景层 + 特效层 + 内容层的视觉方案
4. `character_presence` + 每段 `character_expression` → CharOverlay 组件选择

### 6.3 音频嵌入

> **前置依赖：Stage 4 的 `segment_durations.json` 和音频文件必须已产出。**

HyperFrames 原生支持 `<audio>` 元素：自动发现、多轨混音、AAC 编码、MP4 封装。HTML 中嵌入音频后，`output.mp4` 直接包含完整音轨，无需 FFmpeg 手动合并。

#### 嵌入方式

在 composition 根元素内添加 `<audio>` 元素：

```html
<div class="composition" data-composition-id="main" data-start="0">
  <!-- 旁白音轨（track 1）：单条 narration.mp3，从 t=0 播放到结束 -->
  <audio data-track-index="1" data-volume="1"
         src="narration.mp3" preload="auto"></audio>

  <!-- BGM 音轨（track 2）：bgm.wav 循环播放，音量由 Stage 4 分析结果决定 -->
  <audio data-track-index="2" data-volume="0.06"
         src="bgm.wav" preload="auto" loop></audio>

  <!-- 场景 div ... -->
  <div class="clip s-hook" data-start="0" data-duration="4.2">...</div>
  <div class="clip s-solution" data-start="4.2" data-duration="7.8">...</div>
</div>
```

#### 参数说明

| 属性 | 值 | 说明 |
|------|-----|------|
| `data-track-index` | `1`（旁白）/ `2`（BGM） | HyperFrames 按轨分组混音 |
| `data-volume` | 旁白 `1`，BGM 从 `segment_durations.json` 的 `meta.bgm_volume` 读取 | HyperFrames 混音时的音量系数 |
| `loop` | 仅 BGM 添加 | BGM 循环播放直到视频结束 |
| `preload="auto"` | 必须 | 确保 HyperFrames 预加载音频 |

#### 电影解读模式

电影模式使用 `narration_new.mp3`（含静音填充），并在电影片段场景使用 `<video>` 元素（见 `_movie-clips` 的嵌入规则）。

#### 对齐机制

**场景连续无间隔 + 旁白连续无间隔 → 单条 `narration.mp3` 天然与场景序列对齐。** 每个 scene div 的 `data-duration` 取自 `segment_durations.json` 的对应段落实测时长，画面时长 = 语音时长，零偏移计算。

HyperFrames 的 `resolveMediaDuration()` 还会用 ffprobe 自动检测 `<audio>` 时长，`mediaDurationFloor` 确保视频时间线不短于音频。

### 6.4 编写 HTML 组合（组件装配模式）

**调用 `/hyperframes` 技能**，传入：视觉风格方向、故事板、design.md 路径、`stage6-components.md` 组件库、`segment_durations.json` 时长、`narration_segments.json` 情感标记、音频嵌入参数。

如果 Stage 5 已制备素材，将 `assets/manifest.md` 中列出的文件路径作为 prompt 上下文传入 HyperFrames，让其在 HTML 中嵌入：

- **背景图**：用 `background-image: url(assets/xxx.jpg)` 设为场景背景，加 `background-size: cover` + 半透明遮罩层保证文字可读
- **图表 SVG**：用 `<img src="assets/chart.svg">` 嵌入，或 inline SVG 以便 GSAP 控制动画
- **图标 SVG**：用 `<img src="assets/icons/xxx.svg">` 或 CSS mask 方式嵌入
- **AI 生成图**：同背景图用法，适合定制化场景

> **素材交接方式：** 读取 `assets/manifest.md`，将每个素材的文件名和用途描述写入 HyperFrames 的 prompt。HyperFrames 不解析 manifest.md，由编排者负责桥接。

#### 组件装配流程

1. **读取 `narration_segments.json`** — 每段的 `scene`、`text`（旁白内容）、`visual_phases`、`character_expression`、`humor_type`
2. **读取 `design.md` 的 `storyboard`** — 沉浸模式、叙事模板、情感曲线
3. **读取 `stage6-components-ref.md`** — 视觉推导系统 + CSS 特效参考库 + 组件模板
4. **设计视觉（每个场景独立创作）** — 读场景内容，像导演一样构思画面：
   - 这段内容在说什么？观众该感受到什么？什么视觉能强化这个感受？
   - 参考 `stage6-components-ref.md` 的设计格言（5 条正面引导）
   - 对照反面清单（10 条红线），确保不踩雷
   - 用 CSS 特效参考库的工具实现你的构思
   - **不查表、不套公式、每个场景独立思考**
5. **装配 HTML** — 按 HyperFrames composition 结构组装

#### 场景 → 组件参考

> **这是参考映射，不是固定分配。** 根据场景内容选择最合适的组件组合，允许跨场景复用和变体。

| 场景类型 | 常用组件 | 视觉方向参考 |
|---------|---------|------------|
| hook | HeroCard | 震撼开场：高力度视觉、聚焦元素 |
| 数据/规模 | DataViz, CompareSplit | 数据呈现：结构化、清晰、有科技感 |
| 对比/竞争 | CompareSplit | 双视角：冷暖分割、对冲视觉 |
| 时间线/路径 | TimeLineFlow | 叙事推进：轨道感、节点连线 |
| 突出/揭示 | TextReveal | 悬念展示：渐进揭示、聚光灯效果 |
| 标准模式项目介绍 | ProjectFullCard | 单项目全屏 8 层信息 |
| CTA | TextReveal | 收束聚焦：温暖引导、行动号召 |

> **标准模式项目介绍场景：** 使用 ProjectFullCard 组件（§13），一个项目占满一屏，包含 8 层信息。数据来自 `narration_segments.json` 的 `selling_points`、`commentary` 字段和 content 数据。

#### 角色和幽默组件插入

- `character_expression` 非 null 的场景 → 添加 `CharOverlay` 组件（对应表情 SVG）
- `humor_type` 非 null 的场景 → 添加 `SpeechBubble` 组件（文案从 narration 提取幽默句）
- 角色定位：画面左下角，占 15-20%
- 气泡定位：画面右下角或角色上方

#### 特效填充验证

> `director_gate.py` §6 检查 layer-fx 内容非空，`stage6_gate.sh` 检查空 layer-fx 数量。HTML 写完后直接运行门禁脚本即可。

#### 视觉检查（对照反面清单）

> HTML 写完后，快速扫一遍 `stage6-components-ref.md` 的 10 条反面清单，确保没有踩雷。无需额外检查流程——反面清单已经编码了所有已知的视觉质量问题。

#### 导演自审（Layer 3 — HTML 写完后、渲染前必须执行）

> **目的**：像导演审看每日样片，逐场景检查 HTML 是否实现了导演决策。这是最后一道"导演看监视器"关卡。

读取 `_director-toolkit/questions.md` 的"导演 5 个必答题"，逐 `.clip` 场景自审：

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

### 6.4a 视觉分镜（Visual Phasing）

> **当场景时长 >15 秒时必须使用。** 将一个 `.clip` 拆分为多个视觉阶段（phase），每 phase 8-15 秒，通过 GSAP timeline 控制渐进揭示。遵守 `_shared-rules/visual.md` §6 的切换频率规则。

#### 核心原理

```
改造前: 1 段旁白 ──→ 1 个 clip ──→ 1 个静态画面（30-57 秒不动）
改造后: 1 段旁白 ──→ 1 个 clip ──→ N 个 phase（每 phase 8-15 秒）
```

- 音频管线不变：旁白仍然是连续的 narration.mp3
- `.clip` 数量不变：仍然一个 narration segment 对应一个 clip
- phase 是 `.layer-content` 内的多个子 div，通过 GSAP opacity 控制显示/隐藏

#### Phase HTML 结构

```html
<div class="clip s-biz-elderly" data-start="394" data-duration="50.14">
  <!-- scene-wrap 不设 padding — padding 由 .phase 统一管理（单层 padding 原则，见 _render-safety §1.4a） -->
  <div class="scene-wrap">
    <!-- 三层架构不变 -->
    <div class="layer-bg"><!-- 背景渐变 + 光晕 --></div>
    <div class="layer-fx"><!-- 特效 --></div>
    <!-- layer-content 内包含多个 phase（height:100% 必须有，否则 Phase 塌陷到顶部） -->
    <div class="layer-content" style="height:100%">
      <!-- Phase 1: CSS 默认 opacity:1，GSAP 入场动画。注意 padding 在 .phase 上 -->
      <div class="phase phase-1">
        <div class="phase-title">养老AI手环</div>
        <div class="feature-list">...</div>
      </div>
      <!-- Phase 2-4: CSS 默认 opacity:1，但 GSAP .set() 在 clip 起始时设为 opacity:0 -->
      <div class="phase phase-2"><!-- 定价数据 --></div>
      <div class="phase phase-3"><!-- 用户规模 --></div>
      <div class="phase phase-4"><!-- MVP路线图 --></div>
    </div>
  </div>
</div>
```

**关键规则：**
- 每个 `.phase` 用 `position: absolute; inset: 0` 全屏覆盖，自带 `padding: 180px 80px 220px 80px; display:flex; flex-direction:column; justify-content:center`，内容自动垂直居中（不需要手动加 inline flex）
- **scene-wrap 不设 padding** — padding 统一由 `.phase` 提供（单层 padding 原则）
- **禁止** scene-wrap 和 .phase 同时设置 padding（双重 padding 事故：内容偏左上，可用宽度仅 74%）
- Phase 1 是 CSS 默认可见（opacity:1），遵守 `_render-safety.md` §1.1
- Phase 2+ **不在 CSS 中设 opacity:0**，由 GSAP `.set()` 在运行时初始化（遵守 §1.1a 豁免）
- 所有 phase 共享同一个 `.layer-bg` 和 `.layer-fx`（背景和特效不随 phase 切换）

#### GSAP Phase 切换机制

```javascript
const SCENE_START = 394;   // clip 的 data-start
const PHASE_GAP = 12.5;    // 50.14s / 4 phases ≈ 12.5s per phase

// Phase 1 入场动画（原有机制不变）
tl.from('.s-biz-elderly .phase-1 .phase-title', {opacity:0, y:20, duration:0.4}, SCENE_START)
  .from('.s-biz-elderly .phase-1 .feature-card', {opacity:0, y:15, duration:0.3, stagger:0.15}, SCENE_START + 0.5);

// 初始化 Phase 2-4 为不可见（GSAP .set，不是 CSS opacity:0）
tl.set('.s-biz-elderly .phase-2', {opacity: 0}, SCENE_START)
  .set('.s-biz-elderly .phase-3', {opacity: 0}, SCENE_START)
  .set('.s-biz-elderly .phase-4', {opacity: 0}, SCENE_START);

// Phase 1 → 2: 淡出旧 + 淡入新（使用内容对齐断点，禁止 PHASE_GAP 均分）
tl.to('.s-biz-elderly .phase-1', {opacity: 0, duration: 0.3}, SCENE_START + BP1)
  .to('.s-biz-elderly .phase-2', {opacity: 1, duration: 0.4}, SCENE_START + BP1 + 0.3);

// Phase 2 → 3
tl.to('.s-biz-elderly .phase-2', {opacity: 0, duration: 0.3}, SCENE_START + BP2)
  .to('.s-biz-elderly .phase-3', {opacity: 1, duration: 0.4}, SCENE_START + BP2 + 0.3);

// Phase 3 → 4
tl.to('.s-biz-elderly .phase-3', {opacity: 0, duration: 0.3}, SCENE_START + BP3)
  .to('.s-biz-elderly .phase-4', {opacity: 1, duration: 0.4}, SCENE_START + BP3 + 0.3);
```

**Phase 切换规则：**
- 上一个 phase 淡化到 `opacity: 0`（完全消失，避免与后续 phase 重叠产生重影）
- 新 phase 从 `opacity: 0` 渐显到 `opacity: 1`
- 过渡时长 0.3-0.4 秒
- **Phase 断点必须与旁白话题转换对齐，禁止均分**（见下方 §6.4b）
- Phase 间 GSAP 动画offset：`SCENE_START + BP[i][n-1] + offset`（BP 为内容对齐断点数组）

### 6.4b Phase 断点计算方法（内容对齐，禁止均分）

> **事故复盘**：均分 gap 导致旁白与画面严重不同步——观众听到话题 A，画面已显示话题 B，偏差达 5-12 秒。

**禁止**：`const gap = sc.d / sc.p`（时间均分）

**必须**：逐场景分析旁白文本，按话题转换点计算断点。

**计算步骤**：

1. 读取该场景的 `narration_segments.json` 中的 `text` 和 `visual_phases`
2. 在 `text` 中找到与每个 `visual_phases[n].focus` 对应的文本段落边界
3. 计算字数比例：`ratio_n = boundary_char_position / total_chars`
4. 转换为时间戳：`bp_n = ratio_n * actual_duration`
5. 结果存入 BP 数组

**代码模板**：

```js
// GSAP timeline 中定义断点数组
const BP = [
  [3.21, 16.72],    // 0: scene_name — P1:topic(XX%) P2:topic(XX%) P3:topic(XX%)
  [15.25, 21.57],   // 1: scene_name — P1:topic(XX%) P2:topic(XX%) P3:topic(XX%)
  // ... 每个场景一行
];

S.forEach((sc, i) => {
  const bp1 = BP[i][0];  // Phase 1→2 断点
  const bp2 = BP[i][1];  // Phase 2→3 断点
  // 所有 Phase 切换使用 bp1/bp2 替代 gap/gap*2
});
```

**验证标准**：观看视频时，Phase N 的视觉内容与对应时间段内的旁白文本语义匹配，偏差 ≤ 2 秒。

#### Phase 内容来源

读取 `narration_segments.json` 的 `visual_phases` 数组：

```json
"visual_phases": [
  { "focus": "产品定位与五大核心功能", "visual_type": "list",
    "key_data": ["跌倒检测>95%", "用药提醒", "一键呼叫", "AI语音", "健康监测"] },
  { "focus": "定价与收入模型", "visual_type": "data",
    "key_data": ["硬件599-999元", "月订阅29-49元", "毛利率30-40%"] }
]
```

- `focus` → phase 画面标题（`phase-header`）
- `visual_type` → 选择 `stage6-components-ref.md` 的 Phase 视觉模板
- `key_data` → 画面上的数据/关键词内容

#### Phase 视觉类型 → 模板映射

| visual_type | 画面布局 | 参考组件 |
|------------|---------|---------|
| `hero` | 大标题 + 关键数字 + 副标题 | HeroCard 风格 |
| `list` | 标题 + 带序号的卡片列表 | — |
| `data` | 标题 + 数据行（label + value） | DataViz 风格 |
| `compare` | 标题 + 双栏对比 | CompareSplit 风格 |
| `timeline` | 标题 + 步骤节点 | TimeLineFlow 风格 |
| `highlight` | 大号结论文字 + 强调色 | TextReveal 风格 |

每种类型的具体 HTML/CSS 骨架见 `stage6-components-ref.md` 的「Phase 视觉模板」章节。

#### Phase 完整性验证

> `stage6_gate.sh` 的视觉分镜完整性检查会验证长场景的 phase 数量。HTML 写完后运行门禁即可。

#### 呼吸帧插入

在场景切换点插入 0.3-0.5s 的视觉呼吸：

```javascript
tl.to('.current-scene .scene-content', { scale: 1.02, duration: 0.15, ease: 'power1.inOut' })
  .to('.current-scene .scene-content', { scale: 1.0, duration: 0.15, ease: 'power1.inOut' });
```

#### Canvas 粒子和 Three.js 3D

根据沉浸模式决定是否使用 3D 场景：

| 沉浸模式 | Canvas 效果 | Three.js 3D |
|---------|------------|-------------|
| hyper-pace | CodeRain + ParticleBurst | 否 |
| hidden-gem | PulseOrb | 否 |
| mega-update | ParticleBurst | ThreeScene(旋转立方体群) |
| versus | PulseOrb | 否 |
| story-time | — | 否 |
| fun-tool | ParticleBurst | 否 |

Three.js 使用 `window.__hfThreeTime` 驱动，注册到 GSAP timeline 的 seek 回调。详见 `stage6-components-ref.md` 的 ThreeScene 组件。

#### 降级触发条件

以下任一情况发生时，从 HyperFrames 委托模式降级为自行编写 HTML：

| 触发条件 | 判断方式 |
|---------|---------|
| HyperFrames 技能不可用 | Skill 工具调用 `/hyperframes` 失败或找不到技能 |
| 技能调用超时/报错 | Skill 调用返回错误，或渲染命令 `npx hyperframes` 执行失败 |
| lint 检查不通过 | 产出的 HTML 运行 `npx hyperframes lint` 报错且无法快修复 |

降级时向用户说明原因，然后继续执行。降级自行编写时，**严格遵守以下规则**：

#### 内容规则

> **以下全部规则同样适用于 HyperFrames 委托模式产出的 HTML。**

0. **内容安全规范**遵守 `clipforge/_shared-rules` 全部条款（措辞/CTA/内容安全见 `writing.md`，画面文字/视觉切换见 `visual.md`，渲染安全见 `render-ref.md`）。
0. **渲染安全规范**遵守 `clipforge/_render-safety` 全部条款（Stage 6 必读）。

#### 结构规则

1. `window.__timelines` 是 `{}` 不是 `[]`
2. timeline 必须 `{ paused: true }`
3. 注册 key 匹配根元素的 `data-composition-id`
4. **`data-composition-id` 只在根元素上**，scene div 不要加
5. 根元素必须有 `data-start="0"`
6. **`data-start` 和 `data-duration` 使用秒（不是毫秒）**
7. **`window.__hf` 必须定义 + GSAP timeline 必须注册**
   - 缺少 `__hf` 会导致白屏
   - `window.__timelines = {};`（空对象）会导致空白渲染
   - 必须在 `</body>` 前添加：
     ```html
     <script src="https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.5/gsap.min.js"></script>
     <script>
     window.__timelines = {};
     window.__hf = { duration: TOTAL_DURATION, seek: function(t) {} };
     const tl = gsap.timeline({paused: true});
     // 每个场景的入场动画，offset 与 data-start 对齐
     tl.from('.s-hook .title', {opacity:0, y:20, duration:0.3, ease:'power3.out'}, 0.1)
       .from('.s-what .card', {opacity:0, y:30, duration:0.3, ease:'power3.out', stagger:0.15}, HOOK_DURATION)
     ;
     window.__timelines["main"] = tl;
     </script>
     ```

#### CSS 规则

> **CSS 渲染安全规则全部在 `_render-safety.md` §1 中定义。** 以下仅列 Stage 6 独有规则，不重复渲染安全内容。

8. **`.clip` 只设 `position: absolute` + 尺寸**，不要加其他样式（上140 / 右90 / 下260 / 左70）

#### 视觉结构约束（流程层 — 必须遵守）

- 每个场景必须有背景层（渐变/纯色/纹理），不可纯白或纯黑
- 文字在深色背景上必须有 text-shadow 或足够对比度
- 安全区 padding 由 .phase 统一管理（见 _render-safety §1.4a）

#### 视觉创意空间（内容层 — Agent 自主决策）

以下为指导性建议，Agent 根据场景内容和 design.md 的风格方向自主决定：

- **背景构成**：渐变 + 光晕 + 网格底纹是常见方案，也可根据内容选择其他背景
- **元素密度**：内容场景通常 5+ 元素，hook/CTA 通常 3+ 元素，具体由信息密度决定
- **配色方案**：复用 design.md 的 color_direction，具体冷暖比例由场景情绪决定
- **字号层级**：参考 `_director-toolkit/vocabulary.md` 的字号层级表，具体数值由内容长度调整
- **场景配色**：不强制暖色/冷色分配，由导演自审（Q1-Q5）驱动

##### 整体品质检查

渲染前对照清单：背景层、光晕、配色区分、CTA 完整、安全区、居中（flexbox）、`__hf` + GSAP、音频、无 anim-in、无 HTML 实体、scene-wrap padding、无多余 composition。

#### 动画规则

8. 入场动画时长 **0.3-0.7 秒**（"快入+静止"模式）
9. stagger 间隔 **0.2-0.3 秒**
10. easing: `power3.out` 用于入场
11. 场景间由框架 transitions 处理，不手动 exit
12. **动画设计原则：** 每个场景的动画在 1 秒内完成入场，之后保持最终状态静止直到 `data-duration` 结束。

#### 字体规则

12. 优先使用 HyperFrames 内置字体映射
13. **中文渲染**：先渲染一帧验证，异常时用 `font-family: 'Inter', 'PingFang SC', 'Microsoft YaHei', sans-serif`

#### 渲染规则

14. 渲染传目录路径（`.`），不传文件路径
15. 渲染前确保 `lint` 通过
16. **渲染后白屏/空白检查**：`frame_analysis.py`（Layer 2）自动执行暗帧和亮度检测，`stage6_gate.sh` 调用

### 6.5 默认竖屏

默认输出 **竖屏（1080×1920）**。如用户要求横屏再额外生成。

#### 动画设计原则（HyperFrames 时长模型）

采用"快入+静止"动画策略：入场 0.3-0.7s，之后静止到场景结束。

竖屏字号参考：hero 约 80-100px、title 约 56-72px、body 约 36-44px、tag 约 26-34px。

#### 竖屏垂直居中规则

> **居中已内置到 `.phase` CSS 中**：`.phase` 统一使用 `display:flex;flex-direction:column;justify-content:center`，所有 phase 内容自动垂直居中。不需要在 `.scene-wrap` 或 inline style 上手动添加 flex 居中。

**禁止在 `.scene-wrap` 上加 flex 居中**：Phase 模式下 `.phase` 是 `position:absolute`，不参与 `.scene-wrap` 的 flex 布局，在 scene-wrap 上加 flex 无效。

**禁止紧贴顶部**：不能用 `top: 80px` 等小值。场景内容容器禁止 `position: absolute` + 小 top 值。

#### 布局推导（两级体系）

**垂直方向强制居中**（`.phase` flex 内置），水平方向由布局推导决定：

##### Level 1：visual_type → 布局框架

每个 phase 的布局从 `narration_segments.json` 的 `visual_phases[].visual_type` 推导，不套固定模板。完整规格表见 `stage6-components-ref.md` 的「布局推导体系」章节。

**水平对齐推导规则：**

| visual_type | 水平对齐 | 说明 |
|------------|---------|------|
| hero | 全部居中 | 标题 + 数字 + 副标题，间距 generous |
| list | 标题居中，条目区 width:85% 内部左对齐 | 序号 + 文字条目 |
| data | 标题居中，数据行 width:85% | label-value 行 |
| compare | flex-direction:row，双栏各 flex:1 | 左冷右暖对比色 |
| timeline | 标题居中，步骤区 width:85% 内部左对齐 | 时间标签 + 文字 |
| highlight | 全部居中 | 大号文字 + 可选徽章 |

##### Level 2：内容字数 → 元素尺寸

primary/标题元素根据文本长度缩放：≤4 字 = 1.0×，5-8 字 = 0.85×，9-14 字 = 0.7×，15-24 字 = 0.55×，≥25 字 = 0.45×。具体基准字号见 `stage6-components-ref.md`。

##### 密度控制

- `visual_phases[].layout_hint.density` 可微调间距（compact ×0.7 / standard ×1.0 / generous ×1.3）
- 不指定时从 visual_type 自动推导：hero/highlight → generous，list/timeline → standard，data/compare → compact

##### 渲染顺序原则

- 水平：从左到右（排名 → 名称 → 数据）
- 垂直：从上到下（标签 → 标题 → 描述 → 卖点）
- 不强制所有元素居中，让内容和 visual_type 决定最美观的布局

#### 平台安全区域

- 顶部危险区：上 200px
- 底部危险区：下 300px
- 水平安全边距：左 80px / 右 80px（兼容抖音/小红书/微信视频号三平台）
- 安全内容区：180px ~ 1700px（垂直），80px ~ 1000px（水平）

### 6.6 渲染

#### 渲染前检查（必须执行）

```bash
cd workspace/<YYYY>/<MM>/<DD>/<project-dir>

# 1. 确认音频文件存在
ls -la narration.mp3 bgm.mp3

# 2. 导演门禁 — HTML 设计意图验证（Layer 1）
python3 .claude/commands/clipforge/scripts/director_gate.py .
# 未通过则修复 HTML 后重新执行，不得跳过

# 3. 移除所有非 index.html 的 composition 文件
for f in cover.html index_with_bgm.html cover.html.bak; do
  [ -f "$f" ] && mv "$f" "$f.renderbak"
done
```

#### 渲染命令

```bash
npx hyperframes lint
npx hyperframes render . --output output.mp4 --video-bitrate 5M
```

#### 渲染后恢复

```bash
for f in cover.html index_with_bgm.html; do
  [ -f "$f.renderbak" ] && mv "$f.renderbak" "$f"
done
rm -f cover.html.bak.renderbak index_with_bgm.html.renderbak
```

#### 渲染后音频验证

```bash
ffprobe -v quiet -show_streams -select_streams a output.mp4 | grep codec_name
ffmpeg -i output.mp4 -af "volumedetect" -f null /dev/null 2>&1 | grep volume
```

### 6.7 单次渲染 + ffmpeg 合成

> **HyperFrames 只渲染一次 output.mp4（旁白 + BGM 混合）。** output_no_bgm.mp4 由 ffmpeg 从 output.mp4 视频轨 + narration.mp3（纯旁白源文件）合成，无需二次渲染。

#### 渲染前准备

```bash
cd workspace/<YYYY>/<MM>/<DD>/<project-dir>

# 从 segment_durations.json 读取 BGM 音量，写入 HTML
BGM_VOL=$(python -c "import json; print(json.load(open('segment_durations.json'))['meta'].get('bgm_volume', 0.15))")
sed -i "s/id=\"bgm\" data-volume=\"[^\"]*\"/id=\"bgm\" data-volume=\"${BGM_VOL}\"/" index.html
echo "HTML BGM data-volume set to ${BGM_VOL}"
```

#### 渲染（仅一次）

```bash
# ── 渲染: 完整 HTML → output.mp4（旁白 + BGM）──
npx hyperframes render . --output output.mp4 --video-bitrate 5M
```

#### 合成 output_no_bgm.mp4（ffmpeg，不渲染）

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

#### 文件逻辑

```
output.mp4      = 视频 + 旁白 + BGM（HyperFrames 渲染）
output_no_bgm.mp4 = output.mp4 的视频 + narration.mp3 的音频（ffmpeg 合成）
final.mp4      = cover.png + output.mp4
final_no_bgm.mp4 = cover.png + output_no_bgm.mp4
```

### 6.8 封面帧拼接

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

#### BGM 音量

> BGM 音量由 Stage 4 的 `bgm_gap_check.py` 自动查表校准，值存储在 `segment_durations.json` 的 `meta.bgm_volume`。渲染前从该文件读取并写入 HTML `data-volume`。

#### 致命约束

| 约束 | 违反后果 |
|------|---------|
| **output_no_bgm.mp4 必须用 narration.mp3 合成** | 用 `-map 0:a:0` 从 output.mp4 提取只得到混合轨，BGM 无法消除 |
| **ffmpeg 只做封面帧拼接，不碰 output.mp4/output_no_bgm.mp4 的音频** | concat filter 只拼接视频流，音频从源文件直接 copy |
| **BGM 音量在渲染前写入 HTML** | 渲染后无法修改 HyperFrames 已混入的 BGM 音量 |

> **封面帧仅增加 1/30 秒（~33ms），对音画同步无感知影响。** `cover.png` 仍作为独立封面图上传平台。

### 6.10 Stage 6 完成门禁

```bash
# ── Stage 6 完成门禁 ──
bash .claude/commands/clipforge/scripts/stage6_gate.sh

# ── 渲染帧视觉分析（Layer 2）──
python3 .claude/commands/clipforge/scripts/frame_analysis.py .
```

**如果任何检查失败，修复问题后重新执行，不得跳过。**

## Red Flags（停止信号）

| 信号 | 规则 ID | 说明 |
|------|---------|------|
| 封面帧 anullsrc 非 48kHz | R-STAGE6-010 | 封面 44.1kHz vs 正片 48kHz → TS 拼接后音频异常 |
| 使用 CSS `.anim-in` | R-RENDER-001 | CSS opacity:0 导致 HyperFrames 渲染空白 |
| 使用 HTML 实体 | R-RENDER-003 | 实体在无头浏览器中不解析 |
| scene-wrap 无 padding | R-RENDER-004 | 内容区域在渲染中塌陷不显示 |
| GSAP timeline 未注册 | R-RENDER-009 | 空 __timelines={} 导致全片空白 |
| 音频文件不在项目目录内 | R-RENDER-008 | 绝对路径 404 静音 |
| 渲染前未移除 cover.html 等 | R-RENDER-007 | 多个 root composition 导致渲染冲突 |
| BGM 泄露到 no_bgm 文件 | R-STAGE6-003 | volumedetect 差值 < 3dB → 未用 narration.mp3 合成 |
| 缺少 output_no_bgm.mp4 | R-STAGE6-005 | 双版本输出不可省略 |
| 白屏/黑屏渲染结果 | R-STAGE6-012 | 检查 window.__hf 定义和 data-duration 值 |
| Canvas 使用 requestAnimationFrame | R-RENDER-015 | HyperFrames seek 驱动，独立 rAF 循环导致不一致 |
| Three.js 使用 Date.now() | R-STAGE6-008 | seek 回放时 3D 动画不回溯 |
| 角色遮挡核心内容 | R-STAGE6-009 | CharOverlay 限制 15-20%，仅在角落 |
| 缺少 stage6-components.md 引用 | R-STAGE6-006 | 组件库是装配 HTML 的唯一参考 |

## Common Rationalizations（常见借口反驳）

| 借口 | 事实 |
|------|------|
| "anullsrc 用 44100 也行" | 事故：封面帧 44.1kHz + 正片 48kHz → TS concat 后播放器异常 |
| "CSS 动画更简单" | 事故：CSS opacity:0 入场动画永远不会执行 |
| "`&amp;` 是标准 HTML" | 事故：无头浏览器对实体字符解析不可靠 |
| "不用 padding" | 事故：缺少 padding 导致内容区域塌陷 |
| "GSAP 会自动注册" | 事故：必须显式 `window.__timelines["main"] = tl` |
| "绝对路径也能找到" | 事故：只认项目目录内相对路径 |
| "cover.html 不影响" | 事故：含 data-composition-id 的 HTML 都会导致冲突 |
| "用 -map 0:a:0 提取旁白轨" | 事故：HyperFrames 输出只有 1 条混合音频轨 |
| "双次渲染更安全" | 单次渲染 + ffmpeg 合成更高效，省掉一次 ~15 分钟的渲染 |
| "Canvas 用 rAF 更流畅" | HyperFrames 逐帧 seek 驱动，rAF 与 seek 不同步会导致闪烁 |
| "Three.js 用 performance.now()" | seek 回放时 performance.now() 不回溯，3D 动画不倒放 |
| "组件太多不需要都读" | stage6-components.md 是组件装配的唯一参考 |
