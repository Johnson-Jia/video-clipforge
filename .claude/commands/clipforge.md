---
name: clipforge
description: ClipForge — 从任意内容出发，编排带配乐的抖音短视频全流程创作。覆盖内容分析、场景拆解、TTS 旁白、配乐、竖屏视频渲染、封面生成、抖音文案。每个 stage 内部 = 确定轨（脚本/门禁，LLM 不碰）+ 创意轨（LLM 发挥）；HTML 结构由组装脚本确定性生成，渲染委托 /hyperframes-cli，约束与门禁由引擎层驱动。
---

# ClipForge — 短视频锻造

## 0. 角色

你是短视频制作的**调度编排者**。职责是决定**做什么、调用什么、检查什么**——不是"怎么做"。每个 stage 的具体操作步骤见 `stages/stageN-xxx.md`，本文件只定义调度层的范式、流程和约束。

**双轨铁律**：每个 stage 内部 = **确定轨**（脚本/门禁/schema 管控，LLM 不碰）+ **创意轨**（LLM 发挥）。详见 §1。

**HTML 禁手写**：HTML 结构由 `s6_assemble_html.py` 确定性生成（clip 包裹、GSAP 时间线、`<audio>` 嵌入、DOCTYPE），LLM **只填 `creative/` 碎片**的三层 div（bg/fx/content），**禁碰 `index.html`**；渲染委托 `/hyperframes-cli`。结构门禁失败 → 修 `creative/` 碎片后重跑 `s6_assemble.sh`，**绝不手补 `index.html`**。

**确定轨文件只读**（HARD，gate: config_integrity）：`skills/`、`rules/`、`engine/`、`scripts/`、`components/`、`schema.yaml` 是引擎与门禁的确定性配置，**LLM 一律只读，禁止任何修改**——不得降低门禁阈值（如 `min_bitrate_kbps`、字号下限、安全区），不得改引擎代码。门禁受阻时**只能改创意轨**（`creative/` 碎片、`style.css`、`cover_params.json`、`narration.txt`）。发现确定轨 bug：**报告，不得自行修复**，交人类决策。降低门禁阈值让次品通过 = 等同关闭门禁；`gate.py` 的 `hard_passed` 必须反映真实质量，不是被调出来的。

---

## 1. 双轨执行模型

每个 stage 内部 = 确定轨 + 创意轨。下表是全管线全景：

| Stage | 确定轨（脚本/门禁，LLM 不碰） | 创意轨（LLM 发挥） |
|-------|------------------------|----------------|
| 0 env | `env_check.sh` 全自动（Node/FFmpeg/edge-tts/yt-dlp/HyperFrames 检测+安装） | — |
| 1 content | 文件存在性检测 | 内容提炼/摘要/组织 |
| 2 design | orientation 判定（用户关键词 > 分类配置 > 默认竖屏） | 风格/情绪/配色方向/故事板 |
| 3 scenes | 节奏铁律/visual_phases 计数/narration.txt 格式/hook 模式门禁 | 场景文案/幽默注入/visual_intent/narration_anchor |
| 4 audio | `tts_pipeline.sh` + `bgm_pipeline.sh` 全自动；bgm_volume 由公式计算（禁手设） | BGM 选曲（风格匹配、来源选择） |
| 5 assets | manifest.md 存在性 | 素材创作（极少触发） |
| 6 video | `s6_prepare.sh` → `s6_assemble.sh` → `s6_render.sh` 全自动；4 层门禁 | 填 `creative/sNN.html` 三层 div（bg/fx/content）+ `style.css` |
| 7 delivery | `s7_delivery.sh` 全自动；封面模板锁定结构；cover_check 门禁 | `cover_params.json` 配色文案 + 四平台文案 `douyin.md` |
| 8 feedback | `auto_evolve.py` + `collect_performance.py` 全自动 | 人类主观评分（手动模式） |

**组件库约束**：bg 层强制从 `components/bg/` 选用 1 个组件（R-R-021 HARD），保留 `<!-- bg-component: NAME -->` 标记，允许换色/叠图，**禁自写 bg CSS**；底色 L≥12%、装饰 alpha≥0.12（否则 `frame_analysis.py` 拦截）。组件库共 65 个（27 bg + 14 fx + 24 content），经 `registry.yaml` 粗筛 + 情绪标签匹配，细节见 `stages/stage6-components.md`。

