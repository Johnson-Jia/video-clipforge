# Stage 6 视觉组件参考手册

> **此文件不是独立 stage，是 `stage6-production.md` 的参考附录。** schema.yaml 只引用 `stages/stage6-production`，本文件由 Stage 6 执行时按需加载。
>
> 组件库参考。每个组件包含 HTML 结构、CSS 样式和 GSAP 动画模板。所有组件遵循 HyperFrames 渲染安全规范：默认 opacity:1，入场由 GSAP .from() 驱动。

## 通用规则

- 所有尺寸基于竖屏 1080×1920
- 组件容器使用 flexbox 居中，不使用 absolute + 固定 top
- 入场动画由 GSAP timeline 控制，CSS 不设 opacity:0
- Canvas/Three.js 使用 seek 驱动更新，不用 requestAnimationFrame 独立循环

## 组件索引

> **按需加载：** 只在需要某个组件时，用 Read 工具读取对应文件。不要一次性加载全部组件。

| # | 组件名 | 一句话描述 | 适用场景类型 | 文件路径 |
|---|--------|-----------|-------------|---------|
| 1 | HeroCard | 项目首屏展示，震撼开场 | hook, intro | `.claude/commands/clipforge/components/hero_card.html` |
| 2 | StarCounter | Star 数动态计数动画 | stats, reveal | `.claude/commands/clipforge/components/star_counter.html` |
| 3 | CodeRain | 代码雨背景（Canvas seek 驱动） | tech, coding | `.claude/commands/clipforge/components/code_rain.html` |
| 4 | PulseOrb | 脉冲光球能量装饰 | data, focus | `.claude/commands/clipforge/components/pulse_orb.html` |
| 5 | CompareSplit | 双栏对比布局 | compare, versus | `.claude/commands/clipforge/components/compare_split.html` |
| 6 | TimeLineFlow | 时间线叙事（节点依次出现） | timeline, history | `.claude/commands/clipforge/components/timeline_flow.html` |
| 7 | ParticleBurst | 粒子爆发庆祝效果 | climax, celebration | `.claude/commands/clipforge/components/particle_burst.html` |
| 8 | ThreeScene | 3D 场景容器（需引入 Three.js） | immersive, spatial | `.claude/commands/clipforge/components/three_scene.html` |
| 9 | SpeechBubble | 角色吐槽气泡 | humor, commentary | `.claude/commands/clipforge/components/speech_bubble.html` |
| 10 | CharOverlay | 码力角色覆盖层（6 种表情） | reaction, emotion | `.claude/commands/clipforge/components/char_overlay.html` |
| 11 | DataViz | 数据可视化柱状图卡片 | data, stats | `.claude/commands/clipforge/components/data_viz.html` |
| 12 | TextReveal | 文字揭示动画（悬念展示） | reveal, surprise | `.claude/commands/clipforge/components/text_reveal.html` |
| 13 | ProjectFullCard | 标准模式单项目全屏 8 层卡片 | project-card, listing | `.claude/commands/clipforge/components/project_full_card.html` |
| 14 | VerdictBox | 核心结论框（border-left 高亮 + 标签） | conclusion, summary, thesis | `.claude/commands/clipforge/components/verdict_box.html` |
| 15 | NumGrid | 2×2 数据矩阵（大数字网格） | data, stats, metrics | `.claude/commands/clipforge/components/num_grid.html` |
| 16 | MarketBars | 市场对比条（水平进度条，data-width 驱动） | market, growth, comparison | `.claude/commands/clipforge/components/market_bars.html` |
| 17 | Spectrum | 冲击光谱（色带 + 垂直条形图双形态） | impact, analysis, spectrum | `.claude/commands/clipforge/components/spectrum.html` |
| 18 | ScoreCompare | 对比评分卡（A/B 双卡片 + WIN 徽章） | compare, versus, battle | `.claude/commands/clipforge/components/score_compare.html` |
| 19 | RecStrip | 三档推荐条（优先级排列 + 结论框） | recommendation, ranking, priority | `.claude/commands/clipforge/components/rec_strip.html` |

