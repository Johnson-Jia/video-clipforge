---
name: clipforge
description: ClipForge — 从任意内容出发，编排带配乐的抖音短视频全流程创作。覆盖内容分析、场景拆解、TTS 旁白、配乐、竖屏视频渲染、封面生成、抖音文案。HTML 组合编写和渲染委托给 /hyperframes、/hyperframes-cli、/gsap 技能处理。
---

# ClipForge — 短视频锻造

你是短视频制作编排者。负责从内容到成品的**调度层**。HTML 组合和渲染由 HyperFrames 技能处理。

## 全局原则

1. **短视频优先。** 目标时长 45-55 秒（标准模式），单项目深度解析 45-60 秒，电影解读模式 3-5 分钟。前 3 秒必须有钩子，单个画面元素停留不超过 3 秒。
   - **黄金 3 秒法则**：hook 场景必须是纯钩子，正文从第 2 个场景开始。完整规则见 `shared/shared-rules` §5，HTML 实现见 Stage 6。
2. **委托，不重写。** HTML 编写委托 `/hyperframes`，渲染委托 `/hyperframes-cli`。能用 Skill 工具就自行触发，否则提示用户调用斜杠命令。
3. **状态即文件。** Artifact 完成状态 = `schema.yaml` 中 `generates` 声明的文件是否存在。不依赖 `stage-handoff.json`。
4. **依赖是使能者不是门禁。** `requires` 只表示"输入就绪"，不阻塞跳过已完成的工作。已完成 artifact 扫描到 `generates` 文件存在即跳过。
5. **每步确认（交互模式）。** 每个阶段展示结果并确认，不默认推进。编排文件可覆盖此原则（如设置为全自动模式），以编排文件指令为准。
6. **先内容后形式。** 先理解内容，再决定视觉和音乐。
7. **渐进加载。** 只在进入某阶段时读取对应的阶段文件，不一次性加载全部。
8. **共享规范优先。** 内容措辞、画面语言、定时续期等共享规范统一在 `clipforge/shared/shared-rules`、`clipforge/shared/cron-renew` 中定义。各阶段文件仅保留阶段特有的规则，通过引用共享文件避免重复。
9. **音频内嵌。** 旁白和 BGM 通过 `<audio>` 元素嵌入 HTML，由 HyperFrames 原生混音和封装，无需 FFmpeg 手动合并音轨。
10. **清理不可跳过。** delivery 完成后，必须立即执行 cleanup（读取 `shared/cleanup-rules` 并按规则清理中间产物）。
11. **双版本输出不可省略。** video stage 必须产出 `output.mp4`（含 BGM）和 `output_no_bgm.mp4`（仅旁白）两个文件，delivery stage 必须产出对应的 `final.mp4` 和 `final_no_bgm.mp4`。无论项目类型或时长，缺少任一文件视为阶段未完成。
12. **引擎驱动约束。** 每个 stage 执行前由约束引擎注入正向规则，执行后由门禁引擎校验产出物。引擎规则（`rules/`）是机器可校验的结构化层，与 stage 文件中的文本规则并行生效。
13. **即时评分不可跳过。** delivery 后、cleanup 前，必须运行 gate 全量校验并产出 `score_report.json`。这是机器的预测分数，后续会用播放数据验证。
14. **延迟反馈校准机器。** 发布后补充播放数据和人类主观评分（Stage 8），用机器预测 vs 实际表现的偏差校准 gate 能力。反馈为可选，不阻塞 cleanup。

## 模式

ClipForge 支持三种视频模式，由内容来源自动决定：

| 模式 | 触发条件 | 目标时长   | 场景数 |
|------|---------|--------|--------|
| **标准模式** | 多主题盘点 / 快速资讯 | 45-55s | 6-8 个 |
| **单主题深度解析** | 只聚焦一个主题，需详细解读 | 45-60s | 7-8 个 |
| **电影解读模式** | 场景中含 `video_clip` 类型 | 3-5min | 不限 |

> **模式选择原则：** 用户明确指定时从用户；未指定时，内容涉及 2+ 个主题用标准模式，只聚焦 1 个主题用深度解析模式。各阶段文件中有对应的模板和规则。

## 分类系统

ClipForge 支持内容分类，每个分类有独立的配置文件：

