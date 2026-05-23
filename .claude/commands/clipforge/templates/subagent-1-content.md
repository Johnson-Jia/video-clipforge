# SubAgent 模板 — 批次 1: env-check → content → design → narration

## 项目上下文
- 项目目录: {{PROJECT_DIR}}（cd 到此目录后再执行所有操作）
- **技能库符号链接**：cd 到项目目录后立即执行 `ln -sf "$(git rev-parse --show-toplevel)/.agents" .agents`
- 视频模式: {{VIDEO_MODE}}
- 内容类型: {{CONTENT_TYPE}}
- 视频内不放 URL，项目名称用英文展示
- 不涉及 _movie-clips（电影片段）

## 执行步骤

### 1. env-check
用 Read 工具读取 .claude/commands/clipforge/stage0-env.md，按指引执行。环境通常已就绪。

### 2. content
1. 读取 .claude/commands/clipforge/categories/{{CATEGORY}}.md（分类配置，含数据获取策略、选取规则、数据验证）
2. 读取 .claude/commands/clipforge/stage1-content.md，按指引执行
3. 内容来源: {{CONTENT_SOURCE}}
4. 按 categories/{{CATEGORY}}.md 中的 selection_strategy 选取项目

### 3. design
读取 .claude/commands/clipforge/stage2-analysis.md，按指引执行。
参考 categories/{{CATEGORY}}.md 中的 design.default_style，写入 design.md。

### 4. narration
1. 读取 .claude/commands/clipforge/_shared-rules.md（§1 措辞规范、§5 黄金3秒法则）
2. 读取 .claude/commands/clipforge/stage3-scenes.md，按指引执行
3. 读取 design.md 获取风格方向
4. 产出 narration_segments.json + narration.txt

## 完成后
确认以下文件存在: design.md, narration_segments.json, narration.txt
报告状态: DONE / DONE_WITH_CONCERNS / BLOCKED
