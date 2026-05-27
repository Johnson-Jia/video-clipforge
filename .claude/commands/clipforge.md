---
id: "clipforge"
name: clipforge
description: ClipForge — 通用短视频全流程创作 DAG 编排控制器
version: "2.0.0"
type: WORKFLOW
schema_ref: "clipforge/schema.yaml"
rules_lib_ref: "_rules-lib/"
patterns_ref: "_patterns/store.yaml"
trace_protocol_ref: "_trace-format/"
attribution_ref: "_attribution-protocol.md"
success_analysis_ref: "_success-analysis-protocol.md"
---

# ClipForge — 短视频锻造

你是短视频制作编排者。负责从内容到成品的**调度层**。HTML 组合和渲染由 HyperFrames 技能处理。

## Intent
> 编排从内容到竖屏短视频的全流程制作，含旁白、BGM 和封面。
> 成功标准：final.mp4 + final_no_bgm.mp4 + cover.png + douyin.md 全部产出，双闭环 Trace 已采集。

## Boundary — 编排准则

### 必须遵守（HARD 规则）

1. **委托不重写** — HTML 编写和渲染委托 HyperFrames 技能，不自行实现 ← `R-WF-001`
2. **状态即文件** — artifact 完成 = `generates` 文件存在，不依赖外部状态 ← `R-WF-002`
3. **双版本输出** — video/delivery 必须产出含 BGM 和仅旁白两个版本 ← `R-WF-003`
4. **清理不可跳过** — delivery 后必须执行 cleanup ← `R-WF-004`
5. **闭环必须运行** — 每次执行必须产出 Trace 数据，供归因和成功分析消费 ← `R-WF-005`

### 建议参考（偏好）
- 短视频优先：45-55s 标准模式（HIGH）
- 先内容后形式（MEDIUM）
- 渐进加载（只在进入阶段时读取）（MEDIUM）

## Gate — 编排门禁

### 流程门禁（每个批次完成后运行 `check_gates.sh` 自动验证）
- [ ] SubAgent-1: `design.md` + `narration_segments.json` + `narration.txt` 存在
- [ ] SubAgent-2: `segment_durations.json` + `narration.mp3` + `narration.srt` + `bgm.wav` 存在
- [ ] SubAgent-3: `output.mp4` + `output_no_bgm.mp4` 存在
- [ ] SubAgent-4: `final.mp4` + `final_no_bgm.mp4` + `cover.png` + `douyin.md` + `.cleaned` 存在

### 合规门禁（关键词/正则自动检查）
- [ ] SubAgent-1: 数据验证通过（双源交叉 ≥ 80%，项目数 ≥ 8）
- [ ] SubAgent-3: 旁白无广告敏感词，画面文字以中文为主
- [ ] SubAgent-4: 文案无 URL、无敏感词、标签 ≥ 5 个

## Trace — 运行级采集
- 批次结束时写入 `{project_dir}/trace/run-summary.yaml`
- 格式详见 `clipforge/_trace-format.md`

## Guard — 认知守卫

### Spirit vs Letter

| 规则 | 模式 | 真实意图 |
|------|------|---------|
| R-WF-001 | SPIRIT | 确保 HyperFrames 作为渲染层的单一职责，防止在 clipforge 层重复实现渲染逻辑 |
| R-WF-002 | SPIRIT | 确保中断恢复时能正确跳过已完成阶段，而非依赖外部状态文件 |
| R-WF-003 | SPIRIT | 确保用户始终有无 BGM 版本可用于自定义配乐或重新混音 |
| R-WF-004 | SPIRIT | 防止中间产物无限积累导致磁盘溢出 |
| R-WF-005 | SPIRIT | 确保系统能从历史执行中学习，而非每次从零开始 |

## 全局原则

1. **短视频优先。** 目标时长 45-55 秒（标准模式），单项目深度解析 45-60 秒，电影解读模式 3-5 分钟。前 3 秒必须有钩子，单个画面元素停留不超过 3 秒。
   - **黄金 3 秒法则**：hook 场景必须是纯钩子，正文从第 2 个场景开始。完整规则见 `_shared-rules` §5，HTML 实现见 Stage 6。