```
clipforge/categories/
├── _category-schema.md   # 分类配置文件格式规范
├── github.md             # GitHub 开源项目分类
├── comics.md             # 漫画分类（未来）
└── novel.md              # 小说分类（未来）
```

### 分类配置的作用

分类配置覆盖通用 stage 文件中的分类特定规则：

| Stage | 分类可覆盖的内容 |
|-------|---------------|
| content | 数据获取方式、选取策略、深度调研方法、兜底方案 |
| design | 默认风格方向、配色偏好 |
| narration | 钩子模板、特殊文案规则、字数范围 |
| audio | 固定音色、语速 |
| delivery | 标签列表、评论区模板、封面徽章 |
| shared-rules | 数据验证规范 |

### 如何使用分类

- **交互模式**：用户指定分类时（如"用 GitHub 分类做一个视频"），控制器读取对应的分类配置文件，在执行各 stage 前注入分类覆盖规则
- **自动化模式**：cron 编排文件的 SubAgent prompt 中包含"读取 `categories/{id}.md`"指令，SubAgent 自动加载分类配置
- **未指定分类**：通用 stage 文件的规则直接生效，无需分类配置

### 标准模式 — 选取策略

标准模式的目标是**信息密度**：让观众在 45-55 秒内掌握核心信息。每个项目独占一屏（ProjectFullCard 组件），包含 8 层信息结构。具体选取策略由分类配置定义。未指定分类时，根据内容量和主题数量灵活安排。

### 单主题深度解析模式

当只聚焦一个主题时，采用 7-8 个场景的深度解读结构，覆盖原理、能力、应用、技术栈等维度，而非走马观花式概述。

**核心差异（vs 标准模式）：**
- 场景数从 4-5 增加到 7-8，每个场景专注一个维度
- 总时长从 25-55s 延长到 45-60s
- 文案字数从 150-300 字增加到 300-450 字
- Stage 1 需要更深入的调研（架构、原理、应用场景）
- Stage 3 使用 8 场景深度模板（hook → what → how → capabilities → usecases → tech → privacy → cta）
- 深度调研的具体维度由分类配置定义

## 共享规范索引

| 共享文件 | 内容 | 引用阶段 |
|---------|------|---------|
| `clipforge/shared/shared-rules` | 措辞规范、画面文字语言规范、CTA 时间规范、URL 禁止、黄金 3 秒 | Stage 1/3/6/7 |
| `clipforge/shared/render-safety` | HyperFrames 渲染安全规范 + 三层架构（重型参考） | Stage 6 |
| `clipforge/shared/cron-renew` | 定时任务自续期模式与参数 | 所有自动编排文件 |
| `clipforge/shared/cleanup-rules` | 项目完成后的文件保留/清理规则 | cleanup |
| `clipforge/shared/movie-clips` | 电影片段提取与拼接（仅电影解读模式） | narration → audio 之间 |
| `clipforge/shared/bgm-pixabay` | Pixabay BGM 批量下载（CDN 直链提取 + curl 下载） | audio 或独立执行 |
| `clipforge/shared/director-toolkit` | 导演思维工具包（5 个必答题 + 视觉词汇表 + 爆款导演笔记） | Stage 2/3/6 |
| `clipforge/shared/machine-scoring` | 即时机器评分（delivery 后自动运行 gate 全量校验） | delivery → cleanup 之间 |
| `clipforge/categories/{id}` | 分类配置（数据获取、风格、音色、标签等覆盖规则） | 各 stage 按需读取 |

**共享规范按需加载（不全文加载）：**

| Stage | `shared/shared-rules` 章节 | `shared/director-toolkit` | `shared/render-safety` |
|-------|---------------------|--------------------|-----------------|
| Stage 1 | §1 措辞 + §2 语言 | — | — |
| Stage 2 | — | 第 2 层 视觉词汇表 | — |
| Stage 3 | §1 措辞 + §5 黄金 3 秒 | 第 1 层 5 个必答题 + 第 2 层 | — |
| Stage 6 | §5 黄金 3 秒 + §6 切换频率 | 第 1 层 + 第 2 层 | §1 渲染安全 + §2 三层架构 |
| Stage 7 | §1 措辞 + §3 CTA | — | — |

> 每个共享规范文件顶部有章节号，只读取该 stage 需要的章节，不全文加载。引擎注入已包含结构化规则覆盖，共享规范提供"为什么这样做"的上下文。

