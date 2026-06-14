# Cron 编排通用模板

> 此文件是 `/clipforge-category-setup` 生成定时任务时的参考骨架。生成的 cron 文件必须是自包含的 LLM prompt — 所有执行规则内联写入，不使用跨文件引用。

## §1 前置准备

```bash
export LANG=zh_CN.UTF-8
TODAY=$(date +%Y-%m-%d)
DATE_DIR="$(date +%Y)/$(date +%m)/$(date +%d)"
PROJECT_DIR="workspace/${DATE_DIR}/<project-name>"
mkdir -p "${PROJECT_DIR}"

# 探索-利用决策（种子化确定性，全 DAG 各 SubAgent 读同一 directive）
# 决定本次视频走 explore（采集冷门维度数据）还是 exploit（用最强经验组合）
cd .claude/commands/clipforge && python engine/exploration.py --project-dir "../../../${PROJECT_DIR}" --date "${TODAY}" --category <CATEGORY>
```

> **代理：** 如果本机需要代理才能访问外网，请在执行前设置 `https_proxy` / `http_proxy` 环境变量。
> **`export LANG=zh_CN.UTF-8` 必须设置**：Windows Git Bash 默认 locale 可能是 GBK，导致中文目录名编码错乱。

## §2 自续期（必须最先执行）

> **铁律：续期在任何管线工作之前执行。** 无论后续步骤是否成功，续期保证任务不会因 7 天过期而断档。续期在末尾的旧模式已废弃——管线中断会导致续期被跳过。

执行 `clipforge/shared/cron-renew` 定时任务自续期模式，传入任务关键词。

## §3 数据采集

从分类配置的 `data_source` 和 `data_validation` 段获取：
- **采集命令**：具体的脚本/API 调用命令（必须可直接执行）
- **验证策略**：数据质量检查（数量阈值、去重、时效性）
- **兜底方案**：主数据源失败时的备选路径

生成的 cron 文件中，此步骤必须包含：
1. 完整的 bash 命令（含参数）
2. 验证阈值和失败处理逻辑
3. 输出文件路径确认

## §4 内容整理

从分类配置的 `selection_strategy` 和 `preparation_rules` 段获取：
- **选取规则**：从原始数据中筛选多少条目、按什么排序
- **格式转换**：原始数据 → 中文素材的转换规则
- **额外管理**：如月度清单、跨期去重等（可选）

## §5 DAG 编排

> **引擎命令基础路径**：所有 `python engine/` 和 `bash scripts/` 命令在 `.claude/commands/clipforge/` 目录下执行。

读取 `schema.yaml` 定义 artifact DAG，按依赖关系推导 SubAgent 批次。每个 SubAgent 从零上下文启动，加载对应 stage 技能文件。状态通过文件系统检测（检查 generates 文件是否存在）。

| 批次 | Artifact | SubAgent 加载 |
|------|----------|--------------|
| SubAgent-1 | env-check → topic-plan → content → design → narration | stage0-env + stage0.5-topic-plan + stage1-content + stage2-analysis + stage3-scenes |
| SubAgent-2 | audio | stage4-audio |
| SubAgent-3 | video | stage6-production |
| SubAgent-4 | delivery → machine-scoring → cleanup | stage7-delivery + shared/machine-scoring.md + shared/cleanup-rules.md |

> **movie-clips / assets：** 标准模式下均跳过。按 schema.yaml 条件判断。

### SubAgent Prompt 组装协议

用 Agent 工具启动 4 个 SubAgent，每个从零上下文启动。prompt 由以下要素构成：
- 加载对应 stage 技能文件（`skills/stage{N}-*.yaml`）
- 设置项目目录路径
- 传入分类特定参数

### ⛔ 约束注入协议（必须执行，不可跳过）

> **每个 SubAgent 启动前，主编排必须执行约束注入。** inject 输出包含最新 Delta 演化的规则，跳过 = 自进化全部失效。

**步骤**：

1. 运行约束注入（在 `.claude/commands/clipforge/` 目录下）：
   ```bash
   cd .claude/commands/clipforge && python engine/inject.py --skill <stage-id> --category <category> --project-dir "../../../${PROJECT_DIR}"
   ```

