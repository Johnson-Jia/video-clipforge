# 视觉分镜（Visual Phasing）参考

> **当场景时长 >15 秒时必须使用。** 将一个 `.clip` 拆分为多个视觉阶段（phase），每 phase 8-15 秒，通过 GSAP timeline 控制渐进揭示。遵守 `shared/shared-rules` §6 的切换频率规则。

## 核心原理

```
改造前: 1 段旁白 ──→ 1 个 clip ──→ 1 个静态画面（30-57 秒不动）
改造后: 1 段旁白 ──→ 1 个 clip ──→ N 个 phase（每 phase 8-15 秒）
```

- 音频管线不变：旁白仍然是连续的 narration.mp3
- `.clip` 数量不变：仍然一个 narration segment 对应一个 clip
- phase 是 `.layer-content` 内的多个子 div，通过 GSAP opacity 控制显示/隐藏

## Phase HTML 结构

```html
<div class="clip s-biz-elderly" data-start="394" data-duration="50.14">
  <!-- scene-wrap 不设 padding — padding 由 .phase 统一管理（单层 padding 原则，见 shared/render-safety §1.4a） -->
  <div class="scene-wrap">
    <!-- 三层架构不变 -->
    <div class="layer-bg"><!-- 背景渐变 + 光晕 --></div>
    <div class="layer-fx"><!-- 特效 --></div>
    <!-- layer-content 内包含多个 phase（height:100% 必须有，否则 Phase 塌陷到顶部） -->
    <div class="layer-content" style="height:100%">
      <!-- Phase 1: CSS 默认 opacity:1，GSAP 入场动画。注意 padding 在 .phase 上 -->
      <div class="phase phase-1">
        <div class="phase-title">养老AI手环</div>
        <div class="feature-list">...</div>
      </div>
      <!-- Phase 2-4: CSS 默认 opacity:1，但 GSAP .set() 在 clip 起始时设为 opacity:0 -->
      <div class="phase phase-2"><!-- 定价数据 --></div>
      <div class="phase phase-3"><!-- 用户规模 --></div>
      <div class="phase phase-4"><!-- MVP路线图 --></div>
    </div>
  </div>
</div>
```

**关键规则：**
- 每个 `.phase` 用 `position: absolute; inset: 0` 全屏覆盖，自带 `padding: 180px 80px 220px 80px; display:flex; flex-direction:column; justify-content:center`，内容自动垂直居中（不需要手动加 inline flex）
- **scene-wrap 不设 padding** — padding 统一由 `.phase` 提供（单层 padding 原则）
- **禁止** scene-wrap 和 .phase 同时设置 padding（单层 padding 原则，见 render-safety §1.3）
- Phase 1 是 CSS 默认可见（opacity:1），遵守 `shared/render-safety.md` §1.1
- Phase 2+ **不在 CSS 中设 opacity:0**，由 GSAP `.set()` 在运行时初始化（遵守 §1.1a 豁免）
- 所有 phase 共享同一个 `.layer-bg` 和 `.layer-fx`（背景和特效不随 phase 切换）

## GSAP Phase 切换机制

```javascript
const SCENE_START = 394;   // clip 的 data-start

// Phase 1 入场动画（原有机制不变）
tl.from('.s-biz-elderly .phase-1 .phase-title', {opacity:0, y:20, duration:0.4}, SCENE_START)
  .from('.s-biz-elderly .phase-1 .feature-card', {opacity:0, y:15, duration:0.3, stagger:0.15}, SCENE_START + 0.5);

// 初始化 Phase 2-4 为不可见（GSAP .set，不是 CSS opacity:0）
tl.set('.s-biz-elderly .phase-2', {opacity: 0}, SCENE_START)
  .set('.s-biz-elderly .phase-3', {opacity: 0}, SCENE_START)
  .set('.s-biz-elderly .phase-4', {opacity: 0}, SCENE_START);

// Phase 1 → 2: 淡出旧 + 淡入新（使用内容对齐断点，禁止 PHASE_GAP 均分）
tl.to('.s-biz-elderly .phase-1', {opacity: 0, duration: 0.3}, SCENE_START + BP1)
  .to('.s-biz-elderly .phase-2', {opacity: 1, duration: 0.4}, SCENE_START + BP1 + 0.3);

// Phase 2 → 3
tl.to('.s-biz-elderly .phase-2', {opacity: 0, duration: 0.3}, SCENE_START + BP2)
  .to('.s-biz-elderly .phase-3', {opacity: 1, duration: 0.4}, SCENE_START + BP2 + 0.3);

// Phase 3 → 4
tl.to('.s-biz-elderly .phase-3', {opacity: 0, duration: 0.3}, SCENE_START + BP3)
  .to('.s-biz-elderly .phase-4', {opacity: 1, duration: 0.4}, SCENE_START + BP3 + 0.3);
```

**Phase 切换规则：**
- 上一个 phase 淡化到 `opacity: 0`（完全消失，避免与后续 phase 重叠产生重影）
- 新 phase 从 `opacity: 0` 渐显到 `opacity: 1`
- 过渡时长 0.3-0.4 秒
- **Phase 断点必须与旁白话题转换对齐，禁止均分**（见下方）
- Phase 间 GSAP 动画offset：`SCENE_START + BP[i][n-1] + offset`（BP 为内容对齐断点数组）

## Phase 断点计算（自动校准，禁止手工估算）

> **禁止手工估算断点。** Edge TTS 按 SRT 输出句子级时间戳（精度 ±10ms），配合 `narration_anchor` 自动校准，取代一切手工断点。