**有分类配置时，stage 执行前通过 `engine/render_stage.py` 将分类配置值确定性替换到通用 stage 模板中。LLM 读到的是已合并的完整文件，无需自行做配置合并。分类配置文件中 CONFIG-END 后的详细指南仍需 LLM 读取（数据获取策略、选取规则等长文内容）。**

## 引擎层

ClipForge 引擎层提供四原子约束体系（Intent/Boundary/Gate/Trace），与 stage 文件并行生效。引擎层**不替代** stage 文件中的操作指令，而是提供结构化的约束注入和门禁校验。

### 引擎工具一览

| 工具 | 用途 | 调用时机 |
|------|------|---------|
| `engine/inject.py` | 生成约束 prompt（正向规则 + 经验模式 + Guard Red Flags） | Stage 执行前 |
| `engine/gate.py` | 校验产出物（file_exists / loudnorm / no_url 等） | Stage 执行后 |
| `engine/trace.py` | 记录执行轨迹（skill / result / score / violations） | Stage 完成后 |
| `engine/attribution.py` | 失败归因（强归因：规则匹配 / 弱归因：概率推断） | 门禁失败时 |
| `engine/constraints.py` | 约束集合准备（加载 + 去重 + 合并） | inject 内部调用 |
| `engine/governance.py` | 规则治理（冲突检测 / 膨胀预警） | 维护时使用 |

### 引擎调用约定

所有引擎命令在 `.claude/commands/clipforge/` 目录下执行：

```bash
# 约束注入（输出正向 prompt 段）
python engine/inject.py --skill stage4-audio [--category github]

# 门禁校验（exit 0=通过, 1=失败）
python engine/gate.py --skill stage4-audio --project-dir workspace/2026/05/27/github-trending/

# 轨迹记录
python engine/trace.py record --skill stage4-audio --project-dir workspace/2026/05/27/github-trending/ --result pass --score 85

# 失败归因
python engine/attribution.py --trace-file traces/github-trending/trace.json
```

### 规则与 Skill 的映射

每个 artifact 在 `schema.yaml` 中声明 `template`（如 `stage4-audio`），对应引擎层两个配置：

- **规则文件**：`rules/stage4.yaml` — 该阶段的 HARD/SOFT 约束
- **Skill 声明**：`skills/stage4-audio.yaml` — 四原子定义（Intent/Boundary/Gate/Trace）

全局规则（`rules/00-global-safety.yaml` 等）对所有阶段生效，stage 规则只对该阶段生效。分类规则（`rules/categories/github.yaml`）在指定分类时叠加。

## DAG 编排流程

### DAG 定义

所有 artifact 依赖关系定义在 `.claude/commands/clipforge/schema.yaml`。

### DAG 语义

| 语义 | 含义 | 使用场景 |
|------|------|---------|
| `requires` | 硬依赖，必须完成后才能开始 | 所有 artifact 的主要依赖 |
| `requires_any` | 条件依赖，当条件 artifact 触发时变硬依赖 | audio 等待 movie-clips |
| `optional` | 可选 artifact，不执行不阻塞下游 | assets 可选跳过 |
| `requires_optional` | 软依赖，若 optional artifact 已执行则等待，否则忽略 | video 对 assets |
| `condition` | 条件触发判断 | movie-clips 的 video_clip 检测 |

### DAG 依赖图

```
env-check → content → design ─┬→ narration → audio ──┬→ video → delivery → machine-scoring → cleanup
                               │                assets ┘                        ↓
                               └→ assets                                feedback（可选）
                                                  narration → movie-clips（条件）
```

### 交互模式（手动调用 /clipforge）

