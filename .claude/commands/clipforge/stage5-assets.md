---
name: stage5-assets
description: 视觉素材制备（可选）— 制备 CSS 无法实现的外部视觉素材
version: "1.0.0"
type: EXECUTIVE
rigor: LITE
dependencies: ["clipforge.stage2-analysis"]
optional: true
---

# Stage 5: 视觉素材制备（可选）

## Intent
> 制备 CSS 无法实现的视觉素材（如外部图片、复杂 SVG、品牌 logo）。
> 成功标准：素材已放入 assets/ 目录，manifest.md 已创建。

> **注意：** 本阶段为可选阶段（schema.yaml `optional: true`）。大部分视频可完全跳过——HyperFrames HTML 纯代码渲染已能覆盖绝大多数视觉效果。

## Boundary — 行为准则

### 必须遵守（HARD 规则 · 正向重述）

1. **素材使用相对路径** — 所有素材复制到项目 `assets/` 目录后，用 `<img src="assets/...">` 引用 ← `R-STAGE5-001`
   ↳ 校验：HTML 中所有 img/video src 均为 assets/ 相对路径

### 建议参考（偏好）
- 大部分视频无需本阶段，纯 CSS/HTML 已能覆盖绝大多数视觉效果（HIGH）

## Guard — 认知守卫

| 当你产生这个念头 | 现实是 | 触发行为 |
|---|---|---|
| "素材未复制到 assets/ 就引用" | 渲染时工作目录是项目目录，外部路径会 404 | 先复制素材到 assets/，再引用 |

### Spirit vs Letter

| 规则 | 模式 | 真实意图 |
|---|---|---|
| R-STAGE5-001 | SPIRIT | 确保 HyperFrames 渲染时所有资源可通过相对路径访问 |

## Gate — 通过标准

### 流程门禁（自动化检查，不通过 = 驳回，max_retries: 0）
- [ ] `asset_manifest_exists` — `assets/manifest.md` 存在且列出所有素材文件

## Trace — 采集点
- **执行开始**：记录是否需要本阶段（大部分跳过）
- **执行结束**：记录素材文件数量、类型
- **写入**：`{project_dir}/trace/stage5-{timestamp}.yaml`

## 操作指令

### 视觉实现方式

ClipForge 视频采用 **纯 CSS/HTML** 渲染，不依赖外部图片素材：

| 需求类型 | 实现方式 | 适用场景 |
|---------|---------|---------|
| 背景氛围 | CSS 渐变 + radial-gradient 光效 | 所有场景 |
| 图表 | HTML/CSS 绘制（flex 布局柱状图、conic-gradient 饼图） | 数据对比 |
| 图标 | emoji 或 Unicode 符号 | 功能标签 |
| 动效 | GSAP / CSS animation | 转场、高亮 |

### 何时需要本阶段

仅在以下情况需要手动制备素材：

- 用户提供了自有图片/视频素材需要嵌入
- 需要 CSS 无法实现的复杂图表（可内联 SVG）
- 特定品牌 logo 需要显示

**交付物：** 如有素材，放入 `<project-dir>/assets/` 并在 HTML 中用 `<img src="assets/...">` 引用。无需素材则跳过本阶段，直接进入 Stage 6。

## Red Flags

| 信号 | 说明 |
|------|------|
| 素材未复制到 `assets/` 就引用 | 渲染时工作目录是项目目录，外部路径会 404 |

## Common Rationalizations

| 借口 | 事实 |
|------|------|
| "没有素材也没关系" | 本阶段为 optional，可以跳过。纯 CSS 渐变和光效已能呈现高质量视觉效果 |
