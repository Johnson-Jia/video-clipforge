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

| 情绪（emotion） | 特效类型方向 | 必选特效 | 最小实现 | 视觉特征 |
|-----------------|-------------|---------|---------|---------|
| `grab`（钩子） | 高能量、爆炸型 | FX-1 纸屑 / FX-2 粒子爆炸 / PT-1 漂浮粒子 | Canvas 粒子 或 ≥5 个 CSS 动画元素 | 快速扩散、高亮度、短时爆发 |
| `build`（铺垫） | 持续流动型 | PT-1 漂浮粒子 / PT-4 星云旋转 / 3D-4 视差层叠 | Canvas 粒子 或 ≥3 个 CSS 动画元素 | 缓慢运动、低密度、持续可见 |
| `reveal`（揭示） | 突出强调型 | FX-3 星光绽放 / PT-2 矩阵雨 | Canvas 粒子 或 ≥3 个 CSS 动画元素 | 从中心扩散或从上到下流动 |
| `climax`（高潮） | 爆发 + 强化 | FX-2 粒子爆炸 / FX-4 彩带飘落 / 3D-2 轨道旋转 | Canvas 粒子 或 ≥5 个 CSS 动画元素 | 全屏覆盖、高密度、强烈视觉冲击 |
| `settle`（收束） | 温和收敛型 | PT-1 漂浮粒子（低密度） / FX-3 星光（低 opacity） | Canvas 粒子 或 ≥3 个 CSS 动画元素 | 极缓慢、低密度、淡雅 |
| `summon`（号召） | 温暖引导型 | PT-1 漂浮粒子（暖色调） / FX-1 纸屑（少量） | Canvas 粒子 或 ≥3 个 CSS 动画元素 | 轻快、愉悦、不抢内容 |

> **"最小实现"是硬性门槛，不是建议值。** 低于最小实现的 layer-fx 视为空层，stage6_gate.sh 会拦截。特效数量统计的是 `.layer-fx` 内的子元素数（CSS div 或 Canvas 容器），不统计伪元素。

### 特效选择原则

1. **内容优先**：特效类型应与内容主题协调（科技→矩阵雨/粒子，金融→数据流，生活→纸屑/彩带）
2. **情绪匹配**：每个场景的 `emotion` 字段决定特效的能量级别和最小实现门槛
3. **多样性**：相邻场景避免重复使用同一种特效，交替使用不同类型
4. **不遮挡**：特效 opacity 保持 0.3-0.6，确保 `.layer-content` 始终清晰可读
5. **必选不可跳过**：每个场景的 `.layer-fx` 必须达到最小实现标准，空 layer-fx 会导致 stage6_gate.sh 拦截

### 角色选择原则

- 角色从 `char-effect-library.html` 中标记为 SELECTED 的样例中选取
- 一个视频内使用**同一个角色**（保持一致性）
- 角色大小约 120-150px，放在不遮挡核心内容的位置
- 角色带 idle 动画（idleBounce/idleSway/idleBreathe），保持画面活力

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
