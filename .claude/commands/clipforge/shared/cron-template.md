# Cron 编排通用模板

> 此文件是 `/clipforge-category-setup` 生成定时任务时的参考骨架。生成的 cron 文件必须是自包含的 LLM prompt — 所有执行规则内联写入，不使用跨文件引用。

## 前置准备

```bash
export LANG=zh_CN.UTF-8
TODAY=$(date +%Y-%m-%d)
DATE_DIR="$(date +%Y)/$(date +%m)/$(date +%d)"
PROJECT_DIR="workspace/${DATE_DIR}/<project-name>"
mkdir -p "${PROJECT_DIR}"
```

> **代理：** 如果本机需要代理才能访问外网，请在执行前设置 `https_proxy` / `http_proxy` 环境变量。
> **`export LANG=zh_CN.UTF-8` 必须设置**：Windows Git Bash 默认 locale 可能是 GBK，导致中文目录名编码错乱。

## Step 1: 数据采集

从分类配置的 `data_source` 和 `data_validation` 段获取：
- **采集命令**：具体的脚本/API 调用命令（必须可直接执行）
- **验证策略**：数据质量检查（数量阈值、去重、时效性）
- **兜底方案**：主数据源失败时的备选路径

生成的 cron 文件中，此步骤必须包含：
1. 完整的 bash 命令（含参数）
2. 验证阈值和失败处理逻辑
3. 输出文件路径确认

## Step 2: 内容整理

从分类配置的 `selection_strategy` 和 `preparation_rules` 段获取：
- **选取规则**：从原始数据中筛选多少条目、按什么排序
- **格式转换**：原始数据 → 中文素材的转换规则
- **额外管理**：如月度清单、跨期去重等（可选）

## Step 3: DAG 编排

> **引擎命令基础路径**：所有 `python engine/` 和 `bash scripts/` 命令在 `.claude/commands/clipforge/` 目录下执行。

读取 `schema.yaml` 定义 artifact DAG，按依赖关系推导 SubAgent 批次。每个 SubAgent 从零上下文启动，加载对应 stage 技能文件。状态通过文件系统检测（检查 generates 文件是否存在）。

| 批次 | Artifact | SubAgent 加载 |
|------|----------|--------------|
| SubAgent-1 | env-check → content → design → narration | stage0-env + stage1-content + stage2-analysis + stage3-scenes |
| SubAgent-2 | audio | stage4-audio |
| SubAgent-3 | video | stage6-production |
| SubAgent-4 | delivery → machine-scoring → cleanup | stage7-delivery + shared/machine-scoring.md + shared/cleanup-rules.md |

> **movie-clips / assets：** 标准模式下均跳过。按 schema.yaml 条件判断。

### SubAgent 模板加载

用 Agent 工具启动 4 个 SubAgent，每个从零上下文启动。prompt 由以下要素构成：
- 加载对应 stage 技能文件（`skills/stage{N}-*.yaml`）
- 设置项目目录路径
- 传入分类特定参数

> **⛔ 门禁强制执行铁律：每个 SubAgent 完成其主要任务后，必须运行 `engine/gate.py`。**
>
> 门禁是防事故的最后防线。SubAgent prompt 中必须包含以下指令：
>
> ```
> 完成任务后，必须运行门禁校验：
> cd <clipforge-dir> && python engine/gate.py --skill <stage-id> --project-dir <project-dir>
>
> - HARD 门禁失败：修复问题后重新执行（最多重试 2 次）
> - 仍失败：停止并报告失败原因，不要继续下一阶段
> - 全部通过：报告通过，继续
> ```
>
> **事故记录：2026-05-30 github-trending 视频黑屏事故，因 SubAgent-3 未运行 gate.py，
> 导致 R-R-001（opacity:0）和 R-S6-011（composition 结构）等已有规则未触发拦截。**

### SubAgent-1: content → design → narration

加载：`skills/stage0-env.yaml` + `skills/stage1-content.yaml` + `skills/stage2-analysis.yaml` + `skills/stage3-scenes.yaml`

传入参数：

| 参数 | 说明 | 示例 |
|------|------|------|
| PROJECT_DIR | 项目目录绝对路径 | `workspace/2026/05/29/github-trending` |
| VIDEO_MODE | 视频模式描述 | `标准模式（4-5 场景，20-45s）` |
| CONTENT_TYPE | 内容类型描述 | `GitHub Trending 项目盘点` |
| CATEGORY | 分类 ID | `github` |
| CONTENT_SOURCE | 数据来源文件 | `raw_trending.json` |

**额外指令**：分类特定的选取规则、内容偏好等（从分类配置的 `selection_strategy` 段提取）。

**门禁校验**：完成后运行 `cd <clipforge-dir> && python engine/gate.py --skill stage3-scenes --project-dir <PROJECT_DIR>`

**验证**：`ls -la ${PROJECT_DIR}/design.md ${PROJECT_DIR}/narration_segments.json ${PROJECT_DIR}/narration.txt`

### SubAgent-2: audio

加载：`skills/stage4-audio.yaml`

传入参数：

| 参数 | 说明 | 示例 |
|------|------|------|
| PROJECT_DIR | 项目目录绝对路径 | 同上 |
| CATEGORY | 分类 ID | `github` |

