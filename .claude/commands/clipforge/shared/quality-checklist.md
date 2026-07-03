---
name: quality-checklist
description: Stage 6 渲染前品质检查清单
---

# 渲染前品质检查清单

## §1 视觉三层

| # | 检查项 | 依据 |
|---|--------|------|
| 1 | bg 层 ≥ 2 种视觉元素类型（禁止纯 glow + grid 三件套） | render-safety |
| 2 | fx 层非空（R-R-008 HARD） | R-R-008 |
| 3 | 相邻场景 bg 风格可区分（R-R-010 HARD） | R-R-010 |
| 4 | 光晕效果到位 | render-safety |
| 5 | 卡片三栏布局 | render-safety |
| 6 | 配色方案区分度 | design.md |

## §2 布局与排版

| # | 检查项 | 依据 |
|---|--------|------|
| 7 | CTA 场景完整（关注引导 + 结尾） | stage6 |
| 8 | 字号达标（标题/正文/数据层级） | render-safety §3 |
| 9 | 安全区（1080×1920 内边距） | render-safety |
| 10 | 居中对齐（flexbox） | render-safety |

## §3 HyperFrames 集成

| # | 检查项 | 依据 |
|---|--------|------|
| 11 | `window.__hf` 存在（duration + seek） | R-S6-007 |
| 12 | 场景 id 映射正确（#sN 与 narration_segments.json 对应） | R-S6-008 |
| 13 | GSAP timeline 注册（`__timelines`） | R-S6-009 |
| 14 | 音频 `<audio>` 元素内嵌 | stage6 §6.13 |

## §4 安全禁令

| # | 检查项 | 依据 |
|---|--------|------|
| 15 | 无 `anim-in` 类（HyperFrames seek 不执行 CSS animation） | render-safety |
| 16 | 无 HTML 实体（`&amp;` `&lt;` 等） | render-safety |
| 17 | scene-wrap 有 padding | render-safety |
| 18 | 视觉密度合理（无过度空旷或拥挤） | design.md |
| 19 | 无多余 composition（只一个根 composition） | R-S6-009 |
| 20 | `.clip` 必须是 `inset:0`（禁止 top/right/bottom/left 偏移 → 黑边） | render-safety |

## §5 四轴诊断（软引导 / advisory，不阻塞渲染）

> 借鉴视觉叙事四轴（Block/Murch/Williams/McCloud），诊断「为什么像 PPT」。**advisory 非硬性**——快速播报可酌情，深度解析尽量满足。

| # | 检查项 | 杠杆 |
|---|--------|------|
| 21 | **视觉强度进程**（Block）：视觉密度/对比是否向高潮递进，还是全程均匀（平的视觉强度线 = PPT 签名） | 中 |
| 22 | **剪辑在论点完成处**（Murch）：场景断点是否落在旁白「一个想法完成」处（观众准备眨眼），而非机械段落边界 | 中 |
| 23 | **运动间距非线性**（Williams）：ease 是否用 EASE 预设（standard/tension/resolve/ambient），禁裸 `linear`（均匀间距 = PPT 运动根源，director_gate warn） | 高 |
| 24 | **转场多样**（McCloud）：相邻场景转场是否含 moment-to-moment（让节拍呼吸）/ aspect-to-aspect（游荡氛围），而非全是 action-to-action | 低 |
