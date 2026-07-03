# ClipForge Cinema 后处理配方库（cinema 层）

> Stage 6 参考。配套 `render-safety.md` §2（四层架构）、`stage6-components.md`。
> 本文专注 **cinema 后处理层**——全帧签名质感（颗粒/暗角/光晕/色差），让视频脱离「精致 PPT」的干净感。

## §0 使用约定

- cinema 层是**可选签名层**（z-index 4，`.layer-cinema`）。快速播报不强制每场景用；用于质感档期（深度解析主力、快速盘点可选）。
- 原语是 BASE_CSS 预定义 class（`.cinema-xxx`，定义在 `s6_assemble_html.py` BASE_CSS 段），LLM 在 `.layer-cinema` 内 `<div class="cinema-vignette"></div>` 直接引用，无需写 CSS。
- **Cinema 测试（铁律）**：移除该效果，帧是否丢*信息*或*签名*？两者都不丢 → 剪掉。同一效果用在每帧是装饰不是签名。
- 每视频选 **1-2 个签名**，不要堆砌。cinema 层 `pointer-events:none`，不遮 content。
- 入场用 GSAP `.set()+.to()`（禁 `.from()`，R-S6-026）；`cinema-lightflash` 触发式用 `.to()` 控 opacity。

## §1 HyperFrames 兼容

- `mix-blend-mode: screen/overlay` — HyperFrames 截帧支持，GPU 加速。
- SVG `feTurbulence`（cinema-grain）— 内联 data URI，浏览器渲染生成 noise，截帧可捕获。静态（不换 seed）性能良好。
- `filter: drop-shadow()` 叠加（cinema-aberration）— 比 SVG feColorMatrix 便宜，全帧廉价色差。

## §2 核心原语（BASE_CSS 预定义）

### §2.1 暗角 vignette（聚焦/收紧）

```html
<!-- 嵌入 .layer-cinema -->
<div class="cinema-vignette"></div>
```
**适用**：聚焦中心内容（项目卡片/数字）、论点收紧时强化。静态，无需 GSAP。

### §2.2 胶片颗粒 grain（胶片质感）

```html
<div class="cinema-grain"></div>
```
**适用**：全片底色胶片感（脱离数字干净感）。静态 overlay，opacity .09 已调好（过亮抢眼）。

### §2.3 暖光环绕 halation（暖色签名）

```html
<div class="cinema-halation"></div>
```
**适用**：暖金/琥珀主题（goldminer 暖金风），或情绪高潮段。screen 混合，暖光从下部晕开。

### §2.4 光闪 lightflash（论点落地冲击，触发式）

```html
<div class="cinema-lightflash"></div>
```
```js
// GSAP 触发（默认 opacity:0，论点落地帧闪一下）
tl.to('.cinema-lightflash', {opacity: 0.8, duration: 0.12, ease: EASE.tension}, startTime)
  .to('.cinema-lightflash', {opacity: 0, duration: 0.25, ease: EASE.standard}, startTime + 0.12);
```
**适用**：论点/数据落地瞬间的廉价冲击。**每视频最多 1-2 次**（滥用=廉价）。

### §2.5 色差 aberration（数据失真科技感）

```html
<div class="cinema-aberration"></div>
```
**适用**：科技/AI/数据主题（github-trending），全帧轻微 RGB 分离。drop-shadow 廉价版（参数 1.5px 已调好，过大糊小字边缘）。

## §4 场景 → cinema 签名映射

| 场景类型 | 推荐 cinema 原语 | 说明 |
|---------|-----------------|------|
| 项目卡片展示 | vignette | 聚焦卡片，暗化边缘杂讯 |
| hook 冲击（大数字/反差） | lightflash + vignette | 落地闪一下 + 聚焦 |
| 数据/科技主题 | aberration + grain | 失真感 + 胶片底色 |
| 暖金主题（goldminer） | halation | 暖光签名 |
| CTA/收束 | vignette | 收紧聚焦结论 |

## §5 验证记录

| 原语 | 状态 | 验证方式 | 日期 |
|------|------|---------|------|
| vignette / grain / lightflash | ✅ 已验证 | `workspace/test/cinema-github/` PIL 像素实证：vignette 暗角比 0.848（中心边缘 6.5×）/ grain 邻差 4.31×（SVG feTurbulence 真渲染）/ lightflash 闪峰 +50.8 | 2026-07-03 |
| halation / aberration | ✅ 已验证 | 同上端到端渲染（HyperFrames 截帧兼容 mix-blend-mode:screen/overlay + drop-shadow） | 2026-07-03 |

> 验证要点：cinema 原语全部在 HyperFrames（Puppeteer 截帧）正常渲染，CSS 兼容性确认。SVG `feTurbulence` data URI 的 `%23`/`%25` 转义正确，grain 噪点客观可见（PIL 邻差 4.31×）。
