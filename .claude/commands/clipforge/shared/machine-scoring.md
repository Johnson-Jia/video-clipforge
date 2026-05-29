# 即时机器评分（阶段 A）

> delivery 完成后**立即自动执行**。这不是独立 stage，而是 delivery → cleanup 之间的自动评分步骤。
>
> **架构说明**：machine-scoring 是 `schema.yaml` 中的正式 artifact，但不走引擎四原子体系（无独立 skills YAML / rules YAML）。它通过 `shared/machine-scoring.md` 直接加载执行，由 SubAgent-4 内联调用。

## 执行流程

1. 逐一运行所有 stage 的 gate 校验
2. 汇总各 stage 的 `hard_passed` 和 `soft_score`
3. 计算综合 `overall_soft_score`
4. 将完整结果写入 `score_report.json`

## score_report.json 结构

```json
{
  "project": "workspace/2026/05/29/my-project",
  "timestamp": "2026-05-29T15:30:00Z",
  "phases": {
    "stage1-content": {"hard_passed": true, "soft_score": 1.0},
    "stage3-scenes": {"hard_passed": true, "soft_score": 1.0},
    "stage4-audio": {"hard_passed": true, "soft_score": 1.0},
    "stage6-production": {"hard_passed": true, "soft_score": 1.0},
    "stage7-delivery": {"hard_passed": true, "soft_score": 1.0}
  },
  "overall_soft_score": 1.0,
  "hard_passed_all": true,
  "total_stages": 5,
  "stages_passed": 5
}
```

## 执行命令

```bash
cd .claude/commands/clipforge
for skill in stage1-content stage3-scenes stage4-audio stage6-production stage7-delivery; do
  python engine/gate.py --skill "$skill" --project-dir "$PROJECT_DIR" 2>/dev/null
done
```

将各 stage 结果汇总写入 `$PROJECT_DIR/score_report.json`。

## 关键原则

- **此时无播放数据、无人类评价** → 仅记录，不触发进化
- `score_report.json` 是机器的**预测分数**
- 后续播放数据和人类评分（Stage 8）会验证这个预测是否准确
- 必须在 cleanup 之前执行，因为 cleanup 可能删除部分中间文件