---

## 呼吸帧模板

在场景切换时插入 0.3-0.5s 的视觉呼吸：

```javascript
tl.add('breath-start')
  .to('.scene-content', { scale: 1.02, duration: 0.15, ease: 'power1.inOut' })
  .to('.scene-content', { scale: 1.0, duration: 0.15, ease: 'power1.inOut' })
  .add('breath-end');
```

## 视觉设计：格言 + 反面清单

> **你是导演，不是操作员。** 读内容，想画面，用工具箱实现，不碰红线。不查表、不套公式、每个场景独立思考。
> 执行前读取 `shared/director-toolkit` 获取导演思维工具——5 个必答题帮你从内容推导视觉，视觉词汇表是你的工具箱，导演笔记校准直觉。

### 设计格言（5 条正面引导）

① **内容为王**：特效是舞台灯光，不是演员。观众要看的是内容，特效让观众看得更舒服。
② **暗底亮光**：深色背景上，用光晕和辉度制造视觉焦点，不要大面积浅色块。
③ **层次分明**：背景沉下去，特效浮起来，内容站最前面。三层之间的亮度差就是深度感。
④ **克制即美学**：一个场景用 1-2 种特效就够了。堆砌不等于丰富，留白不等于空旷。
⑤ **每屏独一**：相邻场景的视觉风格必须有明显差异。观众不应该看到两个"差不多的画面"。

### 反面清单（10 条红线，全部来自真实事故）

✗ **背景光晕 opacity < 0.15** — H.264 编码后完全消失，白做了
✗ **特效覆盖在内容文字上方** — 观众看不清内容，特效毫无意义
✗ **连续两个场景用同一种特效** — 视觉疲劳，观众觉得在看同一个画面
✗ **整个视频只用一种配色** — 像没调过色的监控画面
✗ **场景无 padding** — 内容贴边，手机端文字被裁切
✗ **layer-fx 为空** — 三层架构缺一层，等于没做特效
✗ **内容元素 CSS opacity: 0 入场** — HyperFrames 不执行 CSS animation，内容永远不可见
✗ **文字无 text-shadow** — 深色背景上文字浮不起来，像贴了一张纸
✗ **特效元素 opacity > 0.6** — 抢了内容的视觉权重，主次颠倒
✗ **一个场景堆 3+ 种特效** — 像 PowerPoint 动画集锦，不是专业视频

### CSS 特效参考库

> 已验证可在 HyperFrames + H.264 中正确渲染的特效模板。直接用、改参数、组合、变体、或自创——都可以，只要不触碰反面清单和渲染安全约束。

### 渲染安全约束（所有特效必须遵守）

1. **CSS animation 0% 状态必须可见** — 不允许 `scaleY(0)`、`translateY(-100%)`、`opacity:0` 等不可见的初始状态
2. **静态 CSS 状态（无 animation 时）必须视觉正确** — HyperFrames seek 时不执行 CSS animation
3. **opacity ≥ 0.15** — 低于 0.15 在 H.264 视频编码中完全不可见
4. **允许的 CSS animation**：可见位置之间的移动（如漂移、摇摆、脉冲），动画的 0% 状态本身在画面内且可见
5. **禁止的 CSS animation**：从不可见到可见的过渡（如 `scaleY(0)→1`、`opacity:0→1`）
6. **入场动画用 GSAP** — `.from({opacity:0})` 是唯一可靠的入场机制

### 角色选择原则

- 角色从 `char_overlay.html` 组件中选取预设样式
- 一个视频内使用**同一个角色**（保持一致性）
- 角色大小约 120-150px，放在不遮挡核心内容的位置
- 角色带 idle 动画（idleBounce/idleSway/idleBreathe），保持画面活力

### 双轨道粒子规范 (DualOrbit)

> **事故复盘：** 单层粒子 ±30px / 3s 周期导致视觉"晃荡"；全部场景用粒子导致单调。改为双轨道嵌套结构，外层大范围慢漂（20-30s）+ 内层小范围微漂（8-12s），两条不同轨迹叠加产生流畅非重复运动。

