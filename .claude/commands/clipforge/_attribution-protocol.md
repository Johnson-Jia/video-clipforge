# 归因协议（Attribution Protocol）

> 负向闭环核心：失败 → 归因 → 规则回流
> 本协议定义失败案例的根因判定流程和规则变更产出机制。

## Intent
> 准确判定失败案例的根因，产出可信的规则变更提案（Delta Rule）。
> 成功标准：强归因自动完成，弱归因置信度 ≥ 0.7。

## 自动触发条件

**何时执行归因：**

1. **SubAgent 批次完成后**：在 `run_summary.py` 生成汇总之前
2. **触发条件**：`run-summary.yaml` 中任一阶段 `status: FAILED`
3. **执行位置**：由 `subagent-4-delivery.md` 的"反馈循环"段触发
4. **脚本调用**：
   ```bash
   # 1. 生成运行汇总（检测是否有 FAILED）
   python3 .claude/commands/clipforge/scripts/run_summary.py {PROJECT_DIR}

   # 2. 如果有 FAILED，执行归因（人工或自动化）
   # 归因逻辑见下方"双层归因模型"
   ```

## Trace 数据来源

归因协议消费以下 Trace 数据：

- **阶段 Trace**：`{PROJECT_DIR}/trace/stage{N}-{timestamp}.yaml`
  - `gate_report.process_passed: false` 或 `gate_report.compliance_passed: false` → 触发强归因
  - `gate_report.hard_violations` → 违规规则列表
  - `execution.constraint_hits` → 触碰的规则和采取的动作
- **运行汇总**：`{PROJECT_DIR}/trace/run-summary.yaml`
  - `stages[].status: FAILED` → 识别失败阶段

格式定义详见 `_trace-format.md`

## 双层归因模型

### 强归因层（Strong Attribution — 自动执行）

当流程/合规门禁违规时，首先尝试强归因（确定性推理）：

```
门禁违规案例
    │
    ▼
Q: 已有规则是否覆盖此违规？
    │
    ├─ 是 → "rule_hit"（规则命中）
    │       → 检查检测精度：是否存在漏检？
    │       → 动作：OPTIMIZE_DETECTION 或 STRENGTHEN_RULE
    │       → 自动执行，不需人工确认
    │
    └─ 否 → 无法在强归因层结案，进入弱归因层
```

**强归因产出格式**：
```yaml
attribution:
  layer: STRONG
  root_cause: "rule_hit"
  matched_rule: "R-GLOBAL-003"
  detection_gap: "关键词表未覆盖'绝绝子'变体"
  action:
    type: "OPTIMIZE_DETECTION"
    requires_human_review: false
```

### 弱归因层（Weak Attribution — 需置信度）

当强归因无法结案时，进入弱归因（因果推断）：

```
Q: 根因是什么？
    │
    ├─ rule_missing → 场景无规则覆盖
    │   → 产出 Delta Rule 候选（新增规则）
    │   → 置信度 ≥ 0.7 且 class=EXPERIENTIAL → 可自动执行
    │   → 否则 → 标记待人工确认
    │
    ├─ capability_gap → 模型本身无法完成此任务
    │   → 归档，不回流到规则库
    │   → 记录到能力边界清单
    │
    └─ rule_violation → Agent 故意绕过已有规则
        → 加强 Red Flags 表
        → 考虑提升规则 severity
```

**弱归因产出格式**：
```yaml
attribution:
  layer: WEAK
  root_cause: "rule_missing"
  confidence: 0.85
  evidence:
    - "Trace 中无已有规则的触碰记录"
    - "同类场景历史上 3 次出现相似违规"
    - "违规模式可提炼为通用 FORBIDDEN_ACTION"
  action:
    type: "NEW_RULE"
    candidate:
      id: "R-STAGE6-015"
      type: FORBIDDEN_ACTION
      pattern: "..."
      severity: HARD
      class: EXPERIENTIAL
      scope: SKILL
  requires_human_review: false  # confidence ≥ 0.7 自动执行
```

## Delta Rule 产出格式

所有规则变更通过 Delta Rule 表达（增量，非全量替换）：

```yaml
delta:
  id: "D-{timestamp}-{seq}"
  operation: ADDED | MODIFIED | REMOVED | DEPRECATED
  target_rule: "R-xxx"           # MODIFIED/REMOVED/DEPRECATED 时指定
  source: "attribution:T-xxx"    # 变更来源（Trace ID）
  confidence: 0.85               # 变更置信度
  approved_by: null              # null=待审核, "human:xxx"=已审核, "auto"=自动

  # ADDED 时包含完整新规则
  new_rule:
    id: "R-STAGE6-015"
    type: FORBIDDEN_ACTION
    pattern: "..."
    positive: "..."
    guardrail: "..."
    severity: HARD
    class: EXPERIENTIAL
    scope: SKILL

  # MODIFIED 时包含变更字段
  # modified_fields:
  #   pattern:
  #     old: "旧值"
  #     new: "新值"

  # DEPRECATED 时包含替代方案
  # superseded_by: "R-xxx"
  # reason: "被更精确的规则替代"
```

**Delta 操作安全约束**：

| 操作 | 可自动执行 | 限制 |
|------|-----------|------|
| ADDED | confidence ≥ 0.7 且 class=EXPERIENTIAL | SAFETY 规则需人工确认 |
| MODIFIED | confidence ≥ 0.7 且非 SAFETY 规则 | — |
| REMOVED | 仅 EXPERIENTIAL 且命中率 0 持续 60 天 | SAFETY 不可 REMOVED |
| DEPRECATED | 任意 | 不删除数据 |

**生效前校验**：影子校验（用最近 50 条 Trace 重放，确认变更不导致误杀率上升）

## 安全机制

| 机制 | 触发条件 | 动作 |
|------|---------|------|
| 人工审核 | 置信度 < 0.7 | 暂停自动回流，标记待人工确认 |
| 归因熔断 | 近 30 天归因争议率 > 30% | 全局暂停自动归因，进入人工审查期 |
| 规则回滚 | 新增规则后误杀率 > 20% | 自动回滚到上一版本，标记待优化 |
| 归因溯源 | — | 每条规则可查到来源 Trace |

## 置信度评分参考

| 证据强度 | 置信度范围 | 说明 |
|---------|-----------|------|
| 强（多条 Trace + 历史同类） | 0.85-0.95 | 可自动执行 |
| 中（单条 Trace + 逻辑推导） | 0.70-0.84 | 可自动执行（EXPERIENTIAL） |
| 弱（推测 + 少量间接证据） | 0.50-0.69 | 必须人工确认 |
| 极弱（纯推测） | < 0.50 | 归档，不产出 Delta |
