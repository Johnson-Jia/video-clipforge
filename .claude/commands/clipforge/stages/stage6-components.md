# Stage 6 视觉组件参考手册

> `stage6-production.md` 的参考附录，按需加载。组件库参考——每个组件包含 HTML 结构、CSS 样式和 GSAP 动画模板。所有组件遵循 HyperFrames 渲染安全规范：默认 opacity:1，入场由 GSAP .from() 驱动。

## 通用规则

- 所有尺寸基于竖屏 1080×1920
- 组件容器使用 flexbox 居中，不使用 absolute + 固定 top
- 入场动画由 GSAP timeline 控制，CSS 不设 opacity:0
- Canvas/Three.js 使用 seek 驱动更新，不用 requestAnimationFrame 独立循环
- 禁止使用全局通配选择器（如 `.xxx *`）设置 text-shadow、opacity、filter 等视觉属性，会污染渐变文字等特殊样式

## 组件索引

> **按需加载：** 只在需要某个组件时，用 Read 工具读取对应文件。不要一次性加载全部组件。
> **统一索引：** `components/registry.yaml` 是所有组件的元数据汇总，支持按 layer/tags/emotion_range 粗筛。

### 背景层 (bg/)

> 嵌入 `.layer-bg`，提供渐变、光晕等氛围基底。一个场景选 1 个 bg 组件（必须）。
>
> **R-R-009 HARD 门禁**：禁止仅使用 glow+grid 三件套（线性渐变 + 模糊光圆 + grid-bg）作为 bg 方案。每个场景 bg 层必须包含至少 2 种不同类型的视觉元素。

| # | 组件名 | 一句话描述 | 适用场景类型 | 文件路径 |
|---|--------|-----------|-------------|---------|
| 1 | GradientMesh | 渐变色带缓慢摇摆 | ambient, background | `components/bg/gradient_mesh.html` |
| 2 | LightField | 高斯模糊光球 + 渐变背景 | atmosphere, depth | `components/bg/light_field.html` |
| 3 | NoiseField | SVG 噪点纹理 + 移动光斑 | tension, mystery, atmospheric | `components/bg/noise_field.html` |
| 4 | ContourLines | 等高线纹理 + 辉光 | analysis, data, structured | `components/bg/contour_lines.html` |
| 5 | RadialBeams | 径向光束射线发散 | shock, climax, revelation | `components/bg/radial_beams.html` |
| 6 | ScanGrid | 网格 + 移动扫描线 | tech, cyber, futuristic | `components/bg/scan_grid.html` |
| 7 | VignetteGlow | 暗角聚光 + 中心辉光 | warmth, focus, conclusion | `components/bg/vignette_glow.html` |
| 8 | WaveRipple | 同心波纹扩散 | calm, transition, mystery | `components/bg/wave_ripple.html` |
| 9 | AuroraFlow | 水平极光色带 + 竖直射线丝 + 闪烁亮点 | wonder, beauty, curiosity | `components/bg/aurora_flow.html` |
| 10 | HexGrid | SVG 六边形蜂窝网格 + 翡翠绿辉光 + 脉冲 | confidence, precision, tech | `components/bg/hex_grid.html` |
| 11 | NebulaCloud | 星云色团漂移 + 星点闪烁 | wonder, mystery, beauty | `components/bg/nebula_cloud.html` |
| 12 | EmberGlow | 琥珀/橙色余烬上浮 + 火星粒子 + 暖纹 | warmth, nostalgia, beauty | `components/bg/ember_glow.html` |
| 13 | DiamondLattice | 45° 金色菱形网格 + 对角漂移 + 金色辉光 | pride, confidence, elegance | `components/bg/diamond_lattice.html` |
| 14 | ElectricPulse | 旋转光弧 + 脉冲环 + 青白能量核心 | excitement, power, climax | `components/bg/electric_pulse.html` |
| 15 | CosmicPlanet | 地球（海洋/大陆/云层/冰盖/城市灯光）+ 星空 | wonder, epic, mystery | `components/bg/cosmic_planet.html` |
| 16 | FrostCrystal | 冰蓝渐变 + 能量核心 + 旋转星芒 + 脉冲环 + 极光带 | clinical, precision, cold | `components/bg/frost_crystal.html` |
| 17 | MossGarden | 深绿渐变 + 树冠光斑 + 萤火虫 + 有机曲线 + 底部薄雾 | organic, growth, nature, calm | `components/bg/moss_garden.html` |
| 18 | CleanSlate | 钢蓝渐变 + 点阵网格 + 几何装饰线 + 冷蓝聚光灯 + 漂浮形状 | clarity, focus, professional | `components/bg/clean_slate.html` |
| 19 | DarkCipher | 深靛紫底 + 暗红裂缝 + 监控扫描线 + 故障闪烁 + 心跳脉冲 | tension, mystery, suspense | `components/bg/dark_cipher.html` |
| 20 | SoftLinen | 琥珀暖色 + 散景圆环 + 烛光脉冲 + 黄金时刻色带 + 漂浮花瓣 | warmth, cozy, gentle, daily | `components/bg/soft_linen.html` |
| 21 | AuroraNight | 极光帘幕 3 层 + 月光辉光 + 银河雾带 + 雪山剪影 3 层（空气透视） | wonder, tranquility, grandeur | `components/bg/aurora_night.html` |
| 22 | CosmicVoid | 吞噬星空深空：行星+大气光晕 + 虫洞星门能量漩涡 + 金色星力流 + 4 团梦幻星云 | wonder, awe, grandeur, mystery | `components/bg/cosmic_void.html` |
| 23 | RuinCity | 吞噬星空荒野区：血色夕阳 + 断壁楼群剪影 + 尘埃雾霾 + 灰烬粒子 | desolation, danger, tension | `components/bg/ruin_city.html` |
| 24 | AncientRelic | 古文明遗迹：旋转金紫符文阵 + 神圣光柱 + 悬浮石块 + 立柱剪影 | mystery, sacred, wonder | `components/bg/ancient_relic.html` |
| 25 | StarforceOcean | 星力海洋：金色能量漩涡 + 翻涌能量海 + 倾泻光柱 + 能量流光 | power, transcendence, awe | `components/bg/starforce_ocean.html` |
| 26 | VirtualUniverse | 虚拟宇宙：透视数据网格 + 竖直数据流 + 全息光面 + 数据核心 | tech, futuristic, sci-fi | `components/bg/virtual_universe.html` |
| 27 | BloodmoonWild | 血月荒原：巨型血月 + 荒原枯树剪影 + 血雾 + 远处血色闪电 | danger, dread, ominous | `components/bg/bloodmoon_wild.html` |

