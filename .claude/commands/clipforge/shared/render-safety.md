# ClipForge 渲染安全 + 三层架构规范

> **Stage 6 必读。** 其他阶段无需加载。

## 1. HyperFrames 渲染安全规范

> 以下规则为渲染安全硬约束，必须严格遵守。

### 1.1 禁止 CSS `.anim-in` 及任何 CSS `opacity: 0` 入场动画

- **绝不使用 `.anim-in` CSS 类**或任何在 CSS 中设置 `opacity: 0` 的入场机制
- HyperFrames 基于 seek 驱动渲染（逐帧推进），**不触发 CSS animation/transition**，CSS 入场动画永远不会执行，导致内容永远 `opacity: 0`
- **所有内容元素必须默认可见**（`opacity: 1`），不做任何 CSS 入场动画
- 入场动画由 GSAP timeline 的 `.from({opacity:0})` 实现（见 §1.7），不依赖 CSS
- HyperFrames clip 切换由 `data-start`/`data-duration` 控制

### 1.1a 多阶段内容豁免（Phase 2+）

- **Phase 1**（每个 clip 的第一个视觉阶段）**必须 CSS opacity:1**，遵守 §1.1 规则
- **Phase 2+** 允许通过 GSAP `.set({opacity:0})` 在 clip 起始时刻设为不可见
- 这是 **GSAP 驱动的机制**，不是 CSS `opacity:0`，HyperFrames seek 时正确执行
- **禁止在 CSS 样式表中写 `.phase-2 { opacity: 0 }`**，必须通过 GSAP timeline 的 `.set()` 调用实现
- 原因：CSS `opacity:0` 在 HyperFrames seek 时不会被清除，而 GSAP `.set()` 会被正确回放
- Phase 间切换使用 `.to({opacity: 0})` 淡化旧阶段（完全消失，避免重叠重影）+ `.to({opacity: 1})` 显示新阶段
- **Phase 断点计算禁止均分**——`gap = duration / phase_count` 会导致旁白与画面严重不同步（偏差 5-12 秒）。必须逐场景分析旁白文本话题转换点，按字数比例换算时间戳。方法见 `stages/stage6-production.md` §6.4b

### 1.1b 特效元素默认可见规则

- §1.1 的规则不仅适用于 `.layer-content`，也适用于 `.layer-fx` 和 `.layer-bg` 的所有元素
- **任何 HTML 元素的静态 CSS 状态（无 animation 属性时）必须视觉正确**
- CSS `animation:` 在 HyperFrames 中不执行，元素以静态状态呈现
- **允许**的 CSS animation：可见位置之间的移动（如 `driftOuter`、`orbDrift`，0% 状态本身在画面内且可见）
- **禁止**的 CSS animation：从不可见到可见的过渡（如 `scaleY(0)→1`、`opacity:0→1`、`translateY(-100%)→0`）
- "从无到有"的动画必须使用 GSAP `.from()` 实现

### 1.2 禁止 HTML 实体字符

- **不在画面文字中使用 HTML 实体**（如 `&#9733;`、`&#10084;`、`&amp;` 等）
- HyperFrames 无头浏览器对实体字符的解析不可靠，可能导致整段内容不渲染
- **改用 Unicode 字符直接输入**（如 `★`、`❤`）或纯文本替代

### 1.3 安全区 padding 必须存在且只设一次

- 每个场景**必须有四方向安全区 padding**，按画布方向选择：
  - 竖屏（1080×1920）：`padding: 180px 80px 220px 80px`（上 180px，右 80px，下 220px，左 80px）
  - 横屏（1920×1080）：`padding: 60px 120px 60px 120px`（上 60px，右 120px，下 60px，左 120px）
- **padding 只设在一层**，由场景使用的模式决定（见 §1.4b 分类）
- 缺少 padding 会导致内容贴边缘或渲染塌陷；双重 padding 会导致内容偏左上、可用宽度仅 74%

### 1.3a 背景铺满全画幅（铁律）

