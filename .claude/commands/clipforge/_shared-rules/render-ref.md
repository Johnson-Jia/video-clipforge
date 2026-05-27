---
section: "render-ref"
consumers: ["subagent-3"]
---

# 共享规范 — 渲染安全引用

> 仅 SubAgent-3（video）读取。核心禁令摘要，详细规则见 `_render-safety.md`。
> 完整规则 ID：`_rules-lib/video-production-rules.yaml`（R-RENDER-001 ~ R-RENDER-015）。

## 7. 渲染安全 + 三层架构

- `R-RENDER-001`：**禁止 CSS `.anim-in` / `opacity:0` 入场** — HyperFrames seek 不执行 CSS animation
- `R-RENDER-003`：**禁止 HTML 实体字符** — 改用 Unicode 直接输入（`★` 而非 `&#9733;`）
- `R-RENDER-006`：**安全区 padding 只设一层** — `.scene-wrap` 或 `.phase` 二选一（详见 `_render-safety.md` §1.4a）
- `.phase` 统一使用 `display:flex;flex-direction:column;justify-content:center` 垂直居中
- `R-RENDER-007`：**渲染前移除非 index.html 的 HTML 文件** — 避免 multiple_root_compositions 冲突
- `R-RENDER-012`：**每个场景必须三层** — `.layer-bg`(z:1) + `.layer-fx`(z:2) + `.layer-content`(z:3)
