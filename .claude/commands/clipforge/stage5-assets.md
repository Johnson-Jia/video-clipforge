# Stage 5: 视觉素材制备

当 `design.md` 已存在且 ppt-master 已安装时触发。搜索和制备视觉素材。可与音频阶段并行。

## 铁律：先复制再引用

**所有素材必须先复制到视频项目的 `assets/` 目录，再在 HTML 中引用。**

- ppt-master 的模板和图标在 `ppt-master/` 目录下，但 HyperFrames 渲染时工作目录是视频项目目录
- 直接引用 `ppt-master/` 的路径在渲染时**可能找不到文件**
- 正确做法：`cp ppt-master/skills/ppt-master/templates/charts/bar_chart.svg <project-dir>/assets/`
- 然后在 HTML 中写 `<img src="assets/bar_chart.svg">`

## 素材需求分析

根据 Stage 2 风格 + Stage 3 场景表，列出每个场景需要的视觉素材：

| 场景 | 需求类型 | 来源 | 用途 |
|------|---------|------|------|
| hook | 背景图 / 大图 | 图片搜索或 AI 生成 | 场景背景 |
| solution | 图标 | 图标库 | 功能标签 |
| features | 图表 / 截图 | 图表模板 | 数据展示 |
| cta | 图标 | 图标库 | 品牌标识 |

## 5.1 图片搜索

调用 ppt-master 的 `image_search.py` 搜索免费图片：

```bash
PPT_ROOT="ppt-master/skills/ppt-master"
python "$PPT_ROOT/scripts/image_search.py" "搜索关键词" \
  --filename scene_bg \
  -o <project-dir>/assets/ \
  --provider pexels \
  --orientation portrait
```

输出直接到项目的 `assets/` 目录，无需额外复制。

**参数说明：**
- `--provider`: `pexels`（推荐）/ `pixabay` / `openverse` / `wikimedia`
- `--orientation`: `portrait`（竖屏）/ `landscape` / `square`
- `--filename`: 输出文件名（不含扩展名）
- `-o`: 输出目录（默认项目 `assets/`）

## 5.2 AI 图片生成

当搜索不到合适的图片时，用 AI 生成：

```bash
python "$PPT_ROOT/scripts/image_gen.py" "描述性提示词，英文" \
  --aspect_ratio 9:16 \
  --backend gemini \
  -o <project-dir>/assets/ \
  -f generated_bg
```

输出同样直接到项目的 `assets/` 目录。

**参数说明：**
- `--aspect_ratio`: `9:16`（竖屏）/ `16:9`（横屏）/ `1:1`
- `--backend`: `gemini`（推荐，免费）/ `openai` / `fal` / `siliconflow` / `zhipu` 等 14 种
- 提示词使用英文，描述具体场景和风格
- **AI 生成需要对应后端的 API Key**，缺失时降级到图片搜索

## 5.3 图表模板

ppt-master 提供 67+ SVG 图表模板。

**原始路径：** `ppt-master/skills/ppt-master/templates/charts/`

**常用模板：**

| 模板文件 | 用途 | 适合场景 |
|---------|------|---------|
| `bar_chart.svg` | 柱状图 | 数据对比 |
| `pie_chart.svg` / `donut_chart.svg` | 饼图/环形图 | 占比分析 |
| `line_chart.svg` | 折线图 | 趋势变化 |
| `funnel_chart.svg` | 漏斗图 | 转化流程 |
| `comparison_columns.svg` | 对比栏 | 优劣对比 |
| `feature_matrix_table.svg` | 功能矩阵 | 功能展示 |
| `gauge_chart.svg` | 仪表盘 | 指标展示 |
| `radar_chart.svg` | 雷达图 | 多维评估 |
| `timeline_horizontal.svg` | 水平时间线 | 发展历程 |
| `chevron_process.svg` | 流程步骤 | 流程说明 |

**使用步骤（三步）：**
1. **复制**：`cp ppt-master/skills/ppt-master/templates/charts/bar_chart.svg workspace/<project>/assets/`
2. **定制**：编辑 SVG XML，替换占位文字为真实数据（保留 SVG 结构）
3. **嵌入**：在 HTML 中 `<img src="assets/bar_chart.svg">` 或 inline SVG

## 5.4 图标库

5 套图标库，覆盖常用场景。

**原始路径：** `ppt-master/skills/ppt-master/templates/icons/`

| 图标集 | 风格 | 数量 | 适合场景 |
|-------|------|------|---------|
| `tabler-outline` | 线性简洁 | 900+ | 科技/教育类 |
| `tabler-filled` | 实心简洁 | 500+ | 强调/标签 |
| `phosphor-duotone` | 双色调 | 600+ | 现代/时尚 |
| `chunk-filled` | 块状填充 | 300+ | 活泼/年轻 |
| `simple-icons` | 品牌图标 | 200+ | 品牌展示 |

**使用步骤（三步）：**
1. **查找**：浏览 `ppt-master/skills/ppt-master/templates/icons/<icon-set>/` 目录
2. **复制**：`cp ppt-master/.../icons/tabler-outline/rocket.svg <project-dir>/assets/icons/`
3. **嵌入**：在 HTML 中 `<img src="assets/icons/rocket.svg">` 或 CSS mask

## 5.5 素材嵌入 HTML 的方式

| 方式 | 代码 | 适用场景 |
|------|------|---------|
| 背景图 | `background-image: url(assets/bg.jpg)` | 全屏场景背景 |
| `<img>` 标签 | `<img src="assets/chart.svg" />` | 图表/图标展示 |
| inline SVG | 直接粘贴 SVG 代码 | 需要 GSAP 逐元素动画控制时 |
| CSS mask | `mask-image: url(assets/icons/icon.svg)` | 图标作为遮罩 |

## 素材清单输出

完成素材制备后，生成 `<project-dir>/assets/manifest.md`：

```markdown
# 素材清单

## 图片
- scene1_bg.jpg (1080×1920) — Pexels 搜索 "cyberpunk city"
- scene3_chart.svg — 柱状图，展示 GitHub Stars（已定制数据）

## 图标
- rocket.svg (tabler-outline) — hook 场景
- star.svg (tabler-filled) — features 场景
```

**交付物：** 素材清单 + 所有素材文件在 `assets/` 就绪，进入 Stage 6。

---

## Red Flags（停止信号）

| 信号 | 说明 |
|------|------|
| 素材未复制到 `assets/` 就引用 | 渲染时工作目录是项目目录，外部路径会 404 |
| ppt-master 安装失败时仍尝试执行 | 应跳过本阶段，使用纯文字/色块/渐变风格 |

## Common Rationalizations（常见借口反驳）

| 借口 | 事实 |
|------|------|
| "直接用外部路径引用就行" | HyperFrames 渲染时工作目录是项目目录，外部路径不可达，素材会丢失 |
| "没有素材也没关系" | 本阶段为 optional，可以跳过。但决定执行就必须把素材复制到 `assets/` |
| "ppt-master 装不上也试试" | 安装失败应跳过本阶段，强行执行只会浪费时间 |
