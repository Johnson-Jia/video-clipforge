# ClipForge 文字特效配方库（content 层）

> Stage 6 参考附录。配套 `render-safety.md` §1.3、`stage6-components.md`「CSS 特效参考库」（fx 层特效）。
> 本文专注 **content 层文字特效**——给标题/数字/品牌字加视觉冲击力。

## §0 使用约定

- 配方是「LLM 复制改参数」模板，不是自动注入（组件 `<style>/<script>` 不被 s6_assemble 注入，需手动复制到 creative 碎片）。
- **入场动画用 `.set() + .to()`，禁 `.from() / .fromTo()`**（R-S6-026 HARD；`director_gate.py` 对 index.html 的 `tl.from` 零容忍）。
- **循环态用 GSAP `repeat:N yoyo:true`**（N = 场景时长 / 特效周期，向上取整；或 CSS `animation:...infinite` 但 0%帧必须可见）。
- **opacity 范围 0.3–0.9 禁归零**（归零 + seek 不执行 = 永久不可见，phase-visibility 事故同源）。
- 渐变文字必须 `-webkit-background-clip:text` + `background-clip:text` 双写，用 `background-image`（禁 `background` 简写）。
- **胶囊小标签禁用 grad 渐变文字**（feedback-bgclip-text-capsule-conflict）：胶囊元素（含 `padding`+`border`+`background`，如 `.pfc-use`）组合 `grad-*`（`background-clip:text`+`color:transparent`）时，background 被裁到文字范围 + 文字透明 → **整个标签消失**。胶囊用纯场景色 `color`，不组合 `grad-*`。渐变文字只能用在**无胶囊样式**的纯文字元素（大标题/数字）。
- **渐变文字（clip:text）line-height 必须 ≥ 1.0**（feedback-grad-cliptext-line-height，2026-07-03 fc-data-value 事故）：clip:text 的 background 画在元素 line-box；`line-height<1.0` → line-box < 字形高 → 字形上部 ascender 超出 line-box **无 background → 上部截断**（透明缺失）。实色文字不受影响（`color` 填充整个字形）。大字渐变（数字/标题）务必 `line-height ≥ 1.0`（建议 1.1）。
- 所有配方的 GSAP `startTime` 是组件示例占位，组装进 index.html 时替换为该场景的 `sceneStart + 偏移`。

## §1 HyperFrames 特效兼容规则

> 视频由 HTML+GSAP 用 `npx hyperframes render` 渲染（无头浏览器逐帧 seek）。核心：seek 驱动，CSS transition 不执行，CSS animation 有条件执行。

| 类型 | CSS `animation` | GSAP `tl.to repeat` | 入场 `.from/.fromTo`（index.html） |
|------|----------------|---------------------|--------------------------------------|
| **循环态**（0%帧可见） | ✅ 允许（0%帧 opacity≥0.15、scale≥0.85） | ✅ 允许（opacity≥0.3） | — |
| **入场**（从无到有） | ❌ 禁（seek 不执行 → 永久隐藏） | 不适用 | ❌ 禁 `.from`；用 `.set+.to` |
| **transition** | ❌ 完全不执行 | — | — |

**判定准则**：
- `@keyframes X { 0%,100%{opacity:0.4} 50%{opacity:0.8} }; animation:X infinite` → ✅ 循环呼吸（0%可见）
- `@keyframes X { 0%{opacity:0} 100%{opacity:1} }` → ❌ 入场（0%不可见，黑屏）
- `@keyframes X { 0%{transform:translateX(-100%)} 100%{translateX(0)} }` → ❌ 跑马灯入场（停在 -100%）
- `@keyframes X { 0%,100%{translateX(0)} 50%{translateX(50px)} }` → ✅ 循环摆动

---

## §2 核心配方

### §2.1 呼吸 breathing

**安全约束**：GSAP `repeat:N yoyo:true`；opacity 范围 0.3–0.9（禁归零）；scale 范围 0.92–1.12；ease `sine.inOut`。

```css
.breath {
  opacity: 0.6;              /* ⚠️ 默认可见，禁 opacity:0 */
  transform: scale(1);
}
```

```js
// 组件示例（startTime 占位）→ 组装时替换 startTime 为 sceneStart + 偏移
tl.to('.breath', {
  opacity: 0.85, scale: 1.08, duration: 2.4,
  repeat: 4, yoyo: true, ease: 'sine.inOut'
}, startTime);
```

**适用**：光晕、徽章、数字强调、CTA 标识、环形装饰。

---

### §2.2 渐变文字 gradient-text