**CSS keyframes（全局固定，所有场景共享）：**

```css
@keyframes driftOuter {
  0%, 100% { transform: translate(0, 0); }
  33% { transform: translate(180px, -120px); }
  66% { transform: translate(-150px, 100px); }
}
@keyframes driftInner {
  0%, 100% { transform: translate(0, 0) scale(1); }
  50% { transform: translate(60px, -80px) scale(1.1); }
}
```

**HTML 结构（每个粒子 2 层嵌套）：**

```html
<div style="position:absolute;top:25%;left:65%;animation:driftOuter 28s ease-in-out infinite 3s">
  <div style="width:16px;height:16px;border-radius:50%;background:hsl(210,80%,55%);
    opacity:0.5;filter:blur(2px);animation:driftInner 10s ease-in-out infinite 1s"></div>
</div>
```

**参数规范：**

| 参数 | 范围 | 说明 |
|------|------|------|
| 粒子尺寸 | 9-24px | `size = 9 + Math.random() * 15` |
| 数量 | 8-12 | `count = 8 + Math.floor(Math.random() * 5)` |
| 外层周期 | 20-30s | `outerDur = 20 + Math.random() * 10` |
| 内层周期 | 8-12s | `innerDur = 8 + Math.random() * 4` |
| 外层 delay | 0-8s | `outerDelay = Math.random() * 8` |
| 内层 delay | 0-5s | `innerDelay = Math.random() * 5` |
| opacity | 0.4-0.6 | `0.4 + Math.random() * 0.2` |
| blur | 1-3px | `1 + Math.random() * 2` |

**颜色选择：** 根据场景内容选色，不查表。想想这段内容在传达什么——科技用蓝、活力用暖色、增长用绿色、风险用冷紫——你的直觉比查表准。

**JS 生成代码模板（嵌入 `<script>` 标签）：**

```javascript
const LAYER_FX_SELECTOR = '.s-your-scene .layer-fx';
const H_RANGE = [180, 260]; // 根据场景内容选色，不是查表
const count = 8 + Math.floor(Math.random() * 5); // 8-12
const fxEl = document.querySelector(LAYER_FX_SELECTOR);
for (let i = 0; i < count; i++) {
  const h = H_RANGE[0] + Math.random() * (H_RANGE[1] - H_RANGE[0]);
  const s = 70 + Math.random() * 30;
  const l = 50 + Math.random() * 25;
  const size = 9 + Math.random() * 15;  // 9-24px
  const top = 5 + Math.random() * 90;
  const left = 5 + Math.random() * 90;
  const outerDur = 20 + Math.random() * 10; // 20-30s
  const innerDur = 8 + Math.random() * 4;   // 8-12s
  const outerDelay = Math.random() * 8;
  const innerDelay = Math.random() * 5;
  const wrapper = document.createElement('div');
  wrapper.style.cssText = `position:absolute;top:${top}%;left:${left}%;animation:driftOuter ${outerDur}s ease-in-out infinite ${outerDelay}s`;
  const dot = document.createElement('div');
  dot.style.cssText = `width:${size}px;height:${size}px;border-radius:50%;background:hsl(${h},${s}%,${l}%);opacity:${0.4+Math.random()*0.2};filter:blur(${1+Math.random()*2}px);animation:driftInner ${innerDur}s ease-in-out infinite ${innerDelay}s`;
  wrapper.appendChild(dot);
  fxEl.appendChild(wrapper);
}
```

> **规则：** 固定颜色 class 的粒子、单层结构粒子、尺寸 >24px 的粒子，均视为未达标。

---

## CSS 特效参考库（5 种已验证模板）

> **这些是已验证的实现模板，不是分配表。** 选择哪种、如何组合、如何变体，由「视觉推导系统」决定。

### StarBurst（星光绽放）

从画面中心向外的装饰射线 + 闪烁点。射线默认 scaleY(1) 始终可见。

**CSS keyframes（全局）：**

