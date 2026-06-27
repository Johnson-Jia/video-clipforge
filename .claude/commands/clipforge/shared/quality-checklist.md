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
