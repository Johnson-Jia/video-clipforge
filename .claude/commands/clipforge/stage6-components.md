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
      x: 540, y: 960,
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
  if (progress < 0.1) return;
  const t = (progress - 0.1) / 0.9;
  particles.forEach(p => {
    p.life = Math.max(0, 1 - t);
    p.x += p.vx;
    p.y += p.vy;
    p.vy += 0.15;
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
  <svg class="char-svg" viewBox="0 0 200 280" width="180" height="250">
    <!-- 身体 -->
    <rect x="60" y="140" width="80" height="100" rx="16" fill="#4a4a6a"/>
    <!-- 头 -->
    <circle cx="100" cy="90" r="55" fill="#6a6a8a"/>
    <!-- 眼睛 — explode: 星星眼 -->
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
| shock | 大圆 O（circle r="10"） | O 型（ellipse rx="16" ry="18"） | 正常竖起 |
| think | 半闭线（path stroke-width="4"） | 波浪线 | + 问号气泡 |
| cool | 墨镜（rect rx="6" 黑色填充） | 微笑弧线 | 正常 |
| explode | 星星（★ text） | 大张 O | 爆炸状 |
| tease | 眯缝线（line stroke-width="3"） | 坏笑弧线 | 正常 |
| moved | 星光眼（✧ text） | 小嘴微笑 | 正常 + 小泪花 |

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
    <div class="data-bar">
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