- **`.layer-bg` 必须铺满整个画面**（竖屏 1080×1920 / 横屏 1920×1080），禁止被 `.clip` 或任何父元素裁剪
- 实现方式：`.clip` 使用 `position:absolute; inset:0`（与 composition 同尺寸），不做空间偏移
- **禁止** `.clip` 设置 `top/right/bottom/left` 偏移值（如 `top:140px`），这会把背景关在 clip 内，clip 外全是黑色 → 四面黑边
- 安全区内缩**只能**通过 `.scene-wrap` 或组件的 padding 实现，不能通过 `.clip` 的定位
- **HARD，gate: clip_no_offset**

### 1.4 安全边距规则

**竖屏：** 左 80px / 右 80px 对称边距（兼容抖音/小红书/微信视频号三平台）
**横屏：** 左 120px / 右 120px 对称边距

- **禁止** `width: 100%` 的内容行没有水平 padding

### 1.4a 单层 padding 原则（铁律）

- **全项目只允许一个层级设置安全区 padding**（竖屏 `180px 80px 220px 80px` / 横屏 `60px 120px 60px 120px`）
- 禁止 `.scene-wrap` 和 `.phase`（或任何内层元素）同时设置 padding
- 违反会导致双重/三重 padding，内容被压缩到 70% 以下，视觉重心偏移
- **HARD，gate: double_padding**
- **director_gate.py 会自动检测双重 padding，渲染前必须通过**

### 1.4b 组件 padding 分类

所有场景分为三类，padding 落在不同层级：

**Phase 模式**（多视觉阶段场景，最常见）
- `.scene-wrap` **不设 padding**
- `.phase` 设置 `padding: 180px 80px 220px 80px`（竖屏）或 `60px 120px 60px 120px`（横屏）`; display:flex; flex-direction:column; justify-content:center`。横屏 `.phase` 加 `align-items:center` 确保子元素水平居中（子元素内容文字仍可左对齐，但整体容器居中）
- 结构：`.scene-wrap(无padding)` → `.layer-bg` + `.layer-fx` + `.layer-content` → `.phase(padding+flex居中)`

**自带 padding 组件（full-page 型）**：`hero_card`、`project_full_card`
- 组件自带 `padding: 180px 80px 220px 80px`（竖屏）或 `60px 120px 60px 120px`（横屏）
- 外层 `.scene-wrap` **不设 padding**
- 结构：`.scene-wrap(无padding)` → `.layer-bg` + `.layer-fx` + `.layer-content` → 组件(自带padding)

**无 padding 组件（嵌入型）**：其余所有组件
- 组件无外层 padding
- `.scene-wrap` 设置 `padding: 180px 80px 220px 80px`（竖屏）或 `60px 120px 60px 120px`（横屏）
- 结构：`.scene-wrap(padding)` → `.layer-bg` + `.layer-fx` + `.layer-content` → 组件(无padding)

### 1.5 渲染前移除所有非 index.html 的 composition 文件

- **HyperFrames 不允许多个 root composition**（`multiple_root_compositions` 警告）
- 项目目录中**任何**含 `data-composition-id` 的 HTML 文件（不止 `cover.html`）都会导致渲染冲突
- 常见冲突文件：`cover.html`、`index_with_bgm.html`（备份）、`cover.html.bak`（未清理的备份）
- **渲染 index.html 前，移除所有非 index.html 的 HTML 文件：**
  ```bash
  for f in cover.html index_with_bgm.html cover.html.bak; do
    [ -f "$f" ] && mv "$f" "$f.renderbak"
  done
  ```
- **渲染完成后恢复需要的文件：** `mv cover.html.renderbak cover.html`
- **临时备份文件渲染后必须删除：** `rm -f index_with_bgm.html.renderbak cover.html.bak.renderbak`

### 1.6 音频文件必须在项目目录内

- `<audio src="bgm.wav">` 引用的文件**必须存在于 index.html 同级目录**
- HyperFrames 渲染时通过 FileServer 提供文件，路径错误会导致 404 静音
- **渲染前检查：** `ls -la bgm.wav narration.mp3` 确认两个音频文件都存在

### 1.6a 根组合尺寸属性（黑帧防护）

