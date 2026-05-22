# ClipForge 沉浸式视频体验升级设计

> 日期: 2026-05-22
> 范围: GitHub 分类视频全面重构
> 状态: 已确认

## 目标

将 GitHub 视频从"基础可用"升级到"情感化、沉浸式体验"——具备幽默感、视觉冲击力和叙事感染力，实现用户吸引、场景适配和参与度提升。

---

## Section 1: 叙事引擎 (Narrative Engine)

### Stage 2 升级: 故事板设计

当前 Stage 2 仅做情绪提取和配色推导。升级后增加**叙事结构规划**，输出 storyboard JSON:

```yaml
# design.json 新增字段
storyboard:
  narrative_template: "contrast-arc"  # 6 选 1
  emotion_curve: [0.3, 0.5, 0.8, 1.0, 0.6, 0.4]  # 6 拍情感强度
  immersion_mode: "hyper-pace"        # 6 选 1
  humor_style: "dual-track"           # 双线结合
  character_presence: true            # 是否启用码力角色
```

### 6 种叙事结构模板

| 模板 | 适用场景 | 情感弧线 |
|------|----------|----------|
| `contrast-arc` | 重大更新、突破性项目 | 平淡 → 对比 → 震撼 → 高潮 → 沉淀 |
| `underdog` | 小众项目爆发、个人开发者作品 | 低谷 → 逆境 → 逆袭 → 胜利 |
| `showdown` | 竞品对比、同类工具评测 | 紧张 → 交锋 → 揭晓 → 结论 |
| `mystery-box` | 神秘项目、未公开功能 | 好奇 → 线索 → 揭示 → 惊喜 |
| `hyper-pace` | AI 爆发、周榜密集更新 | 快速 → 密集 → 爆发 → 呼吸 |
| `story-time` | 开发者故事、项目历程 | 平静 → 转折 → 深情 → 共鸣 |

### Stage 3 升级: 双线幽默引擎

**听觉线（旁白文案）：**
- 类比幽默: 用生活场景比喻技术概念（"这个 PR 就像在火锅里加了冰淇淋"）
- 反差吐槽: 正经话题突然转折（"这个库 stars 涨得比我工资快多了"）
- 冷知识梗: 开发者文化内行梗（"据说这个 bug 的工龄比实习生还长"）

**视觉线（画面表现）：**
- 浮动弹幕气泡: 关键时刻弹出角色吐槽气泡
- 反应叠加: 角色表情覆盖层（震惊/思考/酷/爆炸/调侃/感动）
- 视觉双关: 代码梗的可视化表达

旁白文案在每个 segment 增加 `humor_type` 标记:
```json
{
  "text": "这个项目一周涨了五千星，比我的发际线退得还快",
  "humor_type": "analogy",
  "emotion": "tease",
  "character_expression": "tease"
}
```

---

## Section 2: 视觉组件系统 (Visual Component System)

### 设计原则

超越基础可用性，每个组件都是**情感载体**——不只是展示信息，而是传递情绪、制造节奏、创造沉浸感。

### 组件库 (10+ 场景类型)

| 组件 | 用途 | 情感目标 |
|------|------|----------|
| `HeroCard` | 项目首屏展示 | 震撼、吸引力 |
| `StarCounter` | Star 数动态计数 | 兴奋、增长感 |
| `CodeRain` | 代码雨背景特效 | 科技感、紧迫感 |
| `PulseOrb` | 脉冲光球装饰 | 能量感、聚焦 |
| `CompareSplit` | 双栏对比布局 | 对抗感、悬念 |
| `TimeLineFlow` | 时间线叙事 | 故事感、推进感 |
| `ParticleBurst` | 粒子爆发庆祝 | 激动、高潮 |
| `ThreeScene` | 3D 场景容器 | 沉浸感、空间感 |
| `SpeechBubble` | 角色吐槽气泡 | 幽默、亲近感 |
| `CharOverlay` | 码力角色覆盖层 | 人格化、情感连接 |
| `DataViz` | 数据可视化卡片 | 信服力、专业感 |
| `TextReveal` | 文字揭示动画 | 悬念、惊喜 |

### Canvas 粒子系统规范

```javascript
// 粒子系统基类 — 适配 HyperFrames seek 驱动渲染
class ParticleSystem {
  constructor(canvas, config) {
    this.ctx = canvas.getContext('2d');
    this.particles = [];
    // config: { count, color, speed, size, life, gravity, fade }
  }

  // HyperFrames seek 驱动: progress 是 0-1 的播放进度
  update(progress) {
    this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
    // 根据 progress 计算粒子状态，确保每帧确定性
  }
}

// 注册到 GSAP timeline
gsap.to({ progress: 0 }, {
  progress: 1,
  duration: sceneDuration,
  onUpdate: function() {
    particleSystem.update(this.targets()[0].progress);
  }
});
```

