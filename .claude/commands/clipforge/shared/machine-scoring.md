# 即时机器评分（阶段 A）

> delivery 完成后**立即自动执行**。这不是独立 stage，而是 delivery → cleanup 之间的自动评分步骤。由 SubAgent-4 内联调用，不走引擎四原子体系。

## §1 执行流程

1. 逐一运行所有 stage 的 gate 校验
2. 汇总各 stage 的 `hard_passed` 和 `soft_score`
3. 计算综合 `overall_soft_score`
4. 将完整结果写入 `score_report.json`

## §2 score_report.json 结构

```json
{
  "project": "workspace/<YYYY>/<MM>/<DD>/<项目名>",
  "timestamp": "<ISO 8601>",
  "phases": {
    "stage0.5-topic-plan": {"hard_passed": true, "soft_score": 1.0},
    "stage1-content": {"hard_passed": true, "soft_score": 1.0},
    "stage3-scenes": {"hard_passed": true, "soft_score": 1.0},
    "stage4-audio": {"hard_passed": true, "soft_score": 1.0},
    "stage6-production": {"hard_passed": true, "soft_score": 1.0},
    "stage7-delivery": {"hard_passed": true, "soft_score": 1.0}
  },
  "overall_soft_score": 1.0,
  "overall_score": 0.85,
  "freshness": {"freshness_score": 0.7, "hook_sim": 0.3, "project_jaccard": 0.2, "template_sim": 0.4},
  "predicted_plays": {"predicted_plays_score": 0.6, "model_version": "heuristic-v1"},
  "scoring_weights": {"compliance": 0.6, "freshness": 0.3, "predicted": 0.1},
  "hard_passed_all": true,
  "total_stages": 6,
  "stages_passed": 6
}
```

## §3 执行命令

```bash
cd .claude/commands/clipforge
python engine/gate.py --generate-report --project-dir "$PROJECT_DIR"
```

无条件运行全阶段门禁，产出 `$PROJECT_DIR/score_report.json`。
与 stage7 是否通过无关 — 失败的项目更需要评分记录。

## §4 关键原则

- **此时无播放数据、无人类评价** → 仅记录，不触发进化
- `score_report.json` 是机器的**预测分数**
- 后续播放数据和人类评分（Stage 8）会验证这个预测是否准确
- 必须在 cleanup 之前执行，因为 cleanup 可能删除部分中间文件