**安全约束**：用 `background-image`（**禁 `background:` 简写**，会重置 clip）；同色系高饱和端点（**禁白色 `#fff`**——深色背景灰暗无力 **+ 手机 OLED 高亮屏过曝刺眼/层次糊**）；`text-shadow` blur ≤12px alpha≤0.4；**glow（独立发光，非描边）≤30px**（过大手机 OLED 过曝）；双写 `-webkit-` 前缀。

```css
.grad-text {
  background-image: linear-gradient(135deg, #ffe082 0%, #f9a825 50%, #ff6b35 100%);
  -webkit-background-clip: text;
  background-clip: text;
  -webkit-text-fill-color: transparent;
  color: transparent;
  text-shadow: 0 0 10px rgba(249,168,37,0.35);   /* blur≤12, alpha≤0.4 */
}
```

**流光变体**（渐变沿文字流动）：

```css
.grad-flow {
  background-image: linear-gradient(90deg, #f9a825, #00f5d4, #f9a825);
  background-size: 200% 100%;                    /* 2 倍宽供流动 */
  -webkit-background-clip: text; background-clip: text;
  color: transparent;
}
```

```js
tl.to('.grad-flow', {
  backgroundPosition: '100% 0%', duration: 3,
  repeat: 4, yoyo: true, ease: 'none'
}, startTime);
```

**适用**：主标题、数字、品牌字、CTA 主字。已用户验证「很赞绚丽」。

---

### §2.3 跑马灯 marquee

**安全约束**：内容必须重复 1 次（`width:200%`），起止都在可见位置；GSAP `xPercent:0 → -50`（非 -100，配双倍内容做无缝）；ease `none`（匀速）。

```css
.marquee-wrap { width: 100%; overflow: hidden; }
.marquee-inner {
  display: inline-flex; white-space: nowrap;
  width: 200%;                   /* 内容重复 1 次 */
}
.marquee-inner > * { flex: 0 0 auto; padding: 0 24px; }
```

```html
<div class="marquee-wrap">
  <div class="marquee-inner">
    <span>topic1</span><span>topic2</span><span>topic3</span>
    <span>topic1</span><span>topic2</span><span>topic3</span>   <!-- 重复一次 -->
  </div>
</div>
```

```js
tl.set('.marquee-inner', { xPercent: 0 }, 0)
  .to('.marquee-inner', {
    xPercent: -50, duration: 8, repeat: 3, ease: 'none'
  }, startTime);
```

**适用**：长项目名滚动、topics 标签列表、获奖记录、技术栈展示。

---

### §2.4 3D 翻转/层叠 3d-card

**安全约束**：父容器 `perspective:1200px`；子元素 `transform-style:preserve-3d`；`rotationY/rotationX` 范围 **-15° ~ +15°**（过大畸变）；GSAP 驱动（`rotationY` 属性，非 CSS transform 3d 字符串）。

```css
.card3d-wrap { perspective: 1200px; perspective-origin: 50% 50%; }
.card3d {
  transform-style: preserve-3d;
  transform: perspective(1200px) rotateY(-5deg);   /* 默认可见态 */
  opacity: 0.9;
}
```

```js
// 循环摆动
tl.to('.card3d', {
  rotationY: 5, duration: 2,
  repeat: 4, yoyo: true, ease: 'sine.inOut',
  transformOrigin: '50% 50%'
}, startTime);
```

```js
// 入场翻转（.set+.to，禁 from）
tl.set('.card3d', { rotationY: -90, opacity: 0.5 }, 0)
  .to('.card3d', { rotationY: 0, opacity: 1, duration: 0.8, ease: 'back.out(1.4)' }, startTime);
```

**适用**：项目卡片层叠、特性展示、产品对比。参考 `layered_cards.html`。

> ✅ **3D 已验证**（2026-06-15 effects-test）：`perspective:1200px` 父容器 + `rotateY` 循环在 H.264 编码后透视保留（抽帧确认卡片左右边不平行、明显纵深）。下方「CSS animation 循环版」已实测通过；GSAP `rotationY` 版同理（tween 逐帧应用 transform，与 CSS animation 循环等价）。

**CSS animation 循环版（effects-test 已验证）**：

```css
.card3d-loop {
  transform-style: preserve-3d;
  animation: card3dRotate 4s ease-in-out infinite;   /* 0%帧 rotateY(-8deg) 可见，HyperFrames 安全 */
}
@keyframes card3dRotate {
  0%, 100% { transform: perspective(1200px) rotateY(-8deg); }
  50%      { transform: perspective(1200px) rotateY(8deg); }
}
```

---

## §3 扩展配方

### §3.1 故障 glitch

**安全约束**：用 GSAP 短促抖动（非 CSS animation 入场）；错位用 `text-shadow` 多色 + GSAP `x` 抖动。

```css
.glitch {
  position: relative; color: #fff;
  text-shadow: 3px 0 #ff00ff, -3px 0 #00ffff;   /* RGB 错位 */
}
```

