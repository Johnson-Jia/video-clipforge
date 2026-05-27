# 成功分析协议（Success Analysis Protocol）

> 正向闭环核心：成功 → 分析 → 经验沉淀
> 本协议定义高分成功案例的分析和经验模式沉淀机制。

## Intent
> 从高分成功案例中提炼可复用的经验模式，沉淀到 Pattern Store。
> 成功标准：高分案例模式沉淀率 ≥ 60%。

## 自动触发条件

**何时执行成功分析：**

1. **SubAgent 批次完成后**：在 `run_summary.py` 生成汇总之后
2. **触发条件**：`run-summary.yaml` 中任一阶段满足成功分析触发条件（见下方"## 触发条件"）
3. **执行位置**：由 `subagent-4-delivery.md` 的"反馈循环"段触发
4. **脚本调用**：
   ```bash
   # 1. 聚合高分 Trace 到全局目录
   python3 .claude/commands/clipforge/scripts/aggregate_traces.py

   # 2. 升级满足条件的 SEED 模式
   python3 .claude/commands/clipforge/scripts/upgrade_patterns.py

   # 3. 转换放宽提案为 Delta Rule
   python3 .claude/commands/clipforge/scripts/convert_relaxation_to_delta.py
   ```

## Trace 数据来源

成功分析协议消费以下 Trace 数据：

- **阶段 Trace**：`{PROJECT_DIR}/trace/stage{N}-{timestamp}.yaml`
  - `gate_report.quality_score ≥ 0.85` → 触发成功分析（首选）
  - `gate_report.process_passed AND compliance_passed` → 降级触发（流程完整性）
  - `execution.steps` → 关键决策点
  - `execution.constraint_hits` → 规则触碰记录
- **全局聚合**：`_success-traces/` 目录
  - 由 `aggregate_traces.py` 从各项目目录收集
  - 用于跨项目模式识别

格式定义详见 `_trace-format.md`

## 触发条件

满足以下**任一**条件时，标记为"高分成功案例"，触发采集和分析：

1. **外部数据触发**（首选）：视频发布后，播放数据回填到 Trace 的 `external_metrics` 字段
   - `aggregate.quality_score ≥ 0.85` 且 `quality_evaluator: PLAYBACK_DATA`
   - 或：任一平台核心指标超 TOP 20% 基准（抖音播放 > 20000 / 视频号完播 > 15% / 小红书收藏率 > 3%）

2. **人工评价触发**：人工审看后回填 `quality_score`（`quality_evaluator: HUMAN`）
   - `quality_score ≥ 0.85`

3. **流程完整性触发**（降级方案，产出 SEED 模式）：
   - `process_passed: true` AND `compliance_passed: true`
   - 无外部数据时，记录为"流程完整案例"
   - 此类案例产出的模式标记为 `type: SEED`，需更多数据验证

## 外部指标回填

视频发布后，将播放数据回填到 Trace 文件：

```yaml
# 回填到 {project_dir}/trace/stage{N}-{timestamp}.yaml
gate_report:
  quality_score: 0.92              # 归一化到 0-1
  quality_evaluator: "PLAYBACK_DATA"
external_metrics:
  play_count: 110000               # 播放量
  completion_rate: 0.45            # 完播率
  like_count: 5200                 # 点赞数
  comment_count: 380               # 评论数
  share_count: 1200                # 分享数
  platform: "douyin"               # 平台
  published_at: "2026-05-19T15:30:00Z"
```

**评分计算参考**（非强制，由评价者决定）：
- 播放量超过同期平均 2 倍 → 基础分 0.7
- 完播率 > 40% → +0.15
- 互动率（点赞+评论+分享/播放）> 5% → +0.15

## 分析流程

