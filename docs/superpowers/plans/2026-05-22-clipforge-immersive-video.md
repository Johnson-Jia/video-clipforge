# ClipForge 沉浸式视频体验升级 — 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 GitHub 视频从基础图文升级为情感化、沉浸式体验，包含叙事引擎、视觉组件系统、角色动画和粒子特效。

**Architecture:** 保持 DAG 不变（schema.yaml 不改），在 Stage 2/3/6 内部增加叙事规划、双线幽默、组件装配和 Canvas/Three.js 特效。新增 `stage6-components.md` 作为组件参考手册。升级 `categories/github.md` 增加沉浸模式映射。

**Tech Stack:** Claude Code Skills (Markdown), GSAP timeline, Canvas 2D API, Three.js (via HyperFrames adapter), HyperFrames seek-driven rendering

**Design Spec:** `docs/superpowers/specs/2026-05-22-clipforge-immersive-video-design.md`

---

## File Structure

| Action | File | Responsibility |
|--------|------|----------------|
| Modify | `.claude/commands/clipforge/categories/github.md` | GitHub 分类配置：新增 narrative/humor/immersion 节 |
| Rewrite | `.claude/commands/clipforge/stage2-analysis.md` | Stage 2：故事板设计、叙事模板、沉浸模式、情感曲线 |
| Rewrite | `.claude/commands/clipforge/stage3-narration.md` | Stage 3：双线幽默引擎、情感标记、角色表情触发 |
| Create | `.claude/commands/clipforge/stage6-components.md` | 12 个视觉组件的 HTML/CSS/JS 模板参考手册 |
| Rewrite | `.claude/commands/clipforge/stage6-production.md` | Stage 6：沉浸式渲染、组件装配、Canvas 粒子、Three.js 3D、角色动画、呼吸帧 |

**Dependencies:** Task 1 和 Task 4 可并行。Task 2 → Task 3 → Task 5 串行（后续依赖前序输出格式）。

---

### Task 1: 升级 GitHub 分类配置

**Files:**
- Modify: `.claude/commands/clipforge/categories/github.md` (末尾追加新节)

在文件末尾 `## shared-rules` 之前插入以下三个新节：

- [ ] **Step 1: 在 `## delivery` 和 `## shared-rules` 之间插入 `## narrative` 节**

追加内容：

```markdown
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
```

- [ ] **Step 2: 验证 front matter 和文件结构完整**

```bash
cd D:/AI-Agent/video-clipforge
head -5 .claude/commands/clipforge/categories/github.md
grep -c "^## " .claude/commands/clipforge/categories/github.md
```

Expected: front matter 正确（name/description/id），`## narrative` 节存在。

- [ ] **Step 3: 验证与 `_category-schema.md` 的兼容性**

确认新增的 `## narrative` 节在 schema 中没有冲突。schema 只定义了 Stage 1-7 和 shared-rules 段，narrative 是新增段，不影响现有段。检查 `grep "narrative" .claude/commands/clipforge/categories/_category-schema.md` 应返回空。

---

### Task 2: 重写 Stage 2 — 故事板设计

**Files:**
- Rewrite: `.claude/commands/clipforge/stage2-analysis.md`

保留原有的「情绪提炼」和「配乐方向」能力，新增故事板规划。design.md 输出格式扩展。

- [ ] **Step 1: 读取现有文件确认当前结构**

```bash
wc -l .claude/commands/clipforge/stage2-analysis.md
```

Expected: ~95 行。确认包含「情绪提炼」「视觉风格」「配乐方向」「素材需求预判」「design.md 格式规范」五节。

- [ ] **Step 2: 重写 stage2-analysis.md**

完整替换为以下内容。**保留原有的情绪提炼、视觉风格表、配乐方向、素材需求预判**，在其后新增故事板设计节。design.md 格式规范扩展。

新文件结构：

```markdown
# Stage 2: 内容分析与故事板设计

当内容摘要已整理且 `design.md` 不存在时触发。推导视觉风格方向、规划叙事结构和沉浸模式。

## 情绪提炼

[保留原有 §情绪提炼 全部内容，不变]

## 视觉风格

[保留原有 §视觉风格 全部内容，不变]

## 配乐方向

[保留原有 §配乐方向 全部内容，不变]

## 素材需求预判

[保留原有 §素材需求预判 全部内容，不变]

## 故事板设计（新增）

在完成上述分析后，规划视频的叙事结构、情感节奏和沉浸模式。输出到 `design.md` 的 `storyboard` 字段。

### 叙事模板选择

根据内容特征选择叙事结构：

| 模板 | 选择条件 | 情感弧线 |
|------|----------|----------|
| `contrast-arc` | 默认/重大更新/突破性项目 | 平淡 → 对比 → 震撼 → 高潮 → 沉淀 |
| `underdog` | 小众项目爆发/个人开发者作品 | 低谷 → 逆境 → 逆袭 → 胜利 |
| `showdown` | 竞品对比/同类工具评测 | 紧张 → 交锋 → 揭晓 → 结论 |
| `mystery-box` | 神秘项目/未公开功能 | 好奇 → 线索 → 揭示 → 惊喜 |
| `hyper-pace` | AI 爆发/周榜密集更新 | 快速 → 密集 → 爆发 → 呼吸 |
| `story-time` | 开发者故事/项目历程 | 平静 → 转折 → 深情 → 共鸣 |

**选择逻辑：**
1. 如果分类配置有 `narrative.default_template`，优先使用
2. 否则根据内容标签匹配：AI 密集 → `hyper-pace`，含"对比" → `showdown`，单项目深度 → `mystery-box`，项目有感人故事 → `story-time`
3. 无明确匹配时默认 `contrast-arc`

### 沉浸模式判定

根据分类配置的 `immersion_mapping` 或内容标签自动选择：

| 模式 | 代表色 | 视觉特征 |
|------|--------|----------|
| `hyper-pace` | #00D4FF | 快速剪辑 + 密集粒子 + 霓虹 |
| `hidden-gem` | #FFB800 | 渐进揭示 + 温暖光效 + 复古 |
| `mega-update` | #7B2FBE | 3D 场景 + 大气粒子 + 暗色 |
| `versus` | #FF3B30 | 分屏对比 + 脉冲能量 + 硬朗 |
| `story-time` | #34C759 | 插画风 + 柔和过渡 + 暖色 |
| `fun-tool` | 彩虹渐变 | 彩色弹跳 + 幽默角色 + 亮色 |

### 6 拍情感节奏

视频按 6 个情感节拍规划时长分配：

| 节拍 | 时长占比 | 情感目标 | 视觉方法 |
|------|----------|----------|----------|
| **抓取 (grab)** | 10% | 好奇、紧迫 | 快速切换 + 大字揭示 + 粒子聚集 |
| **构建 (build)** | 25% | 期待、专注 | 信息渐进 + 数据流动 + 背景渐变 |
| **揭示 (reveal)** | 20% | 惊喜、震撼 | 爆发效果 + 3D 转场 + 色彩跃升 |
| **高潮 (climax)** | 15% | 激动、共鸣 | 粒子爆发 + 震屏 + 角色表情 |
| **沉淀 (settle)** | 20% | 满足、思考 | 缓慢动画 + 柔和色调 + 呼吸帧 |
| **召唤 (summon)** | 10% | 行动欲、记忆点 | 收束聚焦 + CTA 引导 |

`emotion_curve` 是一个 6 元素数组，值域 [0,1]，表示每个节拍的情感强度。示例：`[0.3, 0.5, 0.8, 1.0, 0.6, 0.4]`。

### 角色出场规划

如果分类配置 `character_presence` 为 true：
- `character_presence: true` 写入 design.md
- 记录角色出场时机：高潮段（climax）必出，幽默段（tease）可选
- 表情规划跟随 storyboard，不在 Stage 2 确定具体表情

## design.md 格式规范（扩展）

Stage 2 产出的 `design.md` 在原有字段基础上新增 `storyboard` 节：

```yaml
# design.md — 视觉风格方向 + 故事板