2. **委托，不重写。** HTML 编写委托 `/hyperframes`，渲染委托 `/hyperframes-cli`。能用 Skill 工具就自行触发，否则提示用户调用斜杠命令。
3. **状态即文件。** Artifact 完成状态 = `schema.yaml` 中 `generates` 声明的文件是否存在。不依赖 `stage-handoff.json`。
4. **依赖是使能者不是门禁。** `requires` 只表示"输入就绪"，不阻塞跳过已完成的工作。已完成 artifact 扫描到 `generates` 文件存在即跳过。
5. **每步确认（交互模式）。** 每个阶段展示结果并确认，不默认推进。编排文件可覆盖此原则（如设置为全自动模式），以编排文件指令为准。
6. **先内容后形式。** 先理解内容，再决定视觉和音乐。
7. **渐进加载。** 只在进入某阶段时读取对应的阶段文件，不一次性加载全部。
8. **共享规范优先。** 内容措辞、画面语言、定时续期等共享规范统一在 `clipforge/_shared-rules`、`clipforge/_cron-renew` 中定义。各阶段文件仅保留阶段特有的规则，通过引用共享文件避免重复。
9. **音频内嵌。** 旁白和 BGM 通过 `<audio>` 元素嵌入 HTML，由 HyperFrames 原生混音和封装，无需 FFmpeg 手动合并音轨。
10. **清理不可跳过。** delivery 完成后，必须立即执行 cleanup（读取 `_cleanup-rules` 并按规则清理中间产物）。
11. **双版本输出不可省略。** video stage 必须产出 `output.mp4`（含 BGM）和 `output_no_bgm.mp4`（仅旁白）两个文件，delivery stage 必须产出对应的 `final.mp4` 和 `final_no_bgm.mp4`。无论项目类型或时长，缺少任一文件视为阶段未完成。

## 闭环协议

ClipForge 通过**双闭环**持续进化。每次执行都产生 Trace 数据，供归因和成功分析消费。

### 自动化脚本

所有闭环操作通过脚本自动化执行，避免 Agent 手动解析 YAML 和计算评分：

```
.claude/commands/clipforge/scripts/
├── inject_patterns.sh              # 经验模式注入（按 skill_scope 过滤）
├── check_gates.sh                # 批次门禁检查（文件存在性验证）
├── calc_soft_score.py            # 软门禁评分计算（按 skill.yaml 中的 scoring 函数）
├── write_trace.sh                # Trace 文件生成（标准化 YAML 输出）
├── run_summary.py                # 运行汇总生成（聚合所有阶段 Trace）
├── aggregate_traces.py           # Trace 聚合（收集高分案例到全局目录）
├── apply_delta.py                # Delta Rule 应用（修改规则库 YAML）
├── upgrade_patterns.py           # SEED→VALIDATED 升级（source_traces ≥ 3）
├── check_injection_filter.sh     # 注入过滤器一致性检查
└── convert_relaxation_to_delta.py # 放宽提案转 Delta Rule
```

### Trace 采集（每批次必须执行）

**SubAgent 完成时的标准流程：**

1. 运行门禁检查：
   ```bash
   bash .claude/commands/clipforge/scripts/check_gates.sh {batch} {project_dir}
   ```

2. 计算软门禁评分（如适用）：
   ```bash
   python3 .claude/commands/clipforge/scripts/calc_soft_score.py {skill_scope} \
     --hook_duration=X --word_count=Y --phase_alignment=Z ...
   ```

3. 写入 Trace 文件：
   ```bash
   bash .claude/commands/clipforge/scripts/write_trace.sh {stage} {project_dir} \
     --status=PASSED|FAILED --soft_score=X.XX --constraint_hits=...
   ```

4. 生成运行汇总（仅 SubAgent-4 执行）：
   ```bash
   python3 .claude/commands/clipforge/scripts/run_summary.py {project_dir}
   ```

### 负向闭环（失败 → 归因 → 规则回流）

**自动触发条件**：`run-summary.yaml` 中存在 `status: FAILED` 的阶段

