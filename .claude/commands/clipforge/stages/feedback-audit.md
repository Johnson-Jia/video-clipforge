# 反馈审计与自进化闭环机制

> 本文档定义 ClipForge 的**自进化闭环**(gate 失败 / 评分偏差 → 模式提炼 → Delta → 校验 → 应用)、**产物审计视图**与**模式溯源约定**。
> 它是 `clipforge.md §5.3` 的展开深度文档。`stages/stage8-feedback.md` 引用本文获取机制定义,自身只讲阶段 B 的操作(数据目录 / 命令 / 评分维度)。

## §1 三文档边界

| 文档 | 角色 | 触发 | 产出 | 是否驱动进化 |
|------|------|------|------|------------|
| `shared/machine-scoring.md` | 阶段 A 即时评分 | 渲染后单次 | `score_report.json`(预测分) | 否(仅记录) |
| `stages/stage8-feedback.md` | 阶段 B 操作手册 | 有播放数据 | `performance.json` / `feedback.yaml` | 操作入口 |
| `stages/feedback-audit.md`(本文) | 闭环机制 + 审计 | 闭环常驻 | pattern / delta / threshold | 定义机制本身 |

**握手数据**:`score_report.json`(阶段 A 预测)与 `performance.json`(阶段 B 实际)对齐,差异经 §5 校准回灌评分能力。

## §2 自进化闭环全链路

闭环由两类信号驱动:**gate 失败**(质量回退)与**评分偏差**(阶段 A 预测 vs 阶段 B 实际)。两者最终都产出 Delta(增量规则变更)。治理发现(§6)是第三输入源。

| 步 | 动作 | 实现锚点 |
|----|------|---------|
| 1 | 信号触发 | `engine/gate.py` / `engine/attribution.py` / `engine/governance.py` |
| 2 | 记录上下文 | trace(`engine/trace.py`) |
| 3 | 归因 | `engine/attribution.py` |
| 4 | 生成 Delta | `engine/lib/delta.py:create_delta` |
| 5 | 影子校验(历史 trace 回放) | `engine/lib/delta.py:shadow_validate` |
| 6 | 持久化 + 注入 | `save_delta` → `engine/inject.py` |
| 7 | 校准阈值 / 清理过期 | `phase5_calibrate` / `cleanup_expired_deltas` |

**Delta 生命周期**(核实自 `engine/lib/delta.py` + `engine/attribution.py`):

| 维度 | 规则 |
|------|------|
| 标识 | `D-YYYYMMDD-{rule_id 或 NEW}` |
| 操作类型 | `ADDED` / `MODIFIED` / `REMOVED` / `DEPRECATED` |
| 人工审核触发 | `confidence < 0.70` → `requires_human_review=True` |
| 过期清理 | Delta 文件 > 90 天由 `cleanup_expired_deltas(max_age_days=90)` 删除 |
| SAFETY 保护(P6) | `REMOVED`/`DEPRECATED` 对 `class: SAFETY` 规则静默跳过,不可删除/降级 |
| 断路器 | `engine/dispute_tracker.py:check_circuit_breaker` 触发时附于 Delta |

**shadow_validate 安全判定**(无 trace 不默认通过,强制人工):

| 场景 | 判定 |
|------|------|
| 无历史 trace | `unsafe`(强制人工审核) |
| `REMOVED`/`DEPRECATED` 目标规则曾阻断违规 | `unsafe`(避免安全回退) |
| `ADDED` 与已有规则 pattern 完全相同 | `unsafe`(冲突) |
| 其余 | `safe` |

## §3 auto_evolve 五阶段机制

入口 `python scripts/auto_evolve.py`(全流程),或 `python scripts/collect_performance.py`(仅采集 + 校准)。

| Phase | 函数 | 动作 |
|-------|------|------|
| 1 collect | `phase1_collect` | 采集 trace + performance 数据 |
| 2 analyze | `phase2_analyze` | 跨项目统计:5s 完播率、收藏率、Spearman 相关(c5s→播放、收藏→播放)、daily_growth |
| 3 patterns | `phase3_patterns` | `auto_extract_from_performance`(min_samples=3)+ `gate_validate_pattern` 门禁;高分 hook → `P-hook-*` |
| 4 deltas | `phase4_deltas` | `create_delta` + `shadow_validate` + `save_delta`(去重);confidence = `min(0.7 + valid_count × 0.005, 0.85)` |
| 5 calibrate | `phase5_calibrate` | 更新 `thresholds.yaml`(`5s_completion_low` / `save_rate_high`);防过拟合 |