## 风格
style: 科技赛博
mood: 激烈紧凑

## 配色方向（描述性，不指定具体色值）
color_direction:
  background: 深色暗调（接近纯黑）
  accent_cool: 霓虹青/翠绿（用于 features/more 场景）
  accent_warm: 金色/琥珀（用于 hook/CTA 场景）
  text: 白色主 + 浅灰辅

## 配乐方向
music_mood: 科技/赛博

## 素材预判（可选）
assets_needed: []

## 故事板（新增）
storyboard:
  narrative_template: "contrast-arc"    # 6 选 1
  emotion_curve: [0.3, 0.5, 0.8, 1.0, 0.6, 0.4]
  immersion_mode: "hyper-pace"          # 6 选 1
  humor_style: "dual-track"             # dual-track / narration-only / visual-only
  character_presence: true              # 是否启用码力角色
  beat_mapping:                         # 节拍 → 场景映射（大致分配）
    grab: "hook"
    build: "what, how"
    reveal: "capabilities"
    climax: "features"
    settle: "usecases, tech"
    summon: "CTA"
```

> **beat_mapping 说明：** 这是场景到情感节拍的粗映射，帮助 Stage 3 和 Stage 6 理解每个场景应传递的情感。不是严格约束，Stage 3 可以调整。

---

## Red Flags（停止信号）

| 信号 | 说明 |
|------|------|
| design.md 缺少 storyboard 节 | Stage 3 无法确定叙事结构和情感节奏 |
| emotion_curve 不是 6 元素数组 | 下游 Stage 期望精确 6 个节拍 |
| immersion_mode 不是 6 种之一 | Stage 6 无法匹配视觉风格 |

## Common Rationalizations（常见借口反驳）

| 借口 | 事实 |
|------|------|
| "故事板可以跳过，直接写文案" | 没有故事板，Stage 3 无法规划情感节奏和幽默插入点，视频会回到平铺直叙 |
| "emotion_curve 随便填" | 错误的情感曲线导致高潮段平淡或结尾过于激动，影响观感节奏 |
| "immersion_mode 用默认就行" | 不匹配内容的沉浸模式会让视觉风格与内容情绪割裂 |
```

- [ ] **Step 3: 验证文件语法和节标题**

```bash
grep "^## " .claude/commands/clipforge/stage2-analysis.md
```

Expected 输出应包含：`## 情绪提炼`、`## 视觉风格`、`## 配乐方向`、`## 素材需求预判`、`## 故事板设计（新增）`、`## design.md 格式规范（扩展）`、`## Red Flags`、`## Common Rationalizations`

---

### Task 3: 重写 Stage 3 — 双线幽默引擎

**Files:**
- Rewrite: `.claude/commands/clipforge/stage3-narration.md`

读取现有 stage3 内容，在旁白文案生成规则中增加情感标记、幽默注入和角色表情触发。

- [ ] **Step 1: 读取现有 stage3 确认结构**

```bash
ls .claude/commands/clipforge/stage3*.md
```

- [ ] **Step 2: 在 `narration_segments.json` 格式中增加情感字段**

找到 narration_segments.json 的输出格式定义，将每段格式从：

```json
{"scene": "hook", "type": "text", "text": "..."}
```

扩展为：

```json
{
  "scene": "hook",
  "type": "text",
  "text": "今天涨星最快的几个项目，直接炸了",
  "emotion": "grab",
  "emotion_intensity": 0.3,
  "humor_type": null,
  "character_expression": null
}
```

新增字段说明：

| 字段 | 类型 | 说明 |
|------|------|------|
| `emotion` | string | 6 拍节拍名: grab/build/reveal/climax/settle/summon |
| `emotion_intensity` | float | 0-1，对应 design.md 的 emotion_curve |
| `humor_type` | string/null | `analogy`（类比）/ `sarcasm`（反差吐槽）/ `trivia`（冷知识梗）/ null（无幽默） |
| `character_expression` | string/null | `shock`/`think`/`cool`/`explode`/`tease`/`moved`/null（无角色） |

