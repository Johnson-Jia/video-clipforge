# SubAgent 模板 — 批次 3: video

## 项目上下文
- 项目目录: {{PROJECT_DIR}}（cd 到此目录后再执行所有操作）
- **技能库符号链接**：cd 到项目目录后立即执行 `ln -sf "$(git rev-parse --show-toplevel)/.agents" .agents`
- 输出尺寸: 竖屏 1080×1920
- 视频内不放 URL，项目名称用英文展示
{{EXTRA_CONTEXT}}

## 执行步骤

1. 读取 .claude/commands/clipforge/_shared-rules.md（§2 画面文字语言规范、§7 渲染安全规范）
2. 读取 .claude/commands/clipforge/_render-safety.md（渲染安全完整规范，Stage 6 必读）
3. 读取 .claude/commands/clipforge/stage6-production.md，按指引执行
4. 读取 design.md（视觉风格方向）
5. 读取 segment_durations.json（实际时长，设置 data-duration）
6. 读取 narration_segments.json（场景定义）
7. 编写 HTML + 嵌入 <audio>（narration.mp3 + bgm.wav）
8. BGM data-volume 从 segment_durations.json 的 meta.bgm_volume 读取
9. 渲染 output.mp4 + output_no_bgm.mp4

## 完成后
确认文件: index.html, output.mp4, output_no_bgm.mp4
报告状态: DONE / DONE_WITH_CONCERNS / BLOCKED
