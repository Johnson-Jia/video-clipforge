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

## §4 新鲜度约束（SOFT 全链，不 HARD 阻断）

**架构事实**：freshness 的 hook_sim / template_sim 依赖 `narration_segments.json`（stage3 产出），project_jaccard 依赖 content_ready（stage1 产出）。这些文件在 stage0.5 时**均不存在**——所以 freshness 不做 HARD 阻断 gate（无输入时不阻断，有输入时靠 score 加权反映，不强制 gate 拦截）。

**freshness 反同质化通过两层 SOFT 实现**：
1. **事前引导**（inject）：stage0.5/stage1/stage3 执行前，inject 注入近期 hook/项目摘要 + 题材轮换 pattern，LLM 主动避让重复（`engine/inject.py` recent_context）
2. **事后扣分**（score）：machine-scoring 阶段 `overall_score = 合规·w1 + 新鲜度·w2 + 播放潜力·w3`，与近期高度相似的视频被新鲜度拉低分（`engine/gate.py` generate_score_report）

| 维度 | 阈值（引导参考） | 作用方式 |
|------|------|---------|
| project_jaccard | < 0.5 | inject 预警 + score 扣分 |
| hook_sim | < 0.6 | inject 预警 + score 扣分 |
| template_sim | < 0.7 | inject 预警 + score 扣分 |

> 不做 HARD gate 的原因：同质化是「质量趋势」而非「硬性错误」——HARD 阻断会误杀有潜力的边界内容。SOFT（引导 + 扣分）让 LLM 知道重复 + 评分反映，但不强制阻断创作。

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