在 stage3 文件中找到 narration_segments.json 的格式规范段，将上述扩展格式写入。

- [ ] **Step 3: 新增双线幽默引擎节**

在 stage3 文件中（场景拆解之后、最终检查之前）插入新节：

```markdown
## 双线幽默引擎

读取 `design.md` 的 `storyboard.humor_style` 确定幽默策略。

### 听觉线（旁白文案）

在每个段落的文案生成中，根据 `humor_type` 标记注入幽默：

| humor_type | 注入方法 | 示例 |
|------------|----------|------|
| `analogy` | 用生活场景比喻技术概念 | "这个框架跑起来比我外卖还快" |
| `sarcasm` | 正经话题突然转折 | "这个项目一周涨了五千星，比我的发际线退得还快" |
| `trivia` | 开发者文化内行梗 | "据说这个 bug 存活时间比实习生试用期还长" |

**注入规则：**
- 每 3-4 个段落至少 1 个包含 humor_type
- humor 只在 build/reveal/settle 节拍使用（grab/climax/summon 保持严肃）
- 幽默不改变核心信息，只是表达方式的调剂
- 遵守分类配置的 humor_rules

### 视觉线（画面表现）

`character_expression` 非 null 的段落，Stage 6 会渲染对应表情的码力角色。

**表情触发规则：**
- `shock`：数据震撼时（Star 暴涨、出乎意料的功能）
- `think`：分析思考时（原理解释、技术细节）
- `cool`：展示酷功能时（核心特性、独特能力）
- `explode`：高潮爆发时（总结震撼点、重大发现）
- `tease`：幽默调侃时（与 humor_type 同时出现）
- `moved`：感人/致敬时（开源精神、社区贡献）

### 情感节拍映射

从 `design.md` 的 `storyboard.beat_mapping` 确定每个场景属于哪个节拍：

| 节拍 | 旁白语速建议 | 幽默强度 | 角色出场 |
|------|-------------|---------|---------|
| grab | 快（+10%） | 无 | 无 |
| build | 中（+5%） | 低 | think/cool |
| reveal | 中快（+10%） | 中 | shock/cool |
| climax | 快（+15%） | 无 | explode |
| settle | 慢（-5%） | 高 | tease/moved |
| summon | 中（默认） | 低 | 无 |
```

- [ ] **Step 4: 在 TTS 参数传递节中增加逐段变速说明**

在 stage3 中关于 TTS 的段落，增加说明：每段的 `emotion` 字段对应一个语速偏移量，由 Stage 4 读取。Stage 3 只负责标记 emotion，不设置具体 rate 值。

在文件的 narration.txt 生成说明后追加：

```markdown
### 情感变速标记

每段的 `emotion` 字段指导 Stage 4 的 TTS 语速：

| emotion | Stage 4 TTS rate 偏移 |
|---------|----------------------|
| grab | +10% |
| build | +5% |
| reveal | +10% |
| climax | +15% |
| settle | -5% |
| summon | +0%（基准） |

Stage 3 不设置具体 rate 值，只标记 emotion。Stage 4 读取 emotion 字段后应用偏移。
```

- [ ] **Step 5: 验证 narration_segments.json 新字段**

```bash
grep "emotion" .claude/commands/clipforge/stage3*.md | head -10
grep "humor_type" .claude/commands/clipforge/stage3*.md | head -5
grep "character_expression" .claude/commands/clipforge/stage3*.md | head -5
```

Expected: 三个新字段都在文件中有定义和说明。

---

### Task 4: 创建 Stage 6 组件参考手册

**Files:**
- Create: `.claude/commands/clipforge/stage6-components.md`

- [ ] **Step 1: 创建组件参考手册文件**

创建 `.claude/commands/clipforge/stage6-components.md`，内容如下：

```markdown
# Stage 6 视觉组件参考手册

> Stage 6 编写 HTML 组合时的组件库参考。每个组件包含 HTML 结构、CSS 样式和 GSAP 动画模板。
> 所有组件遵循 HyperFrames 渲染安全规范：默认 opacity:1，入场由 GSAP .from() 驱动。

## 通用规则

- 所有尺寸基于竖屏 1080×1920
- 组件容器使用 flexbox 居中，不使用 absolute + 固定 top
- 入场动画由 GSAP timeline 控制，CSS 不设 opacity:0
- Canvas/Three.js 使用 seek 驱动更新，不用 requestAnimationFrame 独立循环

## 1. HeroCard — 项目首屏展示

**用途:** hook 场景或单项目深度解析的开场
**情感目标:** 震撼、吸引力

```html
<div class="hero-card">
  <div class="hero-glow hero-glow-warm"></div>
  <div class="hero-glow hero-glow-cool"></div>
  <div class="hero-grid"></div>
  <div class="hero-badge">今日 GitHub 榜单</div>
  <div class="hero-title">AI 项目<span class="accent">直接霸榜</span></div>
  <div class="hero-sub">8 个热门 · 6 个 AI 相关</div>