```
用户调用 /clipforge
  → 解析用户 prompt 中的方向关键词：
     - 包含「横屏」「landscape」「宽屏」→ 记录 user_orientation=landscape
     - 包含「竖屏」「portrait」「竖版」→ 记录 user_orientation=portrait
     - 无方向关键词 → user_orientation=null
  → 读取 schema.yaml，解析 artifact DAG
  → 扫描 generates 路径，检测已完成 artifact
  → 拓扑排序，确定执行队列
  → 逐个执行 ready artifact：
     1. 引擎注入：运行 python engine/inject.py --skill <stage-id> [--category <cat>]
        → 将输出（Intent + 正向规则 + 经验模式 + Guard Red Flags）拼入 stage prompt 前段
        → 若 user_orientation 已记录且当前 skill 为 stage2-analysis → 追加方向指令到 prompt
     2. 模板渲染：运行 python engine/render_stage.py --stage stages/<stage-file> --category <cat>
        → 将分类配置的值确定性替换到通用 stage 模板中（音色、标签、关键词等）
        → 无分类时用默认值，LLM 读到的是已合并的完整文件
     3. 读取渲染后的 stage 内容（而非原始模板）
     4. 如有分类，同时读取 clipforge/categories/{id}.md 的详细指南（CONFIG-END 后的内容）
     5. 执行 stage 技能内容
     6. 引擎门禁：运行 python engine/gate.py --skill <stage-id> --project-dir <dir>
        → HARD 门禁失败：展示违规项，要求修复后重新执行此 stage
        → SOFT 门禁失败：展示警告，由用户决定是否接受
        → 全部通过：继续
     7. 轨迹记录：运行 python engine/trace.py record --skill <stage-id> --project-dir <dir> --result pass/fail --score <N>
     8. 展示结果并确认
  → 完成后重新扫描状态，更新队列

> **方向：** 默认竖屏（portrait）。仅当用户明确指定「横屏」或分类配置含 `orientation_hint: landscape` 时才使用横屏。无时长自动推导。
  → 全部完成 → 触发 cleanup
  → 自动检测播放数据 → 结束
```

> **引擎命令基础路径**：`cd .claude/commands/clipforge && python engine/<tool>.py`

**自动检测播放数据**：cleanup 完成后，检查 `workspace/sources/视频数据/` 是否存在未处理的数据文件。如果存在，自动运行数据采集并提示用户是否进入 Stage 8 反馈校准：

```bash
# 检测是否有新数据（对比最近一次采集时间）
python scripts/collect_performance.py --scan --dry-run --json
# 如果有匹配结果，提示用户：
#   "检测到新的播放数据（N 条），已匹配到 M 个项目。是否现在分析数据并校准机器评分？"
#   用户确认后：python scripts/collect_performance.py --scan --backfill
#   然后进入 Stage 8 流程（参见 stages/stage8-feedback.md）
```

**注册播放数据提醒**：无论当前是否检测到数据，确保每日播放数据新鲜度检查任务已注册：

1. CronList 查找 prompt 包含 `playback-reminder` 的任务
2. 如已存在 → 跳过
3. 如不存在 → CronCreate(recurring=true, durable=true, cron="30 10 * * *")，prompt 内联检查逻辑（参见 `shared/playback-reminder.md`）
4. 提醒逻辑：扫描 `workspace/sources/视频数据/` 最新日期，超过 3 天未更新则催促用户导出平台数据（抖音、小红书、哔哩哔哩、微信视频号）

### 自动化模式（cron 编排文件）

```
Controller 读取 schema.yaml
  → 按 DAG 推导 SubAgent 批次
  → 逐批次调度：
     引擎注入：inject.py --skill <stage-id> 输出拼入 SubAgent prompt
     → 加载对应 stage 技能文件内容
     → SubAgent 完成后扫描 generates 文件验证
     → 引擎门禁：gate.py --skill <stage-id> --project-dir <dir>
     → HARD 门禁失败：SubAgent 自动修复并重试（最多 2 次）
     → 轨迹记录：trace.py record --skill <stage-id> --result pass/fail
     → 通过则下一批次
  → 全部完成 → 调用 shared/cron-renew 续期
  → 自动检测播放数据（同交互模式）
```

### SubAgent 批次分组

| 批次 | Artifact | 说明 |
|------|----------|------|
| SubAgent-1 | env-check → content → design → narration | 上游无并行，顺序执行 |
| SubAgent-1b | movie-clips（条件：仅当 narration 含 video_clip 场景时） | 插入 narration 之后、audio 之前 |
| SubAgent-2 | audio + assets（并行） | audio 依赖 narration（若 movie-clips 触发则等其完成），assets 依赖 design |
| SubAgent-3 | video | 等待 audio 完成（assets 为 optional，不阻塞） |
| SubAgent-4 | delivery → machine-scoring → cleanup | 收尾顺序执行 |

### SubAgent prompt 组装

每个 SubAgent 的 prompt 由两部分拼装：

