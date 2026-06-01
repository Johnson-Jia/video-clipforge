---
name: github-weekly-trending
description: 全自动抓取 GitHub 每周热门项目汇总并生成抖音短视频，无需人工确认。完成后自动续期定时任务。
---

# GitHub 每周热门汇总 → 抖音短视频（全自动）

> **全自动执行，不需要人工确认。** 编排模式参见 `clipforge/shared/cron-template.md`，数据验证和周汇总规则参见 `clipforge/categories/github.md`。

## 前置：日期 & 目录

```bash
TODAY=$(date +%Y-%m-%d)
DATE_DIR="$(date +%Y)/$(date +%m)/$(date +%d)"
PROJECT_DIR="workspace/${DATE_DIR}/github-trending-weekly"
mkdir -p "${PROJECT_DIR}"

# 计算周次上下文（供 SubAgent 旁白引用）
WEEK_NUM=$(date +%V)
WEEK_MON=$(date -d 'last monday' +%m月%d日 2>/dev/null || date +%m月%d日)
WEEK_SUN=$(date +%m月%d日)
echo "第${WEEK_NUM}周（${WEEK_MON}-${WEEK_SUN}）" > "${PROJECT_DIR}/week_context.txt"
```

## Step 1: 数据采集

按 `categories/github.md → data_validation` 执行三源交叉验证，使用 weekly 参数：

```bash
python .claude/commands/clipforge/scripts/github_trending.py \
  --output-dir "${PROJECT_DIR}" \
  --date "${TODAY}" \
  --since weekly
```

按 `categories/github.md → quality_gates` 检查数据质量（weekly 模式：>=15 项目）。

## Step 2: 内容整理

按 `categories/github.md → weekly_mode` 规则整理：
- 选取 12-15 个项目，按领域/语言分组
- 不同分类用不同色彩区分
- 场景数 6-7 个，字数 300-450 字

## Step 3: DAG 编排

按 `shared/cron-template.md` 执行标准 4 批次 DAG 编排，插槽替换：

| SubAgent | 差异项 |
|----------|--------|
| SubAgent-1 | `{{VIDEO_MODE}}` = 标准模式（6-7 场景，45-60s），`{{CONTENT_TYPE}}` = GitHub 每周热门汇总（按领域分类），`{{CATEGORY}}` = github，`{{CONTENT_SOURCE}}` = raw_trending.json，`{{ORIENTATION_HINT}}` = （留空，github 分类无 orientation_hint）。额外指令：按 weekly_mode 选取 12-15 个项目分组，不同分类使用不同色彩。读取 `week_context.txt` 获取周次信息，旁白 hook 和 CTA 必须包含周次（如"第22周周榜"或"5月26日-6月1日"），禁止只用"本周"。方向自动判定：完成 narration 后计算预估时长（总字数 ÷ 4.5 字/秒），>180s 写入 `orientation: landscape` + `orientation_source: duration`，≤180s 写入 `orientation: portrait` + `orientation_source: duration` |
| SubAgent-2 | `{{CATEGORY}}` = github |
| SubAgent-3 | `{{EXTRA_CONTEXT}}` = 时长可延长至 45-60 秒，每个分类场景 6-10 秒 |
| SubAgent-4 | `{{CATEGORY}}` = github |

### ⛔ 门禁强制执行铁律

> **每个 SubAgent 完成主要任务后，必须运行 `engine/gate.py`。**
>
> 事故记录：2026-05-30 github-trending 视频黑屏，因 SubAgent-3 未运行 gate.py，导致 CSS 可见性问题和码率异常均未拦截。

**SubAgent-1 门禁**（完成后执行）：

```bash
cd .claude/commands/clipforge && python engine/gate.py --skill stage3-scenes --project-dir "${PROJECT_DIR}"
```

HARD 门禁失败：修复后重试，最多 2 次。仍失败则停止并报告。

**SubAgent-2 门禁**（完成后执行）：

```bash
cd .claude/commands/clipforge && python engine/gate.py --skill stage4-audio --project-dir "${PROJECT_DIR}"
```

**SubAgent-3 门禁**（HTML 编写和渲染完成后必须执行，不可跳过）：

```bash
cd .claude/commands/clipforge && python engine/gate.py --skill stage6-production --project-dir "${PROJECT_DIR}"
```

门禁会检查：
- index.html 是否包含 `window.__hf` API
- 是否使用 CSS class 切换可见性（禁止，必须用 GSAP timeline）
- composition 结构是否完整（`data-composition-id` + `__timelines` + `paused`）
- bg/fx 层质量是否合格
- output.mp4 码率是否正常（<500 kbps = 黑屏）

HARD 门禁失败时：修复问题，重新渲染，再次运行门禁。最多重试 2 次。仍失败时：停止并返回门禁输出，不要继续下一阶段。

**SubAgent-4 门禁**（delivery 完成后、machine-scoring 前执行）：

```bash
cd .claude/commands/clipforge && python engine/gate.py --skill stage7-delivery --project-dir "${PROJECT_DIR}"
```

- 检查 cover.html 封面 7 层结构是否完整（date, scene-label, badge, main-title, divider, subtitle, card）
- 检查 douyin.md 是否含 URL
- 门禁失败则修复后重试，最多 2 次

## Step 4: 自续期

执行 `clipforge/shared/cron-renew`，任务关键词 `github-weekly-trending`。

## 输出

```
📊 GitHub 每周热门汇总视频已生成
周次：YYYY-MM-DD 这周
文件：workspace/<YYYY>/<MM>/<DD>/github-trending-weekly/final.mp4
时长：XXs | 大小：XX MB
项目数：X 个（分 X 类）
定时任务续期：✅ Job ID xxxxx
```