> 确定轨 LLM 不碰，跳过 = 产出不可靠；创意轨不受脚本限制。本表是「职责归属全景」，§4 时序图是「执行时序」，视角互补。

---

## 2. 全局原则

1. **短视频优先。** 标准模式 45-55s，深度解析 45-60s，电影解读 3-5min。前 3 秒必须有钩子，单画面元素停留不超过 3 秒（黄金 3 秒法则见 `shared/shared-rules` §5）。
2. **双轨铁律。** 确定轨由脚本/门禁执行，LLM 不碰（**含配置文件，见 §0「确定轨文件只读」**）；创意轨由 LLM 发挥。门禁受阻只能改创意轨，不得动确定轨配置或引擎代码。
3. **HTML 禁手写。** 结构由 `s6_assemble_html.py` 生成，LLM 只填 `creative/` 碎片；门禁失败修碎片重跑组装脚本，禁手改 `index.html`。
4. **状态即文件。** Artifact 完成 = `schema.yaml` 中 `generates` 声明的文件存在。不依赖 handoff 状态。
5. **依赖是使能者不是门禁。** `requires` 表示"输入就绪"，不阻塞跳过已完成的工作。
6. **每步确认（交互模式）。** 每阶段展示结果并确认。编排文件可设全自动模式，以编排文件为准。
7. **先内容后形式。** 先理解内容，再决定视觉和音乐。
8. **渐进加载。** 进入某阶段时才读对应 stage 文件，不一次性加载全部。
9. **音频内嵌 + 双版本输出。** 旁白/BGM 通过 `<audio>` 嵌入 HTML，HyperFrames 原生混音。video 必须产出 `output.mp4`（含 BGM）+ `output_no_bgm.mp4`（仅旁白），delivery 产出 `final.mp4` + `final_no_bgm.mp4`。缺任一 = 阶段未完成。
10. **清理不可跳过。** delivery 后立即执行 cleanup（`shared/cleanup-rules`，白名单机制）。
11. **引擎约束闭环。** 每个 stage 执行前跑 `python engine/inject.py --skill <stage-id>`，输出拼入 prompt 最前面——**跳过 = 自进化全部失效**；执行后跑 `engine/gate.py` 校验；delivery 后跑 gate 全量产出 `score_report.json`（机器预测分）。
12. **延迟反馈校准机器。** 发布后补播放数据（Stage 8）用预测 vs 实际偏差校准 gate。反馈可选，不阻塞 cleanup。

---

## 3. 模式与分类

### 模式

| 模式 | 触发 | 时长 | 场景数 |
|------|------|------|--------|
| 标准 | 多主题盘点/快速资讯 | 45-55s | 6-8 |
| 深度解析 | 单主题详解读 | 45-60s | 7-8 |
| 电影解读 | 含 `video_clip` 场景 | 3-5min | 不限 |

> 用户指定时从用户；未指定时 2+ 主题用标准，单主题用深度解析。详细模板在各 stage 文件。

### 分类

分类配置 `categories/{id}.md`（已有 github/intro）覆盖通用 stage 规则。`engine/render_stage.py` 三遍扫描（IF 条件块 / INJECT 注入 / `{{field|default}}` 替换）将分类配置合并到 stage 模板——**LLM 读到的是已合并的完整文件，无需手动路由**。

| 维度 | 覆盖 stage |
|------|-----------|
| 数据源/采集 | content |
| 风格/配色 | design |
| 叙事/钩子 | narration |
| 音色/语速 | audio |
| 标签/文案 | delivery |
| 画布方向 | design/video |

---

## 4. 脚本管线与调度流程

### 4.1 完整脚本管线时序