```css
@keyframes rayPulse {
  0%, 100% { opacity: 0.6; }
  50% { opacity: 0.3; }
}
@keyframes starTwinkle {
  0%, 100% { opacity: 0.9; transform: scale(1.3); }
  50% { opacity: 0.5; transform: scale(0.8); }
}
```

**HTML 模板（6-8 条射线 + 4-6 个闪烁点）：**

```html
<div class="layer-fx">
  <!-- 射线（6-8 条，不同角度，默认 scaleY(1) 始终可见） -->
  <div style="position:absolute;top:50%;left:50%;width:3px;height:600px;
    background:linear-gradient(transparent,hsla(45,90%,60%,0.7),transparent);
    transform-origin:top center;transform:rotate(0deg) scaleY(1);
    opacity:0.6;animation:rayPulse 4s ease-in-out infinite 0.3s"></div>
  <div style="position:absolute;top:50%;left:50%;width:3px;height:600px;
    background:linear-gradient(transparent,hsla(45,90%,60%,0.6),transparent);
    transform-origin:top center;transform:rotate(60deg) scaleY(1);
    opacity:0.6;animation:rayPulse 4s ease-in-out infinite 0.6s"></div>
  <!-- ... 重复至 6-8 条，rotate 递增 360/(n) 度 -->
  <!-- 闪烁点（4-6 个，随机位置，默认亮状态） -->
  <div style="position:absolute;top:35%;left:60%;width:10px;height:10px;
    border-radius:50%;background:hsl(45,95%,75%);opacity:0.9;
    box-shadow:0 0 8px hsla(45,95%,70%,0.6);
    animation:starTwinkle 2.5s ease-in-out infinite 0s"></div>
  <!-- ... 重复至 4-6 个 -->
</div>
```

**参数：** 射线默认 opacity 0.5-0.7 / 宽度 3px / 闪烁点 8-12px 默认 opacity 0.8-0.9 / 射线长度 500-800px

---

### LightOrbs（光球漂浮）

3-5 个大尺寸高斯模糊光球缓慢漂移，提供氛围感但不抢内容。

**CSS keyframes（全局）：**

```css
@keyframes orbDrift {
  0%, 100% { transform: translate(0, 0) scale(1); }
  33% { transform: translate(100px, -80px) scale(1.1); }
  66% { transform: translate(-120px, 60px) scale(0.9); }
}
```

**HTML 模板（3-5 个光球）：**

```html
<div class="layer-fx">
  <div style="position:absolute;top:20%;left:30%;width:200px;height:200px;
    border-radius:50%;background:hsl(210,80%,50%);opacity:0.18;filter:blur(50px);
    animation:orbDrift 25s ease-in-out infinite 0s"></div>
  <div style="position:absolute;top:60%;left:65%;width:160px;height:160px;
    border-radius:50%;background:hsl(200,75%,45%);opacity:0.15;filter:blur(45px);
    animation:orbDrift 30s ease-in-out infinite 4s"></div>
  <div style="position:absolute;top:80%;left:15%;width:180px;height:180px;
    border-radius:50%;background:hsl(230,70%,55%);opacity:0.20;filter:blur(55px);
    animation:orbDrift 22s ease-in-out infinite 8s"></div>
</div>
```

**参数：** 尺寸 150-250px / blur 40-60px / opacity 0.15-0.25 / 周期 20-35s

---

### GradientWave（渐变波）

2-3 条半透明渐变色带，缓慢旋转摇摆。色带默认居中可见。

**CSS keyframes（全局）：**

```css
@keyframes waveSway {
  0%, 100% { transform: rotate(-5deg); }
  50% { transform: rotate(5deg); }
}
```

**HTML 模板（2-3 条渐变带）：**

```html
<div class="layer-fx">
  <div style="position:absolute;top:20%;left:0;width:100%;height:300px;
    background:linear-gradient(90deg,transparent,hsla(220,60%,40%,0.15),transparent);
    transform:rotate(-8deg);animation:waveSway 20s ease-in-out infinite 0s"></div>
  <div style="position:absolute;top:55%;left:0;width:100%;height:250px;
    background:linear-gradient(90deg,transparent,hsla(250,50%,45%,0.12),transparent);
    transform:rotate(5deg);animation:waveSway 25s ease-in-out infinite 5s"></div>
</div>
```

