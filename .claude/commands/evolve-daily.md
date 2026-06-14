---
name: evolve-daily
description: 全自动运行 ClipForge 自进化闭环（auto_evolve）——分析播放数据、提炼 pattern/Delta、训练预测模型。无需人工确认，完成后自动续期定时任务。
---

# ClipForge 每日自进化（全自动）

> **全自动执行，不需要人工确认。** 编排模式参见 `clipforge/shared/cron-template.md`。这是反同质化闭环的每日驱动——让真实播放数据回流，校准 score 与 pattern。

## 前置：日期

```bash
export LANG=zh_CN.UTF-8
TODAY=$(date +%Y-%m-%d)
```

## Step 0: 自续期（必须最先执行）

> **铁律：续期在任何工作之前执行。** 无论后续是否成功，续期保证任务不断档。

执行 `clipforge/shared/cron-renew`，任务关键词 `evolve-daily`。

## Step 1: 运行自进化引擎

```bash
cd .claude/commands/clipforge
python scripts/auto_evolve.py
```

auto_evolve 自动完成六阶段：
- **Phase 1**：采集 `workspace/sources/视频数据/` 最新播放数据（collect_performance.py）
- **Phase 2**：跨项目统计 + 相关性计算（留存/收藏/回归归因）
- **Phase 3 / 3.5**：模式提炼（高分→pattern）+ 时效重验（衰减闭环）
- **Phase 4**：Delta 生成（数据洞察→deltas/*.yaml，安全规则自动生效）
- **Phase 5**：阈值校准
- **Phase 6**：播放量预测训练钩子（join 样本 ≥100 自动训练 Ridge 升级启发式，<100 继续启发式，每日 check 不遗忘）

## Step 2: 汇报产出

读 `workspace/sources/evolution-report-${TODAY}.json`，汇报：
- 分析项目数 / 新增 Pattern / 重验 Pattern / 新增 Delta（自动生效的）
- 训练钩子状态：join 样本数 / trained / model_version（heuristic-v1 还是 trained-vN）
- 阈值变更

若近 24h 无新播放数据（`workspace/sources/视频数据/` 无当日目录），简短说明跳过原因，不报错。

## 备注

- **数据来源**：播放数据需用户定期从抖音/B站/视频号/小红书导出到 `workspace/sources/视频数据/YYYY-MM-DD/`。auto_evolve 只分析、不取数据
- **训练升级**：Phase 6 在 join 样本（performance.json × 内容特征）≥100 时自动升级 `predict.py`（启发式→Ridge 回归），模型持久化在 `workspace/evolution/models/`，`score` 自动改用训练模型
- **不遗忘**：即使样本不足，Phase 6 每日 check，达标即训练，无需人工记得
