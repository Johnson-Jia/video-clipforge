# Stage 5: 视觉素材制备（可选）

当 `design.md` 已存在时触发。本阶段为可选阶段，大部分视频可完全跳过 — HyperFrames HTML 纯代码渲染已能覆盖绝大多数视觉效果。

## 视觉实现方式

ClipForge 视频采用 **纯 CSS/HTML** 渲染，不依赖外部图片素材：

| 需求类型 | 实现方式 | 适用场景 |
|---------|---------|---------|
| 背景氛围 | CSS 渐变 + radial-gradient 光效 | 所有场景 |
| 图表 | HTML/CSS 绘制（flex 布局柱状图、conic-gradient 饼图） | 数据对比 |
| 图标 | emoji 或 Unicode 符号 | 功能标签 |
| 动效 | GSAP / CSS animation | 转场、高亮 |

## 何时需要本阶段

仅在以下情况需要手动制备素材：

- 用户提供了自有图片/视频素材需要嵌入
- 需要 CSS 无法实现的复杂图表（可内联 SVG）
- 特定品牌 logo 需要显示

**交付物：** 如有素材，放入 `<project-dir>/assets/` 并在 HTML 中用 `<img src="assets/...">` 引用。无需素材则跳过本阶段，直接进入 Stage 6。

---

> 本阶段的结构化约束（HARD/SOFT 规则 + Guard Red Flags）由引擎注入提供。执行前运行 `python engine/inject.py --skill stage5-assets` 获取完整约束 prompt。

## Red Flags（停止信号）

| 信号 | 说明 |
|------|------|
| 素材未复制到 `assets/` 就引用 | 渲染时工作目录是项目目录，外部路径会 404 |

## Common Rationalizations（常见借口反驳）

| 借口 | 事实 |
|------|------|
| "没有素材也没关系" | 本阶段为 optional，可以跳过。纯 CSS 渐变和光效已能呈现高质量视觉效果 |
