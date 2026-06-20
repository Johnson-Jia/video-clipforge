# 创业淘金者 → 抖音短视频（全自动）

> **全自动执行，不需要人工确认。** 创业淘金者专栏（大浪淘沙），从 loot-drop.io 失败案例淘教训 + 可复用点子。周二/四 19:00 + 周六 10:00。编排模式参见 `clipforge/shared/cron-template.md`，分类规则参见 `clipforge/categories/goldminer.md`。

## 前置：日期 & 目录

```bash
export LANG=zh_CN.UTF-8
TODAY=$(date +%Y-%m-%d)
DATE_DIR="$(date +%Y)/$(date +%m)/$(date +%d)"
PROJECT_DIR="workspace/${DATE_DIR}/goldminer"
mkdir -p "${PROJECT_DIR}"
```

## Step 0: 自续期（必须最先执行）

goldminer 有 **2 个 cron job**（不同时间档：周二/四 19:03 + 周六 10:03）。**不走通用 cron-renew**（它假设 1 关键词 1 job，会把 2 个合并成 1）。改为逐个重建保留 2 个：

1. CronList 找 prompt 含 `goldminer` 的 job（应 2 个）
2. 对每个旧 job：CronCreate 新 job（**同 cron 表达式**：`3 19 * * 2,4` 周二四 / `3 10 * * 6` 周六，prompt `/goldminer`，recurring+durable）→ 确认新建成功 → CronDelete 旧
3. CronList 确认最终 **2 个** job（周二四档 + 周六档）

## Step 1: 数据采集（loot-drop.io 中国失败案例）

```bash
source "$HOME/.claude/commands/clipforge/shared/clipforge-env.sh" 2>/dev/null || source "$(git rev-parse --show-toplevel 2>/dev/null)/.claude/commands/clipforge/shared/clipforge-env.sh"
python scripts/fetch_lootdrop.py --output-dir "${PROJECT_DIR}" --region 中国 --limit 3
```

产出 `raw_failures.json`（3 个中国失败案例，含全文 failure_analysis/startup_learnings/pivot_concept/related）。按 `categories/goldminer.md → selection_strategy` 选 1 主角（受众熟悉/数据震撼/死因反直觉/教训可淘）+ related 作对比。**中国公司起步，逐步全球。**

## Step 2: DAG 编排（goldminer 分类，4 SubAgent）

按 `shared/cron-template.md` 标准 4 批次 DAG，分类=`goldminer`：

| SubAgent | stage | 差异项 |
|----------|-------|--------|
| SubAgent-1 | topic-plan→content→design→narration | goldminer 5段失败复盘（hook→what→why_fail→**loot**→compare），「淘金！开淘！」签名 |
| SubAgent-2 | audio | `{{CATEGORY}}` = goldminer（YunjianNeural +15%） |
| SubAgent-3 | video | 暖金风（goldminer design：#FFB800/#D4A017 + 琥珀 #FF6B00） |
| SubAgent-4 | delivery→scoring→cleanup | `{{CATEGORY}}` = goldminer |

### ⛔ 约束注入 + 门禁（每个 SubAgent）

```bash
cd .claude/commands/clipforge
python engine/inject.py --skill <stage-id> --category goldminer --project-dir "../../../${PROJECT_DIR}"
# SubAgent 完成后：
python engine/gate.py --skill <stage-id> --project-dir "${PROJECT_DIR}"
```

SubAgent-skill 对应：stage3-scenes（SA1）/ stage4-audio（SA2）/ stage6-production（SA3）/ stage7-delivery（SA4）。

### ⛔ 合规红线（goldminer.md HARD，失败案例必读）

> loot-drop.io 内容是 AI 辅助总结。失败案例涉真实公司，**视频必须**：
> 1. **来源标注**：文案/评论区注明 loot-drop.io
> 2. **不杜撰**：死因忠实 `failure_analysis` 原文，禁夸大/添油加醋
> 3. **不点名创始人个人**：只讲公司+商业模式+宏观原因（诽谤风险）

## Step 3: 发布时机（cleanup 之后、汇报之前）

```bash
python scripts/write_publish_note.py --project-dir "${PROJECT_DIR}"
```

读 `workspace/evolution/publish_timing_advice.json`，写 `publish_note.md`（cleanup 后写避免被清理）。

## 输出

```
📊 创业淘金者视频已生成
日期：YYYY-MM-DD
文件：workspace/<YYYY>/<MM>/<DD>/goldminer/final.mp4
主角：<公司名>（中国失败案例，$XM 烧光）
死因：<一句话>
淘金：教训 + 可偷点子
发布时机：✅ publish_note.md
定时任务续期：✅ Job ID xxxxx
```
