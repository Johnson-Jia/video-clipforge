# Trace 格式定义

> 本文件定义 ClipForge 技能体系的执行轨迹采集格式。Trace 是双闭环反馈的数据基础。

## 目录结构

每个项目在执行时创建 `trace/` 目录：

```
{project_dir}/trace/
├── run-summary.yaml          # 本次运行的汇总
├── stage0-{timestamp}.yaml   # Stage 0 执行轨迹
├── stage1-{timestamp}.yaml   # Stage 1 执行轨迹
├── stage2-{timestamp}.yaml
├── stage3-{timestamp}.yaml
├── stage4-{timestamp}.yaml
├── stage5-{timestamp}.yaml   # (optional, 可能跳过)
├── stage6-{timestamp}.yaml
└── stage7-{timestamp}.yaml
```

## 单阶段 Trace 结构

```yaml
trace:
  id: "T-{stage}-{timestamp}"
  skill_id: "clipforge.stage{N}-{name}"
  skill_version: "1.0.0"
  timestamp: "2026-05-27T10:30:00Z"
  status: "PASSED"              # PASSED | FAILED | PASSED_WITH_CONCERNS | SKIPPED

  # 执行上下文快照
  context:
    intent_snapshot: "..."      # 执行时的 Intent（1 句话）
    boundary_snapshot:          # 执行时的规则集摘要
      rule_count: 15
      hard_count: 12
      soft_count: 3
    category: "github"
    video_mode: "standard"

  # 执行过程
  execution:
    constraint_hits:            # 触碰的规则
      - rule: "R-STAGE6-001"
        action: "PATH_SWITCH"   # PATH_SWITCH | BLOCKED | IGNORED
        detail: "发现使用了CSS opacity:0，切换为GSAP .from()"
    path_switches: 1            # 路径切换次数
    retry_count: 0              # 重试次数
    duration_minutes: 12        # 执行耗时

  # 结果
  artifacts:
    generates:                  # 预期产出文件
      - "output.mp4"
      - "output_no_bgm.mp4"
    all_exist: true             # 所有文件是否存在

  # 门禁报告
  gate_report:
    process_passed: true          # 流程门禁全部通过（自动化脚本检查）
    compliance_passed: true       # 合规门禁全部通过（关键词/正则匹配）
    hard_violations: []
    quality_score: null           # 质量评分（由外部回填，非 Agent 自评）
    quality_evaluator: null       # 评分来源：HUMAN | PLAYBACK_DATA | null
    quality_notes: ""             # Agent 的定性描述（流程完整性触发时使用）

  # 归因 / 成功分析（执行后由协议填充）
  attribution: null
  success_analysis: null
```

## 运行汇总结构

```yaml
run:
  id: "RUN-{date}-{seq}"
  project: "{project_name}"
  project_dir: "workspace/2026/05/27/{project_name}"
  category: "github"
  video_mode: "standard"
  started_at: "2026-05-27T10:00:00Z"
  completed_at: "2026-05-27T11:30:00Z"
  overall_status: "SUCCESS"     # SUCCESS | FAILED | PARTIAL

  stages:
    - stage: "stage0-env"
      status: PASSED
      duration_minutes: 1
      trace_file: "stage0-20260527T100000Z.yaml"
    - stage: "stage1-content"
      status: PASSED
      duration_minutes: 5
      trace_file: "stage1-20260527T100100Z.yaml"
    # ... 所有阶段

  # 闭环反馈
  feedback:
    negative_loop: null         # 归因结果（如有失败）
    positive_loop: null         # 成功分析结果（如有高分）
    external_metrics: null      # 外部指标（播放数据回填）
```

## 采集时机

每个 Skill 在以下时点采集数据：

1. **执行开始**：记录 intent 快照 + boundary 快照 + 开始时间
2. **每次路径切换**：记录 constraint_hits（触碰了哪条规则、采取了什么动作）
3. **执行结束**：记录 gate_report + artifacts 检查 + 耗时
4. **写入文件**：将 Trace 写入 `{project_dir}/trace/` 目录

## 与闭环的关系

- **负向闭环**：当 `status: FAILED` 时，Trace 进入归因协议（`_attribution-protocol.md`）
- **正向闭环**：当 `quality_score ≥ 0.85` 时，Trace 进入成功分析协议（`_success-analysis-protocol.md`）
- **降级触发**：当 `process_passed: true` AND `compliance_passed: true` 且外部数据不可用时，以 `quality_notes` 定性描述触发
