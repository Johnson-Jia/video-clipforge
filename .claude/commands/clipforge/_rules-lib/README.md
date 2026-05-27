# ClipForge 规则库（Rules Library）

> 本目录是 ClipForge 技能体系的**结构化规则存储**，供 Skill 通过 `ref:` 引用。

## 文件结构

| 文件 | 作用域 | 规则前缀 | 来源 |
|------|--------|----------|------|
| `global-rules.yaml` | GLOBAL（所有 Skill） | `R-GLOBAL-*` | `_shared-rules.md` §1-§7 |
| `video-production-rules.yaml` | SCENE（视频制作） | `R-RENDER-*` | `_render-safety.md` §1-§2 |
| `cleanup-rules.yaml` | GLOBAL（清理操作） | `R-CLEANUP-*` | `_cleanup-rules.md` |

## 规则结构

每条规则包含以下字段：

```yaml
- id: "R-GLOBAL-001"           # 全局唯一 ID
  type: FORBIDDEN_SPEECH        # 规则类型（ACTION/SPEECH/LOGIC/METHOD）
  pattern: "负向描述"            # 禁止什么（存储格式）
  positive: "正向重述"           # 应该做什么（注入 prompt）
  guardrail: "检测方式"          # 如何校验（校验引擎使用）
  severity: HARD | SOFT         # HARD=驳回，SOFT=记录
  class: SAFETY | EXPERIENTIAL  # SAFETY=不可放宽，EXPERIENTIAL=可双向调整
  scope: GLOBAL | SCENE | SKILL # 生效范围
  source: "来源文档 §段"         # 可追溯到原始规范
```

## 双轨消费

规则通过**双轨机制**消费：

1. **正向重述（`positive`）** → 注入 Agent 的 prompt，告诉它"应该做什么"
2. **校验规则（`guardrail`）** → 供校验引擎使用，检测"是否违规"

这解决了 LLM 的白熊效应问题：负向指令（"不要想 X"）反而增加 X 出现概率，正向表述（"应该做 Y"）更有效引导行为。

## 引用方式

在 `skill.yaml` 的 `boundary.rules` 中通过 `ref:` 引用：

```yaml
boundary:
  rules:
    - ref: "R-GLOBAL-001"       # 引用全局规则
    - ref: "R-RENDER-004"       # 引用场景规则
    - inline:                   # 阶段独有规则
        id: "R-STAGE4-001"
        ...
```

## 规则继承

- **GLOBAL** 规则：所有 Skill 自动继承
- **SCENE** 规则：该场景下的 Skill 继承（如 video-production 场景继承 R-RENDER-*）
- **SKILL** 规则：仅当前 Skill 生效

三层合并后注入 Agent 执行上下文。

## 约束双轨制

| 类型 | 标记 | 放宽策略 |
|------|------|----------|
| 安全约束 | `class: SAFETY` | **只收紧不放宽**——对应组织红线 |
| 经验约束 | `class: EXPERIENTIAL` | **可收紧也可放宽**——需正向闭环提供证据 + 人工确认 |