### 特效层 (fx/)

> 嵌入 `.layer-fx`，提供动态视觉装饰。

**fx 原语库（BASE_CSS 自动注入，优先用，2026-06-17）**：10 个 CSS animation 循环态原语（HyperFrames 安全），LLM 在 `.layer-fx` 内用 `<div class="fx-xxx">` 直接引用，**无需写 CSS**。颜色默认半透明白，可 inline 覆盖（`style="background:var(--accent-warm)"`）。R-R-008 要求 **≥3 元素 且 ≥2 种不同 fx class**（防同类凑数）。

| 原语 | 视觉 | 情绪 |
|------|------|------|
| `fx-aura` | 光晕呼吸 | ambient/focus |
| `fx-ring` | 光环扩散 | focus |
| `fx-particle` | 微粒漂浮 | calm/mystery |
| `fx-scan` | 扫描线 | tech/analysis |
| `fx-beam` | 对角光带扫过 | climax/震撼 |
| `fx-stream` | 垂直数据流 | tech/data/AI |
| `fx-bolt` | 电流闪烁 | shock/dramatic |
| `fx-grid` | 网格脉冲 | tech/cyber |
| `fx-orbit` | 轨道粒子 | energy/dynamic |
| `fx-pulse-ring` | 脉冲环扩散 | focus/alert |

> 下方 fx 组件库（13 个）为重型特效参考，但依赖 GSAP `.from`（HyperFrames seek 不执行入场），**默认用上方原语**；组件库需手动复制且效果不稳定。

| # | 组件名 | 一句话描述 | 适用场景类型 | 文件路径 |
|---|--------|-----------|-------------|---------|
| 1 | CodeRain | 代码雨背景（Canvas seek 驱动） | tech, coding | `components/fx/code_rain.html` |
| 2 | PulseOrb | 脉冲光球能量装饰 | data, focus | `components/fx/pulse_orb.html` |
| 3 | ParticleBurst | 粒子爆发庆祝效果 | climax, celebration | `components/fx/particle_burst.html` |
| 4 | ThreeScene | 3D 场景容器（需引入 Three.js） | immersive, spatial | `components/fx/three_scene.html` |
| 5 | Spectrum | 冲击光谱（色带 + 垂直条形图双形态） | impact, analysis, spectrum | `components/fx/spectrum.html` |
| 6 | ScanLine | 水平扫描线扫过屏幕 | tech, detection, analysis | `components/fx/scan_line.html` |
| 7 | AlertBorder | 脉动警告边框 + 四角标 | warning, urgency, critical | `components/fx/alert_border.html` |
| 8 | FloatParticles | 发光微粒向上漂浮 | calm, mystery, dreamy | `components/fx/float_particles.html` |
| 9 | LightStreak | 对角线光带快速扫过 | climax, dynamic, cinematic | `components/fx/light_streak.html` |
| 10 | DataStream | 垂直数据流（Canvas, 类 Matrix） | tech, data, AI | `components/fx/data_stream.html` |
| 11 | Constellation | 星座网络（发光节点 + 邻近连接线 + 漂移） | tech, network, connection | `components/fx/constellation.html` |
| 12 | Vortex | 能量漩涡（开普勒螺旋粒子 + 星轨拖尾） | energy, immersion, dynamic | `components/fx/vortex.html` |
| 13 | Lightning | 分形闪电（递归分支 + 双层辉光 + 闪光） | shock, dramatic, climax | `components/fx/lightning.html` |

### 内容层 (content/)

> 嵌入 `.layer-content`，承载文字、数据、卡片等信息。一个场景选 1-2 个 content 组件。

| # | 组件名 | 一句话描述 | 适用场景类型 | 文件路径 |
|---|--------|-----------|-------------|---------|
| 1 | HeroCard | 项目首屏展示，震撼开场 | hook, intro | `components/content/hero_card.html` |
| 2 | StarCounter | Star 数动态计数动画 | stats, reveal | `components/content/star_counter.html` |
| 3 | CompareSplit | 双栏对比布局 | compare, versus | `components/content/compare_split.html` |
| 4 | TimeLineFlow | 时间线叙事（节点依次出现） | timeline, history | `components/content/timeline_flow.html` |
| 5 | DataViz | 数据可视化柱状图卡片 | data, stats | `components/content/data_viz.html` |
| 6 | TextReveal | 文字揭示动画（悬念展示） | reveal, surprise | `components/content/text_reveal.html` |
| 7 | ProjectFullCard | 标准模式单项目全屏 9 层卡片（含 owner avatar） | project-card, listing | `components/content/project_full_card.html` |
| 8 | VerdictBox | 核心结论框（border-left 高亮 + 标签） | conclusion, summary, thesis | `components/content/verdict_box.html` |
| 9 | NumGrid | 2×2 数据矩阵（大数字网格） | data, stats, metrics | `components/content/num_grid.html` |
| 10 | MarketBars | 市场对比条（水平进度条，data-width 驱动） | market, growth, comparison | `components/content/market_bars.html` |
| 11 | ScoreCompare | 对比评分卡（A/B 双卡片 + WIN 徽章） | compare, versus, battle | `components/content/score_compare.html` |
| 12 | RecStrip | 三档推荐条（优先级排列 + 结论框） | recommendation, ranking, priority | `components/content/rec_strip.html` |
| 13 | CinematicTitle | 电影标题卡（水平展开 + 金线 + 光晕扫过） | opening, chapter, transition | `components/content/cinematic_title.html` |
| 14 | GlassCard | 毛玻璃卡片（blur + 光泽条 + 彩色边条） | feature, highlight, showcase | `components/content/glass_card.html` |
| 15 | CountdownReveal | 倒计时揭示（3-2-1 缩放 → 内容展开） | reveal, countdown, suspense | `components/content/countdown_reveal.html` |
| 16 | SplitStory | 分屏叙事（50/50 竖分屏 + 渐变分割线） | compare, before-after, story | `components/content/split_story.html` |
| 17 | NeonTitle | 霓虹灯标题（多层发光 + 呼吸亮度） | hook, announcement, tech | `components/content/neon_title.html` |
| 18 | QuoteBlock | 引用卡片（纪录片风格，装饰引号 + 署名） | quote, citation, expert-opinion | `components/content/quote_block.html` |
| 19 | LayeredCards | 层叠透视卡片（3D 倾斜 + 前清后虚） | listing, portfolio, showcase | `components/content/layered_cards.html` |
| 20 | SpotlightCard | 聚光灯卡片（径向聚焦 + 光束射线） | feature, key-point, highlight | `components/content/spotlight_card.html` |
| 21 | KineticText | 动态排版（逐字弹入，冲击力极强） | impact, statement, cta | `components/content/kinetic_text.html` |
| 22 | Breakthrough | 破屏而出（裂纹扩展 + 内容冲出） | reveal, breakthrough, climax | `components/content/breakthrough.html` |

