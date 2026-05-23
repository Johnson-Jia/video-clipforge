# CLAUDE.md

本文件是 Claude Code 的项目入口。

任何视频制作任务前，**必须先阅读 [`.claude/commands/clipforge.md`](.claude/commands/clipforge.md)** — 8 阶段视频管线、DAG 编排和模式选择的权威工作流定义。

## 什么是 ClipForge

ClipForge 是 AI 驱动的通用短视频制作系统。通过 DAG 编排管线，将任意内容（文本、URL、PDF、GitHub 数据等）转化为抖音就绪的竖屏视频，含旁白、BGM 和封面。内容分类（GitHub、漫画、小说等）通过 `clipforge/categories/` 中的分类配置定义。

**核心管线**：`内容 → 设计 → 旁白 → 音频 → 视频 → 交付 → 清理`

## 架构

- `.claude/commands/clipforge.md` — 主控制器：DAG 语义、模式选择、错误恢复
- `.claude/commands/clipforge/schema.yaml` — Artifact DAG 定义（唯一真相源）
- `.claude/commands/clipforge/stage*.md` — 阶段技能文件（通用、自包含的执行指南）
- `.claude/commands/clipforge/categories/` — 分类配置（按分类覆盖数据、风格、音频、交付等规则）
- `.claude/commands/clipforge/_*.md` — 共享规范（内容规范、渲染安全、清理规则、定时续期）
- `.claude/commands/github-*.md` — 定时编排文件（全自动 SubAgent 调度）
- `.claude/commands/clipforge/scripts/` — 工具脚本（趋势抓取、BGM 生成、质量门禁）
- `.claude/commands/clipforge/components/` — 视觉组件库（HTML+CSS+JS 模板）

## 核心原则

1. **Schema 即真相。** 所有 artifact 依赖、产出和完成状态定义在 `schema.yaml` 中，不接受其他来源。
2. **状态即文件。** `generates` 声明的文件存在于磁盘即代表 artifact 完成。无状态数据库。中断后重新运行 `/clipforge` 即自动跳过已完成阶段。
3. **委托，不重写。** HTML 组合和渲染委托给 HyperFrames 技能。
4. **音频内嵌。** 旁白和 BGM 通过 `<audio>` 元素嵌入 HTML，由 HyperFrames 原生混音。
5. **清理不可跳过。** delivery 完成后必须执行 `_cleanup-rules`，无例外。
6. **Stage 文档职责分离。** 操作指令（"做什么"）和事故复盘（"为什么这样做"）严格分离。操作指令只写步骤和命令，事故复盘统一放在 Red Flags 和 Common Rationalizations 部分，不内联在操作步骤中。

## 分类集成

指定分类时，各阶段读取 `categories/{id}.md` 加载分类特定的覆盖规则（数据源、音色、标签等）。通用 stage 文件提供默认值，分类配置只声明差异项。未指定分类时，所有阶段使用内置默认值。

## 命令

| 命令 | 用途 |
|------|------|
| `/clipforge` | 交互式视频制作（手动模式） |
| `/github-daily-trending` | 每日 GitHub 趋势视频（定时任务，全自动） |
| `/github-weekly-trending` | 每周 GitHub 趋势汇总（定时任务，全自动） |
| `/github-weekly-zhihu` | 每周 GitHub 知乎文章（定时任务，全自动） |

## 兼容性

- 本项目是 Claude Code 的技能/工作流包，不是独立应用或 API。
- 视频渲染依赖 [HyperFrames](https://github.com/heygen-com/hyperframes)（通过 `npx skills add` 安装）。
- 与通用编码技能冲突时，以 `clipforge.md` 和本文件为准。
- `workspace/` 是输出目录（已 gitignore），项目产出物存放于此。
