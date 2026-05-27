---
id: "clipforge.templates.subagent-3-video"
name: subagent-3-video
description: SubAgent 模板 — 批次 3: video
version: "2.1.0"
type: TEMPLATE
batch: 3
stages: ["stage6-production"]
---

# SubAgent 模板 — 批次 3: video

## 项目上下文
- 项目目录: {{PROJECT_DIR}}（cd 到此目录后再执行所有操作）
- **技能库符号链接**：cd 到项目目录后立即执行 `ln -sf "$(git rev-parse --show-toplevel)/.agents" .agents`
- 输出尺寸: 竖屏 1080×1920
- 视频内不放 URL，项目名称用英文展示
{{EXTRA_CONTEXT}}

## 经验模式注入

执行前运行脚本注入匹配的经验模式：

```bash
bash .claude/commands/clipforge/scripts/inject_patterns.sh "clipforge.stage6-production"
```

将输出拼入执行上下文。如果输出"无匹配经验模式"则跳过。

## 执行步骤

1. 读取 .claude/commands/clipforge/_shared-rules/visual.md（§2 画面文字 + §5 黄金3秒 + §6 视觉切换）
2. 读取 .claude/commands/clipforge/_shared-rules/render-ref.md（§7 渲染安全引用）
3. 读取 .claude/commands/clipforge/_render-safety.md（渲染安全完整规范，Stage 6 必读）
4. 读取 .claude/commands/clipforge/stage6-production.md，按指引执行
5. 读取 .claude/commands/clipforge/stage6-components.md（组件索引，按需读取具体组件文件）
6. 如需视觉设计参考，读取 .claude/commands/clipforge/stage6-components-ref.md
7. 读取 .claude/commands/clipforge/_director-toolkit/vocabulary.md（视觉词汇表）
8. 读取 .claude/commands/clipforge/_director-toolkit/cases.md（爆款案例解码）
9. 读取 design.md（视觉风格方向）
10. 读取 segment_durations.json（实际时长，设置 data-duration）
11. 读取 narration_segments.json（场景定义）
12. 编写 HTML + 嵌入 <audio>（narration.mp3 + bgm.wav）
13. BGM data-volume 从 segment_durations.json 的 meta.bgm_volume 读取
14. 渲染 output.mp4 + output_no_bgm.mp4

## Gate — 完成门禁

运行脚本检查：
```bash
bash .claude/commands/clipforge/scripts/check_gates.sh stage6 {{PROJECT_DIR}}
```

### 流程门禁（不通过 = BLOCKED）
- [ ] `index.html` 存在
- [ ] `output.mp4` 存在且有音频轨
- [ ] `output_no_bgm.mp4` 存在且有音频轨（仅旁白）

## Trace 采集

执行完成后运行：
```bash
bash .claude/commands/clipforge/scripts/write_trace.sh stage6 {{PROJECT_DIR}} {STATUS} --process_passed={PROCESS} --compliance_passed={COMPLIANCE}
```

- 质量门禁（visual_quality）为 `evaluator: HUMAN`，由人工评价后回填 `--quality_score=X --quality_evaluator=HUMAN`
- **执行结束**：记录渲染次数、失败原因、路径切换、最终通过状态
- 确认 trace/ 目录下有对应的 stage trace 文件

## 完成后
确认文件: index.html, output.mp4, output_no_bgm.mp4
报告状态: DONE / DONE_WITH_CONCERNS / BLOCKED