</div>
```

```css
.hero-card {
  position: relative; width: 100%; height: 100%;
  display: flex; flex-direction: column;
  align-items: center; justify-content: center;
  padding: 120px 60px;
}
.hero-glow {
  position: absolute; border-radius: 50%; filter: blur(140px);
  pointer-events: none;
}
.hero-glow-warm {
  width: 600px; height: 600px; opacity: 0.25;
  background: var(--accent-warm);
  top: 200px; left: -100px;
}
.hero-glow-cool {
  width: 500px; height: 500px; opacity: 0.2;
  background: var(--accent-cool);
  bottom: 300px; right: -80px;
}
.hero-grid {
  position: absolute; width: 100%; height: 100%;
  background-image:
    linear-gradient(rgba(0,229,160,0.04) 1px, transparent 1px),
    linear-gradient(90deg, rgba(0,229,160,0.04) 1px, transparent 1px);
  background-size: 40px 40px; pointer-events: none;
}
.hero-badge {
  font-size: 28px; font-weight: 600;
  color: var(--accent-warm);
  background: rgba(240,180,41,0.15);
  padding: 8px 24px; border-radius: 20px;
  margin-bottom: 40px;
}
.hero-title {
  font-size: 120px; font-weight: 900; color: #fff;
  letter-spacing: -2px; line-height: 1.15;
  text-shadow: 0 0 60px rgba(240,180,41,0.5);
  text-align: center;
}
.hero-title .accent { color: var(--accent-warm); }
.hero-sub {
  font-size: 48px; font-weight: 600;
  color: var(--accent-cool); margin-top: 48px;
}
```

```javascript
// GSAP 入场
tl.from('.hero-badge', {opacity:0, y:30, duration:0.3, ease:'power3.out'}, 0.1)
  .from('.hero-title', {opacity:0, scale:0.8, duration:0.4, ease:'back.out(1.2)'}, 0.2)
  .from('.hero-sub', {opacity:0, y:20, duration:0.3, ease:'power3.out'}, 0.5);
```

## 2. StarCounter — Star 数动态计数

**用途:** 展示项目 Star 数增长
**情感目标:** 兴奋、增长感

```html
<div class="star-counter">
  <div class="star-label">今日涨星</div>
  <div class="star-number" data-target="5123">0</div>
  <div class="star-unit">★</div>
</div>
```

```css
.star-counter {
  display: flex; flex-direction: column;
  align-items: center; gap: 16px;
}
.star-label { font-size: 32px; color: var(--text-secondary); }
.star-number {
  font-size: 140px; font-weight: 900;
  color: var(--accent-warm);
  font-variant-numeric: tabular-nums;
  text-shadow: 0 0 40px rgba(240,180,41,0.4);
}
.star-unit { font-size: 48px; color: var(--accent-warm); opacity: 0.7; }
```

```javascript
// GSAP 计数动画
const counter = { val: 0 };
tl.to(counter, {
  val: 5123, duration: 1.5, ease: 'power2.out',
  onUpdate: () => {
    document.querySelector('.star-number').textContent = Math.floor(counter.val).toLocaleString();
  }
}, startTime);
```

## 3. CodeRain — 代码雨背景

**用途:** 科技感场景背景
**情感目标:** 科技感、紧迫感

```html
<canvas class="code-rain-canvas" width="1080" height="1920"></canvas>
```

```css
.code-rain-canvas {
  position: absolute; top: 0; left: 0;
  width: 100%; height: 100%;
  opacity: 0.15; pointer-events: none;
}
```

```javascript
// Canvas 代码雨 — seek 驱动
const rainCanvas = document.querySelector('.code-rain-canvas');
const rainCtx = rainCanvas.getContext('2d');
const rainCols = Math.floor(1080 / 20);
const rainDrops = Array(rainCols).fill(0);
const rainChars = '01{}[]<>/=;:fnvarletconstreturnifelse'.split('');

function drawRain(progress) {
  rainCtx.fillStyle = 'rgba(8,8,24,0.1)';
  rainCtx.fillRect(0, 0, 1080, 1920);
  rainCtx.fillStyle = '#00e5a0';
  rainCtx.font = '14px monospace';
  const step = Math.floor(progress * 200);
  for (let i = 0; i < step % 50; i++) {
    const char = rainChars[Math.floor(Math.random() * rainChars.length)];
    const x = Math.floor(Math.random() * rainCols) * 20;
    const y = (rainDrops[i] * 20) % 1920;
    rainCtx.fillText(char, x, y);
    rainDrops[i] = (rainDrops[i] + 1) % 96;
  }
}

// 注册到 GSAP timeline
const rainProgress = { val: 0 };
tl.to(rainProgress, {
  val: 1, duration: sceneDuration,
  onUpdate: () => drawRain(rainProgress.val)
}, sceneStart);
```

## 4. PulseOrb — 脉冲光球

**用途:** 能量感装饰，配合数据展示
**情感目标:** 能量感、聚焦

```html
<div class="pulse-orb">
  <div class="orb-core"></div>
  <div class="orb-ring ring-1"></div>
  <div class="orb-ring ring-2"></div>
  <div class="orb-ring ring-3"></div>
</div>
```

```css
.pulse-orb {
  position: absolute; top: 50%; left: 50%;
  transform: translate(-50%, -50%);
  width: 400px; height: 400px;
}
.orb-core {
  position: absolute; top: 50%; left: 50%;
  transform: translate(-50%, -50%);
  width: 80px; height: 80px; border-radius: 50%;
  background: var(--accent-cool);
  box-shadow: 0 0 60px var(--accent-cool), 0 0 120px rgba(0,229,160,0.3);
}
.orb-ring {
  position: absolute; top: 50%; left: 50%;
  transform: translate(-50%, -50%);
  border-radius: 50%;
  border: 2px solid var(--accent-cool);
  opacity: 0.3;
}
.ring-1 { width: 160px; height: 160px; }
.ring-2 { width: 280px; height: 280px; opacity: 0.2; }
.ring-3 { width: 400px; height: 400px; opacity: 0.1; }
```

```javascript
tl.from('.orb-core', {scale:0, duration:0.5, ease:'elastic.out(1, 0.5)'}, startTime)
  .from('.ring-1', {scale:0, opacity:0, duration:0.4, ease:'power2.out'}, startTime + 0.2)
  .from('.ring-2', {scale:0, opacity:0, duration:0.4, ease:'power2.out'}, startTime + 0.3)
  .from('.ring-3', {scale:0, opacity:0, duration:0.4, ease:'power2.out'}, startTime + 0.4);
