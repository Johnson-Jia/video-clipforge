---
id: "clipforge.templates.subagent-2-audio"
name: subagent-2-audio
description: SubAgent 模板 — 批次 2: audio
version: "2.1.0"
type: TEMPLATE
batch: 2
stages: ["stage4-audio"]
---

# SubAgent 模板 — 批次 2: audio

## 项目上下文
- 项目目录: {{PROJECT_DIR}}（cd 到此目录后再执行所有操作）
- **技能库符号链接**：cd 到项目目录后立即执行 `ln -sf "$(git rev-parse --show-toplevel)/.agents" .agents`

## 经验模式注入

执行前运行脚本注入匹配的经验模式：

```bash
bash .claude/commands/clipforge/scripts/inject_patterns.sh "clipforge.stage4-audio"
```

将输出拼入执行上下文。如果输出"无匹配经验模式"则跳过。

## 执行步骤

1. 读取 .claude/commands/clipforge/stage4-audio.md，按指引执行
2. 读取 .claude/commands/clipforge/categories/{{CATEGORY}}/audio.md（audio 配置：音色和语速）
3. 读取 narration_segments.json（narration artifact 产出）
4. TTS: 按 categories/{{CATEGORY}}/audio.md 的 default_voice 和 default_rate 设置（未指定时使用 YunjianNeural +25%）
5. 分段 TTS 输出 segment_durations.json
6. 配乐从 workspace/bgm/ 选取或 yt-dlp 下载
7. BGM 音量写入 segment_durations.json

## Gate — 完成门禁

运行脚本检查：
```bash
bash .claude/commands/clipforge/scripts/check_gates.sh stage4 {{PROJECT_DIR}}
```

### 流程门禁（不通过 = BLOCKED）
- [ ] `segment_durations.json` 存在且含 actual_duration
- [ ] `narration.mp3` 存在
- [ ] `bgm.wav` 存在

## Trace 采集

执行完成后运行：
```bash
bash .claude/commands/clipforge/scripts/write_trace.sh stage4 {{PROJECT_DIR}} {STATUS} --process_passed={PROCESS} --compliance_passed={COMPLIANCE}
```

- **执行结束**：记录 voice、rate、BGM 来源、loudnorm 结果
- 确认 trace/ 目录下有对应的 stage trace 文件

## 完成后
确认文件: segment_durations.json, narration.mp3, bgm.wav
报告状态: DONE / DONE_WITH_CONCERNS / BLOCKED