```
env_check.sh
  → [Stage 1-3 LLM 创意轨：content.md / design.md / narration_segments.json]
  → tts_pipeline.sh（TTS+合并+loudnorm+校验 → narration.mp3 / segment_durations.json / phase_timings.json）
  → bgm_pipeline.sh（验证+标准化+bgm_volume 公式+时长对齐 → bgm.wav）
  → s6_prepare.sh（phase 校准 + creative/ 碎片骨架 + visual_context.json）
  → [LLM 填 creative/sNN.html 碎片]
  → s6_assemble.sh（碎片验证 + 结构校验 + 组装 index.html + 导演门禁）
  → s6_render.sh（渲染前检查 + 导演门禁 + render + build_no_bgm + 完成门禁）
  → s7_delivery.sh（封面生成 + 门禁 + 拼接 + Mastering → final.mp4 / final_no_bgm.mp4）
  → [machine-scoring gate 全量 → score_report.json]
  → cleanup_project.sh（白名单清理 → .cleaned）
  → collect_performance.py → auto_evolve.py（自进化闭环）
```

> `[ ]` 内为 LLM 创意轨，其余为确定轨脚本（全自动）。电影模式在 narration 后插入 movie-clips（条件触发，见 §8）。

### 4.2 交互模式（手动 /clipforge）

```
用户调用 /clipforge
  → 解析方向关键词（横屏/竖屏）→ 记录 user_orientation
  → 读 schema.yaml，扫描 generates 检测已完成 artifact
  → 拓扑排序，逐个执行 ready artifact：
     1. ⛔ 约束注入铁律：python engine/inject.py --skill <stage-id> [--category <cat>]
        输出（Intent+正向规则+经验模式+Red Flags+Delta）拼入 prompt 最前面。跳过 = 自进化失效
     2. 模板渲染：python engine/render_stage.py --stage stages/<file> --category <cat>
     3. 读渲染后的 stage 内容；有分类则读 categories/{id}.md 指南
     4. 执行 stage（创意轨由 LLM，确定轨跑脚本）
        - Stage 6 特有：s6_prepare.sh → 填 creative/ 碎片 → s6_assemble.sh → s6_render.sh
     5. ⛔ 引擎门禁：python engine/gate.py --skill <stage-id> --project-dir <dir>
        HARD 失败→修复重跑此 stage；SOFT 失败→展示警告由用户定
     6. 轨迹记录：python engine/trace.py record --skill <id> --project-dir <dir> --result pass/fail --score <N>
     7. 展示结果并确认
  → 全部完成 → cleanup → 自动检测播放数据
```

> 默认竖屏。仅用户明确指定「横屏」或分类含 `orientation_hint: landscape` 才用横屏。无时长自动推导。

**自动检测播放数据**：cleanup 完成后，检查 `workspace/sources/视频数据/`。若有新数据，提示用户进入 Stage 8；并确保每日播放数据新鲜度检查 cron 已注册（`shared/playback-reminder`）。

### 4.3 自动化模式（cron 编排）

```
Controller 读 schema.yaml → 按 DAG 推导 SubAgent 批次 → 逐批调度：
  ⛔ 引擎注入铁律（同交互模式）
  → 加载 stage 技能文件
  → SubAgent 完成 → 扫描 generates 验证 → gate.py 门禁
  → HARD 失败：自动修复重试（最多 2 次）→ trace 记录 → 通过则下一批
  → 全部完成 → shared/cron-renew 续期 → 自动检测播放数据
```

### 4.4 SubAgent 批次分组

| 批次 | Artifact | 说明 |
|------|----------|------|
| SubAgent-1 | env-check → content → design → narration | 上游顺序执行 |
| SubAgent-1b | movie-clips（条件：narration 含 video_clip） | 插入 narration 后、audio 前 |
| SubAgent-2 | audio + assets（并行） | audio 依赖 narration（movie-clips 触发则等），assets 依赖 design |
| SubAgent-3 | video（s6_prepare→assemble→render） | 等 audio 完成（assets optional 不阻塞） |
| SubAgent-4 | delivery（s7）→ machine-scoring → cleanup | 收尾顺序 |

SubAgent prompt = stage 技能文件内容 + 项目上下文（数据路径、模式、内容类型）。

---

## 5. 引擎层

引擎层提供四原子约束体系（Intent/Boundary/Gate/Trace），与 stage 文件并行生效，不替代操作指令。

### 5.1 四原子 + 严谨度

| 原子 | 定义位置 | 作用 |
|------|---------|------|
| Intent | `skills/*.yaml` → intent | 目标 + 成功标准 |
| Boundary | `skills/*.yaml` → boundary.rule_refs | 规则引用（前缀匹配，如 R-G-* / R-R-*） |
| Gate | `skills/*.yaml` → gate.hard/soft | 门禁校验器列表 |
| Trace | `skills/*.yaml` → trace | 执行轨迹记录（result + gate_report） |