- 根组合 div（`data-composition-id="main"`）**必须**包含 `data-width` 和 `data-height`（竖屏 `"1080"` × `"1920"`，横屏 `"1920"` × `"1080"`）
- 缺少任一属性 → HyperFrames viewport 设置错误 → 输出 **100% 黑帧视频**（码率 <100kbps）
- 所有 `<audio>` 元素**必须**包含 `data-start="0"`，否则音频不播放

```html
<!-- 竖屏 -->
<div data-composition-id="main" data-width="1080" data-height="1920"
     data-start="0" data-duration="174.68">
  <audio data-track-index="1" data-volume="1" data-start="0"
         src="narration.mp3" preload="auto"></audio>
  <audio data-track-index="2" data-volume="0.06" data-start="0"
         src="bgm.wav" preload="auto" loop></audio>
</div>

<!-- 横屏 -->
<div data-composition-id="main" data-width="1920" data-height="1080"
     data-start="0" data-duration="174.68">
  <audio data-track-index="1" data-volume="1" data-start="0"
         src="narration.mp3" preload="auto"></audio>
  <audio data-track-index="2" data-volume="0.06" data-start="0"
         src="bgm.wav" preload="auto" loop></audio>
</div>

<!-- 错误 — 会导致 100% 黑帧 -->
<div data-composition-id="main" data-start="0">
  <audio data-track-index="1" data-volume="1" ...>
</div>
```

### 1.7 GSAP timeline 注册是强制要求

- **`window.__timelines = {};`（空对象）会导致全片空白渲染。** HyperFrames 等待 `window.__timelines["main"]` 被注册，超时后渲染空帧
- 必须引入 GSAP CDN 并注册 timeline：
  ```html
  <script src="https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.5/gsap.min.js"></script>
  <script>
  window.__timelines = {};
  const tl = gsap.timeline({paused: true});
  tl.from('.s-hook .element', {opacity:0, y:20, duration:0.3, ease:'power3.out'}, 0.2);
  // ... 每个场景的入场动画
  window.__timelines["main"] = tl;
  </script>
  ```
- GSAP `.from()` 动画是可靠的入场机制：元素 CSS 默认 `opacity:1`，GSAP `.from({opacity:0})` 在 seek 时正确执行
- 动画 offset 必须与场景 `data-start` 对齐（如 hook 场景从 0 开始，what 场景从 hook 时长开始）

## 2. 三层渲染架构

> **每个场景必须严格分离为三层。** 这是结构规则，不是样式建议。违反会导致特效遮挡内容或背景穿透。

### 2.1 层级定义

| 层级 | z-index | 用途 | 内容 |
|------|---------|------|------|
| 底层 `.layer-bg` | 1 | 场景背景 | 渐变色、光晕、网格底纹、纯色填充 |
| 中间层 `.layer-fx` | 2 | 视觉特效 | 粒子、爆炸、矩阵雨、3D、漂浮物等动态装饰 |
| 顶层 `.layer-content` | 3 | 可读内容 | 文字、数字、徽章、卡片、标签等所有用户需要阅读的元素 |

### 2.2 CSS 模板

```css
.scene-wrap { position: relative; width: 100%; height: 100%; overflow: hidden; }
.layer-bg { position: absolute; inset: 0; z-index: 1; }
.layer-fx { position: absolute; inset: 0; z-index: 2; pointer-events: none; }
.layer-content { position: relative; z-index: 3; height: 100%; }
```

### 2.3 规则

- **每个场景必须包含三层**，无例外
- `.layer-fx` 必须 `pointer-events: none`，防止特效遮挡交互
- 特效 opacity 建议 0.3-0.6（不遮挡内容但可见）
- 特效类型不固定，根据场景情绪和内容主题自行推导（见 `stage6-components.md` 情绪映射表）
- `.layer-bg` 至少包含渐变背景 + 1 个光晕
- **特效层非空规则（§2.4）见下**

### 2.4 特效层非空规则

