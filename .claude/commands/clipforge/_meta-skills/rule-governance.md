---
name: rule-governance
description: 规则库治理 — 保持规则库健康：无冲突、无冗余、不过时
version: "1.0.0"
type: EXECUTIVE
rigor: STANDARD
---

# 元 Skill：规则库治理

## Intent
> 保持规则库健康：无冲突、无冗余、不过时。
> 成功标准：冲突率 = 0，冗余率 < 5%，过时规则已清理。

## Boundary — 行为准则

### 必须遵守（HARD 规则 · 正向重述）

1. **保护有效规则** — 命中次数 > 0 的规则，删除前必须人工确认 ← `R-GOV-001`
   ↳ 校验：hit_count > 0 的规则未被自动 REMOVED
2. **控制瘦身幅度** — 单次治理瘦身删除不超过规则总量的 20% ← `R-GOV-002`
   ↳ 校验：单次 REMOVED Delta 数量 ≤ 总量 × 0.2
3. **保护安全规则** — `class: SAFETY` 的规则不允许 REMOVED 操作，只能 DEPRECATED ← `R-GOV-003`
   ↳ 校验：无 SAFETY 规则的 REMOVED Delta
4. **影子校验必过** — 任何 Delta Rule 生效前必须用最近 50 条 Trace 重放，确认不恶化 ← `R-GOV-004`
   ↳ 校验：影子校验通过率 ≥ 100%（无新增误杀）

### 建议参考（偏好）
- 优先处理高命中率规则的优化（HIGH）
- 冗余合并时保留更精确的规则（MEDIUM）
- 废弃规则保留数据，仅标记 DEPRECATED（MEDIUM）

## Guard — 认知守卫

| 当你产生这个念头 | 现实是 | 触发行为 |
|---|---|---|
| "这条规则很久没命中了，删了吧" | 可能是季节性规则，需要确认 | 检查历史命中趋势 |
| "这两条差不多，合并掉" | 细微差异可能有重要区分 | 逐字比对 pattern 和 guardrail |
| "规则太多了，大刀砍一批" | 单次瘦身超 20% 风险过高 | 分批次，每批 ≤ 20% |

### Spirit vs Letter
| 规则 | 解释模式 | 真实意图 |
|---|---|---|
| R-GOV-001 | SPIRIT | 防止误删仍在发挥防护作用的规则 |
| R-GOV-003 | SPIRIT | 安全红线是组织底线，不可通过治理流程消除 |

## Gate — 通过标准

### 流程门禁（不通过 = 驳回）
- [ ] `governance_compliance` — 无 SAFETY 规则被 REMOVED，hit_count > 0 的规则删除有人工确认
- [ ] `slim_proportion` — 单次瘦身删除 ≤ 总量 20%
- [ ] `shadow_validation` — 所有 Delta Rule 通过影子校验

### 质量门禁（创意评价，不通过 = 记录但放行）
- `governance_efficiency`: 冲突率 + 冗余率评分 ≥ 0.7

## Trace — 采集点
- 治理开始：记录规则库总量、各 class/severity 分布
- 每次 Delta：记录 operation、target_rule、confidence
- 治理结束：记录删除/修改/废弃数量，写入 trace/

## 操作指令

### 治理动作清单

| 动作 | 频率 | Delta 操作 | 说明 |
|------|------|-----------|------|
| 冲突检测 | 每周 | — | 发现互斥规则，人工裁决后产出 MODIFIED Delta |
| 冗余合并 | 每两周 | MODIFIED + DEPRECATED | 语义相近的规则合并，旧规则 DEPRECATED |
| 过时清理 | 每月 | DEPRECATED | 业务已变更的规则标记废弃 |
| 效果评估 | 每月 | — | 每条规则的命中率、误杀率、置信度 |
| 膨胀检查 | 每周 | REMOVED（仅 EXPERIENTIAL） | 单场景规则数 > 80 时预警 |
| 约束分类复核 | 每季度 | MODIFIED | 重新评估 SAFETY / EXPERIENTIAL 分类 |

### Delta 治理流水线

```
治理分析 → 产出 Delta 候选
    → 影子校验（用最近 50 条 Trace 重放，确认不恶化）
    → 审核决策（confidence ≥ 0.7 且 EXPERIENTIAL → 可自动；其余 → 人工）
    → Delta 生效 → 规则库更新
    → 生效后监控 7 天（误杀率、通过率）
    → 异常则自动回滚 Delta
```

### 规则膨胀熔断

- 单场景上限 100 条，触达时强制触发瘦身
- 瘦身产出 REMOVED Delta（仅 EXPERIENTIAL 规则，命中率 0 且存活 > 60 天）
- SAFETY 规则不参与自动淘汰，产出 DEPRECATED Delta 待人工评审
- 每条 Delta 淘汰前需人工确认（防止误删季节性规则）

## Red Flags

| 信号 | 说明 |
|------|------|
| 自动删除了 hit_count > 0 的规则 | 有效规则被误删，可能导致已知问题复发 |
| 单次瘦身超过 20% | 激进瘦身可能误删低频但重要的规则 |
| SAFETY 规则被 REMOVED | 安全红线不可通过治理流程消除 |
| 跳过影子校验直接生效 | 未经验证的变更可能导致误杀率飙升 |

## Common Rationalizations

| 借口 | 事实 |
|------|------|
| "这条规则好久没用了" | 低频 ≠ 无用，可能是季节性规则或低频但关键的防护 |
| "规则太多了影响性能" | 性能问题通过检索优化，不是通过删规则 |
| "差不多就合并吧" | 细微差异可能对应重要的场景区分 |