2. 将 inject 输出作为 **约束段** 附加到 SubAgent prompt 的最前面（在 stage 内容之前）：
   ```
   ## 行为约束（引擎注入，不可修改）
   [inject.py 的完整输出]

   ---
   以下是你的任务指令：
   [stage 内容 + 运行参数]
   ```

3. **SubAgent 对应关系**：

| SubAgent | --skill 参数 |
|----------|-------------|
| SubAgent-1 | stage3-scenes（覆盖 stage0-3 全部约束） |
| SubAgent-2 | stage4-audio |
| SubAgent-3 | stage6-production |
| SubAgent-4 | stage7-delivery |

> **⚠ inject 是约束源不是装饰。跳过 inject = 所有 Delta 演化规则全部失效。**

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
> **⚠ Gate 是防线不是装饰。跳过 gate = 已有规则全部失效。**

### SubAgent-1: content → design → narration

加载：`skills/stage0-env.yaml` + `skills/stage1-content.yaml` + `skills/stage2-analysis.yaml` + `skills/stage3-scenes.yaml`

**约束注入**：运行 `cd .claude/commands/clipforge && python engine/inject.py --skill stage3-scenes --category <CATEGORY> --project-dir "../../../${PROJECT_DIR}"`，将输出作为约束段附加到 SubAgent prompt 最前面。

传入参数：

| 参数 | 说明 | 示例 |
|------|------|------|
| PROJECT_DIR | 项目目录绝对路径 | `workspace/2026/05/29/github-trending` |
| VIDEO_MODE | 视频模式描述 | `标准模式（4-5 场景，20-45s）` |
| CONTENT_TYPE | 内容类型描述 | `GitHub Trending 项目盘点` |
| CATEGORY | 分类 ID | `github` |
| CONTENT_SOURCE | 数据来源文件 | `raw_trending.json` |
| ORIENTATION | 画布方向 | `portrait`（默认）或 `landscape`（仅当分类配置指定时） |

**额外指令**：分类特定的选取规则、内容偏好等（从分类配置的 `selection_strategy` 段提取）。

**方向判定**：默认 `portrait`。仅当分类配置有 `orientation_hint: landscape` 时使用横屏。写入 `orientation` + `orientation_source` 到 design.md。

**门禁校验**：完成后运行 `cd <clipforge-dir> && python engine/gate.py --skill stage3-scenes --project-dir <PROJECT_DIR>`

**验证**：`ls -la ${PROJECT_DIR}/design.md ${PROJECT_DIR}/narration_segments.json ${PROJECT_DIR}/narration.txt`

### SubAgent-2: audio

加载：`skills/stage4-audio.yaml`

**约束注入**：运行 `cd .claude/commands/clipforge && python engine/inject.py --skill stage4-audio --category <CATEGORY> --project-dir "../../../${PROJECT_DIR}"`，将输出作为约束段附加到 SubAgent prompt 最前面。

传入参数：

| 参数 | 说明 | 示例 |
|------|------|------|
| PROJECT_DIR | 项目目录绝对路径 | 同上 |
| CATEGORY | 分类 ID | `github` |

**验证**：`ls -la ${PROJECT_DIR}/segment_durations.json ${PROJECT_DIR}/narration.mp3 ${PROJECT_DIR}/bgm.wav`

**门禁校验**：完成后运行 `cd <clipforge-dir> && python engine/gate.py --skill stage4-audio --project-dir <PROJECT_DIR>`

### SubAgent-3: video

加载：`skills/stage6-production.yaml`

**约束注入**：运行 `cd .claude/commands/clipforge && python engine/inject.py --skill stage6-production --category <CATEGORY> --project-dir "../../../${PROJECT_DIR}"`，将输出作为约束段附加到 SubAgent prompt 最前面。

传入参数：

| 参数 | 说明 | 示例 |
|------|------|------|
| PROJECT_DIR | 项目目录绝对路径 | 同上 |
| EXTRA_CONTEXT | 额外上下文 | 时长可延长至 45-60 秒 |

**⛔ 门禁指令（必须执行，不可跳过）**：

SubAgent-3 的 prompt 中必须包含以下完整指令：

