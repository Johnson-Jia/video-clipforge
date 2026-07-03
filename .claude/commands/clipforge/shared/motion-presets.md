# ClipForge 运动预设（Williams 12 原则→代码）

> Stage 6 参考。配套 `stage6-production.md` GSAP 模板。
> 本文定义 4 个命名 ease 寄存器（替代散落 magic number）+ moving hold 铁律，根治「PPT 线性运动感」。

## §0 使用约定

- 4 预设由 `s6_assemble_html.py` 自动注入每个 index.html 的 JS 常量（`const EASE = {...}`），LLM 直接用 `ease: EASE.standard`，**禁裸 `linear`/`power0`/`none`**（PPT 运动根源，`director_gate` warn）。
- **运动间距 > 时序**：同样 duration，不同 ease（间距分布）= 完全不同的生命感。线性均匀间距 = PPT 的视觉签名（Williams）。
- 入场用 `.set()+.to()`（禁 `.from()`，R-S6-026）。

## §1 四预设（GSAP ease 寄存器）

`s6_assemble_html.py` 在 GSAP 骨架注入：
```js
const EASE = {
  standard: 'power2.out',    // 中性构建（通用入场）
  tension:  'back.out(1.4)', // 张力，快攻+可见过冲（问题揭示/惊讶）
  resolve:  'power3.out',    // 释放，慢控无弹（洞察交付/CTA）
  ambient:  'sine.inOut'     // 呼吸/循环，从不沉淀（背景持续动画）
};
```

| 预设 | 用途 | 时长建议 |
|------|------|---------|
| `EASE.standard` | 通用入场（标题/卡片/数字出现） | 0.8-1.2s |
| `EASE.tension` | 张力揭示（问题/反差/惊讶，带过冲） | 0.4-0.7s |
| `EASE.resolve` | 释放沉淀（洞察/结论/CTA，慢控） | 1.2-2s |
| `EASE.ambient` | 循环呼吸（背景/粒子/光晕持续） | 2-4s，`repeat:-1 yoyo:true` |

**选择逻辑**：构建/出现→standard；揭示/冲击→tension；交付/沉淀→resolve；循环/氛围→ambient。

## §2 moving hold 铁律

**静止永不真正冻结**——否则元素「死在屏幕上」（Williams moving hold）。所有「静止态」加慢漂移/呼吸：

```js
// 静止元素加 breathe（永不冻结）
gsap.to('.hero-num', {scale: 1.03, duration: 3, ease: EASE.ambient, yoyo: true, repeat: -1});
// 或慢漂移
gsap.to('.card', {x: '+=4', duration: 4, ease: EASE.ambient, yoyo: true, repeat: -1});
```

**禁**：元素入场后 `opacity:1` 完全静止、无任何后续动画（死帧）。

## §3 GSAP 用法

```js
// 入场（standard 构建）
tl.set('.title', {opacity: 0, y: 30}).to('.title', {opacity: 1, y: 0, duration: 1.0, ease: EASE.standard}, startTime);
// 张力揭示（tension 过冲）
tl.to('.reveal', {opacity: 1, scale: 1, duration: 0.5, ease: EASE.tension}, startTime + 0.3);
// 释放沉淀（resolve 慢控）
tl.to('.cta', {opacity: 1, duration: 1.5, ease: EASE.resolve}, startTime + 1.2);
// 循环呼吸（ambient）
gsap.to('.aura', {scale: 1.1, duration: 3, ease: EASE.ambient, yoyo: true, repeat: -1});
```

## §4 验证记录

| 预设 | 状态 | 验证方式 | 日期 |
|------|------|---------|------|
| standard/tension/resolve/ambient | ✅ 已验证 | `workspace/test/cinema-github/` 端到端：standard×5（入场）/ tension×5（张力揭示）/ resolve×3（CTA 沉淀）/ ambient×18（循环呼吸）替换裸 sine.inOut，director_gate 无 linear warn，GSAP 执行正常 | 2026-07-03 |

> 验证要点：4 预设在 build_gsap 自动注入的 `const EASE` 常量上工作，HyperFrames seek 渲染下 ease 曲线正确呈现；moving hold（hk-num/pfc-stars-num 慢呼吸）替代死帧。
