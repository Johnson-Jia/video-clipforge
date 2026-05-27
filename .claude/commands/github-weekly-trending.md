---
id: "clipforge.github-weekly-trending"
name: github-weekly-trending
description: 全自动抓取 GitHub 每周热门项目汇总并生成抖音短视频，无需人工确认。完成后自动续期定时任务。
version: "2.0.0"
type: ORCHESTRATOR
category: "github"
schedule: "weekly"
---

# GitHub 每周热门汇总 → 抖音短视频（全自动）

> **全自动执行，不需要人工确认。** 使用 DAG 感知编排 + SubAgent 阶段隔离执行，每个阶段独立上下文窗口。

## Intent
> 全自动抓取 GitHub 每周热门项目汇总并生成抖音短视频。
> 成功标准：数据三源验证通过、分类整理完成、视频渲染成功、定时任务续期完成。

## Boundary — 编排准则

### 必须遵守（HARD 规则）
1. **数据三源验证** — 至少两个数据源交叉验证，项目名交集 ≥80% ← `R-GH-001`
2. **数据量门禁** — 获取 ≥8 个项目 ← `R-GH-002`
3. **活跃度检查** — ≥80% 项目活跃 ← `R-GH-003`
4. **分类覆盖** — 按语言/领域分组，每组 3-4 个项目 ← `R-GH-W001`
5. **续期无条件** — 无论成功失败，必须执行 _cron-renew ← `R-CRON-002`

## Gate — 质量门禁

### 数据采集门禁（Step 1，不通过 = 中止）
- [ ] 项目数 ≥ 8
- [ ] ≥ 80% 项目活跃
- [ ] 三源交叉验证交集 ≥ 80%

### 批次门禁（Step 3，同 daily）
- [ ] SA-1 ~ SA-4 各批次产出文件存在

## Trace — 采集点
- **Step 1**：数据源验证结果、分类统计
- **Step 3**：各批次状态
- **写入**：`{PROJECT_DIR}/trace/run-summary.yaml`

## 前置：日期 & 目录

```bash
TODAY=$(date +%Y-%m-%d)
DATE_DIR="$(date +%Y)/$(date +%m)/$(date +%d)"
PROJECT_DIR="workspace/${DATE_DIR}/github-trending-weekly"
```

> **代理：** 如果本机需要代理才能访问 GitHub，请在执行前设置 `https_proxy` / `http_proxy` 环境变量。

## Step 1: 抓取 GitHub Weekly Trending（三源交叉验证）

### 1.1 主数据源 — Python 脚本抓取（无缓存）

```bash
TODAY=$(date +%Y-%m-%d)
DATE_DIR="$(date +%Y)/$(date +%m)/$(date +%d)"
PROJECT_DIR="workspace/${DATE_DIR}/github-trending-weekly"
mkdir -p "${PROJECT_DIR}"

python .claude/commands/clipforge/scripts/github_trending.py \
  --output-dir "${PROJECT_DIR}" \
  --date "${TODAY}" \
  --since weekly
```

### 1.2 验证源 — web-reader MCP 交叉确认

用 `mcp__web_reader__webReader`（**必须设 `no_cache: true`**）抓取：

```
url: https://github.com/trending?since=weekly&spoken_language_code=
no_cache: true
```

与 `raw_trending.json` 比对项目列表，交集 >= 80% 即通过。

### 1.3 数据质量门禁

同每日命令：项目数 >= 8、活跃度 >= 80%。

### 1.4 读取最终数据

从 `raw_trending.json` 提取前 **12-15 个项目**。

## Step 2: 内容整理 & 分类

将数据整理为中文短视频素材：
- 项目名保留英文
- 描述翻译成中文（简洁口语化）
- **按编程语言/领域分类**（如：AI/ML、前端、后端、DevOps 工具、移动端等），每组 3-4 个项目
- 开头钩子：如"本周 GitHub 最火的开源项目盘点"
- 每个分类用一句话概括趋势（如"AI 项目持续霸榜"）

## Step 3: DAG 编排执行

