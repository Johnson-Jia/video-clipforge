# 组件推导系统设计：内容驱动匹配 + 特效工坊

> 日期：2026-05-29
> 状态：已确认，待实施

## 背景

ClipForge 当前组件库（19 个）是扁平结构，缺少结构化的内容→组件匹配机制，也没有新特效的规范化创建和入库流程。导演在 Design→Scenes→Production 三个视觉决策节点介入，特效应跟随导演的情感意图和视觉逻辑，确保画面合理性与连贯性。

## 核心原则

1. **三层分离**：组件按 layer-bg / layer-fx / layer-content 分目录管理
2. **意图与实现分离**：Stage 3 只记录 visual_intent（意图），Stage 6 特效工坊负责匹配和实现
3. **内容推导，不查表**：匹配算法辅助，但最终由 AI 从内容语义推导视觉表达
4. **手动模式有交互，自动模式无阻塞**：手动模式走预览选择，自动模式 AI 直接使用

## 1. 组件目录重组

### 三层目录结构

```
components/
├── bg/                    ← 背景层组件
│   ├── gradient_mesh.html      渐变网格
│   ├── light_field.html        光场（双光晕背景）
│   └── ...
├── fx/                    ← 特效层组件
│   ├── starburst.html          星光绽放
│   ├── light_orbs.html         光球漂浮
│   ├── gradient_wave.html      渐变波
│   ├── matrix_rain.html        矩阵雨
│   ├── dual_orbit.html         双轨道粒子
│   ├── code_rain.html          代码雨（Canvas）
│   ├── pulse_orb.html          脉冲光球
│   ├── particle_burst.html     粒子爆发
│   ├── spectrum.html           冲击光谱
│   └── ...
├── content/               ← 内容层组件
│   ├── hero_card.html          首屏震撼卡片
│   ├── star_counter.html       Star 计数动画
│   ├── compare_split.html      双栏对比
│   ├── timeline_flow.html      时间线叙事
│   ├── data_viz.html           数据可视化
│   ├── text_reveal.html        文字揭示
│   ├── speech_bubble.html      吐槽气泡
│   ├── char_overlay.html       角色覆盖层
│   ├── project_full_card.html  项目全屏卡片
│   ├── verdict_box.html        结论框
│   ├── num_grid.html           数据矩阵
│   ├── market_bars.html        市场对比条
│   ├── score_compare.html      对比评分卡
│   ├── rec_strip.html          推荐条
│   └── ...
└── registry.yaml          ← 统一元数据索引
```

### 现有组件迁移映射

| 现有文件 | 目标层 | 新路径 |
|---------|--------|--------|
| hero_card.html | content | content/hero_card.html |
| star_counter.html | content | content/star_counter.html |
| compare_split.html | content | content/compare_split.html |
| timeline_flow.html | content | content/timeline_flow.html |
| data_viz.html | content | content/data_viz.html |
| text_reveal.html | content | content/text_reveal.html |
| speech_bubble.html | content | content/speech_bubble.html |
| char_overlay.html | content | content/char_overlay.html |
| project_full_card.html | content | content/project_full_card.html |
| verdict_box.html | content | content/verdict_box.html |
| num_grid.html | content | content/num_grid.html |
| market_bars.html | content | content/market_bars.html |
| score_compare.html | content | content/score_compare.html |
| rec_strip.html | content | content/rec_strip.html |
| code_rain.html | fx | fx/code_rain.html |
| pulse_orb.html | fx | fx/pulse_orb.html |
| particle_burst.html | fx | fx/particle_burst.html |
| three_scene.html | fx | fx/three_scene.html |
| spectrum.html | fx | fx/spectrum.html |

背景层组件（gradient_mesh、light_field）从现有 stage6-components.md 的 CSS 特效参考库中提取为独立 HTML 文件。

### 组件元数据格式

每个组件文件头部内嵌 HTML 注释格式的元数据：

```html
<!--
@ComponentMeta
name: starburst
layer: fx
tags: [celebration, climax, energy, radiate, rays]
emotion_range: [pride, excitement, triumph]
visual_density: medium
complexity: css-only
description: 从画面中心向外的装饰射线 + 闪烁点，适合高潮/庆祝时刻
parameters:
  ray_count: { default: 7, range: [6, 12] }
  ray_opacity: { default: 0.6, range: [0.4, 0.7] }
  twinkle_count: { default: 5, range: [4, 8] }
/ComponentMeta
-->
```

