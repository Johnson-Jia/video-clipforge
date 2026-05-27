<div align="center">

<img src="docs/images/logo.png" width="100%" alt="ClipForge Logo">

# ClipForge

**AI 短视频自进化生产管线 — 弱引导 · 强边界 · 双闭环反馈**

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)

从任意内容到抖音竖屏视频 — 全自动。

由 [HyperFrames](https://github.com/heygen-com/hyperframes) 提供原生混音和 MP4 渲染。

</div>

---

## 为什么选择 ClipForge

大多数 AI 视频工具是带固定模板的 GUI 应用。ClipForge 采用不同方式：基于 **Agent 自进化架构** 构建的代码原生管线。不是写死每一步"怎么做"，而是定义"不能做什么"和"做成什么样算合格"，把创造空间留给 Agent。

核心差异：

1. **不教 Agent 怎么做，教它不能怎么做** — 负向约束 + 正向重述，定义边界而非路径
2. **从失败和成功中自动进化** — 每次执行采集 trace，归因失败收紧规则，分析成功沉淀模式
3. **数据驱动优化** — 基于 58 条抖音视频 + 30 条视频号 + 36 条小红书的真实播放数据优化技能
4. **流程层零自由度，内容层最大自由度** — LETTER（流程）按字面精确执行，SPIRIT（内容）按意图灵活解释

### 为什么不直接用 HyperFrames？

[HyperFrames](https://github.com/heygen-com/hyperframes) 是优秀的 HTML-to-Video 渲染器，但它只解决「最后一公里」——把一段 HTML 渲染成 MP4。一个完整的短视频还需要解决这些问题：

| 问题 | HyperFrames 的能力 | ClipForge 在此之上做了什么 |
|------|-------------------|--------------------------|
| **内容从哪来？** | 不涉及 | Stage 1 从 URL/PDF/GitHub/文本获取原始内容，分类系统定义每种内容的选取策略 |
| **视觉风格怎么定？** | 不涉及 | Stage 2 导演思维工具包（5 个必答题 + 视觉词汇表），从内容情感内核推导配色、排版、沉浸模式 |
| **旁白写什么？** | 不涉及 | Stage 3 场景拆解 + 6 拍情感节拍 + 分段旁白文案，每段独立 TTS 并追踪精确时长 |
| **音频怎么同步？** | 原生混音，但不生成音频 | Stage 4 分段 TTS → loudnorm 响度归一化 → BGM 选取 + 7 档音量表 → 音画精确对齐 |
| **HTML 怎么写？** | 渲染你给的 HTML | Stage 5-6 三层架构（背景/内容/特效）+ 13 个可组合组件 + GSAP 动画编排 + A/V 门禁校验 |
| **如何适配不同内容？** | 不涉及 | 分类系统（categories/）让每种内容有独立的数据源、音色、标签策略，无需改代码 |
| **如何批量自动化？** | 不涉及 | DAG 编排 + SubAgent 批次调度 + cron 定时任务 + 自动续期，每天无人值守产出视频 |
| **如何从数据中进化？** | 不涉及 | Trace 采集 → 归因引擎 → Delta Rule 增量更新 → 成功分析 → Pattern 沉淀，双闭环自进化 |
| **出了问题怎么回退？** | 不涉及 | DAG 依赖图驱动的级联回退表，只回退到最小必要阶段 |

---

## 概述

ClipForge 将任意内容 — 文字、URL、PDF、GitHub 数据等 — 转换为竖屏短视频（1080x1920），包含：

- **DAG 编排 8 阶段流水线** — 每个阶段是自包含技能文件，有明确的输入/输出和错误恢复路径
- **Agent 自进化引擎** — 四原子模型（Intent/Boundary/Gate/Trace）+ 双闭环反馈（负向归因 + 正向分析）
- **数据驱动优化** — 基于三平台真实播放数据的 hook 模式优先级、5s 完播率目标、跨平台发布策略
- **三种视频模式** — 标准模式（45-55s）、单主题深度解析（45-60s）、电影解读（3-5min）
- **音频内嵌** — 旁白和 BGM 通过 `<audio>` 嵌入 HTML，HyperFrames 原生混音
- **分段精确 A/V 同步** — 分段 TTS + 每段时长追踪，消除音画漂移
- **定时任务自动化** — 每日/每周内容视频无人值守运行，定时任务自动续期
- **自动清理** — 交付后删除中间产物，每个项目保持 < 30MB

### 阶段流水线

| 阶段 | 产出 | 说明 |
|------|------|------|
| Stage 0 | env-check | 依赖检测 + 自动安装 |
| Stage 1 | content | 内容获取（文字/文件/URL/分类数据源） |
| Stage 2 | design | 导演思维推导（情感内核 → 配色 → 沉浸模式 → 故事板） |
| Stage 3 | narration | 场景拆解 + 6 拍情感节拍 + 分段旁白文案 |
| Stage 4 | audio | 分段 TTS + loudnorm + BGM 选取 + 7 档音量校准 |
| Stage 5 | assets | 视觉素材制备（可选，纯 CSS/HTML 渲染） |
| Stage 6 | video | 三层架构 HTML + 13 组件 + GSAP 动画 → HyperFrames 渲染 |
| Stage 7 | delivery | 封面帧嵌入 + 封面图 + 3 套抖音文案 + 双版本输出 |
| Stage 8 | cleanup | 删除中间产物 |

DAG 定义在 [`schema.yaml`](.claude/commands/clipforge/schema.yaml) — artifact 依赖、条件阶段、可选阶段，一处定义。

---

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

Agent 逐步引导完成每个阶段，每步确认后继续。

### 定时任务

| 任务 | 命令 | 说明 |
|------|------|------|
| 每日热门视频 | `/github-daily-trending` | 每天自动执行 |
| 每周汇总视频 | `/github-weekly-trending` | 每周自动执行 |
| 每周知乎文章 | `/github-weekly-zhihu` | 每周自动执行 |

全自动化：数据采集（三源交叉验证）→ 视频生产 → 交付 → 清理 → 定时任务自动续期。

---

## 架构设计

### 设计哲学：弱引导 · 强边界

参照 [Agent 自进化架构](docs/agent-self-evolution-architecture.md) 的九大设计原则（P1-P9）：

1. **Schema 即真相** — `schema.yaml` 定义所有 artifact 依赖、产出和完成状态。状态检测基于文件存在，无数据库
2. **技能自包含** — 每个阶段文件包含完整执行指导、Anti-rationalization 表格和红旗警告
3. **委托不重写** — HTML 编写和渲染委托 HyperFrames，音频混音由渲染器原生处理
4. **双域分离** — 流程层零自由度（LETTER 按字面执行），内容层最大自由度（SPIRIT 按意图发挥）
5. **双闭环反馈** — 失败 → 归因 → 收紧规则（负向闭环）+ 成功 → 分析 → 沉淀模式（正向闭环）

### 四原子模型

所有技能定义建立在一个基本观察上：对 Agent 的控制本质上是四个维度的问题。

| 维度 | 回答的问题 | 概念 | 文件体现 |
|------|-----------|------|---------|
| 目标 | 要达成什么？ | **Intent** | `skills/stage*.yaml` 的 `intent` 段 |
| 边界 | 不能做什么？ | **Boundary** | `rules/*.yaml` + `skills/*.yaml` 的 `boundary` 段 |
| 合格 | 怎样算通过？ | **Gate** | `skills/*.yaml` 的 `gate` 段 → `engine/gate.py` 执行 |
| 经验 | 如何改进？ | **Trace** | `engine/trace.py` 采集 → `engine/attribution.py` 归因 |

### 自进化引擎

引擎层（`engine/`）是 ClipForge 的"免疫系统"——不干预正常执行，只在违规和成功时介入。

| 引擎 | 文件 | 职责 |
|------|------|------|
| 门禁引擎 | `gate.py` | HARD + SOFT 校验，SAFETY 门禁不可通过归因自动修复 |
| 注入引擎 | `inject.py` | 将规则正向重述后注入 prompt，LETTER=流程约束，SPIRIT=内容引导 |
| 归因引擎 | `attribution.py` | 强归因（规则命中）+ 弱归因（根因判定 + Delta 产出） |
| 成功分析 | `success_analyzer.py` | 高分案例采集、经验模式提炼、P7 负向闭环否决权 |
| 正向重述 | `lib/positive_rewrite.py` | 负向规则 → 正向表述（避免白熊效应），兜底重写覆盖未知模式 |
| Delta 规则 | `lib/delta.py` | 增量规则变更（ADDED/REMOVED/DEPRECATED），shadow_validate 影子验证 |
| Trace 采集 | `trace.py` | 执行轨迹记录，供归因和成功分析消费 |
| 治理守卫 | `governance.py` | 规则生命周期管理 |

**双闭环运转流程：**

```
执行 → Gate 校验 → [失败] → 归因引擎 → Delta Rule → 收紧规则
                  → [成功] → 成功分析 → Pattern 沉淀 → 放宽偏好
```

**数据驱动验证（2026-05-27）：**

| 发现 | 数据 | 对技能的影响 |
|------|------|-------------|
| 反直觉 hook 效果 8x | 平均 46,596 播放 vs 基线 5,363 | hook_templates 按优先级排序 |
| 5s 完播率是播放量最强预测因子 | ≥44% → 36K 播放，<38% → 3.1K | 新增 R-S3-001b/c 门禁规则 |
| 疑问句式效果最差 | 平均 1,195 播放 | 硬门禁禁止疑问 hook |
| 视频号增长靠分享 | 分享率 4-5% 驱动 | 跨平台发布策略区分 |
| 小红书收藏 >> 点赞 | 1.9 倍 | 内容定位为参考价值 |

### 约束体系

```
rules/                          # 规则库（按领域分文件）
├── 00-global-safety.yaml       # 全局安全规则（违禁词、URL 禁止）
├── 01-content-spec.yaml        # 内容规范
├── 02-render-safety.yaml       # 渲染安全（anim-in 禁用、三层架构）
├── 03-audio.yaml               # 音频规则
├── stage2-7.yaml               # 各阶段专属规则
└── categories/github.yaml      # GitHub 分类规则

skills/                         # 技能声明（四原子模型）
├── stage0-env.yaml ~ stage7-delivery.yaml
├── cleanup.yaml
└── movie-clips.yaml

patterns/                       # 经验模式（成功分析产出）
├── github-highscore.yaml       # GitHub 高分模式（58 条视频数据支撑）
├── cover-design.yaml           # 封面 7 层模板
└── director-toolkit.yaml       # 导演思维工具包

deltas/                         # Delta 规则（归因产出，增量变更）
```

### 渐进严谨

| 级别 | 注入范围 | 适用场景 |
|------|---------|---------|
| LITE | 仅全局安全 + 个性化偏好 | 简单内容，Agent 创造空间最大 |
| STANDARD | + 阶段规则 + LETTER 流程约束 | **默认级别**，平衡创造力和质量控制 |
| STRICT | + SPIRIT 内容引导 + 全部 guardrail | 关键发布，最大化质量保证 |

---

## 核心子系统

| 子系统 | 文件 | 作用 |
|--------|------|------|
| 导演思维工具包 | `_director-toolkit.md` | 5 个必答题 + 视觉词汇表 + 爆款案例，Stage 2/3/6 执行前必读 |
| 渲染安全规范 | `_render-safety.md` | HyperFrames 事故复盘总结：禁用 CSS anim-in、三层架构、安全区 padding |
| 内容规范 | `_shared-rules.md` | 措辞、画面文字语言、CTA 时间、URL 禁止、黄金 3 秒 |
| 分类配置 | `categories/github.md` | GitHub 分类特有的数据源、选取策略、音色、标签覆盖 |
| 爆款案例库 | `_viral-cases/` | 已验证的爆款视频多维分析，可提取模式 |

## 抖音合规

- 视频画面和旁白文案**不出现 URL**，只展示项目名称
- 不点名商业品牌（不说"GPT/DeepSeek"，说"大语言模型/AI 助手"）
- 禁止广告敏感词（"必装/神器/赶紧/最强/免费领"）
- 自动生成 3 套不同风格文案：爆款钩子型 / 信息差型 / 极简型
- **跨平台差异化发布**：抖音（反直觉 hook）、视频号（分享驱动）、小红书（收藏价值）

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
- **新规则：** 在 `rules/` 下添加 YAML 文件，引擎自动加载并注入
- **新阶段：** 在 `schema.yaml` 中添加 artifact，创建对应的 `stageN-xxx.md` + `skills/stageN-xxx.yaml`
- **新视频模式：** 在 stage 文件中定义模式规则，控制器根据内容自动选择

详见 [CONTRIBUTING.md](CONTRIBUTING.md)。

## 项目结构

```
clipforge/
├── CLAUDE.md                              # AI 代理入口点
├── README.md                              # 中文说明（本文件）
├── LICENSE                                # Apache 2.0
├── CONTRIBUTING.md                        # 贡献指南
├── docs/
│   ├── architecture.md                    # DAG + 阶段流水线详解
│   ├── agent-self-evolution-architecture.md  # Agent 自进化架构设计（P1-P9）
│   └── getting-started.md                 # 安装与首次使用
├── .claude/commands/
│   ├── clipforge.md                       # 主控制器（DAG 语义、模式选择、错误恢复）
│   ├── github-daily-trending.md           # 每日定时任务
│   ├── github-weekly-trending.md          # 每周定时任务
│   ├── github-weekly-zhihu.md             # 每周知乎文章
│   └── clipforge/
│       ├── schema.yaml                    # Artifact DAG（唯一事实源）
│       ├── engine/                        # 自进化引擎（Python）
│       │   ├── gate.py                    # 门禁引擎：HARD + SOFT 校验
│       │   ├── inject.py                  # 注入引擎：正向重述 → prompt
│       │   ├── attribution.py             # 归因引擎：强/弱归因 + Delta 产出
│       │   ├── success_analyzer.py        # 成功分析：高分模式提炼 + P7 否决
│       │   ├── trace.py                   # Trace 采集：执行轨迹记录
│       │   ├── governance.py              # 治理守卫：规则生命周期
│       │   └── lib/                       # 引擎核心库
│       │       ├── models.py              # 数据模型（Rule, Violation, GateReport...）
│       │       ├── rule_parser.py         # 规则/Skill YAML 解析器
│       │       ├── positive_rewrite.py    # 正向重述引擎
│       │       └── delta.py               # Delta Rule 管理 + shadow_validate
│       ├── rules/                         # 约束规则库（YAML）
│       │   ├── 00-global-safety.yaml      # 全局安全规则
│       │   ├── 01-content-spec.yaml       # 内容规范
│       │   ├── 02-render-safety.yaml      # 渲染安全
│       │   ├── 03-audio.yaml              # 音频规则
│       │   ├── stage2-7.yaml              # 各阶段规则
│       │   └── categories/github.yaml     # 分类规则
│       ├── skills/                        # 技能声明（四原子模型）
│       │   ├── stage0-env.yaml            #   ~ stage7-delivery.yaml
│       │   ├── cleanup.yaml
│       │   └── movie-clips.yaml
│       ├── patterns/                      # 经验模式（成功分析产出）
│       │   ├── github-highscore.yaml      # GitHub 高分模式（数据驱动）
│       │   ├── cover-design.yaml          # 封面 7 层模板
│       │   └── director-toolkit.yaml      # 导演思维工具包
│       ├── deltas/                        # Delta 规则（归因产出）
│       ├── traces/                        # 执行轨迹（Trace 采集）
│       ├── categories/                    # 分类配置
│       │   ├── _category-schema.md        # 分类配置格式规范
│       │   └── github.md                  # GitHub 分类
│       ├── stage0-env.md ~ stage7-delivery.md  # 阶段执行指南
│       ├── _shared-rules.md               # 内容规范
│       ├── _cleanup-rules.md              # 清理规则
│       ├── _director-toolkit.md           # 导演思维工具包
│       ├── _render-safety.md              # 渲染安全规范
│       ├── _visual-phasing.md             # 视觉分相规则
│       ├── _bgm-pixabay.md                # BGM 下载工具
│       ├── _movie-clips.md                # 电影片段提取
│       ├── scripts/                       # 工具脚本（20+）
│       └── components/                    # 视觉组件库（13 个）
├── install.sh                             # 一键依赖安装
└── workspace/                             # 输出目录（gitignored）
```

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
