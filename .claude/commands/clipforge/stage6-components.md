# Stage 6 视觉组件参考手册

> Stage 6 编写 HTML 组合时的组件库参考。每个组件包含 HTML 结构、CSS 样式和 GSAP 动画模板。
> 所有组件遵循 HyperFrames 渲染安全规范：默认 opacity:1，入场由 GSAP .from() 驱动。

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

---

## 呼吸帧模板

在场景切换时插入 0.3-0.5s 的视觉呼吸：

```javascript
tl.add('breath-start')
  .to('.scene-content', { scale: 1.02, duration: 0.15, ease: 'power1.inOut' })
  .to('.scene-content', { scale: 1.0, duration: 0.15, ease: 'power1.inOut' })
  .add('breath-end');
```

## 特效情绪映射表

> **特效选择不由固定编号决定，而是由场景情绪驱动。** 从 `char-effect-library.html` 中选择与情绪匹配的特效类型。

### 情绪 → 特效类型映射

> **特效选择由场景情绪驱动，但不再统一使用粒子。** 5 种 CSS 特效类型按情绪分配。

| 情绪（emotion） | 主特效 | 备选特效 | 最小实现 | 视觉特征 |
|-----------------|--------|---------|---------|---------|
| `grab`（钩子） | **星光绽放 (StarBurst)** | 双轨道粒子 (DualOrbit) | ≥6 条射线 + ≥4 闪烁点 | 从中心扩散、高亮度、爆发感 |
| `build`（铺垫） | **光球漂浮 (LightOrbs)** 或 **矩阵雨 (MatrixRain)** | 双轨道粒子 (DualOrbit) | 光球≥3个 / 矩阵雨≥8条 | 持续氛围、不抢内容 |
| `reveal`（揭示） | **双轨道粒子 (DualOrbit)** | 光球漂浮 (LightOrbs) | ≥8 个粒子（双层嵌套） | 缓慢漂移、精致点缀 |
| `climax`（高潮） | **星光绽放 (StarBurst)** | 双轨道粒子 (DualOrbit) | ≥8 条射线 + ≥6 闪烁点 | 全屏爆发、高密度 |
| `settle`（收束） | **渐变波 (GradientWave)** | 光球漂浮 (LightOrbs) | ≥2 条渐变带 | 沉静流动、极淡雅 |
| `summon`（号召） | **光球漂浮 (LightOrbs)** | 双轨道粒子 (DualOrbit) | 光球≥3个 / 粒子≥6个 | 温暖引导、轻快愉悦 |

> **"最小实现"是硬性门槛，不是建议值。** 低于最小实现的 layer-fx 视为空层，stage6_gate.sh 会拦截。

### 特效多样性规则（强制）

> **事故复盘：9 个场景全部使用同一种 CSS 粒子，视觉单调且像"晃荡"。** 以下规则强制特效类型多样化。

1. **连续禁止**：相邻场景不得使用同一特效类型超过 2 次。即任意连续 3 个场景中，至少有一种不同特效
2. **类型覆盖**：一个视频内至少使用 3 种不同特效类型（如 StarBurst + LightOrbs + MatrixRain）
3. **内容优先**：特效类型与内容主题协调（科技→MatrixRain，数据→LightOrbs，揭示→DualOrbit，沉静→GradientWave，爆发→StarBurst）
4. **不遮挡**：特效整体保持低调（LightOrbs opacity 0.05-0.12，粒子 opacity 0.2-0.35，射线 opacity 0.3-0.5），确保 `.layer-content` 始终清晰可读
5. **必选不可跳过**：每个场景的 `.layer-fx` 必须达到最小实现标准

### 场景特效分配建议表

> 按常见叙事结构给出推荐分配，具体视频可根据内容主题微调。

| 场景 | 情绪 | 推荐特效 | 理由 |
|------|------|---------|------|
| hook | grab | **StarBurst** | 爆发感开场 |
| 痛点/背景 | build | **LightOrbs** | 严肃话题，光球提供氛围不花哨 |
| 数据/规模 | build | **MatrixRain** | 数据流科技感 |
| 竞争/对比 | reveal | **DualOrbit** | 精致粒子点缀揭示 |
| 技术/方案 | build | **MatrixRain** | 代码/技术氛围 |
| 商业路径 | reveal | **LightOrbs** | 商业分析，沉稳大气 |
| 风险 | settle | **GradientWave** | 沉静收敛 |
| 总结 | summon | **LightOrbs** + 少量 DualOrbit | 暖色引导 |
| CTA | summon | **StarBurst**（少量） | 号召行动收尾 |

### 角色选择原则

- 角色从 `char-effect-library.html` 中标记为 SELECTED 的样例中选取
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
    opacity:0.3;filter:blur(3px);animation:driftInner 10s ease-in-out infinite 1s"></div>
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
| opacity | 0.2-0.35 | `0.2 + Math.random() * 0.15` |
| blur | 2-4px | `2 + Math.random() * 2` |

**颜色生成规则（按情绪选择 HSL 色调范围）：**

| 情绪 | H 范围 | S 范围 | L 范围 |
|------|--------|--------|--------|
| grab/climax | 0-360（全色相） | 70-100% | 50-75% |
| build | 180-260（蓝-青） | 60-90% | 45-65% |
| reveal | 30-60（金-琥珀） | 80-100% | 55-70% |
| settle | 200-280（蓝-紫） | 40-70% | 40-60% |
| summon | 0-40（红-橙） | 70-95% | 55-70% |

**JS 生成代码模板（嵌入 `<script>` 标签）：**

