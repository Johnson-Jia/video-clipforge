# Stage 0.5: 选题规划（防同质化一等公民）

当选题方向尚未确定（`topic_plan.json` 不存在）时触发。在内容获取前规划本期选题，主动避开近期重复——这是播放量的第一杠杆，但长期藏在 content 里被工艺维度淹没。

## §1 触发输入

- `exploration_directive.yaml`：本期 explore 还是 exploit 选题（exploration.py 决定）
- inject 新鲜度预警：近期 hook / 项目 / 相似度（freshness.recent_context）
- `patterns/seed/topic-*.yaml`：题材库（每题材一条选题 pattern）
- 近 N 期历史选题（避免连续同题材）

## §2 选题规划三问

1. **题材轮换**：本期选哪个题材？对照 §3 轮换表，避开连续同题材
2. **新鲜度目标**：与近 5 期至少 2 个维度差异化（hook / 项目集 / 叙事模板）
3. **项目类型多样性**：本期项目类型分布，避免全是同一类（如全 AI Agent）

## §3 题材轮换表（GitHub 分类）

| 题材 | pattern | 适合频率 | 说明 |
|------|---------|---------|------|
| AI-Agent | topic-ai | 每周 ≤2 | 主流但易疲劳，6 月崩盘主因 |
| 工具/效率 | topic-tool | 每周 1-2 | |
| 安全/隐私 | topic-security | 每周 ≤1 | |
| 硬件/端侧 | topic-hardware | 每周 ≤1 | |
| 容器/基建 | topic-container | 每周 ≤1 | |
| 深度专题 | topic-deep-dive | 每周 1 | 单项目深度，破盘点疲劳 |

**轮换铁律**：连续 3 期同题材 → 第 4 期强制换题材（除非有强反直觉爆点）。

## §4 新鲜度约束（HARD，gate 校验）

与近 5 期历史比对（freshness.compute_freshness），至少满足：

| 维度 | 阈值 | 超阈值处理 |
|------|------|-----------|
| hook_sim | < 0.6 | 换钩子句式 / 数字锚点 |
| project_jaccard | < 0.5 | 引入 ≥2 个近 5 期未出现项目 |
| template_sim | < 0.7 | 换叙事模板（盘点→对比弧→揭秘弧） |

> 三项任一超阈值 → 调整选题角度，不得直接进入 content。

## §5 产出 topic_plan.json

```json
{
  "topic_type": "工具/效率",
  "topic_pattern": "topic-tool",
  "angle": "反直觉钩子方向（一句话）",
  "novelty_strategy": "本期如何差异化：换哪个数字锚点 / 换哪种叙事",
  "target_freshness": {"hook_sim_max": 0.6, "project_jaccard_max": 0.5, "template_sim_max": 0.7},
  "project_type_mix": "本期项目类型分布（避免单一）",
  "avoid_recent": ["近5期高频项目 owner/repo，避免重复展开"]
}
```

## §6 与下游衔接

- `content`（stage1）：按 `topic_plan.angle` 抓取数据，不偏离选题方向
- `narration`（stage3）：hook 遵循 `novelty_strategy`，避开 `avoid_recent` 项目重复展开
- `freshness` 门禁（stage1/stage3 gate）：用 `target_freshness` 校验实际新鲜度

> 本阶段是「选题系统化」的入口，配套题材库 `patterns/seed/topic-*.yaml`（P1-2）和探索-利用（exploration.py 已支持 topic 维度）。让选题从 LLM 临场判断，升级为有轮换约束 + 新鲜度门禁的系统化决策。