### Three.js 3D 场景规范

使用 HyperFrames 内置 Three.js adapter，遵循 `/three` skill 规范:

```javascript
// 关键: 使用 window.__hfThreeTime 驱动动画，不用 Date.now()
function animate() {
  requestAnimationFrame(animate);
  // window.__hfThreeTime 由 HyperFrames 注入，seek 时自动回溯
  const t = window.__hfThreeTime || performance.now() / 1000;
  mesh.rotation.y = t * 0.5;
  renderer.render(scene, camera);
}
```

注册要求:
- 定义 `window.__hf` 对象
- 注册 `window.__timelines["main"]` GSAP timeline
- Three.js 场景在 timeline 的 seek 回调中更新

---

## Section 3: 情感沉浸系统 (Emotional Immersion System)

### 6 拍情感节奏模型

视频被拆分为 6 个情感节拍，每个节拍有明确的情感目标和视觉方法:

| 节拍 | 时长占比 | 情感目标 | 视觉方法 | 音频特征 |
|------|----------|----------|----------|----------|
| **抓取 (grab)** | 10% | 好奇、紧迫 | 快速切换 + 大字揭示 + 粒子聚集 | 急促旁白 rate=1.2 |
| **构建 (build)** | 25% | 期待、专注 | 信息渐进 + 数据流动 + 背景渐变 | 平稳旁白 rate=1.0 |
| **揭示 (reveal)** | 20% | 惊喜、震撼 | 爆发效果 + 3D 转场 + 色彩跃升 | 稍快 rate=1.1 |
| **高潮 (climax)** | 15% | 激动、共鸣 | 粒子爆发 + 震屏 + 角色表情 | 快速 rate=1.15 |
| **沉淀 (settle)** | 20% | 满足、思考 | 缓慢动画 + 柔和色调 + 呼吸帧 | 慢速 rate=0.9 |
| **召唤 (summon)** | 10% | 行动欲、记忆点 | 收束聚焦 + CTA 引导 | 中速 rate=1.0 |

### 6 种沉浸模式

根据内容特征自动选择:

| 模式 | 触发条件 | 视觉风格 | 代表色 |
|------|----------|----------|--------|
| **狂飙 (hyper-pace)** | AI/爆发类 | 快速剪辑 + 密集粒子 + 霓虹 | 电光蓝 #00D4FF |
| **寻宝 (hidden-gem)** | 小众/发现类 | 渐进揭示 + 温暖光效 + 复古 | 琥珀金 #FFB800 |
| **震撼 (mega-update)** | 重大更新 | 3D 场景 + 大气粒子 + 暗色 | 深紫 #7B2FBE |
| **对决 (versus)** | 对比/评测类 | 分屏对比 + 脉冲能量 + 硬朗 | 烈焰红 #FF3B30 |
| **故事 (story-time)** | 开发者故事 | 插画风 + 柔和过渡 + 暖色 | 森林绿 #34C759 |
| **玩乐 (fun-tool)** | 有趣工具 | 彩色弹跳 + 幽默角色 + 亮色 | 彩虹渐变 |

### 码力角色系统

SVG 矢量角色 "码力"——一个开发者人格化角色，6 种表情:

| 表情 | 触发场景 | SVG 特征 |
|------|----------|----------|
| **shock** | 震撼数据/意外发现 | 圆眼大嘴 O 型 |
| **think** | 分析/思考环节 | 摸下巴 + 问号气泡 |
| **cool** | 展示酷功能 | 墨镜 + 微笑 |
| **explode** | 高潮爆发时刻 | 爆炸头发 + 星星眼 |
| **tease** | 幽默调侃时刻 | 眯眼坏笑 + 挤眉 |
| **moved** | 感人/致敬场景 | 星光眼 + 小泪花 |

角色渲染规则:
- 占画面 15-20%，不遮挡核心信息
- 出现在画面右下或左下角
- 通过 GSAP timeline 控制入场/退场动画
- 表情切换跟随 storyboard 的 `character_expression` 标记

### 情感驱动音频同步

Stage 4 TTS 升级为**逐段变速**:

```json
{
  "segments": [
    { "text": "这个项目...", "rate": 1.2, "emotion": "grab" },
    { "text": "让我们看看...", "rate": 1.0, "emotion": "build" },
    { "text": "没想到的是...", "rate": 1.1, "emotion": "reveal" }
  ]
}
```

每段 TTS 使用 `edge-tts --rate=+N%` 或 `--rate=-N%` 单独生成，保留原始时长信息供 timeline 对齐。

### 呼吸帧 (Breathing Frames)

在节奏转折点插入 0.3-0.5s 的视觉呼吸:
- 画面轻微缩放（1.0 → 1.02 → 1.0）
- 背景微动（渐变色缓慢偏移）
- 粒子系统减速或暂停
- 角色表情过渡