- `.layer-fx` **禁止为空 div**（即不允许 `<div class="layer-fx"></div>`）
- 每个 `.layer-fx` 必须包含至少 1 个特效子元素（CSS 光球、射线、渐变带、矩阵雨竖线、双轨道粒子等）
- 特效类型由 `stage6-components.md` 的情绪映射表和 CSS 特效库决定，不再统一使用粒子
- **空 layer-fx 等同于缺少该层，视为三层架构违规，stage6_gate.sh 会拦截**
- 最小实现标准（按特效类型，详见 `stage6-components.md`）：
  - StarBurst（grab/climax）：≥6 条射线 + ≥4 闪烁点
  - LightOrbs（build/summon）：≥3 个光球
  - MatrixRain（build）：≥8 条竖线
  - DualOrbit 粒子（reveal）：≥8 个双层嵌套粒子
  - GradientWave（settle）：≥2 条渐变带
- 特效整体保持低调（光球 opacity 0.15-0.35，粒子 opacity 0.2-0.35，射线 opacity 0.3-0.5），确保 `.layer-content` 始终清晰可读
- **opacity 下限 0.15**：低于此值在 H.264 编码后肉眼不可见，等同于没做

### 2.5 特效动画规则

- `.layer-fx` 中每个可见特效元素**必须有 GSAP 动画**（持续动画或入场动画均可）
- 纯静态 fx 元素（GSAP timeline 中无对应 `.to()`/`.from()` 调用）视为违规
- 动画类型不限——脉冲、漂浮、旋转、闪烁、扫描、缩放、位移都可以，由内容推导决定
- 持续动画推荐：`gsap.to(el, {repeat:-1, yoyo:true, duration:2-4})` 实现脉冲/漂浮/旋转等
- **禁止**：fx 元素仅依赖 CSS `animation:` 做入场或可见性变化（HyperFrames seek 不执行 CSS animation）
- **允许**：CSS animation 用于可见位置之间的连续运动（如漂移、摇摆），前提是 0% 状态本身可见
- 组件匹配/创建流程：先在 `components/registry.yaml` 按情绪标签匹配，找不到就从内容推导创建新特效。高质量新特效可封装为组件入库（详见 `stage6-components.md` 组件创建指南）

## 3. 排版规范（双方向）

> **方向由 `design.md` 的 `orientation` 字段决定，`orientation_source` 记录来源。** 来源优先级：`user_explicit` > `category_hint` > `default`。默认竖屏，仅当用户明确指定或分类配置要求时才使用横屏。画布方向由 `data-width`/`data-height` 决定：1080×1920 = 竖屏，1920×1080 = 横屏。

### 3.1 竖屏字号最低标准（1080×1920）

| 元素类型 | 最低字号 | 说明 |
|---------|---------|------|
| 场景标题 | 64px | 场景主标题，用字重和颜色区分层级 |
| 正文/描述 | 36px | 旁白对应的画面文字，手机端必须可读 |
| 标注/注释 | 28px | 辅助信息（语言标签、类别、时间戳等） |
| 数字/数据 | 52px | 核心数据展示，必须一眼看到 |

**违反字号最低标准的文字元素在手机端只有 9-12px，等于不可读。**

### 3.2 禁止 section-tag 小徽章标题

**禁止以下模式作为场景标题：**

```html
<!-- 禁止：小徽章标签 -->
<div class="section-tag" style="background:rgba(249,168,37,0.15);color:var(--accent-warm)">痛点</div>
```

这种 20-24px 带背景色的小标签看起来小气、廉价，不符合竖屏视频的视觉冲击力要求。

**正确方式——用标题层字号 + 视觉权重区分：**

```html
<!-- 正确：大字号标题，用字重/颜色/位置区分 -->
<h2 class="scene-title" style="font-size:72px;font-weight:800;color:var(--accent-warm)">痛点</h2>

<!-- 正确：或者用竖排标签 + 大字号内容 -->
<div style="display:flex;align-items:baseline;gap:20px">
  <span style="font-size:32px;font-weight:700;color:var(--accent-warm);opacity:0.6">01</span>
  <h2 style="font-size:64px;font-weight:900;color:var(--text-primary)">痛点分析</h2>
</div>
```

### 3.3 竖屏布局原则

- **垂直空间是资产**：一行放不下的内容换行，不压缩字号
- **信息层叠**：标题在上 → 核心内容在中 → 辅助信息在下，利用 1920px 的纵向纵深
- **留白制造呼吸感**：竖屏场景不需要填满每一寸，40%+ 留白 = 高端感
- **焦点居中偏上**：视觉焦点在画面黄金分割点（~38% 高度位置，即约 730px 处）