## content 层规范（布局铺满 + 文字特效）

### 布局铺满铁律
竖屏 1080×1920，安全区可用 900×1520。content 组件**禁单列 `align-items:center; justify-content:center`**（垂直利用率仅 33%，元素挤画面正中）。按组件类型选布局：
- **full-page 型**（项目卡片/hook/结论等独占一屏）：`justify-content:space-between` 三带（顶/中/底）填满 1520px，参照 `project_full_card.html` 基准
- **分栏型**（对比/并列）：左右 50/50 或 grid 分割，内层 `space-between`/`flex-start`
- **内嵌型**（数据/列表）：column 顶对齐列表式，元素纵向铺开
- 组件**移除自带 padding**，让 BASE_CSS `.phase`（180/90/220/90）统一提供，避免双重 padding（render-safety.md）

### 文字特效配方（标题/数字必选 1 个）
content 层标题/数字/品牌字必须叠加文字特效。配方库见 `shared/text-effects.md`，含 4 核心（呼吸/渐变文字/跑马灯/3D）+ 5 扩展（故障/霓虹/打字机/流光/描边），每条含 HyperFrames 安全约束 + CSS/GSAP 模板。场景→特效速查：

| 场景 | 推荐特效 |
|------|---------|
| hook | 渐变文字 + 呼吸光晕 |
| 数据 | 渐变数字 + 呼吸强调 |
| 对比 | 描边 + 3D 翻转 |
| 结论 | 渐变标题 + 流光 |
| CTA | 渐变 + 呼吸 + 描边 |

完整表见 `shared/text-effects.md` §4。**同一视频特效组合要多样**（避免所有标题同一渐变角度）。

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

> 读内容，想画面，用工具箱实现，不碰红线。执行前读取 `shared/director-toolkit`。

### 设计格言（5 条正面引导）

① **内容为王**：特效是舞台灯光，不是演员。观众要看的是内容，特效让观众看得更舒服。
② **暗底亮光**：深色背景上，用光晕和辉度制造视觉焦点，不要大面积浅色块。
③ **层次分明**：背景沉下去，特效浮起来，内容站最前面。三层之间的亮度差就是深度感。
④ **克制即美学**：一个场景用 1-2 种特效就够了。堆砌不等于丰富，留白不等于空旷。
⑤ **每屏独一**：相邻场景的视觉风格必须有明显差异。观众不应该看到两个"差不多的画面"。

### 反面清单（10 条红线）

✗ **背景光晕 opacity < 0.15** — H.264 编码后完全消失，白做了
✗ **特效覆盖在内容文字上方** — 观众看不清内容，特效毫无意义
✗ **连续两个场景用同一种特效** — 视觉疲劳，观众觉得在看同一个画面
✗ **整个视频只用一种配色** — 像没调过色的监控画面
✗ **场景无 padding** — 内容贴边，手机端文字被裁切
✗ **layer-fx 为空** — 三层架构缺一层，等于没做特效
✗ **内容元素 CSS opacity: 0 入场** — HyperFrames 不执行 CSS animation，内容永远不可见
✗ **文字无 text-shadow** — 纯色文字在深色背景上需 text-shadow 增强可读性
✗ **全局 `*` 通配选择器设置 text-shadow** — 会污染渐变文字（background-clip:text），导致亮度骤降。text-shadow 只允许设在具体元素上
✗ **特效元素 opacity > 0.6** — 抢了内容的视觉权重，主次颠倒
✗ **一个场景堆 3+ 种特效** — 像 PowerPoint 动画集锦，不是专业视频

### 组件创建指南

当组件库中没有匹配当前场景视觉意图的特效时，创建新特效：

1. **从内容推导**：这段场景在说什么？观众该感受到什么？什么动态视觉能强化这个感受？
2. **选择技术实现**：
   - CSS + GSAP：光球、射线、渐变带、边框脉冲等（推荐，简单可靠）
   - Canvas + GSAP：粒子系统、代码雨、数据流等（适合复杂动态）
3. **遵守约束**：
   - CSS 初始状态必须可见（opacity ≥ 0.15）
   - 必须有 GSAP 动画（持续 `repeat:-1` 或入场 `.from()`）
   - 不依赖 CSS animation 做入场（HyperFrames seek 不执行）
4. **封装为组件**（可选，高质量的特效建议入库）：
   - 文件头添加 `@ComponentMeta`（name, layer, tags, emotion_range, description）
   - 更新 `registry.yaml`
   - 向用户展示样例 HTML，由用户决定是否入库