**严谨度**：LITE（仅 HARD 规则，env/assets）→ STANDARD（全量+经验模式，content/design/scenes/audio）→ STRICT（全量+Red Flags+spirit_vs_letter，仅 video）。

### 5.2 引擎工具

所有命令在 `.claude/commands/clipforge/` 下执行：

```bash
python engine/inject.py --skill stage4-audio [--category github]            # 执行前：约束注入
python engine/gate.py --skill stage4-audio --project-dir workspace/.../     # 执行后：门禁校验
python engine/trace.py record --skill stage4-audio --project-dir <dir> --result pass --score 85  # 完成后：轨迹
python engine/attribution.py --trace-file traces/<project>/trace.json       # 失败时：归因
python engine/render_stage.py --stage stages/<file> --category <cat>         # 执行前：分类合并
```

| 工具 | 用途 | 时机 |
|------|------|------|
| `inject.py` | 生成约束 prompt（正向规则+经验模式+Red Flags+Delta） | stage 执行前 |
| `gate.py` | 校验产出物（55+ checker） | stage 执行后 |
| `trace.py` | 记录轨迹（skill/result/score/violations） | stage 完成后 |
| `attribution.py` | 失败归因（强：规则匹配 / 弱：根因推断） | 门禁失败时 |
| `governance.py` | 规则治理（冲突/膨胀） | 维护时 |

### 5.3 自进化闭环

引擎具备规则自演化能力（无需人工改 `rules/*.yaml`）：

```
gate 失败 → trace 记录 → attribution 归因 → 生成 Delta（YAML 规则补丁）
→ shadow_validate 回放验证 → inject.py 自动应用 → promote/expire
```

| 阈值 | 值 |
|------|-----|
| 自动应用 | 置信度 ≥0.70 + 免审核 + 观察期 7 天 |
| promote 毕业 | ≥0.85 |
| expire 过期 | >30 天 + <0.70 |
| 争议率断路器 | 30 天内 >30% 触发全局暂停 |
| SAFETY 规则 | 不可被 Delta 移除（`merge_rules()` 强制保护） |

**约束注入铁律**是闭环入口——跳过 `inject.py` = Delta 演化规则全部失效。

### 5.4 规则体系

| 前缀 | 域 | 文件 |
|------|-----|------|
| R-G- | 全局安全 | 00-global-safety.yaml |
| R-C- | 内容规范 | 01-content-spec.yaml |
| R-R- | 渲染安全 | 02-render-safety.yaml |
| R-A- | 音频 | 03-audio.yaml |
| R-S2~/S3~/S4~/S6~/S7~/FB- | 各 stage 特有 | stageN.yaml |
| R-CG- | 分类（github） | categories/github.yaml |
| R-PAT- | pattern 衍生 | patterns/（auto_evolve 生成） |

severity：HARD（阻断）/ SOFT（评分）。RuleClass：SAFETY（不可覆盖）/ EXPERIENTIAL（可被 Delta 覆盖）/ QUALITY。Skill 通过 `boundary.rule_refs` 前缀匹配引用规则。

---

## 6. 门禁矩阵

```
Layer 0  engine/gate.py（55+ checker，全 stage 通用）
         file_exists / json_valid / loudnorm / no_url / no_forbidden_speech / no_real_person_name ...
Layer 1  director_gate.py（stage6 渲染前，HARD）
         字号层级 ≥2x / 光晕 opacity 0.15-0.6 / text-shadow / 相邻场景差异 / layer-fx 非空 / 结构完整
Layer 2  frame_analysis.py（stage6 渲染后，非阻塞）
         帧间差异 / 色彩多样性 / 暗帧（<12）/ 亮度分布
Layer 3  validate_html_structure.py（stage6 组装前）
         div 标签平衡 + 三层容器完整性
Layer 4  cover_check.py + validate_cover.py（stage7）
         封面 7 层结构 + PNG 文字像素
```

