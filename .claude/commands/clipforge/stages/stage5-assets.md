# Stage 5: 视觉素材制备（可选 / 深度解析必做架构图）

当 `design.md` 已存在时触发。大部分视频可跳过，但**深度解析模式必做技术架构图素材**（见下「技术架构图素材」段）。

## 视觉实现方式

ClipForge 视频采用 **纯 CSS/HTML** 渲染，不依赖外部图片素材：

| 需求类型 | 实现方式 | 适用场景 |
|---------|---------|---------|
| 背景氛围 | CSS 渐变 + radial-gradient 光效 | 所有场景 |
| 图表 | HTML/CSS 绘制（flex 布局柱状图、conic-gradient 饼图） | 数据对比 |
| 图标 | emoji 或 Unicode 符号 | 功能标签 |
| 动效 | GSAP / CSS animation | 转场、高亮 |

## 技术架构图素材（深度解析模式必做）

> 深度解析模式讲解技术架构时，**架构图必须做成专业 SVG 素材**（不是 HTML/CSS 即兴画）——更精美、符合技术人画图方式（分层框 + 模块 + 依赖箭头 + 数据流）。

**制作方式：LLM 直接生成 SVG**（推荐）
- 矢量精美、技术人标准格式、LLM 直写无需 mmdc/puppeteer 依赖（puppeteer 重、国内下载易失败）、HyperFrames 原生渲染 `<img src="*.svg">`
- 备选 Mermaid（文本→图，需装 mmdc；技术人熟悉语法，但风格固定、依赖重）

**SVG 架构图要素**（技术人画法）：
- 分层框（模块/层，带边框 + 层标签）
- 模块块（真实组件名，核心模块高亮）
- 依赖/调用箭头（连接关系，SVG marker 三角箭头）
- 数据流标注（核心流转路径）
- 配色：深色底 + 冷暖强调（与 `design.md` 一致），文字 ≥32px 等效可读

**输出**：`assets/arch.svg`（矢量，宽度适配竖屏 ~1000px），`manifest.md` 记录用途。

## 何时需要本阶段

仅在以下情况需要手动制备素材：

- 用户提供了自有图片/视频素材需要嵌入
- 需要 CSS 无法实现的复杂图表（可内联 SVG）
- 特定品牌 logo 需要显示

**交付物：** 如有素材，放入 `<project-dir>/assets/` 并在 HTML 中用 `<img src="assets/...">` 引用。无需素材则跳过本阶段，直接进入 Stage 6。

### manifest.md 生成

无论是否有素材，都必须生成 `manifest.md`（schema generates 声明要求）：

**有素材时**：
```bash
cat > assets/manifest.md << 'EOF'
# 素材清单

| 文件 | 用途 | 引用方式 |
|------|------|---------|
| logo.svg | 项目 logo | HTML `<img>` |
EOF
```

**无素材时**（最常见情况）：
```bash
mkdir -p assets && cat > assets/manifest.md << 'EOF'
# 素材清单

本视频未使用外部素材，全部视觉效果由 CSS/HTML/GSAP 实现。
EOF
```

---

> 本阶段的结构化约束（HARD/SOFT 规则 + Guard Red Flags）由引擎注入提供。执行前运行 `python engine/inject.py --skill stage5-assets` 获取完整约束 prompt。

## Red Flags（停止信号）

| 信号 | 说明 |
|------|------|
| 素材未复制到 `assets/` 就引用 | 渲染时工作目录是项目目录，外部路径会 404 |