```
高分成功案例（quality_score ≥ 0.85）
    │
    ▼
Step 1: 提取关键决策点
    │  从 Trace 中提取：
    │  - 选择了什么方案（vs 拒绝了什么）
    │  - 路径切换记录（如果有）
    │  - 效率指标（path_switches、tokens_used）
    │
    ▼
Step 2: 与历史高分案例比对
    │  查找相同 skill_scope 下的历史高分案例
    │  识别重复出现的决策模式
    │
    ▼
Step 3: 识别模式
    │  同一决策模式在 ≥3 个案例中出现 → 候选模式
    │  计算统计置信度
    │
    ▼
Step 4: 负向闭环否决权
    │  检查候选模式是否包含违规内容
    │  如果模式本身触碰 HARD 规则 → 否决，不沉淀
    │
    ▼
Step 5: 沉淀到 Pattern Store
    │  以偏好/示例/放宽提案形式写入 _patterns/store.yaml
    │  设置 skill_scope 和 confidence
    │
    ▼
Step 6: 跨平台对比分析
    │  比较同一视频在三平台的表现差异：
    │  - 抖音高播放 + 视频号高完播 = 内容质量好（双验证）
    │  - 抖音低播放 + 视频号高分享 = 话题有社交价值但算法不推
    │  - 小红书高收藏 = 内容有干货价值（长尾流量信号）
    │  - 三平台一致低 = 内容本身有问题（非分发问题）
    │
    │  按 content_type 分组统计：
    │  - github-daily 基准：抖音均播放 20000，视频号完播 12.6%
    │  - deep-dive 基准：抖音均播放 1800，视频号完播 8.1%
    │  - 超过基准 2x → 高质量信号
    │  - 低于基准 0.5x → 低质量信号
```

## 成功案例采集格式

```yaml
success_trace:
  id: "ST-{timestamp}-{seq}"
  skill_id: "clipforge.stage{N}"
  trace_ref: "T-{timestamp}-{seq}"

  success_factors:
    decision_points:
      - decision: "描述决策"
        chosen: "选择的方案"
        alternatives_rejected: ["拒绝的方案"]
    patterns_observed:
      - "观察到的成功模式"
    efficiency:
      path_switches: 0
      tokens_used: 3200

  quality:
    quality_score: 0.92
    gate_report: { ... }
```

## 沉淀方式

| 方式 | 触发条件 | 作用 | 注入位置 | 自动化 |
|------|---------|------|---------|--------|
| 偏好引导 | 同一模式在 ≥3 个成功案例中出现 | 为后续执行提供参考方向 | prompt "成功经验" 段 | 自动沉淀 |
| Few-shot 示例 | 同一模式在 ≥5 个案例中出现且置信度>0.8 | 作为 prompt 示例注入 | prompt few-shot 段 | 自动生成 |
| 约束放宽提案 | EXPERIENTIAL 约束频繁导致路径切换且切换后评分更低 | 提案放宽（必须人工确认） | Delta Rule 流程 | 自动提案，人工审批 |

## Few-shot 示例生成

当同一模式在 ≥ 5 个成功案例中出现且置信度 > 0.8 时，自动从 Pattern 生成 Few-shot 示例。

### 触发条件
- pattern.evidence.sample_size ≥ 5
- pattern.evidence.confidence > 0.8
- 模式关联的 Skill 类型为 GENERATIVE（创意类输出更适合示例注入）

### 生成流程

```
高分 Trace 累积到 ≥ 5 个
    │
    ▼
提取最高评分的 Trace 输出
    │
    ▼
脱敏处理（移除项目特有信息）
    │
    ▼
生成 Few-shot 结构：
    context: "在什么场景下使用"
    example_output: "脱敏后的高分输出片段"
    │
    ▼
写入 pattern.as_fewshot
    │
    ▼
注入后续执行的 prompt few-shot 段
```

### Few-shot 产出格式

```yaml
as_fewshot:
  context: "规划活动方案时，先分析目标受众再设计形式"
  example_output: |
    ## 受众分析
    - 目标人群：25-35岁科技爱好者
    - 活跃时段：晚间 20:00-22:00
    - 偏好内容：深度技术解析
    
    ## 活动形式
    线上直播 + 互动问答...
  source_pattern: "P-001"
  generated_at: "2026-06-15T10:00:00Z"
```

## 约束放宽提案

当某条 EXPERIENTIAL 约束频繁导致路径切换，且切换后的评分反而更低时，说明该约束可能过严。