> **Layer 编号是门禁分类标识，非执行顺序。** stage6 实际执行时序：Layer 3（`validate_html_structure`，组装阶段）→ Layer 1（`director_gate`，渲染前 fail-fast）→ HyperFrames 渲染 → Layer 0（`gate.py`）+ Layer 2（`frame_analysis`，渲染后非阻塞，完成门禁）。Layer 4 为 stage7 封面专属，故 stage6 = **4 层门禁（Layer 0-3）**。
>
> **director_gate 三重调用为设计性冗余**：assemble（组装后即时校验）、render Step 4（渲染前 fail-fast，省 render 开销）、stage6_gate（独立入口自包含）各跑一次，幂等低开销，不删除。

| Stage | Layer 0（gate.py） | Layer 1-4（专用） |
|-------|--------------------|------------------|
| 0-3 | stage 对应 checker 子集（hook_pattern/no_forbidden_speech 等） | — |
| 4 | bgm_* / narration_* / loudnorm / bgm_volume_provenance | — |
| 6 | 32 HARD（STRICT）| director + frame_analysis + validate_html_structure |
| 7 | cover_layers / douyin_platforms / final_duration | cover_check |

| 严谨度 | HARD 失败 | SOFT 失败 |
|--------|----------|----------|
| STRICT（stage6）| 阻断，修复重跑 | 展示警告 |
| STANDARD | 阻断 | 展示警告 |
| LITE | 阻断 | 跳过 |

---

## 7. 共享规范索引

共享规范按需加载（不全文加载），只读对应 stage 需要的章节。

| 共享文件 | 角色 | 引用 stage |
|---------|------|-----------|
| `shared/shared-rules` | 措辞/CTA/黄金 3 秒/视觉切换（HARD gate 最多） | 1/3/6/7 |
| `shared/render-safety` | HyperFrames 渲染铁律 + 三层架构（stage6 必读） | 6 |
| `shared/director-toolkit` | 导演 5 必答题 + 视觉词汇表 | 2/3/6 |
| `shared/narration-anchoring` | narration_anchor 精确标注（0-index/句拆分） | 3 写 / 6 读 |
| `shared/visual-phasing` | Phase 视觉分镜（断点校准 + GSAP 偏移） | 3/4/6 |
| `shared/quality-checklist` | Stage 6 渲染前品质检查清单 | 6 |
| `shared/bgm-pixabay` | Pixabay BGM 批量下载 | 4 |
| `shared/movie-clips` | 电影片段提取/xfade 拼接（条件阶段） | narration→audio |
| `shared/machine-scoring` | 即时机器评分（gate 全量 → score_report.json） | delivery→cleanup |
| `shared/cleanup-rules` | 项目清理（白名单机制） | cleanup |
| `shared/cron-renew` | 定时任务自续期 | 所有 cron |
| `shared/playback-reminder` | 播放数据新鲜度检查 | 定时任务 |
| `categories/{id}` | 分类配置（render_stage.py 自动合并） | 各 stage |

| Stage | shared-rules | director-toolkit | render-safety |
|-------|--------------|------------------|---------------|
| 1 | §1 措辞 + §2 语言 | — | — |
| 2 | — | 层 2 视觉词汇表 | — |
| 3 | §1 措辞 + §5 黄金 3 秒 | 层 1 必答题 + 层 2 | — |
| 6 | §5 + §6 切换频率 | 层 1 + 层 2 | §1 渲染 + §2 三层 |
| 7 | §1 措辞 + §3 CTA | — | — |

---

## 8. DAG 编排

### 依赖图

```
env-check → content → design ─┬→ narration → audio ──┬→ video → delivery → machine-scoring → cleanup
                               │                assets ┘                        ↓
                               └→ assets                                feedback（optional）
                                    narration → movie-clips（条件）
```

### DAG 语义

| 语义 | 含义 | 用例 |
|------|------|------|
| `requires` | 硬依赖，必须完成 | 所有主依赖 |
| `requires_any` | 条件依赖，触发时变硬依赖 | audio 等 movie-clips |
| `optional` | 可选，不执行不阻塞 | assets / feedback |
| `requires_optional` | 软依赖，有则等无则忽略 | video 等 assets |
| `condition` | 条件触发 | movie-clips（narration 含 video_clip） |