**验证**：`ls -la ${PROJECT_DIR}/segment_durations.json ${PROJECT_DIR}/narration.mp3 ${PROJECT_DIR}/bgm.wav`

**门禁校验**：完成后运行 `cd <clipforge-dir> && python engine/gate.py --skill stage4-audio --project-dir <PROJECT_DIR>`

### SubAgent-3: video

加载：`skills/stage6-production.yaml`

传入参数：

| 参数 | 说明 | 示例 |
|------|------|------|
| PROJECT_DIR | 项目目录绝对路径 | 同上 |
| EXTRA_CONTEXT | 额外上下文 | 时长可延长至 45-60 秒 |

**⛔ 门禁指令（必须执行，不可跳过）**：

SubAgent-3 的 prompt 中必须包含以下完整指令：

```
完成 HTML 编写和渲染后，必须执行门禁校验：

cd .claude/commands/clipforge && python engine/gate.py --skill stage6-production --project-dir <PROJECT_DIR>

门禁会检查：
- index.html 是否包含 window.__hf API
- 是否使用 CSS class 切换可见性（禁止，必须用 GSAP timeline）
- composition 结构是否完整（data-composition-id + __timelines + paused）
- bg/fx 层质量是否合格
- output.mp4 码率是否正常（<500 kbps = 黑屏）

HARD 门禁失败时：修复问题，重新渲染，再次运行门禁。最多重试 2 次。
仍失败时：停止并返回门禁输出，不要继续下一阶段。
```

**验证**：`ls -la ${PROJECT_DIR}/output.mp4 ${PROJECT_DIR}/output_no_bgm.mp4`

### SubAgent-4: delivery → machine-scoring → cleanup

加载：`skills/stage7-delivery.yaml` + `shared/machine-scoring.md` + `shared/cleanup-rules.md`

传入参数：

| 参数 | 说明 | 示例 |
|------|------|------|
| PROJECT_DIR | 项目目录绝对路径 | 同上 |
| CATEGORY | 分类 ID | `github` |

**执行顺序**：
1. delivery（封面 + 双版本 final.mp4）
2. delivery 门禁校验：`cd <clipforge-dir> && python engine/gate.py --skill stage7-delivery --project-dir <PROJECT_DIR>`
   - 检查 cover.html 封面 7 层结构是否完整
   - 检查 douyin.md 是否含 URL
   - 门禁失败则修复后重试，最多 2 次
3. machine-scoring（gate 全量校验 → `score_report.json`）
4. cleanup（按 `shared/cleanup-rules.md` 白名单清理中间产物）

> **⛔ 清理必须通过 SubAgent-4 执行，主编排禁止直接手动清理。** 如 SubAgent-4 跳过或失败，用脚本补救：`bash .claude/commands/clipforge/scripts/cleanup_project.sh "${PROJECT_DIR}"`。禁止手动 `rm -f` 批量删除中间文件。

**验证**：`ls ${PROJECT_DIR}/score_report.json` 确认评分存在，`ls ${PROJECT_DIR}/` 确认中间文件已清理，`du -sh ${PROJECT_DIR}` 确认 < 30 MB。

## Step 3.5: 确保播放数据提醒已注册

> 自进化系统需要平台播放数据来校准机器评分。注册一个每日检查任务，如数据超过 3 天未更新则提醒用户。

检查 CronList 中是否已有 `playback-reminder` 关键词的任务：
- 如已存在 → 跳过
- 如不存在 → CronCreate 注册每日 recurring 任务

CronCreate 参数：
- `cron`: `"30 10 * * *"`（每日上午 10:30）
- `recurring`: `true`
- `durable`: `true`
- `prompt`：内联以下检查逻辑（自包含 prompt，不引用外部文件）

prompt 内容：

```
你是播放数据新鲜度检查助手。执行以下检查：

1. 扫描 workspace/ 下是否有 final.mp4（已交付视频）。没有则静默退出。
2. 检查 workspace/sources/视频数据/ 目录：
   - 不存在或为空 → stale=true
   - 找最新日期子目录，计算距今天数
   - 超过 3 天 → stale=true
   - 3 天内 → stale=false，静默退出
3. 如 stale=true，输出提醒：

📊 播放数据提醒

最近导出：{latest_date}（超过 3 天未更新）

自进化系统需要播放数据来校准机器评分。
请导出平台数据后运行 /clipforge-feedback。

平台导出操作：
- 抖音：创作者中心 → 数据中心 → 作品数据 → 导出 Excel
- 小红书：专业号中心 → 数据中心 → 笔记数据 → 导出
- 哔哩哔哩：创作中心 → 数据中心 → 稿件数据 → 导出 CSV
- 微信视频号：视频号助手 → 数据中心 → 视频数据 → 导出

导出后放到：workspace/sources/视频数据/{今天日期}/
然后运行：/clipforge-feedback
```

注册完成后，执行 `shared/cron-renew` 为此任务续期（关键词：`playback-reminder`）。

## Step 4: 自续期

> **无论前序步骤是否成功，都必须执行此步骤。**

执行 `clipforge/shared/cron-renew` 定时任务自续期模式，传入任务关键词。

## 输出汇报

完成后汇报：

```
📊 <标题>
日期：YYYY-MM-DD
文件：workspace/<path>/final.mp4
时长：XXs | 大小：XX MB
定时任务续期：✅ Job ID xxxxx
```
