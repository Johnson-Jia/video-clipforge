---
id: "clipforge.stage6-components"
description: Stage 6 视觉组件索引 — 13 个组件的文件路径和适用场景
version: "2.1.0"
type: REFERENCE
scope: SKILL
skill_ref: "clipforge.stage6-production"
---

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

> **参考材料：** 设计格言、特效模板（StarBurst/LightOrbs/GradientWave/MatrixRain）、双轨道粒子规范、沉浸模式配色速查、Phase 视觉模板、布局推导体系等详见 `stage6-components-ref.md`（按需读取）。