**参数：** 色带高度 200-350px / opacity 0.10-0.20 / 周期 18-30s

---

### MatrixRain（矩阵雨）

竖向半透明细线，营造数据流感觉。线条默认在画面内可见位置。

**CSS keyframes（全局）：**

```css
@keyframes rainSway {
  0%, 100% { transform: translateY(0); opacity: 0.5; }
  50% { transform: translateY(40px); opacity: 0.3; }
}
```

**HTML 模板（8-12 条竖线）：**

```html
<div class="layer-fx">
  <div style="position:absolute;top:15%;left:22%;width:2px;height:250px;
    background:linear-gradient(transparent,hsla(200,80%,55%,0.5),transparent);
    opacity:0.5;box-shadow:0 0 6px hsla(200,80%,55%,0.3);
    animation:rainSway 14s ease-in-out infinite 0s"></div>
  <div style="position:absolute;top:40%;left:55%;width:2px;height:300px;
    background:linear-gradient(transparent,hsla(210,75%,50%,0.45),transparent);
    opacity:0.45;box-shadow:0 0 6px hsla(210,75%,50%,0.25);
    animation:rainSway 18s ease-in-out infinite 3s"></div>
  <!-- ... 重复至 8-12 条，top 10%-70% 范围内随机 -->
</div>
```

**参数：** 竖线宽度 2-3px / 长度 150-400px / 默认 opacity 0.40-0.60 / box-shadow 发光 / 周期 12-20s

---

## 沉浸模式配色速查

| 模式 | 背景渐变 | --accent-warm | --accent-cool |
|------|---------|---------------|---------------|
| hyper-pace | #080818 → #001a33 | #00D4FF | #0088CC |
| hidden-gem | #1a1208 → #0d0a04 | #FFB800 | #CC8800 |
| mega-update | #12081e → #080412 | #A855F7 | #7B2FBE |
| versus | #1a0808 → #120404 | #FF3B30 | #CC2020 |
| story-time | #081a0e → #041208 | #34C759 | #228B22 |
| fun-tool | #1a1a1a → #0d0d0d | #FF6B9D | #C084FC |

---

## Phase 视觉模板

> **长视频（场景时长 >15s）必用。** 每个 `.clip` 内按 `visual_phases` 数组创建多个 `.phase` div，通过 GSAP timeline 控制渐进揭示。

### Phase 通用 CSS

```css
.phase { position: absolute; inset: 0; display: flex; flex-direction: column;
  align-items: center; justify-content: center; }
.phase-header { font-size: 48px; font-weight: 700; color: var(--accent-warm);
  margin-bottom: 40px; letter-spacing: 2px; }
```

### hero 类型

```html
<div class="phase phase-1">
  <div class="phase-hero-title">养老AI手环</div>
  <div class="phase-hero-num">599-999元</div>
  <div class="phase-hero-sub">面向60岁以上老人 · 子女付费</div>
</div>
```
- 标题 ≥80px，数字 ≥120px，副标题 36px
- 适合场景开篇或核心结论 phase

### list 类型

```html
<div class="phase phase-2">
  <div class="phase-header">核心功能</div>
  <div class="phase-items">
    <div class="phase-item"><span class="item-num">01</span><span class="item-text">跌倒检测 &gt;95%</span></div>
    <div class="phase-item"><span class="item-num">02</span><span class="item-text">用药提醒</span></div>
    <div class="phase-item"><span class="item-num">03</span><span class="item-text">一键紧急呼叫</span></div>
  </div>
</div>
```
- 每项带序号 + 文字，垂直排列，间距 24px
- 序号用强调色，文字用白色

### data 类型

