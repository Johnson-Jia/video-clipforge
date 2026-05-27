---
id: "clipforge.templates.subagent-1-content"
name: subagent-1-content
description: SubAgent 模板 — 批次 1: env-check → content → design → narration
version: "2.1.0"
type: TEMPLATE
batch: 1
stages: ["stage0-env", "stage1-content", "stage2-analysis", "stage3-scenes"]
---

# SubAgent 模板 — 批次 1: env-check → content → design → narration

## 项目上下文
- 项目目录: {{PROJECT_DIR}}（cd 到此目录后再执行所有操作）
- **技能库符号链接**：cd 到项目目录后立即执行 `ln -sf "$(git rev-parse --show-toplevel)/.agents" .agents`
- 视频模式: {{VIDEO_MODE}}
- 内容类型: {{CONTENT_TYPE}}
- 视频内不放 URL，项目名称用英文展示
- 不涉及 _movie-clips（电影片段）

## 经验模式注入

执行前运行脚本注入匹配的经验模式：

```bash
bash .claude/commands/clipforge/scripts/inject_patterns.sh "clipforge.stage3-scenes"
```

将输出拼入执行上下文。如果输出"无匹配经验模式"则跳过。

## 执行步骤

### 1. env-check
用 Read 工具读取 .claude/commands/clipforge/stage0-env.md，按指引执行。环境通常已就绪。

### 2. content
1. 读取 .claude/commands/clipforge/categories/{{CATEGORY}}/content-design-narration.md（分类配置，含数据获取策略、选取规则、数据验证）
2. 读取 .claude/commands/clipforge/stage1-content.md，按指引执行
3. 内容来源: {{CONTENT_SOURCE}}
4. 按 content-design-narration.md 中的 selection_strategy 选取项目

### 3. design
1. 读取 .claude/commands/clipforge/stage2-analysis.md，按指引执行
2. 读取 .claude/commands/clipforge/_director-toolkit/questions.md（导演 5 个必答题）
3. 读取 .claude/commands/clipforge/_director-toolkit/cases.md（爆款案例解码）
4. 参考 content-design-narration.md 中的 design.default_style，写入 design.md

### 4. narration
1. 读取 .claude/commands/clipforge/_shared-rules/writing.md（§1 措辞规范 + §3 CTA + §4 内容安全）
2. 读取 .claude/commands/clipforge/_shared-rules/visual.md（§2 画面文字 + §5 黄金3秒 + §6 视觉切换）
3. 读取 .claude/commands/clipforge/stage3-scenes.md，按指引执行
4. 读取 design.md 获取风格方向
5. 产出 narration_segments.json + narration.txt

## Gate — 完成门禁

运行脚本检查：
```bash
bash .claude/commands/clipforge/scripts/check_gates.sh stage3 {{PROJECT_DIR}}
```

### 流程门禁（不通过 = BLOCKED）
- [ ] `design.md` 存在
- [ ] `narration_segments.json` 存在
- [ ] `narration.txt` 存在

## Trace 采集

每个阶段完成后运行：
```bash
bash .claude/commands/clipforge/scripts/write_trace.sh {STAGE_ID} {{PROJECT_DIR}} {STATUS} --process_passed={PROCESS} --compliance_passed={COMPLIANCE}
```

- **执行开始**：记录 video_mode、content_type、category
- **每个阶段**：记录 status（PASSED/FAILED）、duration
- **执行结束**：确认 trace/ 目录下有对应的 stage trace 文件

## 完成后
确认以下文件存在: design.md, narration_segments.json, narration.txt
报告状态: DONE / DONE_WITH_CONCERNS / BLOCKED