5. **GSAP 动画模板**：
   - 持续脉冲：`tl.to('#sN .fx-el', {scale:1.2, opacity:0.6, duration:2, repeat:-1, yoyo:true, ease:'sine.inOut'}, sceneStart)`
   - 持续漂浮：`tl.to('#sN .fx-el', {y:'-=30', duration:3, repeat:-1, yoyo:true, ease:'sine.inOut'}, sceneStart)`
   - 持续旋转：`tl.to('#sN .fx-el', {rotation:360, duration:8, repeat:-1, ease:'none'}, sceneStart)`
   - 入场动画：`tl.from('#sN .fx-el', {scale:0, opacity:0, duration:0.5, ease:'back.out(1.7)'}, sceneStart)`

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

- 角色通过 SVG 内联绘制（简易卡通风格），直接嵌入场景 HTML
- 一个视频内使用**同一个角色**（保持一致性）
- 角色大小约 120-150px，放在不遮挡核心内容的位置
- 角色带 idle 动画（idleBounce/idleSway/idleBreathe），保持画面活力

### 双轨道粒子规范 (DualOrbit)

> 双轨道嵌套结构：外层大范围慢漂（20-30s）+ 内层小范围微漂（8-12s），两条不同轨迹叠加产生流畅非重复运动。禁止单层粒子或固定颜色粒子。

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

### 通用背景动画 keyframes

> 以下 keyframes 被 6 个增强背景组件和新 7 个背景共享，使用前需写入 `<style>`。

```css
/* 漂浮粒子 — 背景装饰粒子上下漂移 */
@keyframes floatParticle {
  0%, 100% { transform: translateY(0) translateX(0); opacity: 0.4; }
  50% { transform: translateY(-50px) translateX(8px); opacity: 0.7; }
}
/* 辉光脉冲 — 中心辉光缩放+透明度呼吸 */
@keyframes glowPulse {
  0%, 100% { opacity: 0.6; transform: scale(1); }
  50% { opacity: 0.9; transform: scale(1.05); }
}
/* 光带呼吸 — 对角线/竖线透明度脉冲 */
@keyframes beamBreath {
  0%, 100% { opacity: 0.5; }
  50% { opacity: 0.8; }
}
/* 闪烁点 — 小圆点闪烁 */
@keyframes starDot {
  0%, 100% { opacity: 0.3; }
  50% { opacity: 0.6; }
}
/* 毛玻璃折射 — 微妙的光泽移动效果 */
@keyframes glassShimmer {
  0%, 100% { opacity: 0.15; }
  50% { opacity: 0.20; }
}
/* 棱镜色散呼吸 — 色散带透明度呼吸 */
@keyframes prismShimmer {
  0%, 100% { opacity: 0.15; }
  50% { opacity: 0.18; }
}
/* 噪点微移 — SVG 噪点纹理微小位移 */
@keyframes grainShift {
  0% { transform: translate(0, 0); }
  50% { transform: translate(-8px, 6px); }
  100% { transform: translate(0, 0); }
}
/* 尘埃浮沉 — 暗色场景微粒缓慢上浮 */
@keyframes dustFloat {
  0%, 100% { transform: translateY(0); opacity: 0.25; }
  50% { transform: translateY(-30px); opacity: 0.45; }
}
/* 暖色扩散环 — 从中心向外扩散渐隐 */
@keyframes warmRing {
  0% { transform: scale(0.9); opacity: 0.15; }
  100% { transform: scale(1.5); opacity: 0; }
}
/* 光晕扫描 — 水平光带缓慢横移 */
@keyframes lightStreak {
  0% { transform: translateX(-100%); }
  100% { transform: translateX(300%); }
}
/* 等高线漂移 — 副层等高线中心微移 */
@keyframes contourShift {
  0%, 100% { background-position: 0% 50%; }
  50% { background-position: 3% 48%; }
}
/* 等高线脉冲 — 主层等高线透明度呼吸 */
@keyframes contourPulse {
  0%, 100% { opacity: 0.7; }
  50% { opacity: 0.9; }
}
/* 光斑漂移 — 大型模糊光斑缓慢位移+缩放 */
@keyframes noiseDrift {
  0%, 100% { transform: translate(0, 0) scale(1); }
  33% { transform: translate(40px, -30px) scale(1.08); }
  66% { transform: translate(-25px, 35px) scale(0.94); }
}
/* 光束旋转 — 径向光束360度旋转 */
@keyframes beamRotate {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}
/* 扫描线 — 水平线从上到下移动 */
@keyframes scanLine {
  0% { top: -10%; }
  100% { top: 110%; }
}
/* 网格脉冲 — 网格透明度呼吸 */
@keyframes gridPulse {
  0%, 100% { opacity: 0.4; }
  50% { opacity: 0.7; }
}
/* 暗角脉冲 — 中心微光透明度呼吸 */
@keyframes vignettePulse {
  0%, 100% { opacity: 0.10; }
  50% { opacity: 0.16; }
}
/* 暖光呼吸 — 中心暖辉光缩放+透明度呼吸 */
@keyframes warmBreath {
  0%, 100% { transform: scale(1); opacity: 0.10; }
  50% { transform: scale(1.06); opacity: 0.18; }
}
/* 波纹扩散 — 同心圆环扩大渐隐 */
@keyframes rippleExpand {
  0% { transform: scale(0.8); opacity: 0.5; }
  100% { transform: scale(1.5); opacity: 0; }
}
/* 波纹呼吸 — 同心波纹图案透明度呼吸 */
@keyframes rippleBreath {
  0%, 100% { opacity: 0.5; }
  50% { opacity: 0.8; }
}
```

---

### AuroraFlow（极光流动）

4 条水平极光色带（绿/青/紫）缓慢流动 + 竖直射线丝 + 顶部光源 + 闪烁亮点。色带默认居中可见。

**CSS keyframes（全局）：**