```html
<div class="phase phase-3">
  <div class="phase-header">市场规模</div>
  <div class="phase-data">
    <div class="data-row"><span class="data-label">2025年</span><span class="data-value">845亿美元</span></div>
    <div class="data-row"><span class="data-label">2030年</span><span class="data-value">1767亿美元</span></div>
    <div class="data-row"><span class="data-label">年复合增长</span><span class="data-value">15.9%</span></div>
  </div>
</div>
```
- 数据行用 label + value 布局，value 字号 ≥48px
- 大数字可用 JetBrains Mono 等宽字体

### compare 类型

```html
<div class="phase phase-4">
  <div class="phase-header">红海 vs 蓝海</div>
  <div class="phase-compare">
    <div class="compare-col compare-left">
      <div class="compare-title">消费级</div>
      <div class="compare-item">大厂红海</div>
      <div class="compare-item">胜率极低</div>
    </div>
    <div class="compare-divider"></div>
    <div class="compare-col compare-right">
      <div class="compare-title">养老级</div>
      <div class="compare-item">蓝海空白</div>
      <div class="compare-item">窗口期2-3年</div>
    </div>
  </div>
</div>
```
- 双栏等宽，中间分隔线
- 左栏用冷色调，右栏用暖色调

### timeline 类型

```html
<div class="phase phase-5">
  <div class="phase-header">MVP路线图</div>
  <div class="phase-timeline">
    <div class="tl-step"><span class="tl-week">1-2周</span><span class="tl-text">ESP32原型搭建</span></div>
    <div class="tl-step"><span class="tl-week">3-4周</span><span class="tl-text">跌倒检测算法训练</span></div>
    <div class="tl-step"><span class="tl-week">5-8周</span><span class="tl-text">硬件原型+社区试点</span></div>
    <div class="tl-step"><span class="tl-week">9-12周</span><span class="tl-text">迭代优化产品</span></div>
  </div>
</div>
```
- 步骤垂直排列，左侧时间标签，右侧内容
- 用圆点或连接线串联

### highlight 类型

```html
<div class="phase phase-6">
  <div class="phase-highlight-text">养老AI硬件需求最硬、竞争最小、窗口期最明确</div>
  <div class="phase-highlight-badge">核心结论</div>
</div>
```
- 文字 ≥56px，居中，用强调色
- 可加装饰性徽章或底线

---

## 布局推导体系（两级）

> **解决"每个场景画面都一样"的问题。** 特效、配色有推导机制，但布局缺少推导——同一个 flex 居中容器装不同内容，视觉差异全靠内容本身。布局推导让每个 phase 有自己的空间性格。

### 设计原则

1. **visual_type 决定大框架**：hero 一眼震撼、data 数字驱动、list 逐条展开、compare 双栏对峙、timeline 步骤递进、highlight 一锤定音
2. **内容长度微调元素尺寸**：同一框架下，4 字标题和 20 字标题用不同字号
3. **密度控制间距**：layout_hint.density 或 visual_type 自带密度决定元素间距
4. **`.phase` flex 居中是安全网**：即使布局推导失败，flex 居中保证内容不偏移

### Level 1: visual_type → 布局规格

每种 visual_type 的完整布局规格。HTML 骨架见上方「Phase 视觉模板」。

#### hero 布局

| 属性 | 规则 |
|------|------|
| 元素数 | 2-3（标题 + 数字/副标题 + 可选第三行） |
| 间距 | 40-60px（元素间） |
| primary 字号 | 基准 100px（见 Level 2 缩放） |
| primary 颜色 | 白色 900 + text-shadow |
| secondary 字号 | 数字类 120px / 副标题类 36px |
| secondary 颜色 | accent-warm（数字）或 text-secondary（副标题） |
| 水平对齐 | 全部居中 |
| 视觉重量 | 画面最重（字号最大、间距最宽、留白最多） |

#### list 布局

| 属性 | 规则 |
|------|------|
| 元素数 | 标题 + 2-6 条目 |
| 间距 | 标题→列表 24-32px，条目间 12-20px |
| 标题字号 | 44px, accent 色, 700 |
| 序号字号 | 28px, accent 色, 700 |
| 条目文字 | 32px, 白色, 400 |
| 水平对齐 | 标题居中；条目区 `width:85%` 居中、内部左对齐 |
| 视觉重量 | 中等（信息密度较高，需要扫描） |

