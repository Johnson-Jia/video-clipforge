# SubAgent 模板 — 批次 4: delivery → cleanup

## 项目上下文
- 项目目录: {{PROJECT_DIR}}（cd 到此目录后再执行所有操作）
- **技能库符号链接**：cd 到项目目录后立即执行 `ln -sf "$(git rev-parse --show-toplevel)/.agents" .agents`
- 视频内不放 URL，项目名称用英文展示

## Part A: delivery — 封面 + 交付 + 抖音文案

1. 读取 .claude/commands/clipforge/_shared-rules.md（§1 措辞规范、§2 画面文字语言规范）
2. 读取 .claude/commands/clipforge/stage7-delivery.md，按指引执行
3. 读取 .claude/commands/clipforge/categories/{{CATEGORY}}.md（delivery 配置：标签、评论区模板、封面徽章）
4. 读取 design.md 获取风格方向（封面复用视频风格）
5. 封面: 6 层模板 + 双色光晕 + 渐变背景，2x 超采样 → 缩放
6. 封面嵌入第一帧: final.mp4 + final_no_bgm.mp4
7. 生成 3 套抖音文案，标签使用 categories/{{CATEGORY}}.md 的 delivery.hashtags

确认文件: cover.png, final.mp4, final_no_bgm.mp4, douyin.md

## Part B: cleanup — 项目清理

1. 读取 .claude/commands/clipforge/_cleanup-rules.md，按指引执行完整清理
2. bgm.wav 如来自 workspace/bgm/ 素材库，删除项目副本
3. 报告清理前后磁盘占用

确认项目目录仅含保留文件，磁盘占用 < 30 MB。
报告状态: DONE / DONE_WITH_CONCERNS / BLOCKED