> schema.yaml 的 `template` 字段指向 stage/shared 的 **markdown 文档**（如 `stages/stage4-audio` → `stages/stage4-audio.md`）。大部分 artifact 的文档名同时是 `skills/*.yaml` 的 skill id（供 inject/gate `--skill`）。**内联步骤**（machine-scoring）无 skill yaml，由 `gate.py --generate-report` 执行，不走四原子体系。`generates` 文件全存在 = artifact 完成。

---

## 9. 项目目录结构

工作目录按「年→月→日→项目」四级组织，**路径全英文**（避免 Windows 中文编码问题）：

```
workspace/
├── covers/ bgm/ sources/          # 公共封面库/BGM 库/源文件
└── <YYYY>/<MM>/<DD>/<项目名>/
    ├── design.md                  # design（含 style/mood/color_direction/storyboard/orientation）
    ├── narration.txt              # narration（一行一段）
    ├── narration_segments.json    # narration（分段+emotion/visual_intent/visual_phases）
    ├── segment_durations.json     # audio（每段实际时长 + meta.bgm_volume，Stage 6 唯一时长源）
    ├── sentence_timestamps.json / phase_timings.json   # ★ 运行时中间产物（TTS 强制对齐 + phase 校准）；非 artifact 完成判据，缺失由脚本运行时校验，不进 DAG 状态
    ├── narration.mp3 / narration.srt / bgm.wav
    ├── clips_16x9/ movie_audio.wav clip_durations.json   # movie-clips（仅电影模式）
    ├── assets/manifest.md         # assets（可选）
    ├── creative/                  # video 中间产物（s6_prepare 生成）
    │   ├── sNN.html               #   场景碎片（LLM 填三层 div）
    │   └── style.css              #   自定义 CSS（LLM 追加）
    ├── index.html                 # video（s6_assemble 组装，LLM 禁碰）
    ├── output.mp4 / output_no_bgm.mp4   # video 双版本
    ├── cover.html / cover.png / cover_params.json  # delivery
    ├── douyin.md                  # delivery（四平台文案）
    ├── final.mp4 / final_no_bgm.mp4     # delivery 双版本
    ├── score_report.json          # machine-scoring
    └── .cleaned                   # cleanup
```

| 概念 | 路径 |
|------|------|
| 工作根 | `workspace/` |
| 项目目录 | `workspace/<YYYY>/<MM>/<DD>/<项目名>/`（Stage 1 创建，各 stage 的 `<project-dir>`） |
| 公共封面库 / BGM 库 / 源文件 | `workspace/covers/` `workspace/bgm/` `workspace/sources/` |

---

## 10. 错误恢复

只回退到必须修改的最小阶段。DAG 决定级联范围。

| 问题 | 表现 | 回退到 | 修复 |
|------|------|--------|------|
| 旁白时长偏差 1-3s | 节奏略快/慢 | video | 调 data-duration 重渲染 |
| 旁白时长偏差 >3s | 场景时长严重不匹配 | narration | 重写时间轴 → audio → video → delivery |
| 视觉风格不对 | 配色/字体不搭 | design | 重推导风格 → narration → audio → video → delivery |
| 旁白内容问题 | 文案不通/信息错 | narration | 重写 → audio → video → delivery |
| BGM 情绪不对 | 音乐不搭 | audio | 换 BGM + 调 data-volume + 重渲染 |
| 碎片组装失败 | s6_assemble.sh 失败 | video | 修 `creative/sNN.html` 碎片重跑 s6_assemble.sh，**禁手改 index.html** |
| 视频黑屏 | output.mp4 码率 <500kbps | video | CSS class 可见性切换改 GSAP timeline（禁 .active/.show） |
| 电影片段硬切 | 片段跳转突兀 | movie-clips | 增 xfade 时长 → audio → video → delivery |
| 电影片段提取失败 | clip_durations.json 缺失 | narration | 移除 video_clip 场景 → 标准/深度流程 |
| 封面/交付失败 | final.mp4 缺失 | video | Stage 7 三级降级（HyperFrames→Chrome headless→ffmpeg 首帧） |

### 引擎归因

stage 失败或门禁不通过时，跑归因定位根因：

```bash
python engine/attribution.py --trace-file traces/<project>/trace.json
```

返回违反的规则 ID（强归因）+ 能力缺口/规则缺失（弱归因），据此决定修复重试还是回退上游。