#### data 布局

| 属性 | 规则 |
|------|------|
| 元素数 | 标题 + 2-6 数据行 |
| 间距 | 标题→数据 28-36px，行间 16-24px |
| 标题字号 | 44px, accent 色 |
| 数值字号 | 基准 56px, JetBrains Mono, accent-warm |
| 标签字号 | 26px, text-secondary |
| 水平对齐 | 居中；数据行 `width:85%` 居中 |
| 视觉重量 | 中高（数字即视觉焦点） |

#### compare 布局

| 属性 | 规则 |
|------|------|
| 元素数 | 标题 + 2 栏 × 2-4 项 |
| 间距 | 栏间 40-60px（含分隔线），项间 12-16px |
| 标题字号 | 44px |
| 栏标题 | 34px |
| 栏项 | 26px |
| 颜色分配 | 左栏 accent-cool, 右栏 accent-warm |
| 水平对齐 | phase 改为 `flex-direction:row`，2 栏各 `flex:1` |
| 视觉重量 | 高（对比产生视觉张力） |

> **compare 是唯一使用 `flex-direction:row` 的布局类型。** 其余类型都是默认的 column。

#### timeline 布局

| 属性 | 规则 |
|------|------|
| 元素数 | 标题 + 3-5 步骤 |
| 间距 | 标题→步骤 24-32px，步骤间 16-24px |
| 标题字号 | 44px, accent 色 |
| 时间标签 | 26px, accent 色 |
| 步骤文字 | 30px, 白色 |
| 水平对齐 | 标题居中；步骤区 `width:85%` 居中、内部左对齐 |
| 视觉重量 | 中等（线性流动感） |

#### highlight 布局

| 属性 | 规则 |
|------|------|
| 元素数 | 1-2（大文字 + 可选徽章/标签） |
| 间距 | 16-24px |
| 文字字号 | 基准 56px（见 Level 2 缩放） |
| 颜色 | accent-warm 或 accent-cool（取场景强调色） |
| 水平对齐 | 居中 |
| 视觉重量 | 极简但极强（元素少、字号大、颜色突出） |

### Level 2: 内容长度 → 元素尺寸缩放

**适用于所有布局的 primary/标题元素。** 字数 = 该元素文本的汉字数（英文按 `词数 × 1.5` 折算）。

| 字数范围 | 倍率 | hero 基准 100px | data 基准 56px | highlight 基准 56px |
|---------|------|----------------|----------------|-------------------|
| ≤4 字 | 1.0× | 100px | 56px | 56px |
| 5-8 字 | 0.85× | 85px | 48px | 48px |
| 9-14 字 | 0.7× | 70px | 39px | 39px |
| 15-24 字 | 0.55× | 55px | 31px | 31px |
| ≥25 字 | 0.45× | 45px | 25px | 25px |

**使用方法**：先确定 visual_type 的基准字号（上方各表），再根据 primary 元素字数查倍率。结果低于该层级下限（primary ≥ 44px, secondary ≥ 24px）时使用下限值。

### layout_hint 微调（可选，来自 Stage 3）

Stage 3 可在 visual_phases 中添加 `layout_hint` 提供额外微调：

```json
{
  "focus": "核心功能",
  "visual_type": "list",
  "key_data": ["功能1", "功能2", "功能3"],
  "layout_hint": {
    "density": "compact"
  }
}
```

| density | 间距倍率 | 适用时机 |
|---------|---------|---------|
| compact | × 0.7 | 内容条目多（≥5 条）、时间紧 |
| standard | × 1.0 | 大多数场景（默认） |
| generous | × 1.3 | 元素少（≤3）、强调留白和冲击力 |

**density 不指定时**从 visual_type 自动推导：
- hero、highlight → generous
- list、timeline → standard
- data、compare → compact