```javascript
const LAYER_FX_SELECTOR = '.s-your-scene .layer-fx';
const H_RANGE = [180, 260]; // 按情绪修改：build=[180,260] reveal=[30,60] 等
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
  dot.style.cssText = `width:${size}px;height:${size}px;border-radius:50%;background:hsl(${h},${s}%,${l}%);opacity:${0.2+Math.random()*0.15};filter:blur(${2+Math.random()*2}px);animation:driftInner ${innerDur}s ease-in-out infinite ${innerDelay}s`;
  wrapper.appendChild(dot);
  fxEl.appendChild(wrapper);
}
```

> **规则：** 固定颜色 class 的粒子、单层结构粒子、尺寸 >24px 的粒子，均视为未达标。

---

## CSS 特效库（4 种特效模板）

> **按情绪和内容选择特效类型，不再全部使用粒子。** 每种特效包含 CSS keyframes + HTML 结构模板。

### StarBurst（星光绽放）— 用于 grab/climax

从画面中心向外的装饰射线 + 闪烁点。射线默认 scaleY(1) 始终可见。

**CSS keyframes（全局）：**

```css
@keyframes rayPulse {
  0%, 100% { opacity: 0.35; }
  50% { opacity: 0.15; }
}
@keyframes starTwinkle {
  0%, 100% { opacity: 0.7; transform: scale(1.2); }
  50% { opacity: 0.3; transform: scale(0.8); }
}
```

**HTML 模板（6-8 条射线 + 4-6 个闪烁点）：**

```html
<div class="layer-fx">
  <!-- 射线（6-8 条，不同角度，默认 scaleY(1) 始终可见） -->
  <div style="position:absolute;top:50%;left:50%;width:2px;height:600px;
    background:linear-gradient(transparent,hsla(45,90%,60%,0.5),transparent);
    transform-origin:top center;transform:rotate(0deg) scaleY(1);
    opacity:0.35;animation:rayPulse 4s ease-in-out infinite 0.3s"></div>
  <div style="position:absolute;top:50%;left:50%;width:2px;height:600px;
    background:linear-gradient(transparent,hsla(45,90%,60%,0.4),transparent);
    transform-origin:top center;transform:rotate(60deg) scaleY(1);
    opacity:0.35;animation:rayPulse 4s ease-in-out infinite 0.6s"></div>
  <!-- ... 重复至 6-8 条，rotate 递增 360/(n) 度 -->
  <!-- 闪烁点（4-6 个，随机位置，默认亮状态） -->
  <div style="position:absolute;top:35%;left:60%;width:8px;height:8px;
    border-radius:50%;background:hsl(45,95%,70%);opacity:0.7;
    animation:starTwinkle 2.5s ease-in-out infinite 0s"></div>
  <!-- ... 重复至 4-6 个 -->
</div>
```

**参数：** 射线默认 opacity 0.3-0.5 / 闪烁点 6-10px 默认 opacity 0.7 / 射线长度 500-800px

---

### LightOrbs（光球漂浮）— 用于 build/settle/summon

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
  <div style="position:absolute;top:20%;left:30%;width:180px;height:180px;
    border-radius:50%;background:hsl(210,80%,50%);opacity:0.08;filter:blur(80px);
    animation:orbDrift 25s ease-in-out infinite 0s"></div>
  <div style="position:absolute;top:60%;left:65%;width:120px;height:120px;
    border-radius:50%;background:hsl(200,75%,45%);opacity:0.06;filter:blur(60px);
    animation:orbDrift 30s ease-in-out infinite 4s"></div>
  <div style="position:absolute;top:80%;left:15%;width:150px;height:150px;
    border-radius:50%;background:hsl(230,70%,55%);opacity:0.07;filter:blur(70px);
    animation:orbDrift 22s ease-in-out infinite 8s"></div>
</div>
```

**参数：** 尺寸 100-200px / blur 60-100px / opacity 0.05-0.12 / 周期 20-35s

---

### GradientWave（渐变波）— 用于 settle

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
    background:linear-gradient(90deg,transparent,hsla(220,60%,40%,0.06),transparent);
    transform:rotate(-8deg);animation:waveSway 20s ease-in-out infinite 0s"></div>
  <div style="position:absolute;top:55%;left:0;width:100%;height:250px;
    background:linear-gradient(90deg,transparent,hsla(250,50%,45%,0.05),transparent);
    transform:rotate(5deg);animation:waveSway 25s ease-in-out infinite 5s"></div>
</div>
```

**参数：** 色带高度 200-350px / opacity 0.04-0.08 / 周期 18-30s

---

### MatrixRain（矩阵雨）— 用于 build（科技场景）

竖向半透明细线，营造数据流感觉。线条默认在画面内可见位置。

**CSS keyframes（全局）：**

```css
@keyframes rainSway {
  0%, 100% { transform: translateY(0); opacity: 0.3; }
  50% { transform: translateY(40px); opacity: 0.15; }
}
```

**HTML 模板（8-12 条竖线）：**

```html
<div class="layer-fx">
  <div style="position:absolute;top:15%;left:22%;width:1px;height:250px;
    background:linear-gradient(transparent,hsla(200,80%,55%,0.3),transparent);
    opacity:0.3;animation:rainSway 14s ease-in-out infinite 0s"></div>
  <div style="position:absolute;top:40%;left:55%;width:1px;height:300px;
    background:linear-gradient(transparent,hsla(210,75%,50%,0.25),transparent);
    opacity:0.25;animation:rainSway 18s ease-in-out infinite 3s"></div>
  <!-- ... 重复至 8-12 条，top 10%-70% 范围内随机 -->
</div>
```

**参数：** 竖线宽度 1-2px / 长度 150-400px / 默认 opacity 0.15-0.35 / 周期 12-20s

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