**元数据字段说明：**

| 字段 | 类型 | 说明 |
|------|------|------|
| name | string | 组件唯一标识（kebab-case） |
| layer | enum | bg / fx / content |
| tags | string[] | 适用场景标签，用于粗筛交集匹配 |
| emotion_range | string[] | 适配的情绪范围 |
| visual_density | enum | low / medium / high |
| complexity | enum | css-only / canvas / threejs |
| description | string | 自然语言描述，用于 AI 精排 |
| parameters | object | 可调参数定义（含默认值和范围） |

### registry.yaml

由脚本从组件文件头部元数据自动生成/同步，提供粗筛所需的快速查询能力。格式：

```yaml
components:
  - name: starburst
    layer: fx
    file: fx/starburst.html
    tags: [celebration, climax, energy, radiate, rays]
    emotion_range: [pride, excitement, triumph]
    visual_density: medium
    complexity: css-only
  # ...
```

## 2. 匹配算法

### 输入：visual_intent

Stage 3 在 `narration_segments.json` 中为每个场景新增 `visual_intent` 字段：

```json
{
  "scene": "s2-stats",
  "text": "这个项目已经获得了 15,000 颗星...",
  "visual_phases": ["..."],
  "visual_intent": {
    "bg": {
      "mood": "data-driven, cool, professional",
      "color_hint": "deep blue to dark gradient",
      "density": "standard"
    },
    "fx": {
      "emotion": "pride, growth, momentum",
      "motion_style": "upward, expanding",
      "complexity": "css-only"
    },
    "content": {
      "visual_type": "data",
      "focus": "star count growth",
      "layout_hint": { "density": "compact" }
    }
  }
}
```

**关键原则：** `visual_intent` 只记录意图（导演想表达什么），不记录实现（用什么组件）。

### 粗筛：结构化元数据过滤

对每个场景的每一层，从该层组件池中筛选：

1. **layer 过滤** — 只在目标层的组件池内搜索
2. **tags 交集** — 场景标签与组件标签有交集的保留
3. **emotion_range 匹配** — 场景情感落入组件情绪范围的保留
4. **complexity 筛选** — 场景标记 css-only 则排除 Canvas/Three.js 组件

粗筛输出：每个场景 × 每层 → 0~N 个候选组件。

### 精排：AI 语义理解

AI 读取以下上下文：

- 场景的完整 `visual_intent`（包含自然语言描述）
- 粗筛候选组件的 `description` + HTML 模板
- 相邻场景已选组件（避免视觉重复）

精排输出：

- **匹配成功** → 选择最佳组件 + 参数变体建议，写入 `component_manifest.md`
- **匹配失败** → 标记该场景 × 该层为「需要新特效」，进入特效工坊

### 跨场景连贯性检查

匹配完成后，对所有场景的组件方案做全局检查：

- 相邻场景背景渐变不重复
- 特效层无连续相同组件
- 配色方案在相邻场景间有足够区分度
- 不通过则自动调整参数变体或替换组件

### component_manifest.md 格式

```markdown
# 视觉组件清单

## s1-hook
| 层 | 组件 | 来源 | 参数变体 |
|---|------|------|---------|
| bg | light_field | library | accent=#FFB800, blur=160px |
| fx | starburst | library | ray_count=8, opacity=0.55 |
| content | hero_card | library | — |

## s2-stats
| 层 | 组件 | 来源 | 参数变体 |
|---|------|------|---------|
| bg | gradient_mesh | library | direction=dark-to-warm |
| fx | matrix_rain | library | line_count=10 |
| content | data_viz | **new** | 自定义：环形进度图 |

## 跨场景检查
- ✅ 相邻场景背景渐变不重复
- ✅ 特效层无连续相同组件
- ⚠️ s4/s5 配色接近，已调整 s5 accent 色相 +30
```

`来源` 列：`library`（现有组件）或 `new`（需要创建）。

## 3. 特效工坊（Stage 6 前置子流程）

### 触发条件

Stage 6 正式开始时，检测 `component_manifest.md` 是否存在 `new` 条目：

- 无 `new` → 跳过工坊，直接进入 HTML 编写
- 有 `new` → 启动特效工坊

### 工坊流程

