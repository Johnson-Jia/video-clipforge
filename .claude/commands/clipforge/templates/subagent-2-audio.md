# SubAgent 模板 — 批次 2: audio

## 项目上下文
- 项目目录: {{PROJECT_DIR}}（cd 到此目录后再执行所有操作）
- **技能库符号链接**：cd 到项目目录后立即执行 `ln -sf "$(git rev-parse --show-toplevel)/.agents" .agents`

## 执行步骤

1. 读取 .claude/commands/clipforge/stage4-audio.md，按指引执行
2. 读取 .claude/commands/clipforge/categories/{{CATEGORY}}.md（audio 配置：音色和语速）
3. 读取 narration_segments.json（narration artifact 产出）
4. TTS: 按 categories/{{CATEGORY}}.md 的 audio.default_voice 和 audio.default_rate 设置（未指定时使用 YunjianNeural +25%）
5. 分段 TTS 输出 segment_durations.json
6. 配乐从 workspace/bgm/ 选取或 yt-dlp 下载
7. BGM 音量写入 segment_durations.json

## 完成后
确认文件: segment_durations.json, narration.mp3, bgm.wav
报告状态: DONE / DONE_WITH_CONCERNS / BLOCKED
