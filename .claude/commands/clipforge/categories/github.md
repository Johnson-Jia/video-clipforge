---
name: "GitHub 开源项目"
description: "GitHub Trending 热门项目盘点和深度解析视频"
id: "github"
version: "2.1.0"
type: CATEGORY
category_id: "github"
---

# GitHub 分类配置

> **分段加载：** SubAgent 按需读取对应阶段文件，不加载全文。

| SubAgent | 读取文件 | 内容 |
|----------|---------|------|
| SA-1 (content→narration) | `categories/github/content-design-narration.md` | 数据获取、选取策略、设计风格、旁白规则、叙事模板 |
| SA-2 (audio) | `categories/github/audio.md` | 音色、语速 |
| SA-4 (delivery→cleanup) | `categories/github/delivery.md` | 标签、评论区、封面、数据验证 |

> **完整规则引用：** 分类特有规则（R-GITHUB-001~008）定义在 `content-design-narration.md` 的 Boundary Overrides 段。
