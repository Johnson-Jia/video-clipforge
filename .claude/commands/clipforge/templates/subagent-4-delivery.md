---
id: "clipforge.templates.subagent-4-delivery"
name: subagent-4-delivery
description: SubAgent 模板 — 批次 4: delivery → cleanup
version: "2.1.0"
type: TEMPLATE
batch: 4
stages: ["stage7-delivery", "_cleanup-rules"]
---

# SubAgent 模板 — 批次 4: delivery → cleanup

## 项目上下文
- 项目目录: {{PROJECT_DIR}}（cd 到此目录后再执行所有操作）
- **技能库符号链接**：cd 到项目目录后立即执行 `ln -sf "$(git rev-parse --show-toplevel)/.agents" .agents`
- 视频内不放 URL，项目名称用英文展示

## 经验模式注入

执行前运行脚本注入匹配的经验模式：

```bash
bash .claude/commands/clipforge/scripts/inject_patterns.sh "clipforge.stage7-delivery"
```

将输出拼入执行上下文。如果输出"无匹配经验模式"则跳过。

## Part A: delivery — 封面 + 交付 + 三平台文案

1. 读取 .claude/commands/clipforge/_shared-rules/writing.md（§1 措辞规范 + §3 CTA + §4 内容安全）
2. 读取 .claude/commands/clipforge/stage7-delivery.md，按指引执行
3. 读取 .claude/commands/clipforge/categories/{{CATEGORY}}/delivery.md（delivery 配置：各平台标签、评论区模板、封面徽章、数据验证）
4. 读取 design.md 获取风格方向（封面复用视频风格）
5. 封面: 结构约束 + 创意空间，2x 超采样 → 缩放（详见 stage7-delivery.md §7.1）
6. 封面嵌入第一帧: final.mp4 + final_no_bgm.mp4
7. 生成**三平台差异化文案**：
   - 读取 `categories/{{CATEGORY}}/delivery.md` 获取各平台的标签和评论区模板
   - 抖音文案：数据锚定 hook + 泛流量标签 + 项目名列表
   - 视频号文案：专业深度 + 职业标签 + 转发引导
   - 小红书文案：SEO 标题 + 干货列表体 + 搜索标签（8-10个）
   - 输出到 `douyin.md`（含三平台文案，用 `## 抖音` / `## 视频号` / `## 小红书` 分段）

确认文件: cover.png, final.mp4, final_no_bgm.mp4, douyin.md

## Part B: cleanup — 项目清理

> **⛔ 必须通过脚本执行清理，禁止手动 rm。**
> 2026-05-22 和 2026-05-27 两次事故均因手动 rm 删除了保留清单文件。

1. 读取 .claude/commands/clipforge/_cleanup-rules.md（保留清单 + 必删列表）
2. **执行清理脚本**：`bash .claude/commands/clipforge/scripts/cleanup_project.sh "${PROJECT_DIR}"`
3. 如果脚本不可用，按 _cleanup-rules.md 的 §清理前检查点 逐步执行
4. 清理后验证：`ls -la ${PROJECT_DIR}/` 确认保留清单文件仍存在
5. 报告清理前后磁盘占用

确认项目目录仅含保留文件，磁盘占用 < 30 MB。

## Gate — 完成门禁

运行脚本检查：
```bash
bash .claude/commands/clipforge/scripts/check_gates.sh stage7 {{PROJECT_DIR}}
```

### 流程门禁（不通过 = BLOCKED）
- [ ] `cover.png` 存在且非空
- [ ] `final.mp4` 存在且有音频轨
- [ ] `final_no_bgm.mp4` 存在且有音频轨
- [ ] `douyin.md` 存在
- [ ] 项目目录已清理（`.cleaned` 标记存在）

## Trace 采集

执行完成后运行：
```bash
bash .claude/commands/clipforge/scripts/write_trace.sh stage7 {{PROJECT_DIR}} {STATUS} --process_passed=true --compliance_passed=true
```

- **执行结束**：记录封面渲染方式（A/B/C）、文案风格、清理结果
- **质量评价**：`cover_quality` 和 `copy_engagement` 由人类评价（evaluator: HUMAN），无需自动计算
- 确认 trace/ 目录下有对应的 stage trace 文件

## 反馈循环

执行完成后，触发反馈循环脚本：

### 负向闭环（如有 FAILED 阶段）
运行归因分析，结果写入 `_deltas/D-{timestamp}.yaml`：
```bash
# 生成运行汇总
python3 .claude/commands/clipforge/scripts/run_summary.py {{PROJECT_DIR}}
```

### 正向闭环
当所有阶段的 `process_passed: true` AND `compliance_passed: true` 时，记录为"流程完整案例"。
后续由外部数据（播放指标回填）或人工评价决定是否升级为"高分成功案例"。

```bash
# 聚合流程完整的 Trace
python3 .claude/commands/clipforge/scripts/aggregate_traces.py --min_score=0.0 --process_only
```

### 经验模式注入验证
验证注入过滤器配置是否与实际数据一致：
```bash
bash .claude/commands/clipforge/scripts/check_injection_filter.sh
```

### Delta Rules 应用
如果 `_deltas/` 目录存在待应用规则：
```bash
python3 .claude/commands/clipforge/scripts/apply_delta.py
```

## 完成后
报告状态: DONE / DONE_WITH_CONCERNS / BLOCKED
