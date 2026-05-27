---
id: "clipforge.shared-rules"
description: ClipForge 共享内容规范索引 — 所有阶段必须遵守的跨阶段规则
version: "2.1.0"
type: SPEC
scope: GLOBAL
rules_lib_ref: "_rules-lib/global-rules.yaml"
---

# ClipForge 共享内容规范

> **分段加载：** SubAgent 按需读取对应段落，不加载全文。
> 每条规则与 `_rules-lib/global-rules.yaml` 中的规则 ID 对齐。

| SubAgent | 读取文件 | 内容 |
|----------|---------|------|
| SA-1 (content→narration) | `_shared-rules/writing.md` + `_shared-rules/visual.md` | 措辞规范 + 黄金3秒 + 视觉切换 |
| SA-3 (video) | `_shared-rules/visual.md` + `_shared-rules/render-ref.md` | 画面文字 + 切换频率 + 渲染安全引用 |
| SA-4 (delivery) | `_shared-rules/writing.md` | 措辞规范 + 内容安全 |
