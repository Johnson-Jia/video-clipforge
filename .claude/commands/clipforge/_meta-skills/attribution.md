---
name: attribution
description: 归因判定 — 准确判定失败案例的根因，产出可信的规则变更提案
version: "1.0.0"
type: ANALYTICAL
rigor: STRICT
---

# 元 Skill：归因判定

## Intent
> 准确判定失败案例的根因，产出可信的规则变更提案。
> 成功标准：强归因自动完成，弱归因置信度 ≥ 0.7。

## Boundary — 行为准则

### 必须遵守（HARD 规则 · 正向重述）

1. **低置信度必须人工** — 弱归因置信度 < 0.7 时，标记待人工确认，不自动执行规则回流 ← `R-ATTR-001`
   ↳ 校验：requires_human_review 与 confidence 一致
2. **能力与规则显式区分** — 将能力不足（capability_gap）归因为规则缺失（rule_missing）是禁止的 ← `R-ATTR-002`
   ↳ 校验：capability_gap 案例不产出 NEW_RULE Delta
3. **归因结论可溯源** — 每条归因必须附带证据列表，可追溯到原始 Trace ← `R-ATTR-003`
   ↳ 校验：evidence 数组非空，且引用有效 Trace ID
4. **争议率监控** — 近 30 天归因争议率 > 30% 时触发归因熔断 ← `R-ATTR-004`
   ↳ 校验：controversy_rate ≤ 0.3

### 建议参考（偏好）
- 优先完成强归因（确定性高，可全自动）（HIGH）
- 弱归因附带尽可能多的证据（MEDIUM）
- 历史同类案例作为参考基线（MEDIUM）

## Guard — 认知守卫

| 当你产生这个念头 | 现实是 | 触发行为 |
|---|---|---|
| "看起来像是规则缺失" | 可能是能力不足，需要更多证据 | 检查是否有同类成功案例 |
| "置信度差不多够了" | 0.7 是硬线，低于必须人工 | 重新评估证据强度 |
| "这条归因没问题吧" | 争议率超限会触发全局熔断 | 对照历史同类案例验证 |

### Spirit vs Letter
| 规则 | 解释模式 | 真实意图 |
|---|---|---|
| R-ATTR-001 | SPIRIT | 防止低置信度归因污染规则库 |
| R-ATTR-002 | SPIRIT | 能力问题用规则解决不了，会制造无效规则 |

## Gate — 通过标准

### 流程门禁（不通过 = 驳回）
- [ ] `attribution_consistency` — 归因结论与历史同类案例一致（无矛盾）
- [ ] `confidence_valid` — 弱归因置信度标注正确，< 0.7 时 requires_human_review = true
- [ ] `evidence_complete` — 每条归因附带 ≥ 1 条有效证据

### 质量门禁（创意评价，不通过 = 记录但放行）
- `attribution_confidence`: 平均置信度趋势上升 ≥ 0.7

## Trace — 采集点
- 归因开始：记录违规案例 ID、违规规则、Trace 引用
- 强归因：记录是否命中已有规则、检测精度评估
- 弱归因：记录根因类型、置信度、证据列表
- 归因结束：记录 Delta Rule 产出（如有），写入 trace/

## 操作指令

### 归因执行流程

详见 `_attribution-protocol.md`。

### 归因结果分类处理

| 归因类型 | 层级 | 自动化 | 产出 |
|---------|------|--------|------|
| rule_hit | STRONG | 全自动 | OPTIMIZE_DETECTION Delta |
| rule_missing | WEAK | confidence ≥ 0.7 + EXPERIENTIAL | NEW_RULE Delta |
| capability_gap | WEAK | 归档 | 能力边界清单更新 |
| rule_violation | WEAK | 加强 Red Flags | Red Flags 更新 |

## Red Flags

| 信号 | 说明 |
|------|------|
| 置信度 < 0.7 但自动执行了规则回流 | 低置信度归因可能污染规则库 |
| 将能力不足归因为规则缺失 | 制造无效规则，增加规则膨胀 |
| 归因无证据支撑 | 无法溯源，审计链断裂 |
| 忽略争议率告警 | 争议率 > 30% 说明归因模型有问题 |

## Common Rationalizations

| 借口 | 事实 |
|------|------|
| "看起来就是规则缺失" | 需要证据支撑，不能凭直觉 |
| "置信度差不多" | 0.7 是硬线，模糊判断不行 |
| "先加上规则再说" | 低质量规则比没有规则更有害（误杀） |