```

## 5. CompareSplit — 双栏对比

**用途:** 对比两个项目或功能
**情感目标:** 对抗感、悬念

```html
<div class="compare-split">
  <div class="compare-col left">
    <div class="compare-header">项目 A</div>
    <div class="compare-items">
      <div class="compare-item"><span class="label">速度</span><span class="value">快</span></div>
      <div class="compare-item"><span class="label">内存</span><span class="value">低</span></div>
    </div>
  </div>
  <div class="compare-divider"></div>
  <div class="compare-col right">
    <div class="compare-header">项目 B</div>
    <div class="compare-items">
      <div class="compare-item"><span class="label">速度</span><span class="value">更快</span></div>
      <div class="compare-item"><span class="label">内存</span><span class="value">较高</span></div>
    </div>
  </div>
</div>
```

```css
.compare-split {
  display: flex; width: 100%; height: 100%;
  padding: 120px 40px;
}
.compare-col {
  flex: 1; display: flex; flex-direction: column;
  align-items: center; justify-content: center;
  padding: 40px;
}
.compare-col.left { background: linear-gradient(135deg, rgba(0,229,160,0.08), transparent); }
.compare-col.right { background: linear-gradient(225deg, rgba(240,180,41,0.08), transparent); }
.compare-header { font-size: 42px; font-weight: 800; color: #fff; margin-bottom: 40px; }
.compare-divider {
  width: 2px; background: linear-gradient(180deg, transparent, #fff, transparent);
  opacity: 0.3; align-self: stretch; margin: 100px 0;
}
.compare-items { display: flex; flex-direction: column; gap: 20px; width: 100%; }
.compare-item {
  display: flex; justify-content: space-between;
  padding: 16px 24px; border-radius: 12px;
  background: rgba(255,255,255,0.05);
}
.compare-item .label { font-size: 28px; color: var(--text-secondary); }
.compare-item .value { font-size: 28px; font-weight: 700; color: #fff; }
```

## 6. TimeLineFlow — 时间线叙事

**用途:** 项目发展历程、版本迭代
**情感目标:** 故事感、推进感

```html
<div class="timeline-flow">
  <div class="timeline-line"></div>
  <div class="timeline-node" data-index="0">
    <div class="node-dot"></div>
    <div class="node-content">
      <div class="node-date">2024.01</div>
      <div class="node-text">项目启动</div>
    </div>
  </div>
  <!-- 更多节点... -->
</div>
```

```css
.timeline-flow {
  position: relative; width: 100%;
  padding: 120px 80px;
  display: flex; flex-direction: column; gap: 60px;
}
.timeline-line {
  position: absolute; left: 140px; top: 120px; bottom: 120px;
  width: 3px;
  background: linear-gradient(180deg, var(--accent-cool), var(--accent-warm));
  opacity: 0.5;
}
.timeline-node {
  display: flex; align-items: center; gap: 40px;
  padding-left: 100px;
}
.node-dot {
  width: 24px; height: 24px; border-radius: 50%;
  background: var(--accent-cool);
  box-shadow: 0 0 20px var(--accent-cool);
  flex-shrink: 0;
}
.node-date { font-size: 24px; color: var(--accent-warm); font-weight: 700; }
.node-text { font-size: 32px; color: #fff; margin-top: 8px; }
```

```javascript
tl.from('.timeline-node', {
  opacity:0, x:-30, duration:0.3,
  ease:'power3.out', stagger:0.2
}, startTime);
```

## 7. ParticleBurst — 粒子爆发庆祝

**用途:** 高潮段庆祝效果
**情感目标:** 激动、高潮

```html
<canvas class="particle-canvas" width="1080" height="1920"></canvas>
```

```css
.particle-canvas {
  position: absolute; top: 0; left: 0;
  width: 100%; height: 100%;
  pointer-events: none;
}
```

```javascript
// 粒子爆发系统 — seek 驱动
const pCanvas = document.querySelector('.particle-canvas');
const pCtx = pCanvas.getContext('2d');
const PARTICLE_COUNT = 80;
let particles = [];

function initParticles() {
  particles = [];
  for (let i = 0; i < PARTICLE_COUNT; i++) {
    const angle = (Math.PI * 2 * i) / PARTICLE_COUNT + Math.random() * 0.5;
    const speed = 3 + Math.random() * 8;
    particles.push({
      x: 540, y: 960, // 画面中心
      vx: Math.cos(angle) * speed,
      vy: Math.sin(angle) * speed,
      size: 3 + Math.random() * 5,
      color: ['#f0b429','#00e5a0','#fff','#ff6b6b','#4ecdc4'][Math.floor(Math.random()*5)],
      life: 1
    });
  }
}

function drawParticles(progress) {
  pCtx.clearRect(0, 0, 1080, 1920);
  if (progress < 0.1) return; // 前 10% 不显示
  const t = (progress - 0.1) / 0.9; // 归一化到 0-1
  particles.forEach(p => {
    p.life = Math.max(0, 1 - t);
    p.x += p.vx;
    p.y += p.vy;
    p.vy += 0.15; // 重力
    if (p.life > 0) {
      pCtx.globalAlpha = p.life;
      pCtx.fillStyle = p.color;
      pCtx.beginPath();
      pCtx.arc(p.x, p.y, p.size * p.life, 0, Math.PI * 2);
      pCtx.fill();
    }
  });
  pCtx.globalAlpha = 1;
}

initParticles();
const burstProgress = { val: 0 };
tl.to(burstProgress, {
  val: 1, duration: 2,
  onUpdate: () => drawParticles(burstProgress.val)
}, startTime);
```

## 8. ThreeScene — 3D 场景容器

**用途:** 需要空间感的沉浸场景
**情感目标:** 沉浸感、空间感

```html
<canvas class="three-canvas" width="1080" height="1920"></canvas>
```

```css
.three-canvas {
  position: absolute; top: 0; left: 0;
  width: 100%; height: 100%;
  pointer-events: none; opacity: 0.6;
}
```

```javascript
// Three.js 3D 场景 — 使用 __hfThreeTime
// 引入: <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
const threeCanvas = document.querySelector('.three-canvas');
const renderer = new THREE.WebGLRenderer({ canvas: threeCanvas, alpha: true });
renderer.setSize(1080, 1920);
renderer.setPixelRatio(1);

const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(60, 1080/1920, 0.1, 1000);
camera.position.z = 5;

// 示例：旋转立方体群
const cubes = [];
for (let i = 0; i < 20; i++) {
  const geo = new THREE.BoxGeometry(0.3, 0.3, 0.3);
  const mat = new THREE.MeshStandardMaterial({
    color: new THREE.Color().setHSL(i/20, 0.8, 0.6),
    transparent: true, opacity: 0.7
  });
  const mesh = new THREE.Mesh(geo, mat);
  mesh.position.set(
    (Math.random() - 0.5) * 8,
    (Math.random() - 0.5) * 12,
    (Math.random() - 0.5) * 4
  );
  scene.add(mesh);
  cubes.push(mesh);
}

const light = new THREE.PointLight(0x00e5a0, 2, 20);
light.position.set(0, 0, 5);
scene.add(light);
scene.add(new THREE.AmbientLight(0xffffff, 0.3));

// 关键：使用 __hfThreeTime 而非 Date.now()
function updateThree(progress) {
  const t = window.__hfThreeTime || progress * sceneDuration;
  cubes.forEach((cube, i) => {
    cube.rotation.x = t * 0.3 + i;
    cube.rotation.y = t * 0.5 + i * 0.5;
  });
  renderer.render(scene, camera);
}

const threeProgress = { val: 0 };
tl.to(threeProgress, {
  val: 1, duration: sceneDuration,
  onUpdate: () => updateThree(threeProgress.val)
}, sceneStart);
```

## 9. SpeechBubble — 角色吐槽气泡

**用途:** 幽默段角色吐槽叠加
**情感目标:** 幽默、亲近感

```html
<div class="speech-bubble">
  <div class="bubble-text">涨星比发际线退得还快</div>
  <div class="bubble-tail"></div>
</div>
```

```css
.speech-bubble {
  position: absolute; bottom: 280px; right: 60px;
  background: rgba(255,255,255,0.95);
  border-radius: 24px; padding: 24px 36px;
  max-width: 500px; z-index: 10;
  box-shadow: 0 8px 32px rgba(0,0,0,0.3);
}
.bubble-text {
  font-size: 30px; font-weight: 700;
  color: #1a1a2e; line-height: 1.4;
}
.bubble-tail {
  position: absolute; bottom: -12px; right: 60px;
  width: 0; height: 0;
  border-left: 16px solid transparent;
  border-right: 16px solid transparent;
  border-top: 16px solid rgba(255,255,255,0.95);
}
```

```javascript
tl.from('.speech-bubble', {
  opacity:0, scale:0.5, y:20,
  duration:0.3, ease:'back.out(2)'
}, startTime);
```

## 10. CharOverlay — 码力角色覆盖层

**用途:** 角色表情反应
**情感目标:** 人格化、情感连接

```html
<div class="char-overlay" data-expression="explode">
  <!-- SVG 角色 — 6 种表情通过 CSS class 切换 -->
  <svg class="char-svg" viewBox="0 0 200 280" width="180" height="250">
    <!-- 身体 -->
    <rect x="60" y="140" width="80" height="100" rx="16" fill="#4a4a6a"/>
    <!-- 头 -->
    <circle cx="100" cy="90" r="55" fill="#6a6a8a"/>
    <!-- 眼睛 — explode 表情: 星星眼 -->
    <text x="78" y="95" font-size="24" fill="#f0b429">★</text>
    <text x="112" y="95" font-size="24" fill="#f0b429">★</text>
    <!-- 嘴 — explode: 大张嘴 -->
    <ellipse cx="100" cy="120" rx="18" ry="14" fill="#2a2a4a"/>
    <!-- 头发 — explode: 爆炸发型 -->
    <path d="M55,55 L40,20 L70,45 L60,10 L90,40 L85,5 L110,38 L120,10 L130,45 L140,20 L145,55"
          stroke="#f0b429" stroke-width="4" fill="none" stroke-linecap="round"/>
  </svg>
</div>
```

```css
.char-overlay {
  position: absolute; bottom: 200px; left: 60px;
  z-index: 10;
}
.char-svg { filter: drop-shadow(0 4px 12px rgba(0,0,0,0.3)); }
```

**6 种表情 SVG 差异:**

| 表情 | 眼睛 | 嘴 | 头发/配饰 |
|------|------|-----|----------|
| shock | 大圆 O（`<circle r="10"/>`） | O 型（`<ellipse rx="16" ry="18"/>`） | 正常竖起 |
| think | 半闭（`<path d="M.." stroke-width="4"/>`） | 波浪线 | + 问号气泡 |
| cool | 墨镜（`<rect rx="6"/>` 黑色填充） | 微笑弧线 | 正常 |
| explode | 星星（`★` text） | 大张 O | 爆炸状 |
| tease | 眯缝（`<line stroke-width="3"/>`）+ 挤眉 | 坏笑弧线 | 正常 |
| moved | 星光眼（`✧` text） | 小嘴微笑 | 正常 + 小泪花 |

每种表情用 `data-expression` 属性标记，Stage 6 编写时根据 narration 的 `character_expression` 字段选择对应 SVG。

```javascript
tl.from('.char-overlay', {
  opacity:0, x:-40, duration:0.4,
  ease:'back.out(1.5)'
}, startTime);
```

## 11. DataViz — 数据可视化卡片

**用途:** 展示 Star 数、语言占比等数据
**情感目标:** 信服力、专业感

```html
<div class="data-viz">
  <div class="data-title">语言分布</div>
  <div class="data-bars">
    <div class="data-bar" data-pct="45">
      <div class="bar-label">Python</div>
      <div class="bar-track"><div class="bar-fill" style="width:45%"></div></div>
      <div class="bar-value">45%</div>
    </div>
    <!-- 更多条目... -->
  </div>
</div>
```

```css
.data-viz {
  background: rgba(255,255,255,0.05);
  border-radius: 20px; padding: 40px;
  border: 1px solid rgba(255,255,255,0.1);
}
.data-title { font-size: 36px; font-weight: 700; color: #fff; margin-bottom: 32px; }
.data-bar {
  display: flex; align-items: center; gap: 20px;
  margin-bottom: 20px;
}
.bar-label { font-size: 28px; color: var(--text-secondary); width: 160px; }
.bar-track {
  flex: 1; height: 12px; border-radius: 6px;
  background: rgba(255,255,255,0.1);
  overflow: hidden;
}
.bar-fill {
  height: 100%; border-radius: 6px;
  background: linear-gradient(90deg, var(--accent-cool), var(--accent-warm));
}
.bar-value { font-size: 28px; font-weight: 700; color: var(--accent-warm); width: 80px; text-align: right; }
```

```javascript
tl.from('.bar-fill', {
  scaleX:0, duration:0.6, ease:'power2.out',
  stagger:0.1, transformOrigin:'left center'
}, startTime);
```

## 12. TextReveal — 文字揭示动画

**用途:** 悬念揭示、关键信息展示
**情感目标:** 悬念、惊喜

```html
<div class="text-reveal">
  <div class="reveal-mask">
    <div class="reveal-text">58K Star</div>
  </div>
</div>
```

```css
.text-reveal {
  display: flex; align-items: center; justify-content: center;
}
.reveal-mask {
  overflow: hidden;
}
.reveal-text {
  font-size: 140px; font-weight: 900;
  color: var(--accent-warm);
  text-shadow: 0 0 80px rgba(240,180,41,0.6);
}
```

```javascript
tl.from('.reveal-text', {
  y:'100%', duration:0.6, ease:'power4.out'
}, startTime);
```

---

## 呼吸帧模板

在场景切换时插入 0.3-0.5s 的视觉呼吸：

```javascript
// 在两个场景之间插入呼吸帧
tl.add('breath-start')
  .to('.scene-content', { scale: 1.02, duration: 0.15, ease: 'power1.inOut' })
  .to('.scene-content', { scale: 1.0, duration: 0.15, ease: 'power1.inOut' })
  .add('breath-end');
```

## 沉浸模式配色速查

| 模式 | 背景渐变 | --accent-warm | --accent-cool |
|------|---------|---------------|---------------|
| hyper-pace | #080818 → #001a33 | #00D4FF | #0088CC |
| hidden-gem | #1a1208 → #0d0a04 | #FFB800 | #CC8800 |
| mega-update | #12081e → #080412 | #A855F7 | #7B2FBE |
| versus | #1a0808 → #120404 | #FF3B30 | #CC2020 |
| story-time | #081a0e → #041208 | #34C759 | #228B22 |
| fun-tool | #1a1a1a → #0d0d0d | #FF6B9D | #C084FC |
```

- [ ] **Step 2: 验证文件创建成功**

```bash
wc -l .claude/commands/clipforge/stage6-components.md
grep -c "^## " .claude/commands/clipforge/stage6-components.md
```

Expected: 文件存在且包含 12 个组件 + 通用规则 + 呼吸帧模板 + 沉浸模式配色速查（约 15 个 `##` 标题）。

---

### Task 5: 重写 Stage 6 — 沉浸式渲染

**Files:**
- Rewrite: `.claude/commands/clipforge/stage6-production.md`

这是最大的任务。保留所有渲染安全规则、音频嵌入、无 BGM 版本、渲染命令、门禁检查。重写 HTML 编写部分为组件装配模式。

- [ ] **Step 1: 确认需要保留的节**

读取当前 stage6-production.md，确认以下节完整保留（不修改）：
- §6.1 项目初始化
- §6.3 音频嵌入
- §6.5 默认竖屏
- §6.6 渲染
- §6.7 无 BGM 版本渲染
- §6.8 Stage 6 完成门禁
- Red Flags 表
- Common Rationalizations 表

- [ ] **Step 2: 重写 §6.2 读取 design.md**

将现有的简单风格读取替换为包含故事板读取的扩展版本：

```markdown
## 6.2 读取 design.md + storyboard

Stage 2 已将视觉风格方向和故事板写入 `design.md`。本阶段读取以下字段：

| 字段 | 用途 |
|------|------|
| `style`, `mood` | 整体风格方向 |
| `color_direction` | 配色方案选择 |
| `storyboard.immersion_mode` | 沉浸模式 → 匹配 `stage6-components.md` 的配色速查 |
| `storyboard.emotion_curve` | 6 拍情感强度 → 影响每个场景的视觉力度 |
| `storyboard.narrative_template` | 叙事模板 → 影响场景布局选择 |
| `storyboard.humor_style` | 幽默策略 → 是否添加 SpeechBubble 组件 |
| `storyboard.character_presence` | 角色出场 → 是否添加 CharOverlay 组件 |

**沉浸模式 → CSS 变量映射：** 从 `stage6-components.md` 的「沉浸模式配色速查」表获取具体色值，写入 `:root` CSS 变量。
```

- [ ] **Step 3: 重写 §6.4 编写 HTML 组合**

将现有的图文卡片模式替换为组件装配系统。保留降级触发条件，重写「内容规则」「结构规则」「CSS 规则」「视觉设计规则」「动画规则」：

```markdown
## 6.4 编写 HTML 组合（组件装配模式）

**调用 `/hyperframes` 技能**，传入：视觉风格方向、故事板、design.md 路径、`stage6-components.md` 组件库、`segment_durations.json` 时长、`narration_segments.json` 情感标记、音频嵌入参数。

### 组件装配流程

1. **读取 `narration_segments.json`** — 每段的 `scene`、`emotion`、`character_expression`、`humor_type`
2. **读取 `design.md` 的 `storyboard`** — 沉浸模式、叙事模板、情感曲线
3. **选择组件** — 每个场景根据 `emotion` 和内容类型从 `stage6-components.md` 选择组件
4. **装配 HTML** — 按 HyperFrames composition 结构组装

### 场景 → 组件映射

| 场景类型 | 主组件 | 辅助组件 | 特效 |
|---------|--------|---------|------|
| hook | HeroCard | StarCounter | PulseOrb |
| what/how | DataViz | CompareSplit | CodeRain(背景) |
| capabilities | DataViz | TextReveal | ParticleBurst(揭示时) |
| features | DataViz | CompareSplit | PulseOrb + ParticleBurst |
| usecases | TimeLineFlow | DataViz | — |
| tech | DataViz | CodeRain(背景) | — |
| CTA | TextReveal | — | ParticleBurst(结尾) |

### 角色和幽默组件插入

- `character_expression` 非 null 的场景 → 添加 `CharOverlay` 组件（对应表情 SVG）
- `humor_type` 非 null 的场景 → 添加 `SpeechBubble` 组件（文案从 narration 提取幽默句）
- 角色定位：画面左下角，占 15-20%
- 气泡定位：画面右下角或角色上方

### 呼吸帧插入

在场景切换点（由 `data-start` 间隔自然形成）插入呼吸帧：

```javascript
// 每个场景切换之间
tl.to('.current-scene .scene-content', { scale: 1.02, duration: 0.15 })
  .to('.current-scene .scene-content', { scale: 1.0, duration: 0.15 });
```

### Canvas 粒子和 Three.js 3D

根据沉浸模式决定是否使用 3D 场景：

| 沉浸模式 | Canvas 效果 | Three.js 3D |
|---------|------------|-------------|
| hyper-pace | CodeRain + ParticleBurst | 否 |
| hidden-gem | PulseOrb | 否 |
| mega-update | ParticleBurst | ThreeScene(旋转立方体群) |
| versus | PulseOrb | 否 |
| story-time | — | 否 |
| fun-tool | ParticleBurst | 否 |

Three.js 使用 `window.__hfThreeTime` 驱动，注册到 GSAP timeline 的 seek 回调。详见 `stage6-components.md` 的 ThreeScene 组件。

### 保留的渲染安全规则

以下规则**不变**（来自 `_shared-rules.md` §7 和现有 stage6）：

1. `window.__hf` 必须定义
2. `window.__timelines["main"]` 必须注册 GSAP timeline
3. 禁止 CSS `.anim-in` 类
4. 禁止 HTML 实体字符
5. scene-wrap 必须有 padding: 120px
6. `.clip` 只设 `position: absolute` + 尺寸，不设 opacity
7. 渲染前移除非 index.html 的 composition 文件
8. 音频文件必须在项目目录内
9. render-bitrate 5M

### 视觉密度要求（不变）

每场景可见视觉元素 ≥ 8 个（hook/CTA ≥ 5 个）。组件装配后检查元素数。
```

- [ ] **Step 4: 保留所有渲染和门禁检查**

确认以下节从现有文件完整复制到新文件，不做修改：
- §6.3 音频嵌入（全文保留）
- §6.5 默认竖屏（全文保留）
- §6.6 渲染（全文保留）
- §6.7 无 BGM 版本渲染（全文保留）
- §6.8 Stage 6 完成门禁（全文保留）

- [ ] **Step 5: 更新 Red Flags 表**

在现有 Red Flags 表中追加新条目：

```markdown
| Canvas 粒子使用 requestAnimationFrame | HyperFrames seek 驱动，独立 rAF 循环会导致画面不一致 |
| Three.js 使用 Date.now() | 必须 __hfThreeTime，否则 seek 回放时 3D 动画不回溯 |
| 角色遮挡核心内容 | CharOverlay 限制 15-20%，仅在非核心区域（角落） |
| 缺少 stage6-components.md 引用 | Stage 6 必须读取组件参考手册才能装配正确组件 |
```

- [ ] **Step 6: 验证完整文件**

```bash
wc -l .claude/commands/clipforge/stage6-production.md
grep "^## " .claude/commands/clipforge/stage6-production.md
```

Expected: 文件行数 > 600（保留的渲染规则 + 新增的组件装配），包含 `## 6.1` 到 `## 6.8` 所有节。

---

## Self-Review

### 1. Spec Coverage

| Spec 需求 | 对应 Task |
|-----------|-----------|
| 6 种叙事模板 | Task 2 (stage2 新增故事板节) |
| 6 拍情感节奏 | Task 2 (emotion_curve) + Task 3 (emotion 标记) |
| 6 种沉浸模式 | Task 1 (github.md immersion_mapping) + Task 4 (配色速查) |
| 双线幽默引擎 | Task 3 (humor_type 字段) + Task 4 (SpeechBubble 组件) |
| 码力角色系统 | Task 3 (character_expression) + Task 4 (CharOverlay 组件 + 6 种表情 SVG) |
| Canvas 粒子系统 | Task 4 (CodeRain + ParticleBurst 组件) |
| Three.js 3D | Task 4 (ThreeScene 组件) + Task 5 (使用规则) |
| 呼吸帧 | Task 4 (呼吸帧模板) + Task 5 (插入规则) |
| 情感驱动音频 | Task 3 (emotion → rate 偏移表) |
| DAG 不变 | 所有 Task 均不修改 schema.yaml |
| 组件参考手册 | Task 4 (stage6-components.md) |

### 2. Placeholder Scan

无 TBD/TODO/"implement later"/"add validation"/"similar to Task N"。所有代码块包含完整内容。

### 3. Type Consistency

- `narration_segments.json` 新字段名在 Task 3 定义、Task 5 引用：`emotion`, `emotion_intensity`, `humor_type`, `character_expression` — 一致
- `design.md` 的 `storyboard` 子字段在 Task 2 定义、Task 5 读取：`narrative_template`, `emotion_curve`, `immersion_mode`, `humor_style`, `character_presence` — 一致
- 沉浸模式名称在 Task 1/4/5 中一致：`hyper-pace`, `hidden-gem`, `mega-update`, `versus`, `story-time`, `fun-tool`
- 角色表情名称在 Task 3/4 中一致：`shock`, `think`, `cool`, `explode`, `tease`, `moved`