### 3.4 横屏字号最低标准（1920×1080）

| 元素类型 | 最低字号 | 说明 |
|---------|---------|------|
| 场景标题 | 56px | 横屏标题层，视觉权重不足则失去标题作用 |
| 正文/描述 | 32px | 横屏在手机端播放 DPR 缩放比 ~2.67x，32px 缩放后 ≈ 12px，是可读性底线 |
| 标注/注释 | 24px | 辅助信息，低于此值横屏画面中不可辨 |
| 数字/数据 | 48px | 核心数据展示，必须一眼看到 |

**横屏正文 32px 是底线不是目标。** 推荐正文 36-44px，标注 28-36px。手机横屏播放时 32px ≈ 12px 已是可读极限，再低则等于白做。

### 3.5 横屏布局原则

- **视觉平衡**：内容区域的视觉重心应分布在画布中段（水平 20%-80% 范围内），不偏向一侧
- **实现方式灵活**：
  - 单栏文字：内容容器 `max-width:1400px; margin:0 auto` + 文字可左对齐/居中按导演意图
  - 双栏/并排：利用水平空间做信息对比，左右栏宽度比不超过 3:1
  - 宽幅排版：标题横跨、数据卡片行等利用全宽元素自然平衡
- **禁止**：所有内容挤在画布左 30% 或右 30%，另一侧大面积空白
- **水平空间是资产**：横屏 1920px 宽幅用于信息密度和信息对比，不做窄栏左对齐阅读流

## Red Flags（停止信号）

| 信号 | 说明 |
|------|------|
| 使用 `.anim-in` CSS 类 | HyperFrames 不执行 CSS animation，导致内容永远不可见 |
| HTML 实体字符（`&#9733;`） | 无头浏览器解析不可靠，可能导致整段不渲染 |
| scene-wrap 和 .phase 同时有 padding | 双重 padding 导致内容偏左上、可用宽度仅 74%（§1.4a 单层 padding 铁律） |
| 任何层级缺少安全区 padding | 内容贴边缘或渲染塌陷（§1.3） |
| 多个含 `data-composition-id` 的 HTML 文件 | 渲染冲突，multiple_root_compositions 警告 |
| `window.__timelines = {};` 空对象未注册 | 全片空白渲染 |
| 音频文件不在项目目录内 | 404 静音 |
| 场景只有两层（缺少 .layer-fx） | 特效会遮挡内容或背景穿透 |
| 空的 layer-fx（`<div class="layer-fx"></div>`） | §2.4 违规：空层等同于缺少该层，stage6_gate.sh 会拦截 |
| `.layer-content` 缺少 `height:100%` | Phase 内容塌陷到顶部（§2.2）：绝对定位的 phase 无法解析 inset:0 |
| 特效元素 CSS animation 从不可见状态开始（scaleY:0 / translateY(-100%) / opacity:0） | HyperFrames 不执行 CSS animation，特效永远不可见（§1.1b） |
| fx 元素无 GSAP 动画（纯静态 div） | §2.5 违规：无动画的特效等同于装饰背景，不算特效层 |
| fx 元素 opacity < 0.15 | H.264 编码后不可见，等同于没做（§2.4） |
| Phase 断点使用 `gap = duration / phase_count` 均分 | 旁白与画面内容严重不同步，偏差 5-12 秒 |
| 根组合缺少 `data-width` 或 `data-height` | HyperFrames viewport 错误 → 100% 黑帧（§1.6a） |
| `<audio>` 缺少 `data-start="0"` | 音频不播放（§1.6a） |
| 竖屏场景标题 < 64px 或正文 < 36px | 手机端不可读，等于做了白做（§3.1） |
| 使用 section-tag 小徽章作为场景标题 | 视觉廉价，不符合竖屏冲击力（§3.2） |
| 横屏场景正文 < 32px 或标注 < 24px | 手机端不可读，等于做了白做（§3.4） |
| 横屏场景内容视觉重心偏移（内容偏向一侧） | 画面失衡，观感差（§3.5） |