呼吸帧不是独立场景，而是嵌入在场景切换的 GSAP timeline 中:

```javascript
timeline.add('breath-start')
  .to('.scene-content', { scale: 1.02, duration: 0.15, ease: 'power1.inOut' })
  .to('.scene-content', { scale: 1.0, duration: 0.15, ease: 'power1.inOut' })
  .add('breath-end');
```

---

## Section 4: 架构变更 (Architecture Changes)

### DAG 不变

`schema.yaml` 的 artifact 定义不变。所有新能力在 Stage 内部实现，不引入新的 artifact 类型。

### 文件变更清单

#### 重写文件 (3 个)

| 文件 | 变更内容 |
|------|----------|
| `stage2-analysis.md` | 新增: storyboard 规划、叙事模板选择、沉浸模式判定、情感曲线设计 |
| `stage3-narration.md` | 新增: 双线幽默引擎、逐段情感标记、角色表情触发点 |
| `stage6-production.md` | 全面重写: 组件装配系统、Canvas 粒子、Three.js 3D、角色动画、呼吸帧 |

#### 新增文件 (1 个)

| 文件 | 用途 |
|------|------|
| `stage6-components.md` | 视觉组件参考手册——所有 12 个组件的 HTML/CSS/JS 模板、参数说明、情感映射 |

#### 升级文件 (1 个)

| 文件 | 变更内容 |
|------|----------|
| `categories/github.md` | 新增: narrative/humor_rules/character_presence/immersion_mapping 配置节 |

#### 不变文件

| 文件 | 原因 |
|------|------|
| `schema.yaml` | DAG artifact 不变，新能力在 Stage 内部 |
| `clipforge.md` (主控制器) | 模式选择逻辑不变，Stage 行为由各自文件定义 |
| `stage0-env.md` | 依赖检测不变 |
| `stage1-content.md` | 内容获取逻辑不变 |
| `stage4-audio.md` | 音频生成逻辑不变，情感变速是参数化配置 |
| `stage5-assets.md` | 素材制备不变（纯 CSS/HTML 渲染不需要额外素材） |
| `stage7-delivery.md` | 交付逻辑不变 |
| `stage8-cleanup.md` | 清理逻辑不变 |
| `_shared-rules.md` | 内容规范不变 |
| `_cleanup-rules.md` | 清理规则不变 |

### Stage 间数据流

```
Stage 1 (content)
  → content.json (不变)
    ↓
Stage 2 (analysis) ★ 重写
  → design.json (新增 storyboard/immersion_mode/emotion_curve)
    ↓
Stage 3 (narration) ★ 重写
  → narration.json (每段新增 emotion/humor_type/character_expression)
    ↓
Stage 4 (audio)
  → audio/ (每段 TTS 带独立 rate 参数)
    ↓
Stage 5 (assets) — 跳过（纯 CSS/HTML/Canvas/Three.js）
    ↓
Stage 6 (production) ★ 全面重写
  → 读取 design.json + narration.json + stage6-components.md
  → 组装: 组件选择 → Canvas 粒子 → Three.js 3D → 角色动画 → 呼吸帧
  → 输出 HTML composition → HyperFrames 渲染
    ↓
Stage 7 (delivery) — 不变
```

### 渲染安全约束

所有 Stage 6 变更必须遵守 `_shared-rules.md` 中的 HyperFrames 渲染安全规则:
- `window.__hf` 必须定义
- `window.__timelines["main"]` 必须注册 GSAP timeline
- 禁止 CSS `.anim-in` 类
- 禁止 HTML entities
- scene-wrap 必须有 padding
- render-bitrate 5M
- Three.js 使用 `window.__hfThreeTime` 而非 `Date.now()`

### GitHub 分类升级

`categories/github.md` 新增配置节:

```yaml
# 新增节
narrative:
  default_template: "contrast-arc"
  humor_rules:
    - 用类比而非直白吐槽
    - 开发者文化梗优先
    - 避免低俗和人身攻击
  character_presence: true

immersion_mapping:
  ai_burst: "hyper-pace"      # AI 类项目
  hot_repo: "mega-update"     # 热门项目
  hidden_gem: "hidden-gem"    # 小众宝藏
  comparison: "versus"        # 对比评测
  dev_story: "story-time"     # 开发者故事
  fun_tool: "fun-tool"        # 有趣工具
```

---

## 验收标准

1. **叙事**: 每个 GitHub 视频都有明确的叙事模板和 6 拍情感节奏
2. **幽默**: 至少 30% 的段落包含双线幽默（旁白或视觉）
3. **视觉冲击**: 不再有纯图文卡片，至少包含粒子效果或 3D 场景
4. **角色**: 码力角色在高潮和幽默段出现，表情与内容匹配
5. **音频同步**: TTS 速率随情感节拍变化，不再全线均匀
6. **安全**: 所有渲染遵守 HyperFrames 约束，无黑屏/闪烁