```js
// 周期性故障抖动
tl.to('.glitch', { x: -4, duration: 0.05 }, startTime)
  .to('.glitch', { x: 4, duration: 0.05 })
  .to('.glitch', { x: 0, duration: 0.05 })
  .to('.glitch', { x: -2, duration: 0.05 })
  .to('.glitch', { x: 0, duration: 0.1 });   // 单次故障序列，可 repeat
```

**适用**：科技/赛博/异常主题标题、bug 类内容。

---

### §3.2 霓虹 neon

**安全约束**：`text-shadow` 多层递增 blur（每层 blur 翻倍，alpha 递减），总 blur 不超 16px（feedback-text-shadow-blur-gate）；可配呼吸。

```css
.neon {
  color: #fff;
  text-shadow:
    0 0 4px #00f5d4,
    0 0 8px #00f5d4,
    0 0 16px #00f5d4;        /* 最大 blur 16 */
}
```

```js
// 霓虹呼吸（亮度脉动）
tl.to('.neon', {
  opacity: 0.75, duration: 1.5,
  repeat: 4, yoyo: true, ease: 'sine.inOut'
}, startTime);
```

**适用**：霓虹标题、强调数字、夜店/电竞风。

---

### §3.3 打字机 typewriter

**安全约束**：每字符包 `<span>`，GSAP `.set(opacity:0) + .to(stagger)`（**禁 CSS opacity:0 + .from**）；用 clip-path 从左展开也可。

```html
<h2 class="typewriter">
  <span>c</span><span>l</span><span>i</span><span>p</span><span>f</span><span>o</span><span>r</span><span>g</span><span>e</span>
</h2>
```

```js
tl.set('.typewriter span', { opacity: 0 }, 0)
  .to('.typewriter span', { opacity: 1, duration: 0.04, stagger: 0.08, ease: 'none' }, startTime);
```

**适用**：代码/终端场景、逐步揭示、悬念标题。

---

### §3.4 流光 flow

渐变文字的流动变体（见 §2.2 流光变体）。渐变沿文字横向流动，适合长停留标题。

**适用**：主标题长时间停留、品牌字、CTA。

---

### §3.5 描边 stroke

**安全约束**：`-webkit-text-stroke` + `color:transparent`；可叠加渐变填充。

```css
.stroke-text {
  -webkit-text-stroke: 2px var(--accent-cool);
  color: transparent;                 /* 纯描边 */
}
.stroke-fill {
  -webkit-text-stroke: 2px #00f5d4;
  -webkit-text-fill-color: #f9a825;   /* 描边 + 实心填充 */
}
```

**适用**：大字标题、对比强调、复古/印章风。

---

## §4 场景 → 特效推荐表

| 场景类型 | 常用组件 | 推荐文字特效组合 |
|---------|---------|-----------------|
| hook 钩子 | HeroCard | 渐变文字（暖→冷）+ 呼吸光晕 |
| 数据/规模 | DataViz, NumGrid, MarketBars | 渐变数字 + 呼吸强调 |
| 对比/竞争 | CompareSplit, ScoreCompare | 描边 + 3D 翻转 |
| 结论/摘要 | VerdictBox, RecStrip | 渐变标题 + 流光 |
| 标准项目介绍 | ProjectFullCard | 渐变项目名 + avatar 光环呼吸 |
| CTA 行动号召 | TextReveal | 渐变 + 呼吸 + 描边 |
| 科技/赛博 | Terminal, 代码场景 | 故障 glitch + 打字机 |
| 时间线/路径 | TimeLineFlow | 霓虹节点 + 渐变连线 |

> **强制**：选 content 组件时，标题/数字元素至少选 1 个文字特效。同一视频内特效组合要多样（避免所有标题用同一渐变角度）。

## §5 验证记录

| 配方 | 验证状态 | 验证方式 | 日期 |
|------|---------|---------|------|
| 呼吸 breathing | ✅ 已验证（CSS animation 循环态，技术等价 3D） | effects-test 同期 | 2026-06-15 |
| 渐变文字 gradient-text | ✅ 已验证（06/15 生产） | feedback-gradient-text | 2026-05 |
| 跑马灯 marquee | ✅ 已验证（CSS animation 循环态，技术等价 3D） | effects-test 同期 | 2026-06-15 |
| 3D 3d-card | ✅ 已验证（perspective+rotateY 循环，H.264 透视保留） | effects-test s02 抽帧 | 2026-06-15 |
| 故障/霓虹/打字机/流光/描边 | 待验证 | 后续抽帧 | — |

> 验证流程：`workspace/test/effects-test/` 各场景放 1 类特效 → s6_render → frame_analysis 亮度 + 人工抽帧 → 结论回填本表。