**执行流程**：
1. 读取 `trace/run-summary.yaml`，定位失败阶段
2. 执行**强归因**：检查已有规则是否覆盖此违规
3. 如未覆盖，进入**弱归因**：判定根因（rule_missing / capability_gap / rule_violation）
4. 产出 Delta Rule 候选，写入 `_deltas/D-{timestamp}.yaml`
5. 应用 Delta Rule（confidence ≥ 0.7 且 EXPERIMENTAL 时自动执行）：
   ```bash
   python3 .claude/commands/clipforge/scripts/apply_delta.py _deltas/ _rules-lib/
   ```

**协议详情**：`clipforge/_attribution-protocol.md`

### 正向闭环（成功 → 分析 → 经验沉淀）

**自动触发条件**：`run-summary.yaml` 中存在 `soft_score ≥ 0.85` 的阶段

**执行流程**：
1. 聚合高分 Trace 到全局目录：
   ```bash
   python3 .claude/commands/clipforge/scripts/aggregate_traces.py {project_dir} _success-traces/
   ```

2. 标记为"高分成功案例"，提取关键决策点
3. 与历史高分案例比对，识别重复模式
4. 校验不违规（负向闭环否决权）
5. 沉淀到 `_patterns/store.yaml`（type=SEED, requires_validation=true）
6. 升级满足条件的模式（source_traces ≥ 3）：
   ```bash
   python3 .claude/commands/clipforge/scripts/upgrade_patterns.py _patterns/store.yaml
   ```
7. 转换放宽提案为 Delta Rule（如有）：
   ```bash
   python3 .claude/commands/clipforge/scripts/convert_relaxation_to_delta.py _patterns/store.yaml _deltas/
   ```

**协议详情**：`clipforge/_success-analysis-protocol.md`

### 经验模式注入（每批次开始前）

**自动执行**：SubAgent 启动时自动注入匹配的经验模式

```bash
bash .claude/commands/clipforge/scripts/inject_patterns.sh {skill_scope}
```

**过滤逻辑**：
- 按 `skill_scope` 匹配（如 `clipforge.stage3-scenes`）
- 按 `weight` 排序（HIGH > MEDIUM > LOW）
- 输出 `as_preference.text`（SEED 和 VALIDATED 模式）
- 输出 `as_fewshot.example_output`（仅 VALIDATED 模式）

**注入位置**：SubAgent prompt 的"经验模式注入"段

### Trace 采集

每个阶段执行时，在 `{project_dir}/trace/` 目录下写入 Trace 文件：
- 格式：`stage{N}-{timestamp}.yaml`（详见 `clipforge/_trace-format.md`）
- 内容：gate_report（门禁结果）、constraint_hits（规则触碰）、artifacts（产出文件）
- 批次结束时写入 `run-summary.yaml`（汇总所有阶段状态）

### 负向闭环（失败 → 归因 → 规则回流）

当某阶段流程/合规门禁未通过时：
1. 记录违规详情到 Trace
2. 执行**强归因**：检查已有规则是否覆盖此违规
3. 如未覆盖，进入**弱归因**：判定根因（rule_missing / capability_gap / rule_violation）
4. 产出 Delta Rule 候选（详见 `clipforge/_attribution-protocol.md`）
5. confidence ≥ 0.7 且 EXPERIENTIAL → 自动执行；否则 → 标记待人工确认

### 正向闭环（成功 → 分析 → 经验沉淀）

当某阶段软门禁评分 ≥ 0.85 时：
1. 标记为"高分成功案例"，记录到 Trace
2. 提取关键决策点
3. 与历史高分案例比对，识别重复模式
4. 校验不违规（负向闭环否决权）
5. 沉淀到 `_patterns/store.yaml`（详见 `clipforge/_success-analysis-protocol.md`）

## 经验模式注入

每次执行前，从 `_patterns/store.yaml` 读取与当前 Skill 相关的经验模式：
- 按 `skill_scope` 过滤（如 Stage 3 只读取 scope 含 `stage3-scenes` 的模式）
- 将 `as_preference.text` 注入 SubAgent prompt 的"成功经验"段
- 将 `as_fewshot.example_output` 注入 few-shot 示例（如有）

