# Stage 2: 内容分析与故事板设计

当内容摘要已整理且 `design.md` 不存在时触发。推导视觉风格方向、规划叙事结构和沉浸模式。

> **执行前读取 `shared/director-toolkit`**，用导演 5 个必答题驱动风格推导。

## 情绪提炼

| 维度 | 说明 |
|------|------|
| 主题 | 内容讲的是什么？ |
| 情绪基调 | 主要传递什么情感？ |
| 情绪弧线 | 开头→中间→结尾的情感变化 |
| 节奏感 | 短视频默认：紧凑 |
| 文化调性 | 东方古典 / 现代科技 / 自然清新 / 暗黑悬疑 / ... |

## 视觉风格

基于内容推导，不查表。**用户明确指定的优先。**

**黄金 3 秒视觉要求：** hook 场景必须是全片视觉最强画面——字号最大、对比最强、布局最精致、配色最优雅。`design.md` 的配色方向必须能支撑这种冲击力。详见 `shared/shared-rules` §5。

### 风格原则

① **风格服务内容**：读完内容感受它的调性，选择能放大这种调性的视觉风格——科技内容有未来感、商业内容有专业感、人文内容有温度感
② **深色做底亮色做刀**：深色背景让亮色元素更突出，这是短视频的黄金法则
③ **统一但不单调**：同一个视频内风格统一（配色体系、字体层级），但不同场景之间有足够的视觉差异

### 风格反面清单

✗ 科技内容配暖色生活风 → 观感割裂
✗ 全片只有一种色调 → 像监控画面
✗ hook 场景视觉最弱 → 观众直接划走
✗ 情感曲线全平或全满 → 无张力
✗ 字体超过 3 种 → 杂乱不专业

## 字体气质

> **读取 `shared/director-toolkit` 第 2 层「字体气质」+ `shared/font-palette`。** 字体气质由 Q1 情感内核推导，不查分类表。

字体是视觉风格的一部分，与配色一同决定。基于 Q1 选择标题字体气质，正文和数据固定：

1. **标题气质 = Q1 情感内核**
   - 震撼/骄傲/史诗 → 毛笔力量（Ma Shan Zheng）
   - 知识/文化/深度 → 衬线庄重（Noto Serif SC 900）
   - 紧凑/专业/利落 → 几何简洁（Inter 900）
   - 温暖/趣味/轻松 → 圆润亲和（ZCOOL QingKe HuangYou）
   - 理性/精准/极客 → 等宽极客（JetBrains Mono 800）
   - 文艺/诗意/柔软 → 细楷诗意（ZCOOL XiaoWei）
2. **正文 = 可读性优先**。中文项目用 Noto Sans SC，纯英文用 Inter
3. **数据 = 等宽体**。JetBrains Mono

选择写入 design.md 的 `fonts` 字段，含 `voice`（气质名）链接 Q1，供审查与一致性校验。

## 配乐方向

基于情绪基调确定配乐搜索关键词、风格和氛围。具体来源和下载方式见 Stage 4（§4.2 配乐）。

## 素材需求预判

预判哪些场景需要外部素材：

| 判断条件 | 建议 |
|---------|------|
| 内容含数据对比 | 准备图表（纯 CSS/HTML 实现） |
| 内容含功能列表 | 准备图标（emoji 或 HTML 内联图标） |
| 场景需要氛围感 | 使用 CSS 渐变/光效背景 |
| 纯文字/概念展示 | 无需额外素材，纯 CSS 渐变即可 |

## 故事板设计

在完成上述分析后，规划视频的叙事结构、情感节奏和沉浸模式。输出到 `design.md` 的 `storyboard` 字段。

### 叙事模板选择

根据内容自然选择叙事结构——有对比就用对比弧，有悬念就用揭秘弧，无明确匹配时用默认弧。分类配置有 `narrative.default_template` 时优先使用。

| 模板 | 情感弧线 |
|------|----------|
| `contrast-arc` | 平淡 → 对比 → 震撼 → 高潮 → 沉淀 |
| `underdog` | 低谷 → 逆境 → 逆袭 → 胜利 |
| `showdown` | 紧张 → 交锋 → 揭晓 → 结论 |
| `mystery-box` | 好奇 → 线索 → 揭示 → 惊喜 |
| `hyper-pace` | 快速 → 密集 → 爆发 → 呼吸 |
| `story-time` | 平静 → 转折 → 深情 → 共鸣 |

### 沉浸模式判定

根据分类配置的 `immersion_mapping` 或内容标签自动选择。6 种模式的配色速查见 `stage6-components.md`。

### 6 拍情感节奏