```css
@keyframes auroraFlow {
  0%, 100% { transform: translateX(-8%) scaleY(1); }
  50% { transform: translateX(8%) scaleY(1.12); }
}
@keyframes auroraCurtain {
  0%, 100% { transform: scaleY(1) translateY(0); opacity: 0.5; }
  50% { transform: scaleY(1.15) translateY(-10px); opacity: 0.8; }
}
```

**HTML 模板（色带 + 射线 + 亮点 + 玻璃折射 + 棱镜色散）：**

```html
<div class="layer-bg">
  <!-- 深青黑底 -->
  <div style="position:absolute;inset:0;background:linear-gradient(180deg,hsl(200,30%,5%),hsl(180,25%,8%))"></div>
  <!-- 极光色带 -->
  <div style="position:absolute;top:15%;left:-10%;width:120%;height:180px;
    background:linear-gradient(90deg,transparent 5%,hsla(150,70%,45%,0.18),hsla(160,55%,40%,0.12),transparent 95%);
    filter:blur(45px);animation:auroraFlow 22s ease-in-out infinite 0s"></div>
  <div style="position:absolute;top:35%;left:-10%;width:120%;height:150px;
    background:linear-gradient(90deg,transparent 10%,hsla(180,60%,50%,0.16),hsla(170,50%,45%,0.10),transparent 90%);
    filter:blur(50px);animation:auroraFlow 26s ease-in-out infinite 4s"></div>
  <div style="position:absolute;top:55%;left:-10%;width:120%;height:160px;
    background:linear-gradient(90deg,transparent 8%,hsla(280,50%,50%,0.16),hsla(260,45%,40%,0.10),transparent 92%);
    filter:blur(55px);animation:auroraFlow 20s ease-in-out infinite 8s"></div>
  <!-- 顶部光源 -->
  <div style="position:absolute;top:-15%;left:15%;width:70%;height:250px;border-radius:50%;
    background:radial-gradient(ellipse at 50% 100%,hsla(155,65%,45%,0.18),hsla(170,50%,40%,0.08),transparent 70%);
    filter:blur(60px);animation:auroraCurtain 14s ease-in-out infinite"></div>
  <!-- 竖直射线丝 -->
  <div style="position:absolute;top:0;left:38%;width:2.5px;height:70%;
    background:linear-gradient(180deg,hsla(170,70%,52%,0.28),hsla(170,60%,45%,0.10) 35%,transparent 100%);
    filter:blur(1.5px);animation:auroraCurtain 7s ease-in-out infinite 2s"></div>
  <!-- 射线亮点 -->
  <div style="position:absolute;top:18%;left:37%;width:5px;height:5px;border-radius:50%;
    background:hsla(165,70%,60%,0.4);box-shadow:0 0 12px hsla(165,70%,55%,0.5);animation:starTwinkle 3s ease-in-out infinite"></div>
  <!-- 玻璃折射层 -->
  <div style="position:absolute;inset:0;
    background:linear-gradient(135deg,rgba(255,255,255,0.02) 0%,transparent 40%,rgba(255,255,255,0.03) 60%,transparent 100%);
    animation:glassShimmer 9s ease-in-out infinite"></div>
</div>
```

**参数：** 色带 3-4 条 / blur 40-55px / 周期 18-30s / 射线 5-7 条 / 射线高度 45%-70%

---

### HexGrid（蜂窝网格）

SVG 六边形蜂窝网格 + 翡翠绿辉光 + 脉冲呼吸。网格默认可见。

**CSS keyframes（全局）：**

```css
@keyframes hexPulse {
  0%, 100% { opacity: 0.5; }
  50% { opacity: 0.85; }
}
```

**HTML 模板（SVG 网格 + 辉光 + 玻璃折射 + 棱镜色散）：**

```html
<div class="layer-bg">
  <!-- 翡翠黑底 -->
  <div style="position:absolute;inset:0;background:linear-gradient(180deg,hsl(160,20%,4%),hsl(170,15%,8%),hsl(160,20%,4%))"></div>
  <!-- 六边形网格 SVG -->
  <svg style="position:absolute;inset:0;width:100%;height:100%;opacity:0.55" xmlns="http://www.w3.org/2000/svg">
    <defs>
      <pattern id="hexPat" width="56" height="100" patternUnits="userSpaceOnUse" patternTransform="scale(1.4)">
        <path d="M28 0 L56 16.7 L56 50 L28 66.7 L0 50 L0 16.7 Z" fill="none" stroke="hsla(155,70%,45%,0.12)" stroke-width="0.8"/>
        <path d="M28 33.3 L56 50 L56 83.3 L28 100 L0 83.3 L0 50 Z" fill="none" stroke="hsla(155,70%,45%,0.12)" stroke-width="0.8"/>
      </pattern>
    </defs>
    <rect width="100%" height="100%" fill="url(#hexPat)"/>
  </svg>
  <!-- 网格脉冲 -->
  <div style="position:absolute;inset:0;animation:hexPulse 7s ease-in-out infinite"></div>
  <!-- 中心翡翠辉光 -->
  <div style="position:absolute;top:30%;left:25%;width:500px;height:500px;border-radius:50%;
    background:radial-gradient(circle,hsla(150,80%,50%,0.22),hsla(155,60%,40%,0.08),transparent 70%);
    filter:blur(100px)"></div>
  <!-- 玻璃折射层 -->
  <div style="position:absolute;inset:0;
    background:linear-gradient(120deg,rgba(255,255,255,0.015) 0%,transparent 30%,transparent 70%,rgba(255,255,255,0.02) 100%);
    animation:glassShimmer 8s ease-in-out infinite"></div>
</div>
```

**参数：** 网格缩放 1.0-2.0 / 辉光尺寸 300-500px / 脉冲周期 5-12s

---

### NebulaCloud（星云宇宙）

3 团星云色团漂移 + 8 颗闪烁星点。色团默认居中可见。

**CSS keyframes（全局）：** 复用 `orbDrift`（见 LightField）+ `starTwinkle`（见 StarBurst）

**HTML 模板（色团 + 星点 + 玻璃折射 + 棱镜色散）：**