SubAgent prompt 组装时追加：
```
成功经验（来自历史高分案例，供参考）：
{pattern_store 中相关偏好列表}
```

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
| `clipforge/_shared-rules` | 措辞规范、画面文字语言规范、CTA 时间规范、URL 禁止、黄金 3 秒 | Stage 1/3/6/7 |
| `clipforge/_render-safety` | HyperFrames 渲染安全规范 + 三层架构（重型参考） | Stage 6 |
| `clipforge/_cron-renew` | 定时任务自续期模式与参数 | 所有自动编排文件 |
| `clipforge/_cleanup-rules` | 项目完成后的文件保留/清理规则 | cleanup |
| `clipforge/_movie-clips` | 电影片段提取与拼接（仅电影解读模式） | narration → audio 之间 |
| `clipforge/_bgm-pixabay` | Pixabay BGM 批量下载（CDN 直链提取 + curl 下载） | audio 或独立执行 |
| `clipforge/_director-toolkit` | 导演思维工具包（5 个必答题 + 视觉词汇表 + 爆款导演笔记） | Stage 2/3/6 |
| `clipforge/_viral-cases/{file}` | 爆款视频案例库（多维度分析 + 可提取模式） | Stage 2/3/7 按需参考 |
| `clipforge/categories/{id}` | 分类配置（数据获取、风格、音色、标签等覆盖规则） | 各 stage 按需读取 |
| `clipforge/_patterns/store.yaml` | 经验模式库（从高分案例沉淀的可复用模式） | SubAgent prompt 注入 |
| `clipforge/_rules-lib/` | 结构化规则库（全局 + 场景 + 清理规则，统一编号） | 各 stage 的 Boundary 引用 |

**Stage 1/3/6/7 执行前，必须先读取 `clipforge/_shared-rules` 获取内容规范。Stage 2/3/6 执行前读取 `clipforge/_director-toolkit` 获取导演思维工具。Stage 6 额外读取 `clipforge/_render-safety` 获取渲染安全和三层架构规范。**

**有分类配置时，各 stage 还需读取 `clipforge/categories/{id}.md` 获取分类特定的覆盖规则。分类配置优先于通用 stage 文件中的默认值。**

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
env-check → content → design ─┬→ narration → audio ──┬→ video → delivery → cleanup
                               │                assets ┘
                               └→ assets
                                                  narration → movie-clips（条件）
```

### 交互模式（手动调用 /clipforge）

```
用户调用 /clipforge
  → 读取 schema.yaml，解析 artifact DAG
  → 扫描 generates 路径，检测已完成 artifact
  → 拓扑排序，确定执行队列
  → 逐个执行 ready artifact：
     1. 读取对应 stage 技能文件（如 clipforge/stage0-env）
     2. 执行 stage 技能内容
     3. 展示结果并确认
  → 完成后重新扫描状态，更新队列
  → 全部完成 → 触发 cleanup → 结束
```

### 自动化模式（cron 编排文件）

```
Controller 读取 schema.yaml
  → 按 DAG 推导 SubAgent 批次
  → 逐批次调度：
     加载对应 stage 技能文件内容
     → SubAgent 完成后扫描 generates 文件验证
     → 通过则下一批次
  → 全部完成 → 调用 _cron-renew 续期
```

### SubAgent 批次分组

| 批次 | Artifact | 说明 |
|------|----------|------|
| SubAgent-1 | env-check → content → design → narration | 上游无并行，顺序执行 |
| SubAgent-1b | movie-clips（条件：仅当 narration 含 video_clip 场景时） | 插入 narration 之后、audio 之前 |
| SubAgent-2 | audio + assets（并行） | audio 依赖 narration（若 movie-clips 触发则等其完成），assets 依赖 design |
| SubAgent-3 | video | 等待 audio 完成（assets 为 optional，不阻塞） |
| SubAgent-4 | delivery → cleanup | 收尾顺序执行 |

### SubAgent prompt 组装

每个 SubAgent 的 prompt 由两部分拼装：

1. `clipforge/stageN-xxx.md` — 具体 stage 技能内容（包含执行步骤、规则、Anti-rationalization）
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
                ├── trace/              # Trace 数据
                │   ├── stage0-*.yaml
                │   ├── stage1-*.yaml
                │   ├── ...
                │   └── run-summary.yaml
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
