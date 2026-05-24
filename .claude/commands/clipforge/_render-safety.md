# ClipForge 渲染安全 + 三层架构规范

> **Stage 6 必读。** 其他阶段无需加载。

## 1. HyperFrames 渲染安全规范

> **多次出现过"只有背景没有内容"的线上事故。** 以下规则均为事故复盘总结，必须严格遵守。

### 1.1 禁止 CSS `.anim-in` 及任何 CSS `opacity: 0` 入场动画

- **绝不使用 `.anim-in` CSS 类**或任何在 CSS 中设置 `opacity: 0` 的入场机制
- HyperFrames 基于 seek 驱动渲染（逐帧推进），**不触发 CSS animation/transition**，CSS 入场动画永远不会执行，导致内容永远 `opacity: 0`
- **所有内容元素必须默认可见**（`opacity: 1`），不做任何 CSS 入场动画
- 入场动画由 GSAP timeline 的 `.from({opacity:0})` 实现（见 §3），不依赖 CSS
- HyperFrames clip 切换由 `data-start`/`data-duration` 控制

### 1.1a 多阶段内容豁免（Phase 2+）

- **Phase 1**（每个 clip 的第一个视觉阶段）**必须 CSS opacity:1**，遵守 §1.1 规则
- **Phase 2+** 允许通过 GSAP `.set({opacity:0})` 在 clip 起始时刻设为不可见
- 这是 **GSAP 驱动的机制**，不是 CSS `opacity:0`，HyperFrames seek 时正确执行
- **禁止在 CSS 样式表中写 `.phase-2 { opacity: 0 }`**，必须通过 GSAP timeline 的 `.set()` 调用实现
- 原因：CSS `opacity:0` 在 HyperFrames seek 时不会被清除，而 GSAP `.set()` 会被正确回放
- Phase 间切换使用 `.to({opacity: 0})` 淡化旧阶段（完全消失，避免重叠重影）+ `.to({opacity: 1})` 显示新阶段
- **Phase 断点计算禁止均分**——`gap = duration / phase_count` 会导致旁白与画面严重不同步（偏差 5-12 秒）。必须逐场景分析旁白文本话题转换点，按字数比例换算时间戳。方法见 `stage6-production.md` §6.4b

### 1.2 禁止 HTML 实体字符

- **不在画面文字中使用 HTML 实体**（如 `&#9733;`、`&#10084;`、`&amp;` 等）
- HyperFrames 无头浏览器对实体字符的解析不可靠，可能导致整段内容不渲染
- **改用 Unicode 字符直接输入**（如 `★`、`❤`）或纯文本替代

### 1.3 scene-wrap 必须有 padding

- 每个场景的 `.scene-wrap`（或等效内容容器）**必须显式设置四方向 padding**
- 推荐值：`padding: 120px 90px 240px 36px`（上 120px，右 90px，下 240px，左 36px——多平台兼容安全区）
- 水平 padding 确保内容不贴视频边缘，防止手机端文字被裁切
- 缺少 padding 可能导致内容区域在 HyperFrames 渲染中塌陷不显示

### 1.4 水平安全边距规则（抖音竖屏非对称）

- **左 36px / 右 90px** 非对称边距（兼容抖音/小红书/微信视频号三平台）
- 水平 padding 只在 `.scene-wrap` 一层设置，内层元素不再重复
- **禁止** `width: 100%` 的内容行没有水平 padding

### 1.4a 单层 padding 原则

- 水平 padding **只在 `.scene-wrap` 设置**
- `.phase`、`.layer-content`、`.pfc-main` 等内层元素**禁止添加水平 padding**
- 违反会导致双重/三重 padding，内容被压缩到 70% 以下
- 历史事故：`.scene-wrap`(70px) + `.phase`(70px) = 累计 140px/侧，内容仅 800px (74%)

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

- `<audio src="bgm.mp3">` 引用的文件**必须存在于 index.html 同级目录**
- HyperFrames 渲染时通过 FileServer 提供文件，路径错误会导致 404 静音
- **渲染前检查：** `ls -la bgm.mp3 narration.mp3` 确认两个音频文件都存在

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
.scene-wrap { position: relative; overflow: hidden; }
.layer-bg { position: absolute; inset: 0; z-index: 1; }
.layer-fx { position: absolute; inset: 0; z-index: 2; pointer-events: none; }
.layer-content { position: relative; z-index: 3; }
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
- 每个 `.layer-fx` 必须包含至少 1 个特效子元素（Canvas 粒子容器、CSS 漂浮元素、SVG 装饰、脉冲光球等）
- 特效类型由 `stage6-components.md` 的情绪映射表决定，不固定但不可缺
- **空 layer-fx 等同于缺少该层，视为三层架构违规，stage6_gate.sh 会拦截**
- 最小实现标准（按情绪）：
  - grab/climax：Canvas 粒子 或 ≥5 个 CSS 动画元素
  - build/reveal：Canvas 粒子 或 ≥3 个 CSS 动画元素
  - settle/summon：Canvas 粒子 或 ≥3 个 CSS 动画元素
- 特效 opacity 保持 0.3-0.6，确保 `.layer-content` 始终清晰可读

## Red Flags（停止信号）

| 信号 | 说明 |
|------|------|
| 使用 `.anim-in` CSS 类 | HyperFrames 不执行 CSS animation，导致内容永远不可见 |
| HTML 实体字符（`&#9733;`） | 无头浏览器解析不可靠，可能导致整段不渲染 |
| scene-wrap 无 padding | 内容区域可能塌陷不显示 |
| 内层元素（.phase/.pfc-main）添加水平 padding | 双重/三重 padding 导致内容宽度不足 80%（§1.4a） |
| 多个含 `data-composition-id` 的 HTML 文件 | 渲染冲突，multiple_root_compositions 警告 |
| `window.__timelines = {};` 空对象未注册 | 全片空白渲染 |
| 音频文件不在项目目录内 | 404 静音 |
| 场景只有两层（缺少 .layer-fx） | 特效会遮挡内容或背景穿透 |
| 空的 layer-fx（`<div class="layer-fx"></div>`） | §2.4 违规：空层等同于缺少该层，stage6_gate.sh 会拦截 |
| Phase 断点使用 `gap = duration / phase_count` 均分 | 旁白与画面内容严重不同步，偏差 5-12 秒 |