```html
<div class="layer-bg">
  <!-- 深紫黑底 -->
  <div style="position:absolute;inset:0;background:linear-gradient(160deg,hsl(260,25%,4%),hsl(240,20%,7%),hsl(255,22%,5%))"></div>
  <!-- 星云 1：深紫 -->
  <div style="position:absolute;top:15%;left:10%;width:500px;height:500px;border-radius:50%;
    background:radial-gradient(circle,hsla(280,60%,35%,0.16),hsla(270,45%,25%,0.06),transparent 70%);
    filter:blur(100px);animation:orbDrift 24s ease-in-out infinite 0s"></div>
  <!-- 星云 2：暗红 -->
  <div style="position:absolute;top:45%;left:45%;width:420px;height:420px;border-radius:50%;
    background:radial-gradient(circle,hsla(350,50%,30%,0.13),hsla(340,40%,22%,0.04),transparent 70%);
    filter:blur(90px);animation:orbDrift 28s ease-in-out infinite 6s"></div>
  <!-- 星云 3：深蓝 -->
  <div style="position:absolute;top:60%;left:5%;width:350px;height:350px;border-radius:50%;
    background:radial-gradient(circle,hsla(220,55%,35%,0.11),hsla(230,40%,25%,0.04),transparent 70%);
    filter:blur(85px);animation:orbDrift 22s ease-in-out infinite 12s"></div>
  <!-- 星点（6-8 颗） -->
  <div style="position:absolute;top:12%;left:65%;width:3px;height:3px;border-radius:50%;background:white;opacity:0.40;box-shadow:0 0 6px rgba(255,255,255,0.5);animation:starTwinkle 4s ease-in-out infinite 0s"></div>
  <div style="position:absolute;top:42%;left:78%;width:3px;height:3px;border-radius:50%;background:white;opacity:0.45;box-shadow:0 0 7px rgba(255,255,255,0.5);animation:starTwinkle 3.5s ease-in-out infinite 3s"></div>
  <!-- 玻璃折射层 -->
  <div style="position:absolute;inset:0;
    background:linear-gradient(135deg,rgba(255,255,255,0.015) 0%,transparent 35%,transparent 65%,rgba(255,255,255,0.02) 100%);
    animation:glassShimmer 10s ease-in-out infinite"></div>
</div>
```

**参数：** 色团 2-4 个 / blur 85-100px / 漂移周期 18-35s / 星点 6-12 颗

---

### EmberGlow（余烬暖光）

3 团余烬辉光上浮 + 漂浮火星粒子 + 对角暖光带 + 水平余烬纹。辉光默认底部可见。

**CSS keyframes（全局）：**

```css
@keyframes emberRise {
  0%, 100% { transform: translateY(0) scale(1); opacity: 0.16; }
  50% { transform: translateY(-40px) scale(1.08); opacity: 0.24; }
}
@keyframes emberFloat {
  0%, 100% { transform: translateY(0) translateX(0); opacity: 0.5; }
  50% { transform: translateY(-60px) translateX(10px); opacity: 0.8; }
}
@keyframes warmShift {
  0%, 100% { opacity: 0.15; }
  50% { opacity: 0.18; }
}
```

**HTML 模板（辉光 + 粒子 + 暖纹 + 暗角）：**

```html
<div class="layer-bg">
  <!-- 暖棕黑底 -->
  <div style="position:absolute;inset:0;background:linear-gradient(180deg,hsl(25,30%,4%),hsl(15,25%,7%))"></div>
  <!-- 余烬辉光 -->
  <div style="position:absolute;top:55%;left:15%;width:450px;height:450px;border-radius:50%;
    background:radial-gradient(circle,hsla(30,80%,50%,0.17),hsla(25,60%,40%,0.06),transparent 70%);
    filter:blur(100px);animation:emberRise 22s ease-in-out infinite 0s"></div>
  <div style="position:absolute;top:65%;left:50%;width:380px;height:380px;border-radius:50%;
    background:radial-gradient(circle,hsla(15,70%,45%,0.13),hsla(10,50%,35%,0.04),transparent 70%);
    filter:blur(85px);animation:emberRise 26s ease-in-out infinite 5s"></div>
  <!-- 对角暖光带 -->
  <div style="position:absolute;top:20%;left:-20%;width:140%;height:250px;
    background:linear-gradient(100deg,transparent 20%,hsla(30,70%,50%,0.06),hsla(20,60%,45%,0.04),transparent 80%);
    filter:blur(60px);transform:rotate(-8deg);animation:warmShift 12s ease-in-out infinite"></div>
  <!-- 漂浮火星粒子（3-5 颗） -->
  <div style="position:absolute;top:50%;left:20%;width:4px;height:4px;border-radius:50%;background:hsla(35,90%,65%,0.6);box-shadow:0 0 8px hsla(35,80%,55%,0.5);animation:emberFloat 6s ease-in-out infinite 0s"></div>
  <div style="position:absolute;top:45%;left:70%;width:3px;height:3px;border-radius:50%;background:hsla(40,80%,60%,0.55);box-shadow:0 0 7px hsla(40,70%,50%,0.45);animation:emberFloat 5s ease-in-out infinite 4s"></div>
  <!-- 水平余烬纹 -->
  <div style="position:absolute;top:58%;left:-5%;width:110%;height:3px;
    background:linear-gradient(90deg,transparent 10%,hsla(30,80%,55%,0.18) 40%,hsla(35,70%,50%,0.15) 60%,transparent 90%);
    filter:blur(2px)"></div>
  <!-- 暖色玻璃折射层 -->
  <div style="position:absolute;inset:0;
    background:linear-gradient(135deg,rgba(255,200,100,0.02) 0%,transparent 40%,rgba(255,180,80,0.025) 60%,transparent 100%);
    animation:glassShimmer 9s ease-in-out infinite"></div>
  <!-- 暖色暗角 -->
  <div style="position:absolute;inset:0;
    background:radial-gradient(ellipse at 50% 55%,transparent 35%,hsla(15,30%,3%,0.55) 100%)"></div>
</div>
```