```
读取 component_manifest.md 中所有 new 条目
  │
  ├─ 按场景逐个处理：
  │    1. 读取该场景的 visual_intent
  │    2. 读取已匹配的 library 组件（确保新特效与已有方案协调）
  │    3. AI 推导新特效的 CSS/Canvas/Three.js 实现
  │    4. 生成样本 HTML（独立文件，可单独预览）
  │
  ├─ 批量预览（手动模式）：
  │    ├─ 纯 CSS 特效 → 浏览器打开样本 HTML
  │    ├─ Canvas/Three.js 特效 → npx hyperframes render 渲染为短视频片段
  │    ├─ 用户逐个查看 → 标记「使用/不使用/入库/不入库」
  │    └─ 用户不满意 → AI 调整参数/重新推导 → 重新预览（最多 3 轮）
  │
  ├─ 自动模式：
  │    └─ AI 直接选择并使用，不暂停预览
  │
  └─ 工坊输出：
       ├─ 确认的 new 组件 → 写入 components/{layer}/ 目录
       ├─ 用户勾选入库的 → 更新 registry.yaml + 组件文件头元数据
       ├─ component_manifest.md 中 new → 替换为实际组件名
       └─ 继续进入 Stage 6 正式 HTML 编写
```

### 样本 HTML 规范

每个样本是独立可运行的文件，固定结构：

```html
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <!-- @ComponentMeta 元数据 -->
  <style>
    body { margin:0; width:1080px; height:1920px; background:#0a0a0a; }
    /* 组件 CSS（遵守渲染安全约束）*/
  </style>
</head>
<body>
  <div class="preview-canvas">
    <!-- 目标层的实际效果 -->
    <!-- 其他层用占位符（灰色方块 + 标签） -->
  </div>
</body>
</html>
```

预览时只展示目标层效果，其他层用占位符，让用户聚焦判断特效本身是否合适。

### 工坊文件位置

```
workspace/<YYYY>/<MM>/<DD>/<project>/
├── component_manifest.md        ← 工坊输入
├── fx_workshop/                  ← 工坊临时目录
│   ├── sample_s2_content.html
│   ├── sample_s5_bg.html
│   └── sample_s7_fx.html
└── ...                           ← 工坊完成后继续 Stage 6
```

`fx_workshop/` 由 cleanup 阶段清理，已入库的组件已复制到 `components/`。

## 4. Stage 3 变更

### 新增 visual_intent 字段

在 `narration_segments.json` 每个场景中新增 `visual_intent`，由导演 5 个必答题推导得出：

```json
"visual_intent": {
  "bg": {
    "mood": "<情感氛围的自然语言描述>",
    "color_hint": "<配色方向>",
    "density": "<compact/standard/generous>"
  },
  "fx": {
    "emotion": "<情感内核关键词>",
    "motion_style": "<运动方向/风格>",
    "complexity": "<css-only/canvas/threejs>"
  },
  "content": {
    "visual_type": "<hero/list/data/compare/timeline/highlight>",
    "focus": "<内容焦点>",
    "layout_hint": { "density": "<compact/standard/generous>" }
  }
}
```

Stage 3 不碰组件，不碰实现，只记录意图。

## 5. 模式差异

| 环节 | 手动模式 | 自动模式 |
|------|---------|---------|
| Stage 3 visual_intent | AI 推导 | 相同 |
| 组件匹配 | AI 匹配 | 相同 |
| 工坊预览 | 创建样本 → 用户预览选择 → 入库 | 跳过预览，AI 直接使用 |
| 入库 | 用户勾选 | 写入 `auto_candidates/{layer}/` 待下次手动模式审阅 |
| component_manifest | 用户确认后锁定 | AI 直接锁定 |

### 自动模式候选入库机制

AI 认为值得复用的特效写入 `components/auto_candidates/{layer}/`（与 bg/fx/content 同级），不进入正式组件库。下次手动模式时，如果匹配到候选组件，提示用户「这是一个自动模式创建的候选组件，是否正式入库？确认后移动到对应层的正式目录」。

## 影响范围

| 文件 | 变更类型 |
|------|---------|
| `components/` 目录结构 | 重组：扁平 → 三层子目录 |
| `stage6-components.md` | 更新组件索引表，指向新路径 |
| `stage6-production.md` | 新增 §6.4b 特效工坊子流程 |
| `clipforge/stages/stage3-scenes.md` | 新增 visual_intent 记录步骤 |
| `clipforge/shared/visual-phasing.md` | 更新组件引用路径 |
| `registry.yaml` | 新增文件 |
| 现有 19 个组件文件 | 迁移到新目录 + 补充元数据头 |
| `clipforge/schema.yaml` | 无变更（不新增 stage） |