### 触发条件（必须全部满足）
- 目标规则 `class: EXPERIENTIAL`（SAFETY 规则绝不可放宽）
- 近 30 天内该规则导致路径切换 ≥ 5 次
- 路径切换后的平均 quality_score < 切换前的平均 quality_score
- 切换后无 HARD 门禁违规

### 生成流程

```
统计规则 R-xxx 的路径切换数据
    │
    ├─ 切换次数 < 5 → 不触发
    │
    └─ 切换次数 ≥ 5
        │
        ▼
    比较切换前后评分
        │
        ├─ 切换后评分 ≥ 切换前 → 规则合理，不放宽
        │
        └─ 切换后评分 < 切换前 → 规则可能过严
            │
            ▼
        检查切换后是否有 HARD 违规
            │
            ├─ 有 → 不放宽（放宽会导致安全问题）
            │
            └─ 无 → 产出放宽提案
                │
                ▼
            ⚠️ 必须人工确认（requires_human_review: true）
```

### 放宽提案产出格式

```yaml
as_constraint_relaxation:
  target_rule: "R-xxx"
  evidence:
    switch_count_30d: 8
    avg_score_before_switch: 0.82
    avg_score_after_switch: 0.71
    hard_violations_after_switch: 0
  proposal: "DOWNGRADE_HARD_TO_SOFT"  # 或 NARROW_SCOPE
  requires_human_review: true
  generated_at: "2026-06-15T10:00:00Z"
```

### 放宽操作类型

| 操作 | 说明 | 适用场景 |
|------|------|---------|
| DOWNGRADE_HARD_TO_SOFT | 从硬约束降级为软约束 | 规则仍然重要但不必强制 |
| NARROW_SCOPE | 从 SCENE 收窄到 SKILL | 规则只在特定 Skill 中有效 |
| DEPRECATE | 标记废弃 | 规则已过时 |

### 安全约束（不可放宽）

以下情况绝不产出放宽提案：
- `class: SAFETY` 的规则
- 放宽后会导致 HARD 门禁违规的模式
- 无成功案例支撑的放宽（必须有统计数据）

## Pattern 产出格式

```yaml
pattern:
  id: "P-{seq}"
  source_traces: ["ST-xxx", "ST-yyy", "ST-zzz"]
  skill_scope: "clipforge.stage{N}"

  description: "模式描述"
  evidence:
    sample_size: 3
    avg_quality_score_with_pattern: 0.91
    avg_quality_score_without_pattern: 0.72
    confidence: 0.83

  # 方式 1：偏好引导
  as_preference:
    text: "偏好描述文本"
    weight: MEDIUM
    source_pattern: "P-{seq}"

  # 方式 2：Few-shot 示例（置信度 >0.8 时）
  # as_fewshot:
  #   context: "使用场景描述"
  #   example_output: "脱敏后的高分输出片段"

  # 方式 3：约束放宽提案（需人工确认）
  # as_constraint_relaxation:
  #   target_rule: "R-xxx"
  #   evidence: "放宽理由"
  #   proposal: "DOWNGRADE_HARD_TO_SOFT"
  #   requires_human_review: true
```

## 与负向闭环的制衡

```
候选模式
    │
    ▼
负向闭环否决权检查：
    │
    ├─ 模式包含违规内容？ → 否决，不沉淀
    ├─ 模式与现有 HARD 规则冲突？ → 否决
    └─ 通过 → 允许沉淀

约束放宽提案：
    │
    ├─ 目标是 SAFETY 规则？ → 拒绝（SAFETY 不可放宽）
    ├─ 无成功案例支撑？ → 拒绝
    └─ 通过 → 提交人工确认
```

## 经验模式有效性评估

| 指标 | 健康标准 | 告警阈值 |
|------|---------|---------|
| 模式应用后评分变化 | 上升 | 下降 → 标记待淘汰 |
| 模式复用率 | 持续上升 | 连续 30 天未命中 → 淘汰 |
| 模式与规则冲突 | 0 | > 0 → 立即审查 |