> **核心机制：** 读取 `schema.yaml` 定义 artifact DAG，按依赖关系推导 SubAgent 批次。每个 SubAgent 从零上下文启动，加载对应 stage 技能文件。状态通过文件系统检测（检查 generates 文件是否存在）。

### DAG 批次调度

| 批次 | Artifact | 说明 |
|------|----------|------|
| SubAgent-1 | env-check → content → design → narration | 顺序执行，6-7 场景，45-60s |
| SubAgent-2 | audio | TTS + BGM |
| SubAgent-3 | video | HTML + 渲染 |
| SubAgent-4 | delivery → cleanup | 封面 + 交付 + 清理 |

> **movie-clips / assets：** 周汇总为标准模式，均跳过。

### 3.1 SubAgent-1: content → design → narration

读取 `.claude/commands/clipforge/templates/subagent-1-content.md`，替换插槽后作为 SubAgent prompt：
- `{{PROJECT_DIR}}` → `${PROJECT_DIR}`
- `{{VIDEO_MODE}}` → 标准模式（6-7 场景，45-60s）
- `{{CONTENT_TYPE}}` → GitHub 每周热门汇总（按领域分类）
- `{{CATEGORY}}` → github
- `{{CONTENT_SOURCE}}` → 项目目录下的 raw_trending.json（数据已准备好）

额外指令（追加到模板 prompt 末尾）：
- content 步骤: 选取 12-15 个项目，按领域/语言分组
- design 步骤: 不同分类可使用不同色彩区分（如 AI 组用冷色系、前端组用暖色系），整体保持协调统一
- narration 步骤: 场景数 6-7 个（hook → 分类1 → 分类2 → 分类3 → 分类4 → 趋势总结 → CTA），目标字数 300-450 字，目标时长 45-60 秒

**验证：** `ls -la ${PROJECT_DIR}/design.md ${PROJECT_DIR}/narration_segments.json ${PROJECT_DIR}/narration.txt`

### 3.2 SubAgent-2: audio

读取 `.claude/commands/clipforge/templates/subagent-2-audio.md`，替换插槽后作为 SubAgent prompt：
- `{{PROJECT_DIR}}` → `${PROJECT_DIR}`
- `{{CATEGORY}}` → github

**验证：** `ls -la ${PROJECT_DIR}/segment_durations.json ${PROJECT_DIR}/narration.mp3 ${PROJECT_DIR}/bgm.wav`

### 3.3 SubAgent-3: video

读取 `.claude/commands/clipforge/templates/subagent-3-video.md`，替换插槽后作为 SubAgent prompt：
- `{{PROJECT_DIR}}` → `${PROJECT_DIR}`
- `{{EXTRA_CONTEXT}}` → - 时长可延长至 45-60 秒，每个分类场景 6-10 秒

**验证：** `ls -la ${PROJECT_DIR}/output.mp4 ${PROJECT_DIR}/output_no_bgm.mp4`

### 3.4 SubAgent-4: delivery → cleanup

读取 `.claude/commands/clipforge/templates/subagent-4-delivery.md`，替换插槽后作为 SubAgent prompt：
- `{{PROJECT_DIR}}` → `${PROJECT_DIR}`
- `{{CATEGORY}}` → github

> **⛔ 清理必须通过 SubAgent-4 执行，主编排禁止直接手动清理。** 如 SubAgent-4 跳过或失败，用脚本补救：`bash .claude/commands/clipforge/scripts/cleanup_project.sh "${PROJECT_DIR}"`。禁止手动 `rm -f` 批量删除中间文件。

**验证：** `ls ${PROJECT_DIR}/` 确认中间文件已清理，`du -sh ${PROJECT_DIR}` 确认 < 30 MB。

## Step 5: 自续期

执行 `clipforge/_cron-renew` 定时任务自续期模式，任务关键词为 `github-weekly-trending`。

## 输出

完成后汇报：
```
📊 GitHub 每周热门汇总视频已生成
周次：YYYY-MM-DD 这周
文件：workspace/<YYYY>/<MM>/<DD>/github-trending-weekly/final.mp4
时长：XXs | 大小：XX MB
项目数：X 个（分 X 类）
抖音文案：[文案内容摘要]
定时任务续期：✅ Job ID xxxxx
```