1. `clipforge/stages/stageN-xxx.md` — 具体 stage 技能内容（包含执行步骤、规则、Anti-rationalization）
2. 项目上下文 — 数据文件路径、视频模式、内容类型等运行时参数

## 项目目录结构

工作目录按「年 → 月 → 日 → 项目」四级结构组织，公共资源集中管理。**路径全部使用英文**，避免 Windows 中文编码问题：

```
workspace/
├── covers/                                     # 公共封面库（非视频项目封面）
├── bgm/                                        # BGM 素材库（保留原始下载文件）
├── sources/                                    # 报告/内容源文件
│
└── <YYYY>/                                     # 按年归档
    └── <MM>/                                   #   按月归档
        └── <DD>/                               #     按日归档
            ├── github-trending/                #       日期下的具体项目
            ├── github-trending-weekly/
            └── <项目名>/                       #       项目目录（内容如下）
                ├── design.md           # design artifact
                ├── narration.txt       # narration artifact
                ├── narration_segments.json  # narration artifact
                ├── segment_durations.json  # audio artifact
                ├── narration.mp3       # audio artifact
                ├── narration.srt       # audio artifact
                ├── bgm.wav             # audio artifact
                ├── clips_16x9/         # movie-clips artifact（仅电影解读模式）
                ├── movie_audio.wav     # movie-clips artifact
                ├── clip_durations.json # movie-clips artifact
                ├── assets/             # assets artifact（可选）
                │   └── manifest.md     #   素材清单
                ├── index.html          # video artifact
                ├── output.mp4          # video artifact
                ├── output_no_bgm.mp4   # video artifact
                ├── cover.html          # delivery artifact（项目内生成）
                ├── cover.png           # delivery artifact
                ├── douyin.md           # delivery artifact
                ├── final.mp4           # delivery artifact
                ├── final_no_bgm.mp4    # delivery artifact
                └── .cleaned            # cleanup artifact
```

### 路径约定

| 概念 | 路径 | 说明 |
|------|------|------|
| **工作根目录** | `workspace/` | 所有视频项目的根 |
| **项目目录** | `workspace/<YYYY>/<MM>/<DD>/<项目名>/` | 单个视频的完整工作空间 |
| **公共封面库** | `workspace/covers/` | 非视频项目封面（公共用途） |
| **BGM 库** | `workspace/bgm/` | 配乐素材（保留原始下载文件供复用） |
| **源文件** | `workspace/sources/` | 报告、内容原文等 |

### 路径使用规则

1. **Stage 1 启动时**：确定当天日期，创建 `workspace/<YYYY>/<MM>/<DD>/<项目名>/` 作为项目目录
2. **所有阶段的工作目录**：`cd` 到项目目录执行
3. **路径简写**：各 Stage 文件中的 `<project-dir>` 指 `workspace/<YYYY>/<MM>/<DD>/<项目名>/`

## 错误恢复

当某个阶段产出不理想时，根据偏差类型选择最经济的回退路径：

| 问题 | 表现 | 回退到 | 级联范围 |
|------|------|--------|---------|
| 旁白时长偏差 1-3s | 视频节奏略快/慢 | video | 仅调整 data-duration 并重新渲染 |
| 旁白时长偏差 >3s | 场景时长严重不匹配 | narration | 重写场景时间轴 → audio → video → delivery |
| 视觉风格不对 | 配色/字体与内容不搭 | design | 重新推导风格 → assets → video |
| 旁白内容问题 | 文案不通顺/信息错误 | narration | 重写旁白 → audio → video → delivery |
| BGM 情绪不对 | 音乐与视频调性不搭 | audio | 更换 BGM + 调整 data-volume + 重新渲染 |
| 电影片段拼接硬切 | 片段间跳转突兀 | movie-clips | 增加 xfade 时长 → audio → video → delivery |
| 电影原音不清晰 | 对白被 BGM/旁白盖住 | video | 调整 `<audio data-volume>` 参数 |

> **原则：** 只回退到必须修改的最小阶段。DAG 依赖图决定了级联范围——上游改动会级联到所有下游 artifact。

### 引擎归因（失败诊断）

当 stage 执行失败或门禁不通过时，运行归因引擎定位根因：

```bash
python engine/attribution.py --trace-file traces/<project>/trace.json
```

归因引擎返回：违反的规则 ID（强归因）+ 可能的能力缺口/规则缺失（弱归因）。根据归因结果决定是修复重试还是回退上游。