**参数：** 辉光 2-4 个 / 粒子 3-8 颗 / 上浮周期 18-30s / 粒子周期 5-8s

---

### DiamondLattice（菱形网格）

45° 金色菱形网格 + 对角漂移 + 金色辉光。网格默认居中可见。

**CSS keyframes（全局）：**

```css
@keyframes latticeDrift {
  0%, 100% { transform: translate(0, 0); }
  50% { transform: translate(30px, 30px); }
}
```

**HTML 模板（菱形网格 + 辉光 + 玻璃折射 + 棱镜色散）：**

```html
<div class="layer-bg">
  <!-- 暖金黑底 -->
  <div style="position:absolute;inset:0;background:linear-gradient(135deg,hsl(40,20%,4%),hsl(30,15%,7%))"></div>
  <!-- 菱形网格（45° + -45° 交叉线） -->
  <div style="position:absolute;inset:0;animation:latticeDrift 24s ease-in-out infinite;
    background-image:
      repeating-linear-gradient(45deg,transparent,transparent 59px,hsla(40,70%,55%,0.055) 59px,hsla(40,70%,55%,0.055) 60px),
      repeating-linear-gradient(-45deg,transparent,transparent 59px,hsla(40,70%,55%,0.055) 59px,hsla(40,70%,55%,0.055) 60px);
    background-size:85px 85px"></div>
  <!-- 中心金色辉光 -->
  <div style="position:absolute;top:30%;left:25%;width:500px;height:500px;border-radius:50%;
    background:radial-gradient(circle,hsla(38,80%,50%,0.20),hsla(35,60%,40%,0.08),transparent 70%);
    filter:blur(90px)"></div>
  <!-- 暖色玻璃折射层 -->
  <div style="position:absolute;inset:0;
    background:linear-gradient(135deg,rgba(255,220,150,0.02) 0%,transparent 40%,rgba(255,200,120,0.025) 60%,transparent 100%);
    animation:glassShimmer 8s ease-in-out infinite"></div>
</div>
```

**参数：** 网格间距 40-80px / 线透明度 0.03-0.10 / 漂移周期 18-35s

---

### ElectricPulse（电脉冲）

旋转锥形光弧 + 能量核心 + 脉冲环扩散 + 暗角聚焦。核心默认可见。

**CSS keyframes（全局）：**

```css
@keyframes arcRotate {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}
@keyframes pulseExpand {
  0% { transform: scale(0.85); opacity: 0.5; }
  100% { transform: scale(1.6); opacity: 0; }
}
@keyframes coreBreathe {
  0%, 100% { opacity: 0.28; transform: scale(1); }
  50% { opacity: 0.38; transform: scale(1.08); }
}
```

**HTML 模板（光弧 + 核心 + 脉冲环 + 暗角 + 玻璃折射）：**

```html
<div class="layer-bg">
  <!-- 深蓝黑底 -->
  <div style="position:absolute;inset:0;background:linear-gradient(160deg,hsl(220,25%,3%),hsl(200,20%,6%))"></div>
  <!-- 旋转锥形光弧 -->
  <div style="position:absolute;top:0;left:0;width:200%;height:200%;transform-origin:25% 17.5%;animation:arcRotate 45s linear infinite;
    background:conic-gradient(from 0deg,
      transparent 0deg,hsla(180,70%,50%,0.07) 25deg,transparent 50deg,
      transparent 90deg,hsla(185,65%,48%,0.05) 115deg,transparent 140deg,
      transparent 180deg,hsla(175,70%,50%,0.06) 205deg,transparent 230deg,
      transparent 270deg,hsla(190,60%,45%,0.04) 295deg,transparent 320deg)"></div>
  <!-- 能量核心 -->
  <div style="position:absolute;top:25%;left:25%;width:500px;height:500px;border-radius:50%;
    background:radial-gradient(circle,hsla(185,90%,60%,0.30),hsla(190,70%,45%,0.10),transparent 50%);
    filter:blur(60px);animation:coreBreathe 5s ease-in-out infinite"></div>
  <!-- 脉冲环（3 层，交错延迟） -->
  <div style="position:absolute;top:calc(35% - 80px);left:calc(35% - 80px);width:160px;height:160px;border-radius:50%;
    border:2px solid hsla(190,80%,55%,0.18);animation:pulseExpand 4s ease-out infinite 0s"></div>
  <div style="position:absolute;top:calc(35% - 80px);left:calc(35% - 80px);width:160px;height:160px;border-radius:50%;
    border:1.5px solid hsla(190,70%,50%,0.14);animation:pulseExpand 4s ease-out infinite 1.5s"></div>
  <div style="position:absolute;top:calc(35% - 80px);left:calc(35% - 80px);width:160px;height:160px;border-radius:50%;
    border:1px solid hsla(185,65%,48%,0.10);animation:pulseExpand 4s ease-out infinite 3s"></div>
  <!-- 暗角聚焦 -->
  <div style="position:absolute;inset:0;
    background:radial-gradient(ellipse at 50% 45%,transparent 25%,hsla(220,30%,2%,0.55) 80%,hsla(220,35%,2%,0.75) 100%)"></div>
  <!-- 玻璃折射层 -->
  <div style="position:absolute;inset:0;
    background:linear-gradient(150deg,rgba(255,255,255,0.02) 0%,transparent 30%,transparent 70%,rgba(255,255,255,0.025) 100%);
    animation:glassShimmer 7s ease-in-out infinite"></div>
</div>
```

**参数：** 光弧旋转周期 30-60s / 脉冲周期 3-6s / 核心强度 0.20-0.45

---

### CosmicPlanet（星空地球）

深空背景 + 星点群 + 银河带 + 地球（海洋/大陆/云层/冰盖/城市灯光/大气层蓝边）。地球默认可见。

**CSS keyframes（全局）：**

