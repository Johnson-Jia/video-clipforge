---
id: "clipforge.render-safety"
description: ClipForge 渲染安全 + 三层架构规范 — HyperFrames 渲染引擎的强制约束
version: "2.0.0"
type: SPEC
scope: SCENE
scene: "video-production"
rules_lib_ref: "_rules-lib/video-production-rules.yaml"
---

# ClipForge 渲染安全 + 三层架构规范

> **Stage 6 必读。** 其他阶段无需加载。
> 每条规则与 `_rules-lib/video-production-rules.yaml` 中的规则 ID 对齐。

## 1. HyperFrames 渲染安全规范

> **多次出现过"只有背景没有内容"的线上事故。** 以下规则均为事故复盘总结，必须严格遵守。

### 1.1 禁止 CSS `.anim-in` 及任何 CSS `opacity: 0` 入场动画

`R-RENDER-001` [HARD/SAFETY]：**入场动画由 GSAP .from({opacity:0}) 实现**
- 正向：所有内容元素默认 `opacity:1` 可见，入场动画由 GSAP timeline `.from({opacity:0})` 驱动
- 绝不使用 `.anim-in` CSS 类或任何在 CSS 中设置 `opacity: 0` 的入场机制
- HyperFrames 基于 seek 驱动渲染（逐帧推进），**不触发 CSS animation/transition**，CSS 入场动画永远不会执行
- HyperFrames clip 切换由 `data-start`/`data-duration` 控制
- **Spirit：** 确保 HyperFrames seek 驱动下所有元素正确可见

### 1.1a 多阶段内容豁免（Phase 2+）

`R-RENDER-002` [HARD/SAFETY]：**Phase 2+ 通过 GSAP .set({opacity:0}) 实现隐藏**
- 正向：Phase 1 必须 CSS opacity:1；Phase 2+ 通过 GSAP `.set({opacity:0})` 在 clip 起始设为不可见
- 这是 GSAP 驱动的机制，HyperFrames seek 时正确执行
- 禁止在 CSS 中写 `.phase-2 { opacity: 0 }`
- Phase 间切换使用 `.to({opacity: 0})` 淡化旧阶段 + `.to({opacity: 1})` 显示新阶段

`R-RENDER-011` [HARD/EXPERIENTIAL]：**Phase 断点按旁白话题转换点对齐**
- 正向：逐场景分析旁白文本话题转换点，按字数比例换算时间戳
- 禁止 `gap = duration / phase_count` 均分（偏差 5-12 秒）
- 方法见 `stage6-production.md` §6.4b

### 1.8 特效元素默认可见规则

`R-RENDER-010` [HARD/SAFETY]：**"从无到有"动画必须使用 GSAP .from() 实现**
- 正向：任何 HTML 元素的静态 CSS 状态（无 animation 时）必须视觉正确
- CSS `animation:` 在 HyperFrames 中不执行，元素以静态状态呈现
- **允许**的 CSS animation：可见位置之间的移动（如 `driftOuter`、`orbDrift`）
- **禁止**的 CSS animation：从不可见到可见（如 `scaleY(0)→1`、`opacity:0→1`、`translateY(-100%)→0`）
- §1.1 的规则不仅适用于 `.layer-content`，也适用于 `.layer-fx` 和 `.layer-bg`

### 1.2 禁止 HTML 实体字符

`R-RENDER-003` [HARD/SAFETY]：**改用 Unicode 字符直接输入**
- 正向：使用 Unicode 字符（`★`、`❤`）或纯文本替代 HTML 实体
- HyperFrames 无头浏览器对实体字符（`&#9733;`、`&#10084;`、`&amp;`）解析不可靠

### 1.3 安全区 padding 必须存在且只设一次

`R-RENDER-004` [HARD/SAFETY]：**每个场景有且仅有一层设置安全区 padding**
- 正向：每个场景设置 `padding: 180px 80px 220px 80px`（上/右/下/左），且只设在一层
- 缺少 padding → 内容贴边缘或渲染塌陷
- 双重 padding → 内容偏左上、可用宽度仅 74%

### 1.4 水平安全边距规则

`R-RENDER-005` [HARD/SAFETY]：**左右各 80px 对称边距**
- 正向：左 80px / 右 80px 对称（兼容抖音/小红书/微信视频号三平台）
- 禁止 `width: 100%` 的内容行没有水平 Padding

### 1.4a 单层 padding 原则（铁律）

`R-RENDER-006` [HARD/SAFETY]：**全项目只允许一个层级设置安全区 padding**
- 正向：`.scene-wrap` 和 `.phase`（或任何内层元素）不同时设置 padding
- 历史事故：`.scene-wrap`(70px) + `.phase`(70px) = 累计 140px/侧，内容仅 800px (74%)
- **`director_gate.py` 会自动检测双重 padding，渲染前必须通过**
- **Spirit：** 防止多层累计 padding 导致内容区域严重压缩

### 1.4b 组件 padding 分类

所有场景分为三类，padding 落在不同层级：

**Phase 模式**（多视觉阶段场景，最常见）
- `.scene-wrap` **不设 padding**
- `.phase` 设置 `padding: 180px 80px 220px 80px; display:flex; flex-direction:column; justify-content:center`
- 结构：`.scene-wrap(无padding)` → `.layer-bg` + `.layer-fx` + `.layer-content` → `.phase(padding+flex居中)`