```
### 组装铁律（HARD）

1. **LLM 只填 creative/ 碎片**：每个场景写一个 `creative/sNN.html`（纯视觉创意：bg 组件 + fx 动画 + content 文字），**绝不创建、绝不手改 index.html**
2. **index.html 由 s6_assemble.sh 生成**：碎片填完后必须运行 `bash .claude/commands/clipforge/scripts/s6_assemble.sh --project-dir <PROJECT_DIR>`，由脚本完成 clip 包裹、data-start/data-duration、GSAP timeline、phase 切换、window.__hf、audio 嵌入、DOCTYPE/HEAD 结构
3. **门禁失败禁止手补 index.html**：结构类失败（window.__hf / composition / clip id / data-width / audio data-start）一定是碎片内容或组装步骤的问题。**回到 creative/ 修对应碎片，重跑 s6_assemble.sh**。直接编辑 index.html 修补会引入新结构错误，陷入"手写 → 失败 → 再手写"的重试泥潭（trace 实证：手写 HTML 平均需多轮磨，用脚本 0 次结构失败）

### 安全区铁律（HARD）

1. **安全区 padding 固定值**：竖屏 `180px 90px 220px 90px`（上180 右90 下220 左90），横屏 `60px 120px 60px 120px`
2. **单层 padding 原则**：padding 只设在 `.phase` 或 `.scene-wrap` 上（二选一），禁止在 composition / clip / layer-content 等其他层级设置 padding
3. **禁止修改值**：安全区 padding 值是平台适配标准，不允许 SubAgent 自行调整

完成 creative/ 碎片填充 + s6_assemble.sh 组装 + 渲染后，必须执行门禁校验：

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

**约束注入**：运行 `cd .claude/commands/clipforge && python engine/inject.py --skill stage7-delivery --category <CATEGORY> --project-dir "../../../${PROJECT_DIR}"`，将输出作为约束段附加到 SubAgent prompt 最前面。

传入参数：

| 参数 | 说明 | 示例 |
|------|------|------|
| PROJECT_DIR | 项目目录绝对路径 | 同上 |
| CATEGORY | 分类 ID | `github` |

**执行顺序**：
1. delivery（封面 + 双版本 final.mp4）
   - **封面生成（脚本化，禁止手写 HTML）**：
     1. LLM 从 `design.md` 推导配色方案，从 `narration_segments.json` / `content_summary.md` 提取内容数据
     2. LLM 生成 `cover_params.json`（内容参数 + 3 个核心色值），schema 见下方
     3. 运行脚本：`cd <clipforge-dir> && python scripts/generate_cover.py --project-dir <PROJECT_DIR> --render`
     4. 脚本自动生成 `cover.html` + `cover.png`
   - **禁止 SubAgent 手写 cover.html**。结构由模板控制，LLM 只提供内容参数和色彩方案
   - 封面之后的步骤（douyin.md、assemble_final.sh）照常执行
   - **douyin.md 文案硬性要求（SubAgent 必须遵守）**：
     1. **四平台差异化文案**：`## 抖音`、`## B站`、`## 视频号`、`## 小红书` 四个标题，每个标题下有完整文案（标题+正文+标签）
     2. **标题字数上限**（HARD，超出视为门禁失败）：
        - 抖音：≤ 30 字
        - B站：≤ 80 字
        - 小红书：≤ 20 字
        - 视频号：≤ 16 字
     3. **标题必须包含核心关键词**：让人一眼看到本期最核心的功能/项目/数据，便于检索和吸引目标受众。禁止纯情绪标题（如"炸了""太猛了"）无实质信息
     4. **抖音**：爆款钩子型（反直觉钩子 + 数字锚定，至少 2 个数字）
     5. **B站**：信息密度高，标题可带 1-2 个项目名 + 核心数据
     6. **视频号**：必须包含分享引导（如"转发给做开发的朋友"）
     7. **小红书**：必须包含收藏引导（如"建议收藏备用""先收藏再看"），突出参考价值
     8. **评论区自评**（`## 评论区自评`）：每个项目必须包含：
        - 项目英文名 + 一句话中文描述
        - `路径: owner/repo`
        - `语言: XX | XX.XK⭐ | 今日+XXX`
     9. **禁止**：搜索引导（"GitHub搜索:xxx"）、URL/链接、极限词（"最强""必装"）
     10. 标签 ≥5 个，覆盖核心圈/领域/热点/身份/泛流量
