# Stage 8: 延迟反馈与评分校准（阶段 B）

> 发布后有播放数据时触发。**全自动**（`auto_evolve.py`），也可手动逐项目操作。
> 完整自进化文档见 `stages/feedback-audit.md`。

## 自动模式（推荐）

将各平台导出数据放入 `workspace/sources/视频数据/YYYY-MM-DD/`，运行：

```bash
cd .claude/commands/clipforge
python scripts/auto_evolve.py
```

脚本自动完成：数据采集 → 批量分析 → 模式提炼 → Delta 生成 → 阈值校准。
安全 Delta 自动生效，无需人工审批。

## 手动模式（备选）

> 以下为逐项目手动操作流程，仅在需要人工评分校准时使用。

## 触发条件

- 视频已发布到平台 ≥ 1 天
- 用户手头有播放数据（播放量、5s 完播率、分享率等）

## 数据目录约定

将各平台导出的数据文件放到 `workspace/sources/视频数据/YYYY-MM-DD/` 目录：

| 平台 | 文件名 | 格式 |
|------|--------|------|
| 抖音 | `抖音作品列表.xlsx` | xlsx |
| B站 | `哔哩哔哩近期稿件对比.csv` | csv |
| 视频号 | `微信视频号动态数据明细.csv` 或 `视频号动态数据明细.csv` | csv |
| 小红书 | `小红书笔记列表明细表.xlsx` | xlsx |

按日期建子目录，每次导出放一份。脚本会自动扫描所有日期。

### 各平台数据导出方法

**抖音**：抖音创作者中心 → 数据中心 → 作品分析 → 投稿作品 → 投稿列表 → 选择全部 → 导出数据

**微信视频号**：视频号 · 助手 → 数据中心 → 视频数据 → 单篇视频 → 下载表格

**小红书**：小红书创作服务平台 → 数据看板 → 内容分析 → 笔记数据 → 全部 → 导出数据

**哔哩哔哩**：创作中心 → 数据概览 → 拉到最下面 → 近期稿件对比 → 导出按钮（一次导出十个视频，多次导出）

## 执行流程

### 0. 自动数据检测（推荐）

检查 `$PROJECT_DIR/performance.json` 是否已存在：

```bash
cat "$PROJECT_DIR/performance.json"
```

**已存在** → 跳到步骤 2（人类评分）或步骤 3（机器校准）。

**不存在** → 运行自动采集：

```bash
python scripts/collect_performance.py --scan --backfill
```

脚本会自动解析四平台文件、通过标题匹配到项目目录、回填 performance 数据。
也可指定日期：`--date 2026-05-29`，或用 `--dry-run` 先查看匹配结果。

### 1. 播放数据回填（手动备选）

如果自动采集匹配不准确，手动指定：

```bash
python engine/trace.py backfill \
  --project-dir "$PROJECT_DIR" \
  --performance '{"platform":"douyin","plays":5200,"completion_5s_rate":0.42,"completion_rate":0.045}'
```

已有引擎支持：`trace.py` 的 `backfill_performance()` + `attribution.py` 的 `performance_attribution()` 四平台阈值。

### 2. 人类主观评分（交互模式）

展示 `final.mp4` + 封面 + 抖音文案，收集：

| 维度 | 类型 | 范围 | 必填 |
|------|------|------|------|
| hook 吸引力 | 滑块 | 1-5 | 是 |
| 信息密度 | 滑块 | 1-5 | 是 |
| 视觉风格 | 滑块 | 1-5 | 是 |
| 音频质量 | 滑块 | 1-5 | 是 |
| 整体满意度 | 滑块 | 1-5 | 是 |
| 最薄弱环节 | 单选 | hook/文案/配音/画面/节奏/其他 | 是 |
| 薄弱环节说明 | 自由文本 | — | 否 |

**自动模式下跳过人类评分**，仅使用播放数据做校准。

### 3. 机器评分能力校准

对比 `score_report.json`（机器预测）vs 实际表现，产出校准信号：

| 机器预测 | 实际表现 | 校准动作 |
|---------|---------|---------|
| 高分（≥0.8） | 差（低播放/低完播率） | `STRENGTHEN_RULE`：收紧被高估的 gate checker |
| 低分（<0.5） | 好（高播放/高完播率） | `DEPRECATED`：放松过严规则（仅 EXPERIENTIAL） |
| 一致 | — | 标记为可靠校准样本 |

校准逻辑由 `attribution.py` 的 `calibrate_machine_scoring()` 执行。

### 4. 产出 feedback.yaml

```yaml
project: "workspace/2026/05/29/my-project"
created: "2026-05-29T15:30:00Z"
updated: "2026-06-02T10:00:00Z"

machine_scoring:
  overall_soft_score: 1.0
  hard_passed_all: true

performance:
  platform: douyin
  plays: 5200
  completion_5s_rate: 0.42
  completion_rate: 0.045
  collected_at: "2026-06-02"

human_scores:
  hook: 2
  density: 5
  visual: 4
  audio: 4
  overall: 4
  weakest_link: "hook"
  weakest_detail: "开头太平淡"

calibration:
  machine_prediction: "HIGH"
  actual_outcome: "MEDIUM"
  verdict: "OVERESTIMATED"
  diagnosis: ""
  action: null
```

## 校准产物的处理

校准产出的 Delta 走正常 Delta 流程：
1. `shadow_validate()` 影子校验
2. 标记 `requires_human_review`
3. 写入 `deltas/` 目录
4. 不自动执行，等待人工确认
