<div align="center">

<img src="docs/images/logo.png" width="100%" alt="ClipForge Logo">

# ClipForge

**基于 Claude Code 的通用 AI 短视频生产管线**

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Claude Code Skills](https://img.shields.io/badge/Claude%20Code-Skills-orange)](https://docs.anthropic.com/en/docs/claude-code/skills)

[中文](#概述) · [English](README_EN.md)

从任意内容到抖音竖屏视频 — 全自动。

由 [HyperFrames](https://github.com/heygen-com/hyperframes) 提供原生混音和 MP4 渲染。

</div>

---

## 为什么选择 ClipForge

大多数 AI 视频工具是带固定模板的 GUI 应用。ClipForge 采用不同方式：基于 Claude Code 技能系统构建的**代码原生管线**，融合[自进化架构](docs/agent-self-evolution-architecture.md)设计理念。每个阶段是四原子（Intent + Boundary + Gate + Trace）定义的自包含技能，有双轨声明（结构化 YAML + 自然语言 MD）、三层门禁校验和双闭环反馈机制。

**结果：** 可审计、可自进化、可在 cron 上无人值守运行的生产级视频管线。

### 为什么不直接用 HyperFrames？

[HyperFrames](https://github.com/heygen-com/hyperframes) 是优秀的 HTML-to-Video 渲染器，但它只解决「最后一公里」——把一段 HTML 渲染成 MP4。一个完整的短视频还需要解决这些问题：

| 问题 | HyperFrames 的能力 | ClipForge 在此之上做了什么 |
|------|-------------------|--------------------------|
| **内容从哪来？** | 不涉及 | Stage 1 从 URL/PDF/GitHub/文本获取原始内容，分类系统定义每种内容的选取策略 |
| **视觉风格怎么定？** | 不涉及 | Stage 2 导演思维工具包（5 个必答题 + 视觉词汇表），从内容情感内核推导配色、排版、沉浸模式 |
| **旁白写什么？** | 不涉及 | Stage 3 场景拆解 + 6 拍情感节拍 + 分段旁白文案，每段独立 TTS 并追踪精确时长 |
| **音频怎么同步？** | 原生混音，但不生成音频 | Stage 4 分段 TTS → loudnorm 响度归一化 → BGM 选取 + 音量校准 → 音画精确对齐 |
| **HTML 怎么写？** | 渲染你给的 HTML | Stage 6 三层架构（背景/特效/内容）+ 13 个可组合组件 + GSAP 动画编排 + A/V 门禁校验 |
| **如何适配不同内容？** | 不涉及 | 分类系统（categories/）让每种内容有独立的数据源、音色、标签策略，无需改代码 |
| **如何批量自动化？** | 不涉及 | DAG 编排 + SubAgent 批次调度 + cron 定时任务 + 自动续期，每天无人值守产出视频 |
| **出了问题怎么回退？** | 不涉及 | DAG 依赖图驱动的级联回退表，只回退到最小必要阶段 |
| **系统如何自进化？** | 不涉及 | 双闭环反馈：失败→归因→规则回流，成功→分析→经验沉淀，约束库随运行数据自动丰富 |
| **磁盘会被撑爆吗？** | 不涉及 | 自动清理策略，每个项目交付后 < 30MB |

**简而言之：** HyperFrames 是渲染引擎，ClipForge 是从内容到成品的完整编排层 + 自进化框架。

## 概述

ClipForge 将任意内容 — 文字、URL、PDF、GitHub 数据等 — 转换为竖屏短视频（1080x1920），包含：

- **DAG 编排 8 阶段流水线** — 每个阶段是四原子定义的自包含技能（Intent + Boundary + Gate + Trace）
- **双轨声明格式** — 结构化元数据（`.skill.yaml`，机器消费）+ 自然语言指令（`.md`，Agent 注入）
- **双域分离** — 协议域零弹性（DAG、门禁、轨迹确定可审计），生成域满弹性（视觉、布局、音乐自主创作）
- **三层门禁** — 流程门禁（脚本检查）+ 合规门禁（正则匹配）+ 质量门禁（人类评价）
- **双闭环反馈** — 负向闭环（失败→归因→规则回流）+ 正向闭环（成功→分析→经验沉淀）
- **分类系统** — 通过可插拔的分类配置文件定义内容特有规则（数据获取、风格、音色、标签等）
- **三种视频模式** — 标准模式（45-55s）、单主题深度解析（45-60s）、电影解读（3-5min）
- **音频内嵌** — 旁白和 BGM 通过 `<audio>` 嵌入 HTML，HyperFrames 原生混音
- **定时任务自动化** — 每日/每周内容视频无人值守运行，定时任务自动续期
- **自动清理** — 交付后删除中间产物，每个项目保持 < 30MB

### 阶段流水线

| 阶段 | 产出 | 严谨度 | 说明 |
|------|------|:------:|------|
| Stage 0 | env-check | LITE | 依赖检测 + 自动安装 |
| Stage 1 | content | STANDARD | 内容获取（文字/文件/URL/分类数据源） |
| Stage 2 | design | STANDARD | 导演思维推导（情感内核 → 配色 → 沉浸模式 → 故事板） |
| Stage 3 | narration | STANDARD | 场景拆解 + 6 拍情感节拍 + 分段旁白文案 |
| Stage 4 | audio | STANDARD | 分段 TTS + loudnorm + BGM 选取 + 音量校准 |
| Stage 5 | assets | LITE | 视觉素材制备（可选，纯 CSS/HTML 渲染） |
| Stage 6 | video | **STRICT** | 三层架构 HTML + 13 组件 + GSAP 动画 → HyperFrames 渲染 |
| Stage 7 | delivery | STANDARD | 封面帧嵌入 + 封面图 + 3 套抖音文案 + 双版本输出 |
| Stage 8 | cleanup | LITE | 删除中间产物 |

DAG 定义在 [`schema.yaml`](.claude/commands/clipforge/schema.yaml) — artifact 依赖、条件阶段、可选阶段、严谨度分级，一处定义。

## 架构设计

### 四原子模型

每个 Skill（能力单元）由四个核心原子组成：

```
Skill = Intent + Boundary + Gate + Trace
```

| 原子 | 职责 | 方向 |
|------|------|------|
| **Intent** | 要达成什么（≤2 句话） | 正向，极简 |
| **Boundary** | 不能做什么（结构化规则集） | 负向，约束 |
| **Gate** | 怎样算通过（三层门禁） | 校验，分级 |
| **Trace** | 如何改进（执行轨迹采集） | 反馈，闭环 |

### 双域分离

Agent 的运行空间被分为两个域，遵循相反的自由度策略：

```
┌──────────────────────────────┐  ┌─────────────────────────┐
│       协 议 域                │  │       生 成 域           │
│       (Protocol Domain)      │  │       (Generation Domain)│
│                              │  │                         │
│  零弹性 · 确定 · 可审计       │  │  满弹性 · 自主 · 受边界  │
│                              │  │                         │
│  DAG 拓扑                    │  │  视觉特效选择            │
│  门禁评估流程                 │  │  布局/字号/配色          │
│  轨迹采集结构                 │  │  音乐/音效风格           │
│  规则注入管线                 │  │  文案措辞/幽默密度       │
│  归因双层级                   │  │  路径切换决策            │
└──────────────┬───────────────┘  └───────────┬─────────────┘
               │                              │
               └──────────┬───────────────────┘
                          │
                   ┌──────┴──────┐
                   │    Gate     │  ← 协议域通过 Gate 检验
                   │  （门禁）   │    生成域的产出，但从不
                   └─────────────┘    干预生成路径
```

**判定准则**：一个能力如果交给 Agent 自主决定会导致安全性不可审计，就归入协议域；否则归入生成域。

### 三层门禁模型

| 层级 | 名称 | 检查方式 | 不通过动作 | 域归属 |
|------|------|---------|-----------|--------|
| **process** | 流程门禁 | 自动化脚本（文件存在性、格式校验） | 立即驳回 → 归因 | 协议域 |
| **compliance** | 合规门禁 | 关键词/正则匹配（敏感词、URL） | 立即驳回 → 归因 | 协议域 |
| **quality** | 质量门禁 | 人类评价 / 外部播放数据 | 记录但放行 | 生成域 |

### 双闭环反馈

```
        负 向 闭 环（约束优化 · 减少犯错）
        犯错 → 归因 → 收紧约束 → 下次不犯这个错
        作用：提升 Agent 的下限（越来越安全）
                      ↕ 互相制衡
        正 向 闭 环（能力进化 · 发现优秀）
        成功 → 分析 → 沉淀经验 → 下次做得更好
        作用：提升 Agent 的上限（越来越强大）
```

- **负向闭环**：失败案例 → 双层归因（强归因自动 + 弱归因需置信度）→ Delta Rule → 规则库更新
- **正向闭环**：高分案例 → 经验模式提炼 → Pattern Store → 注入后续执行
- **制衡**：负向闭环否决违规经验沉淀；正向闭环提案放宽过严约束

### 双轨声明格式

| 维度 | `.skill.yaml` | `.md` |
|------|:---:|:---:|
| **读者** | 运行时引擎（机器解析） | Agent prompt 注入 + 人类阅读 |
| **内容** | 结构化字段（规则 ID、阈值、门禁） | 自然语言描述（操作指令、守卫） |
| **创建门槛** | 中（需理解 YAML schema） | 低（写 Markdown 即可） |

### 渐进严谨度

三级严谨度调节**协议域的厚度**——生成域的自由度始终不变：

| | LITE | STANDARD | STRICT |
|---|---|---|---|
| **适用** | 低风险、高频 | 通用（默认） | 高风险、合规敏感 |
| **约束注入** | 仅 HARD 规则 | 全量 + 经验模式 | 全量 + Guard 完整加载 |
| **门禁** | 仅流程门禁 | 流程 + 合规 | 三层 + 人工复核 |
| **轨迹** | SUMMARY | FULL | FULL（不可降级） |
| **归因** | 仅强归因 | 双层归因 | 双层 + 归因审计 |

## 快速开始

```bash
# 1. 克隆仓库
git clone https://github.com/Johnson-Jia/video-clipforge.git
cd video-clipforge

# 2. 启动 Claude Code（技能自动加载）
claude

# 3. 生成视频
/clipforge 制作一个关于 XXX 的视频
```

首次运行自动检测并安装依赖（HyperFrames）。

**前置依赖：** Node.js >= 22、FFmpeg、edge-tts、yt-dlp。详见 [安装指南](docs/getting-started.md)。

## 使用方式

### 交互模式

```
/clipforge 从这篇文章生成视频：https://...
```

Claude 逐步引导完成每个阶段，每步确认后继续。

### 定时任务

| 任务 | 命令 | 说明 |
|------|------|------|
| 每日热门视频 | `/github-daily-trending` | 每天自动执行 |
| 每周汇总视频 | `/github-weekly-trending` | 每周自动执行 |
| 每周知乎文章 | `/github-weekly-zhihu` | 每周自动执行 |

全自动化：数据采集（三源交叉验证）→ 视频生产 → 交付 → 清理 → 定时任务自动续期。

## 核心子系统

### 技能基础设施

| 子系统 | 目录/文件 | 作用 |
|--------|----------|------|
| 规则库 | `_rules-lib/` | 结构化规则（GLOBAL/SCENE/SKILL 三级作用域，SAFETY/EXPERIENTIAL 双轨分类） |
| 经验模式库 | `_patterns/store.yaml` | 从高分案例沉淀的可复用模式（SEED → VALIDATED 生命周期） |
| 归因协议 | `_attribution-protocol.md` | 失败根因判定（强归因自动 + 弱归因需置信度） |
| 成功分析协议 | `_success-analysis-protocol.md` | 高分案例模式提炼（偏好/few-shot/放宽提案三种沉淀方式） |
| 轨迹格式 | `_trace-format.md` | 执行轨迹采集标准（供双闭环消费） |
| 元技能 | `_meta-skills/` | 架构自身运维能力（规则治理、归因判定、成功分析） |

### 创作工具

| 子系统 | 文件 | 作用 |
|--------|------|------|
| 导演思维工具包 | `_director-toolkit/` | 5 个必答题 + 视觉词汇表 + 爆款案例（按层分段加载） |
| 渲染安全规范 | `_render-safety.md` | HyperFrames 事故复盘：禁用 CSS anim-in、三层架构、安全区 padding |
| 内容规范 | `_shared-rules/` | 措辞、画面文字语言、CTA、URL 禁止、黄金 3 秒（按消费方分段加载） |
| 分类配置 | `categories/` | 分类特有规则覆盖（按 Stage 分段加载，减少 token 消耗） |
| 组件库 | `components/` | 13 个可组合视觉组件（按需加载单个组件文件） |

### 自动化脚本

| 脚本 | 作用 |
|------|------|
| `inject_patterns.sh` | 经验模式注入（按 skill_scope 过滤，替代全量加载） |
| `check_gates.sh` | 三层门禁检查（process + compliance + quality） |
| `write_trace.sh` | Trace 文件标准化生成 |
| `calc_soft_score.py` | 质量评分计算（外部指标 + 内置函数） |
| `run_summary.py` | 运行汇总生成（聚合所有阶段 Trace） |
| `aggregate_traces.py` | 高分案例聚合（跨项目收集到全局目录） |
| `apply_delta.py` | Delta Rule 应用（修改规则库 YAML） |
| `upgrade_patterns.py` | SEED→VALIDATED 升级检查 |
| `convert_relaxation_to_delta.py` | 放宽提案转 Delta Rule |
| `check_injection_filter.sh` | 注入过滤器一致性诊断 |

## 抖音合规

- 视频画面和旁白文案**不出现 URL**，只展示项目名称
- 不点名商业品牌（不说"GPT/DeepSeek"，说"大语言模型/AI 助手"）
- 禁止广告敏感词（"必装/神器/赶紧/最强/免费领"）
- 自动生成 3 套不同风格文案：爆款钩子型 / 信息差型 / 极简型

## 依赖

### 自动安装

| 依赖 | 用途 |
|------|------|
| HyperFrames | HTML 转视频渲染，原生混音封装 |

### 手动安装

| 依赖 | 用途 | 安装 |
|------|------|------|
| Node.js >= 22 | HyperFrames CLI | `winget install OpenJS.NodeJS.LTS` |
| FFmpeg | 音视频处理 | `winget install Gyan.FFmpeg` |
| edge-tts | 中文 TTS 旁白 | `pip install edge-tts` |
| yt-dlp | YouTube 免版税音乐 | `pip install yt-dlp` |

## 扩展

- **新内容源：** 添加 cron 文件（参照 `github-daily-trending.md`），获取数据并分派 SubAgent
- **新分类：** 在 `categories/` 下创建配置文件，定义该分类特有的规则覆盖
- **新阶段：** 在 `schema.yaml` 中添加 artifact，创建对应的 `stageN-xxx.skill.yaml` + `stageN-xxx.md` 双轨文件
- **新规则：** 在 `_rules-lib/` 中添加规则，通过 `ref:` 引用到 skill.yaml 的 Boundary 段
- **新经验模式：** 高分案例经成功分析协议自动沉淀到 `_patterns/store.yaml`

详见 [CONTRIBUTING.md](CONTRIBUTING.md)。

## 项目结构

```
video-clipforge/
├── CLAUDE.md                              # AI 代理入口点
├── README.md                              # 中文说明（本文件）
├── LICENSE                                # Apache 2.0
├── docs/
│   ├── agent-self-evolution-architecture.md # 自进化架构设计文档（权威）
│   └── getting-started.md                 # 安装与首次使用
├── .claude/commands/
│   ├── clipforge.md                       # 主控制器（DAG 编排 + 双闭环协议）
│   ├── github-daily-trending.md           # 每日定时任务编排
│   ├── github-weekly-trending.md          # 每周定时任务编排
│   ├── github-weekly-zhihu.md             # 每周知乎文章编排
│   └── clipforge/
│       ├── schema.yaml                    # Artifact DAG（唯一事实源，含严谨度分级）
│       │
│       ├── ─── 双轨技能文件 ───────────────────
│       ├── stage0-env.md / .skill.yaml    # Stage 0: 环境检测 (LITE)
│       ├── stage1-content.md / .skill.yaml # Stage 1: 内容获取 (STANDARD)
│       ├── stage2-analysis.md / .skill.yaml # Stage 2: 风格推导 (STANDARD)
│       ├── stage3-scenes.md / .skill.yaml  # Stage 3: 场景+旁白 (STANDARD)
│       ├── stage4-audio.md / .skill.yaml   # Stage 4: TTS+BGM (STANDARD)
│       ├── stage5-assets.md / .skill.yaml  # Stage 5: 素材 (LITE, 可选)
│       ├── stage6-production.md / .skill.yaml # Stage 6: 渲染 (STRICT)
│       ├── stage7-delivery.md / .skill.yaml # Stage 7: 交付 (STANDARD)
│       ├── _movie-clips.md / .skill.yaml   # 电影片段 (条件阶段)
│       ├── _cron-renew.md / .skill.yaml    # 定时续期 (STRICT)
│       ├── _cleanup-rules.md               # 清理规则
│       │
│       ├── ─── 自进化基础设施 ─────────────────
│       ├── _rules-lib/                    # 结构化规则库
│       │   ├── global-rules.yaml          #   GLOBAL 级规则 (17 条)
│       │   ├── video-production-rules.yaml #   SCENE 级规则 (15 条)
│       │   └── cleanup-rules.yaml         #   清理规则 (5 条)
│       ├── _patterns/                     # 经验模式库
│       │   ├── store.yaml                 #   模式存储 (SEED/VALIDATED)
│       │   └── README.md                  #   使用说明
│       ├── _attribution-protocol.md       # 归因协议（负向闭环）
│       ├── _success-analysis-protocol.md  # 成功分析协议（正向闭环）
│       ├── _trace-format.md               # Trace 格式定义
│       ├── _deltas/                       # Delta Rule 暂存（运行时填充）
│       ├── _success-traces/               # 高分案例聚合（运行时填充）
│       ├── _meta-skills/                  # 元技能（架构自运维）
│       │   ├── rule-governance.md         #   规则库治理
│       │   ├── attribution.md             #   归因判定
│       │   └── success-analysis.md        #   成功分析
│       │
│       ├── ─── 创作工具 ─────────────────────
│       ├── _director-toolkit/             # 导演思维工具包（按层分段加载）
│       │   ├── questions.md               #   第 1 层：5 个必答题
│       │   ├── vocabulary.md              #   第 2 层：视觉词汇表
│       │   └── cases.md                   #   第 3 层：爆款案例解码
│       ├── _shared-rules/                 # 内容规范（按消费方分段加载）
│       │   ├── writing.md                 #   措辞+CTA+内容安全
│       │   ├── visual.md                  #   画面文字+黄金3秒+切换频率
│       │   └── render-ref.md              #   渲染安全引用
│       ├── _render-safety.md              # 渲染安全 + 三层架构（完整版）
│       ├── _bgm-pixabay.md                # Pixabay BGM 下载工具
│       ├── _viral-cases/                  # 爆款视频案例库
│       │   └── 05-19-douyin.md            #   05-19 爆款复盘
│       ├── stage6-components.md           # 组件索引（按需加载）
│       ├── stage6-components-ref.md       # 组件参考材料（设计格言+配色+布局）
│       │
│       ├── ─── 分类与模板 ───────────────────
│       ├── categories/                    # 分类配置（按 Stage 分段加载）
│       │   ├── _category-schema.md        #   分类格式规范
│       │   ├── github.md                  #   GitHub 分类索引
│       │   └── github/                    #   GitHub 分类分段文件
│       │       ├── content-design-narration.md
│       │       ├── audio.md
│       │       └── delivery.md
│       ├── templates/                     # SubAgent prompt 模板
│       │   ├── subagent-1-content.md      #   批次 1: 内容+设计+旁白
│       │   ├── subagent-2-audio.md        #   批次 2: 音频
│       │   ├── subagent-3-video.md        #   批次 3: 视频渲染
│       │   └── subagent-4-delivery.md     #   批次 4: 交付+清理
│       │
│       ├── ─── 组件与脚本 ───────────────────
│       ├── components/                    # 视觉组件库（13 个，按需加载）
│       │   ├── hero_card.html             #   首屏英雄卡片
│       │   ├── project_full_card.html     #   项目完整信息卡
│       │   ├── text_reveal.html           #   文字揭示动画
│       │   ├── code_rain.html             #   代码雨特效
│       │   ├── particle_burst.html        #   粒子爆发
│       │   ├── pulse_orb.html             #   脉冲光球
│       │   ├── star_counter.html          #   星标计数器
│       │   ├── timeline_flow.html         #   时间线流动
│       │   ├── compare_split.html         #   对比分屏
│       │   ├── data_viz.html             #   数据可视化
│       │   ├── speech_bubble.html         #   气泡对话
│       │   ├── char_overlay.html          #   角色叠加
│       │   └── three_scene.html           #   Three.js 3D 场景
│       └── scripts/                       # 自动化脚本（31 个）
│           ├── ─── 闭环自动化 ──────────────
│           ├── inject_patterns.sh         #   经验模式注入器
│           ├── check_gates.sh             #   三层门禁检查器
│           ├── write_trace.sh             #   Trace 文件生成器
│           ├── calc_soft_score.py         #   质量评分计算器
│           ├── run_summary.py             #   运行汇总生成器
│           ├── aggregate_traces.py        #   Trace 聚合器
│           ├── apply_delta.py             #   Delta Rule 应用器
│           ├── upgrade_patterns.py        #   SEED→VALIDATED 升级器
│           ├── convert_relaxation_to_delta.py # 放宽提案转换器
│           ├── check_injection_filter.sh  #   注入过滤器诊断
│           ├── ─── 生产管线 ────────────────
│           ├── github_trending.py         #   GitHub Trending 抓取
│           ├── tts_pipeline.sh            #   TTS 流程脚本
│           ├── tts_segments.py            #   分段 TTS 管线
│           ├── bgm_pipeline.sh            #   BGM 处理管线
│           ├── bgm_gap_check.py           #   BGM 缺口检测
│           ├── loudnorm.sh                #   loudnorm 响度归一化
│           ├── polyphone_fix.py           #   TTS 多音字预处理
│           ├── assemble_final.sh          #   TS concat 无损拼接
│           ├── merge_video_audio.sh       #   音视频合并
│           ├── merge_srt.py               #   SRT 字幕合并
│           ├── render_cover.sh            #   封面渲染
│           ├── validate_cover.py          #   封面结构门禁
│           ├── stage6_gate.sh             #   Stage 6 A/V 门禁
│           ├── director_gate.py           #   导演思维门禁
│           ├── frame_analysis.py          #   帧分析工具
│           ├── movie_narration.py         #   电影旁白合成
│           ├── movie_xfade.sh             #   电影片段 xfade
│           ├── env_check.sh               #   环境检测
│           ├── cleanup_project.sh         #   项目清理
│           ├── generate_bgm.py            #   MusicGen BGM 生成
│           └── validate_schema.py         #   Schema 校验
└── workspace/                             # 输出目录（gitignored）
```

## 设计哲学

参照 [Agent 自进化架构](docs/agent-self-evolution-architecture.md) 的九条设计原则：

| 原则 | 内容 |
|------|------|
| **P1** 负向为主，正向为辅 | 禁止规则定义边界，极简目标指明方向，Red Flags 认知层拦截 |
| **P2** 双域分离 | 协议域零弹性（确定可审计），生成域满弹性（自主创新） |
| **P3** 双向沉淀 | 失败→规则（减少犯错），成功→模式（提升能力） |
| **P4** 闭环耦合，DAG 驱动 | 四原子单次独立、跨执行耦合；工件依赖图驱动调度 |
| **P5** 证据驱动，增量表达 | 规则变更用 Delta Rule，每条可追溯到来源 Trace |
| **P6** 安全底线不可逾越 | SAFETY 约束只收紧不放宽，EXPERIENTIAL 可双向调整 |
| **P7** 双闭环互相制衡 | 负向否决违规经验，正向提案放宽过严约束 |
| **P8** 轻量创建，重量执行 | 写 Markdown 就能创建 Skill，运行时校验不因创建简单而缩水 |
| **P9** 渐进严谨度 | LITE/STANDARD/STRICT 三级，调节协议域厚度，生成域自由度不变 |

## 赞赏支持

如果 ClipForge 帮你做出了满意的视频，欢迎请创作者喝杯咖啡续命 ☕

让 AI 帮你做视频是免费的，但教会 AI 做视频的那些深夜，全靠咖啡因撑着。

<div align="center">

| 支付宝 | 微信 |
|:---:|:---:|
| <img src="docs/images/ali_pay_qrcode.jpg" width="200" alt="支付宝"> | <img src="docs/images/wechat_pay_qrcode.png" width="200" alt="微信"> |

</div>

## 许可证

[Apache License 2.0](LICENSE)