2. delivery 门禁校验：`cd <clipforge-dir> && python engine/gate.py --skill stage7-delivery --project-dir <PROJECT_DIR>`
   - 检查 cover.html 封面 7 层结构 + 结构性合规（.cover 容器、:root 变量、字体、画布尺寸等）
   - 检查 douyin.md 是否含 URL
   - 门禁失败则修复后重试，最多 2 次
3. machine-scoring（gate 全量校验 → `score_report.json`）
4. cleanup（按 `shared/cleanup-rules.md` 白名单清理中间产物）

### cover_params.json Schema

LLM 生成此文件，脚本读取后填充模板。LLM 的创意域 = 所有字段的值；结构由模板锁定。

```json
{
  "orientation": "portrait",
  "date": "2026年6月4日",
  "scene_label": "GITHUB TRENDING",
  "badge": "6个项目",
  "title": [
    [{"text": "今日GitHub", "style": "white"}],
    [{"text": "热门", "style": "accent"}]
  ],
  "data_subtitle": "20万星项目首上榜",
  "cards": [
    {"num": "205K", "label": "ECC"},
    {"num": "179K", "label": "hermes-agent"},
    {"num": "35K", "label": "trivy"}
  ],
  "colors": {
    "accent_warm": "#f9a825",
    "accent_cool": "#00f5d4",
    "bg_dark": "#0a0e1a",
    "glow_warm_opacity": "0.18",
    "glow_cool_opacity": "0.10"
  }
}
```

**字段说明：**

| 字段 | 必填 | 说明 |
|------|------|------|
| orientation | 是 | `portrait`（默认）或 `landscape` |
| date | 是 | 中文日期格式 |
| scene_label | 是 | 场景分类标签 |
| badge | 是 | 胶囊徽章文案 |
| title | 是 | 嵌套数组：外层=行，内层=同行色段。每段 `{text, style}`，style 可选 `white`/`accent`/`cool`。同行多段不换行，不同行自动 `<br>` |
| data_subtitle | 是 | 数据说明文案 |
| cards | 是 | 1-3 个数据卡片，每项 `{num, label}` |
| colors.accent_warm | 是 | 主强调色（hex），脚本自动派生 soft/rgb 变体 |
| colors.accent_cool | 是 | 辅助色（hex），脚本自动派生 |
| colors.bg_dark | 是 | 深色背景（hex），脚本自动派生 mid/bottom 变体 |
| colors.glow_warm_opacity | 否 | 暖光晕强度，默认 0.18 |
| colors.glow_cool_opacity | 否 | 冷光晕强度，默认 0.10 |

> **设计哲学：** LLM 只需提供 3 个核心色值（warm/cool/bg），脚本自动派生完整 12 色调色板。LLM 的创造力聚焦于"什么颜色最适合这个内容"，而非"怎么写 CSS"。

> **⛔ 清理必须通过 SubAgent-4 执行，主编排禁止直接手动清理。** 如 SubAgent-4 跳过或失败，用脚本补救：`bash .claude/commands/clipforge/scripts/cleanup_project.sh "${PROJECT_DIR}"`。禁止手动 `rm -f` 批量删除中间文件。

**验证**：`ls ${PROJECT_DIR}/score_report.json` 确认评分存在，`ls ${PROJECT_DIR}/` 确认中间文件已清理，`du -sh ${PROJECT_DIR}` 确认 < 30 MB。

## §6 确保播放数据提醒已注册

> 自进化系统需要平台播放数据来校准机器评分。注册一个每日检查任务，如数据超过 3 天未更新则提醒用户。

> ⚠️ 以下检查逻辑是 `shared/playback-reminder.md` 的独立副本（cron 文件必须是自包含 prompt）。
> 修改 `playback-reminder.md` 时必须同步更新此处。

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

## §7 输出汇报

完成后汇报：

```
📊 <标题>
日期：YYYY-MM-DD
文件：workspace/<path>/final.mp4
时长：XXs | 大小：XX MB
定时任务续期：✅ Job ID xxxxx
```