```css
@keyframes planetRotate {
  0% { background-position: 0% 50%; }
  100% { background-position: 200% 50%; }
}
@keyframes planetGlow {
  0%, 100% { opacity: 0.6; box-shadow: 0 0 60px hsla(200,60%,45%,0.15), inset 0 0 30px hsla(200,50%,40%,0.08); }
  50% { opacity: 0.8; box-shadow: 0 0 80px hsla(200,60%,45%,0.22), inset 0 0 40px hsla(200,50%,40%,0.12); }
}
```

**HTML 模板（太空底 + 银河 + 大气晕 + 地球 + 星点 + 玻璃折射）：**

```html
<div class="layer-bg">
  <!-- 深空底色 -->
  <div style="position:absolute;inset:0;background:linear-gradient(170deg,hsl(230,30%,3%),hsl(220,25%,5%),hsl(235,28%,3%))"></div>
  <!-- 银河带 -->
  <div style="position:absolute;top:30%;left:-20%;width:140%;height:120px;opacity:0.15;
    background:linear-gradient(100deg,transparent 10%,hsla(220,30%,50%,0.35),hsla(260,25%,45%,0.3),hsla(200,30%,50%,0.35),transparent 90%);
    filter:blur(50px);transform:rotate(-10deg)"></div>
  <!-- 大气层外晕 -->
  <div style="position:absolute;top:18%;left:38%;width:480px;height:480px;border-radius:50%;
    background:radial-gradient(circle,hsla(210,70%,55%,0.08),hsla(215,55%,42%,0.03),transparent 55%);
    filter:blur(30px);animation:planetGlow 8s ease-in-out infinite"></div>
  <!-- 地球本体 -->
  <div style="position:absolute;top:26%;left:46%;width:320px;height:320px;border-radius:50%;overflow:hidden;
    box-shadow:0 0 60px hsla(210,65%,50%,0.10),0 0 120px hsla(205,55%,40%,0.05);
    background:hsla(215,55%,12%,0.75)">
    <!-- 海洋底色 -->
    <div style="position:absolute;inset:0;border-radius:50%;
      background:radial-gradient(circle at 38% 35%,hsla(205,65%,32%,0.85) 0%,hsla(210,60%,25%,0.80) 40%,hsla(220,50%,15%,0.75) 75%,hsla(230,40%,8%,0.70) 100%)"></div>
    <!-- 大陆色块（background-size:200% + planetRotate 实现自转） -->
    <div style="position:absolute;inset:0;border-radius:50%;
      background:
        radial-gradient(ellipse 80px 65px at 22% 35%,hsla(100,35%,28%,0.38),hsla(120,30%,25%,0.20),transparent),
        radial-gradient(ellipse 50px 90px at 40% 50%,hsla(85,30%,25%,0.34),hsla(95,25%,22%,0.18),transparent),
        radial-gradient(ellipse 70px 45px at 55% 30%,hsla(35,40%,30%,0.32),hsla(40,35%,25%,0.16),transparent),
        radial-gradient(ellipse 55px 60px at 68% 55%,hsla(110,28%,26%,0.28),hsla(100,22%,20%,0.12),transparent);
      background-size:200% 100%;
      animation:planetRotate 35s linear infinite"></div>
    <!-- 云层 -->
    <div style="position:absolute;inset:0;border-radius:50%;
      background:
        radial-gradient(ellipse 90px 25px at 18% 40%,hsla(0,0%,100%,0.14),hsla(0,0%,95%,0.06),transparent),
        radial-gradient(ellipse 70px 20px at 50% 28%,hsla(0,0%,100%,0.12),transparent);
      background-size:200% 100%;
      animation:planetRotate 24s linear infinite"></div>
    <!-- 大气层蓝边 -->
    <div style="position:absolute;inset:-3px;border-radius:50%;
      background:radial-gradient(circle at 35% 32%,transparent 45%,
        hsla(210,70%,65%,0.16) 47%,hsla(205,65%,60%,0.25) 48.5%,hsla(200,60%,55%,0.12) 50%,transparent 52%)"></div>
    <!-- 暗面阴影 -->
    <div style="position:absolute;inset:0;border-radius:50%;
      background:linear-gradient(110deg,transparent 30%,hsla(225,35%,4%,0.45) 65%,hsla(230,40%,2%,0.60) 85%)"></div>
    <!-- 夜面城市灯光（4-6 颗暖色小点） -->
    <div style="position:absolute;top:38%;left:68%;width:2px;height:2px;border-radius:50%;background:hsla(45,80%,70%,0.35);box-shadow:0 0 4px hsla(45,70%,60%,0.28)"></div>
    <div style="position:absolute;top:50%;left:75%;width:1.5px;height:1.5px;border-radius:50%;background:hsla(50,80%,70%,0.28);box-shadow:0 0 3px hsla(50,70%,60%,0.20)"></div>
  </div>
  <!-- 星点群（12-20 颗，部分带闪烁） -->
  <div style="position:absolute;top:3%;left:10%;width:2px;height:2px;border-radius:50%;background:white;opacity:0.55;box-shadow:0 0 4px rgba(255,255,255,0.5);animation:starTwinkle 4s ease-in-out infinite 0s"></div>
  <div style="position:absolute;top:12%;left:72%;width:3px;height:3px;border-radius:50%;background:white;opacity:0.60;box-shadow:0 0 6px rgba(255,255,255,0.5);animation:starTwinkle 5s ease-in-out infinite 1s"></div>
  <div style="position:absolute;top:88%;left:80%;width:3px;height:3px;border-radius:50%;background:white;opacity:0.50;box-shadow:0 0 5px rgba(255,255,255,0.45);animation:starTwinkle 4.5s ease-in-out infinite 0.8s"></div>
  <!-- 玻璃折射层 -->
  <div style="position:absolute;inset:0;
    background:linear-gradient(135deg,rgba(255,255,255,0.01) 0%,transparent 35%,transparent 65%,rgba(255,255,255,0.015) 100%);
    animation:glassShimmer 10s ease-in-out infinite"></div>
</div>
```

**参数：** 地球尺寸 240-400px / 自转周期 25-50s / 云层周期 20-35s / 星点 12-25 颗

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