视频按 6 个情感节拍规划：**grab（好奇）→ build（期待）→ reveal（惊喜）→ climax（激动）→ settle（思考）→ summon（行动）**。时长分配由内容决定，不套固定比例。

`emotion_curve` 是一个 6 元素数组，值域 [0,1]，表示每个节拍的情感强度。示例：`[0.3, 0.5, 0.8, 1.0, 0.6, 0.4]`。各阶段根据节拍名称自主推导视觉方法，不查表。

### 角色出场规划

如果分类配置 `character_presence` 为 true：
- `character_presence: true` 写入 design.md
- 记录角色出场时机：高潮段（climax）必出，幽默段（tease）可选
- 表情规划跟随 storyboard，不在 Stage 2 确定具体表情

**交付物：** 展示「视觉风格」（含字体气质）、「配乐方向」、「素材需求预判」、「故事板设计」和「画布方向（默认 portrait）」，确认后**写入 `design.md`** 并进入 Stage 3。

> **design.md 归属：Stage 2 负责写入。** Stage 6 仅读取此文件，不重写。如需调整风格，回退到 Stage 2 重新生成。

## design.md 格式规范（扩展）

Stage 2 产出的 `design.md` 是**方向性规范**，定义视觉风格方向、情绪基调和故事板。具体配色、字号、间距由 Stage 6 根据场景类型和组件库自行决定。

```yaml
# design.md — 视觉风格方向 + 故事板

## 风格
style: 科技赛博        # 风格名称（中文）
mood: 激烈紧凑          # 情绪基调

## 配色方向（描述性，不指定具体色值）
color_direction:
  background: 深色暗调（接近纯黑）
  accent_cool: 霓虹青/翠绿（用于 features/more 场景）
  accent_warm: 金色/琥珀（用于 hook/CTA 场景）
  text: 白色主 + 浅灰辅

## 字体（三层 + voice 链接 Q1）
fonts:
  title:
    voice: "毛笔力量"          # 气质名（链接 Q1 情感内核，便于审查）
    family: "Ma Shan Zheng"
    weight: 400
    rationale: "震撼的情感内核需要力量感的标题字体"
    fallback: "'Ma Shan Zheng','PingFang SC','Microsoft YaHei',cursive"
  body:
    family: "Noto Sans SC"
    weight: 400
    fallback: "'Noto Sans SC','PingFang SC','Microsoft YaHei',sans-serif"
  data:
    family: "JetBrains Mono"
    weight: 700
    fallback: "'JetBrains Mono','Consolas',monospace"

## 配乐方向
music_mood: 科技/赛博

## 素材预判（可选）
assets_needed: []       # 如需外部素材在此列出，否则留空

## 故事板（新增）
storyboard:
  narrative_template: "contrast-arc"    # 6 选 1
  emotion_curve: [0.3, 0.5, 0.8, 1.0, 0.6, 0.4]
  immersion_mode: "hyper-pace"          # 6 选 1
  humor_style: "dual-track"             # dual-track / narration-only / visual-only
  character_presence: true              # 是否启用码力角色
  beat_mapping:                         # 节拍 → 场景映射（大致分配）
    grab: "hook"
    build: "what, how"
    reveal: "capabilities"
    climax: "features"
    settle: "usecases, tech"
    summon: "CTA"

## 方向（新增）
orientation: portrait   # portrait | landscape
orientation_source: default  # default | user_explicit | category_hint
```

> **beat_mapping 说明：** 这是场景到情感节拍的粗映射，帮助 Stage 3 和 Stage 6 理解每个场景应传递的情感。不是严格约束，Stage 3 可以调整。

> **design.md 定位：** 方向性指导，不包含具体色值/字号/间距。Stage 6 根据 `style`、`color_direction`、`orientation`、`immersion_mode` 和 `fonts` 选择对应的组件、配色和字体（字体加载参数见 `shared/font-palette`），Stage 7 封面复用同一风格方向（封面字体有独立规则，不复用 `fonts`）。

> **orientation 判定逻辑（Stage 2）：**
> 1. 若用户明确指定方向（inject 参数或 prompt 上下文中的方向关键词）→ 写入用户指定值 + `orientation_source: user_explicit`
> 2. 若分类配置有 `orientation_hint`（render_stage 已注入到模板）→ 写入 hint 值 + `orientation_source: category_hint`
> 3. 以上均无 → 写入 `portrait` + `orientation_source: default`
>
> 默认竖屏。仅在用户明确指定或分类配置要求时才使用横屏。

---

## 约束声明

> 本阶段的结构化约束（HARD/SOFT 规则 + Guard Red Flags）由引擎注入提供。执行前运行 `python engine/inject.py --skill stage2-analysis` 获取完整约束 prompt。