产物:`evolution-report-{date}.json`(含 thresholds_changed、过期 Delta 清理计数)。

## §4 模式沉淀与质量门禁

模式(pattern)三形态入库(`engine/success_analyzer.py` + `engine/inject.py:load_patterns`):

| 形态 | 注入内容 | 注入侧 |
|------|---------|--------|
| `as_preference` | `text` | 偏好提示 |
| `as_fewshot` | `example_output`[:200] | 示例提示 |
| `as_constraint_relaxation` | (归因判定) | 约束放宽 |

**P4 入库门禁 `gate_validate_pattern`**(核实自 `success_analyzer.py:59`):

| 检查项 | 门槛 |
|--------|------|
| 样本量 | `evidence.sample_size ≥ 3` |
| 置信度 | `evidence.confidence ≥ 0.60`(min_confidence) |
| 实质性 | `as_preference.text` 非空且非 generic(禁"执行路径高效 / 可直接复用 / 表现良好") |
| P7 否决 | 模式文本不得包含任何 HARD 规则的违禁关键词 |

**模式老化**:pattern 文件 mtime > 90 天,`load_patterns` 跳过(不再注入)。

## §5 机器评分能力校准

阶段 A 预测与阶段 B 实际对齐后,`engine/attribution.py:calibrate_machine_scoring` 产出校准信号:

| 信号 | 含义 | 产出 |
|------|------|------|
| `STRENGTHEN_RULE` | 实际优于预测 | 强化该评分维度的规则 |
| `STRENGTHEN_INJECTION` | 注入侧强化 | 偏好 / fewshot 加权 |
| `DEPRECATED` | 预测持续偏离实际 | 弃用 / 降权该维度 |

校准 Delta 是闭环第二输入源(第一是 gate 失败)。校准 Delta 自身 confidence = 0.70。

## §6 治理闭环

`python engine/governance.py {check|stats|remediate}` 做规则库健康治理,发现产出 Delta:

| 检测 | 触发 | Delta 操作 | confidence |
|------|------|-----------|-----------|
| 冲突(`detect_conflicts`) | 重复 id / keyword_overlap | 报告 | — |
| 冗余(`detect_redundancy`) | pattern 完全重复 | `DEPRECATED`(合并) | 0.80 |
| 膨胀(`check_bloat`) | scope > 100 条 / 总计 > 300 条 | `DEPRECATED`(淘汰零命中 EXPERIENTIAL) | 0.70 |

治理默认 `--dry-run`(只产 Delta 不保存),`--apply` 才 `save_delta`。所有治理 Delta 经 `shadow_validate`。

## §7 产物目录与审计视图

| 产物 | 命名 | 清理 |
|------|------|------|
| trace | (按项目 / gate) | 滚动 |
| pattern | `P-<scope>-<topic>` | mtime > 90 天跳过注入 |
| delta | `D-YYYYMMDD-*` | > 90 天删除 |
| threshold | `thresholds.yaml` | 随 `phase5_calibrate` 更新 |
| report | `evolution-report-{date}.json` | 滚动保留 |

> 审计入口:`governance.py stats` 看规则命中率 / 零命中;`evolution-report` 看本轮闭环变更。

## §8 模式溯源约定

`source` / `source_pattern` 字段性质(核实:`engine/inject.py:load_patterns` 对其**零读取**):

- **纯元数据**,仅用于人类审计回溯。
- 不进入 LLM 提示词,不消耗 token / 注意力。

写法规范:

| 场景 | 写法 | 示例 |
|------|------|------|
| 文档溯源 | `<doc>.md §<真实章节>` | `shared/render-safety.md §1.13` |
| 门禁溯源 | `engine/gate.py <checker>` | `engine/gate.py check_orientation_consistency` |
| 模式溯源 | `source_pattern: "P-<真实id>"` | `P-cover-design` |
| 事故溯源 | `事故: <机制主题>` | `事故: BGM 时长远短于旁白` |
| 反馈溯源 | `用户反馈: <机制主题>` | `用户反馈: 相邻场景视觉同质化` |

**禁止**:

- `P-feedback-*` 前缀(无对应真实 pattern,从源头杜绝悬空引用)。
- 事故日期(`2026-05-28` 之类)与项目名(`ai-training-impact` 之类)——属 git history,不入 source 字段(去运行时化)。
- 指向不存在文件的文件名引用。