**禁止**：手工在 GSAP 中硬编码 `tl.to(..., 176.0, ...)` 绝对时间戳

**必须**：由 `phase_timings.json`（`phase_calibrator.py` 自动产出）驱动 GSAP timeline

### 自动校准流程

```
Stage 3 → narration_segments.json（visual_phases[].narration_anchor 标注句子索引）
    ↓
Stage 4 → tts_segments.py
    ├→ narration_seg_N.srt（Edge TTS 按句输出时间戳）
    └→ sentence_timestamps.json（解析 SRT 后的句子时间戳聚合）
    ↓
phase_calibrator.py（自动执行，无需手工干预）
    输入: narration_segments.json + sentence_timestamps.json
    输出: phase_timings.json
    ↓
Stage 6 → skeleton_builder 读取 phase_timings.json → 注入 GSAP timeline
```

### phase_timings.json 格式

```json
{
  "meta": { "voice": "zh-CN-YunjianNeural", "rate": "+25%", "calibration_source": "edge-tts-srt" },
  "scenes": [
    {
      "scene": "s3_pipeline_overview",
      "segment_index": 7,
      "global_start": 141.14,
      "duration": 34.54,
      "phases": [
        { "phase": 1, "start_offset": 0.0, "end_offset": 8.16, "sentences": [0, 1], "calibration": "sentence-anchor" },
        { "phase": 2, "start_offset": 8.16, "end_offset": 34.54, "sentences": [2, 3, 4], "calibration": "sentence-anchor" }
      ]
    }
  ]
}
```

### 校准精度

| 校准方式 | 精度 | 条件 |
|---------|------|------|
| `sentence-anchor` | ±50ms | visual_phases 含 narration_anchor |
| `auto-split` | ±30% | 无 narration_anchor，按句子等分（SOFT 警告） |

### GSAP 自动注入（Stage 6 skeleton_builder）

```javascript
// phase_timings.json 由 skeleton_builder 注入为 PHASE_TIMINGS 全局变量
const PT = PHASE_TIMINGS;

PT.scenes.forEach(sc => {
  const baseTime = sc.global_start;
  sc.phases.forEach((p, i) => {
    if (i === 0) return; // phase-1 不需要切换（CSS 默认可见）
    const t = baseTime + p.start_offset;
    // 淡出上一个 phase，淡入当前 phase
    tl.to(`#${sc.scene} .phase-${i}`, { opacity: 0, duration: 0.3 }, t);
    tl.to(`#${sc.scene} .phase-${i + 1}`, { opacity: 1, duration: 0.4 }, t + 0.1);
  });
});
```

**验证标准**：phase_timings.json 中每个 phase 的 `calibration` 字段必须为 `sentence-anchor`（HARD）。`auto-split` 触发 SOFT 警告。

## Phase 内容来源

读取 `narration_segments.json` 的 `visual_phases` 数组：

```json
"visual_phases": [
  { "focus": "产品定位与五大核心功能", "visual_type": "list",
    "key_data": ["跌倒检测>95%", "用药提醒", "一键呼叫", "AI语音", "健康监测"] },
  { "focus": "定价与收入模型", "visual_type": "data",
    "key_data": ["硬件599-999元", "月订阅29-49元", "毛利率30-40%"] }
]
```

- `focus` → phase 画面标题（`phase-header`）
- `visual_type` → 选择 `stage6-components.md` 的 Phase 视觉模板
- `key_data` → 画面上的数据/关键词内容

## Phase 视觉类型 → 模板映射

| visual_type | 画面布局 | 参考组件 |
|------------|---------|---------|
| `hero` | 大标题 + 关键数字 + 副标题 | `components/content/hero_card.html` |
| `list` | 标题 + 带序号的卡片列表 | — |
| `data` | 标题 + 数据行（label + value） | `components/content/data_viz.html` |
| `compare` | 标题 + 双栏对比 | `components/content/compare_split.html` |
| `timeline` | 标题 + 步骤节点 | `components/content/timeline_flow.html` |
| `highlight` | 大号结论文字 + 强调色 | `components/content/text_reveal.html` |

每种类型的具体 HTML/CSS 骨架见 `stage6-components.md` 的「Phase 视觉模板」章节。

## Phase 完整性验证

> `stage6_gate.sh` 的视觉分镜完整性检查会验证长场景的 phase 数量。HTML 写完后运行门禁即可。

## 呼吸帧插入

在场景切换点插入 0.3-0.5s 的视觉呼吸：

```javascript
tl.to('.current-scene .scene-content', { scale: 1.02, duration: 0.15, ease: 'power1.inOut' })
  .to('.current-scene .scene-content', { scale: 1.0, duration: 0.15, ease: 'power1.inOut' });
```

## Canvas 粒子和 Three.js 3D

根据沉浸模式决定是否使用 3D 场景：

| 沉浸模式 | Canvas 效果 | Three.js 3D |
|---------|------------|-------------|
| hyper-pace | `components/fx/code_rain.html` + `components/fx/particle_burst.html` | 否 |
| hidden-gem | `components/fx/pulse_orb.html` | 否 |
| mega-update | `components/fx/particle_burst.html` | `components/fx/three_scene.html`(旋转立方体群) |
| versus | `components/fx/pulse_orb.html` | 否 |
| story-time | — | 否 |
| fun-tool | `components/fx/particle_burst.html` | 否 |

Three.js 使用 `window.__hfThreeTime` 驱动，注册到 GSAP timeline 的 seek 回调。详见 `stage6-components.md` 的 ThreeScene 组件。