**自带 padding 组件（full-page 型）**：`hero_card`、`project_full_card`
- 组件自带 `padding: 180px 80px 220px 80px`
- 外层 `.scene-wrap` **不设 padding**

**无 padding 组件（嵌入型）**：其余所有组件
- 组件无外层 padding
- `.scene-wrap` 设置 `padding: 180px 80px 220px 80px`

### 1.5 渲染前移除所有非 index.html 的 composition 文件

`R-RENDER-007` [HARD/SAFETY]：**渲染前将非 index.html 文件重命名为 .renderbak**
- 正向：渲染 index.html 前，将 cover.html 等含 `data-composition-id` 的文件临时重命名
- HyperFrames 不允许多个 root composition
- 渲染完成后恢复需要的文件
- 临时备份文件渲染后必须删除

```bash
# 渲染前
for f in cover.html index_with_bgm.html cover.html.bak; do
  [ -f "$f" ] && mv "$f" "$f.renderbak"
done
# 渲染后
mv cover.html.renderbak cover.html
rm -f index_with_bgm.html.renderbak cover.html.bak.renderbak
```

### 1.6 音频文件必须在项目目录内

`R-RENDER-008` [HARD/SAFETY]：**确保音频文件存在于 index.html 同级目录**
- 正向：渲染前 `ls -la bgm.mp3 narration.mp3` 确认两个音频文件都存在
- HyperFrames 通过 FileServer 提供文件，路径错误 → 404 静音

### 1.7 GSAP timeline 注册是强制要求

`R-RENDER-009` [HARD/SAFETY]：**必须注册 window.__timelines["main"] = tl**
- 正向：引入 GSAP CDN 并注册 timeline，确保 `window.__timelines["main"]` 非空
- `window.__timelines = {};`（空对象）→ 全片空白渲染

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

## 2. 三层渲染架构

> **每个场景必须严格分离为三层。** 这是结构规则，不是样式建议。

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

`R-RENDER-012` [HARD/SAFETY]：**每个场景必须包含三层（bg + fx + content）**
- `.layer-fx` 必须 `pointer-events: none`
- 特效 opacity 建议 0.3-0.6
- `.layer-bg` 至少包含渐变背景 + 1 个光晕

`R-RENDER-014` [HARD/SAFETY]：`.layer-content` 必须设置 `height:100%`

### 2.4 特效层非空规则

`R-RENDER-013` [HARD/EXPERIENTIAL]：**layer-fx 必须包含至少 1 个特效子元素**
- 正向：每个 `.layer-fx` 包含特效子元素（光球/射线/渐变带/矩阵雨/双轨道粒子等）
- 空 layer-fx = 缺少该层 → stage6_gate.sh 拦截
- 最小实现标准：
  - StarBurst（grab/climax）：≥6 条射线 + ≥4 闪烁点
  - LightOrbs（build/summon）：≥3 个光球
  - MatrixRain（build）：≥8 条竖线
  - DualOrbit 粒子（reveal）：≥8 个双层嵌套粒子
  - GradientWave（settle）：≥2 条渐变带
- 特效整体保持低调（光球 0.05-0.12，粒子 0.2-0.35，射线 0.3-0.5）

`R-RENDER-015` [HARD/SAFETY]：**HyperFrames seek 驱动下不使用 requestAnimationFrame**
- 正向：使用 `__hfThreeTime` 替代 `performance.now()`

## Guard — 认知守卫

### Red Flags（停止信号）

| 信号 | 规则 ID | 说明 |
|------|---------|------|
| 使用 `.anim-in` CSS 类 | R-RENDER-001 | 内容永远不可见 |
| HTML 实体字符 | R-RENDER-003 | 整段不渲染 |
| scene-wrap 和 .phase 同时有 padding | R-RENDER-006 | 可用宽度仅 74% |
| 任何层级缺少安全区 padding | R-RENDER-004 | 内容贴边缘 |
| 多个含 `data-composition-id` 的 HTML 文件 | R-RENDER-007 | 渲染冲突 |
| `window.__timelines = {};` 空对象 | R-RENDER-009 | 全片空白 |
| 音频文件不在项目目录内 | R-RENDER-008 | 404 静音 |
| 场景只有两层 | R-RENDER-012 | 特效遮挡 |
| 空的 layer-fx | R-RENDER-013 | §2.4 违规 |
| `.layer-content` 缺少 `height:100%` | R-RENDER-014 | Phase 内容塌陷 |
| 特效 CSS animation 从不可见开始 | R-RENDER-010 | 特效永远不可见 |
| Phase 断点均分 | R-RENDER-011 | 旁白画面不同步 |

### Spirit vs Letter

| 规则 | 模式 | 真实意图 |
|------|------|---------|
| R-RENDER-001 | SPIRIT | 确保 HyperFrames seek 驱动下所有元素正确可见 |
| R-RENDER-006 | SPIRIT | 防止多层累计 padding 导致内容区域严重压缩 |
| R-RENDER-009 | SPIRIT | 确保 HyperFrames 有可执行的 timeline，不渲染空帧 |
| R-RENDER-012 | SPIRIT | 确保内容不被特效遮挡，背景不穿透 |
