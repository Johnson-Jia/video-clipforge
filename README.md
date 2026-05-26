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

大多数 AI 视频工具是带固定模板的 GUI 应用。ClipForge 采用不同方式：基于 Claude Code 技能系统构建的**代码原生管线**。每个阶段是自包含技能文件，有明确的输入、输出和错误恢复路径。DAG 依赖图在 `schema.yaml` 中定义一次，驱动所有调度、状态检测和重试逻辑。

**结果：** 可审计、可扩展、可在 cron 上无人值守运行的生产级视频管线。

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
| **出了问题怎么回退？** | 不涉及 | DAG 依赖图驱动的级联回退表，只回退到最小必要阶段 |
| **磁盘会被撑爆吗？** | 不涉及 | 自动清理策略，每个项目交付后 < 30MB |

**简而言之：** HyperFrames 是渲染引擎，ClipForge 是从内容到成品的完整编排层。HyperFrames 解决「怎么把 HTML 变成视频」，ClipForge 解决「这个视频的 HTML 从哪来、内容是什么、风格怎么定、音频怎么同步、如何批量生产」。

## 概述

ClipForge 将任意内容 — 文字、URL、PDF、GitHub 数据等 — 转换为竖屏短视频（1080x1920），包含：

- **DAG 编排 8 阶段流水线** — 每个阶段是自包含技能文件，有明确的输入/输出和错误恢复路径
- **分类系统** — 通过可插拔的分类配置文件定义内容特有规则（数据获取、风格、音色、标签等）
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

## 架构设计

遵循三个设计原则：

1. **Schema 即真相** — `schema.yaml` 定义所有 artifact 依赖、产出和完成状态。状态检测基于文件存在（glob 模式匹配），无数据库。
2. **技能自包含** — 每个阶段文件包含完整执行指导、Anti-rationalization 表格和红旗警告。
3. **委托不重写** — HTML 编写和渲染委托 HyperFrames，音频混音由渲染器原生处理，无需 FFmpeg 后处理。

### 核心子系统

| 子系统 | 文件 | 作用 |
|--------|------|------|
| 导演思维工具包 | `_director-toolkit.md` | 5 个必答题 + 视觉词汇表 + 爆款案例，Stage 2/3/6 执行前必读 |
| 渲染安全规范 | `_render-safety.md` | HyperFrames 事故复盘总结：禁用 CSS anim-in、三层架构、安全区 padding |
| 内容规范 | `_shared-rules.md` | 措辞、画面文字语言、CTA 时间、URL 禁止、黄金 3 秒 |
| 分类配置 | `categories/github.md` | GitHub 分类特有的数据源、选取策略、音色、标签覆盖 |
| 爆款案例库 | `_viral-cases/` | 已验证的爆款视频多维分析，可提取模式 |

详见 [架构文档](docs/architecture.md)。

## 设计哲学

参照 [OpenSpec](https://github.com/nicholasgriffintn/openspec) 和 [Superpowers](https://github.com/nicholasgriffintn/superpowers) 的设计思想：

- **Schema 即真相** — DAG 驱动的工作流，schema 是唯一事实来源
- **Anti-rationalization** — 每个技能有明确的红旗警告和常见自我合理化，Token 预算保持技能聚焦

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
- **新阶段：** 在 `schema.yaml` 中添加 artifact，创建对应的 `stageN-xxx.md` 技能文件
- **新视频模式：** 在 stage 文件中定义模式规则，控制器根据内容自动选择

详见 [CONTRIBUTING.md](CONTRIBUTING.md)。

## 项目结构

```
clipforge/
├── CLAUDE.md                              # AI 代理入口点
├── README.md                              # 中文说明（本文件）
├── README_EN.md                           # English README
├── LICENSE                                # Apache 2.0
├── CONTRIBUTING.md                        # 贡献指南
├── docs/
│   ├── architecture.md                    # DAG + 阶段流水线详解
│   └── getting-started.md                 # 安装与首次使用
├── .claude/commands/
│   ├── clipforge.md                       # 主控制器（DAG 语义、模式选择、错误恢复）
│   ├── github-daily-trending.md           # 每日定时任务
│   ├── github-weekly-trending.md          # 每周定时任务
│   ├── github-weekly-zhihu.md             # 每周知乎文章
│   └── clipforge/
│       ├── schema.yaml                    # Artifact DAG（唯一事实源）
│       ├── categories/                    # 分类配置
│       │   ├── _category-schema.md        # 分类配置格式规范
│       │   └── github.md                  # GitHub 分类
│       ├── stage0-env.md                  # Stage 0: 环境检测
│       ├── stage1-content.md              # Stage 1: 内容获取
│       ├── stage2-analysis.md             # Stage 2: 导演思维 + 风格推导
│       ├── stage3-scenes.md               # Stage 3: 场景拆解 + 旁白
│       ├── stage4-audio.md                # Stage 4: TTS + BGM
│       ├── stage5-assets.md               # Stage 5: 素材制备
│       ├── stage6-components.md           # Stage 6: 组件库参考
│       ├── stage6-production.md           # Stage 6: HTML 组装 + 渲染
│       ├── stage7-delivery.md             # Stage 7: 封面 + 文案 + 交付
│       ├── templates/                     # SubAgent prompt 模板
│       │   ├── subagent-1-content.md      # 批次 1: 内容 + 设计 + 旁白
│       │   ├── subagent-2-audio.md        # 批次 2: 音频 + 素材
│       │   ├── subagent-3-video.md        # 批次 3: 视频渲染
│       │   └── subagent-4-delivery.md     # 批次 4: 交付 + 清理
│       ├── _shared-rules.md               # 内容规范（措辞/画面文字/CTA）
│       ├── _cleanup-rules.md              # 文件保留规则
│       ├── _cron-renew.md                 # 定时任务续期
│       ├── _director-toolkit.md           # 导演思维工具包（5 必答题 + 视觉词汇）
│       ├── _render-safety.md              # 渲染安全 + 三层架构规范
│       ├── _movie-clips.md                # 电影片段提取（条件阶段）
│       ├── _bgm-pixabay.md                # Pixabay BGM 下载工具
│       ├── _viral-cases/                  # 爆款视频案例库
│       │   └── 05-19-douyin.md            # 05-19 爆款复盘
│       ├── scripts/                       # 工具脚本
│       │   ├── github_trending.py         # GitHub Trending 抓取
│       │   ├── generate_bgm.py            # MusicGen BGM 生成
│       │   ├── tts_segments.py            # 分段 TTS 管线
│       │   ├── tts_pipeline.sh            # TTS 流程脚本
│       │   ├── bgm_pipeline.sh            # BGM 处理管线
│       │   ├── bgm_gap_check.py           # BGM 缺口检测
│       │   ├── loudnorm.sh                # loudnorm 响度归一化
│       │   ├── polyphone_fix.py           # TTS 多音字预处理
│       │   ├── assemble_final.sh          # TS concat 无损拼接
│       │   ├── merge_video_audio.sh       # 音视频合并
│       │   ├── merge_srt.py               # SRT 字幕合并
│       │   ├── render_cover.sh            # 封面渲染
│       │   ├── validate_cover.py          # 封面结构门禁
│       │   ├── stage6_gate.sh             # Stage 6 A/V 门禁
│       │   ├── director_gate.py           # 导演思维门禁
│       │   ├── frame_analysis.py          # 帧分析工具
│       │   ├── movie_narration.py         # 电影旁白合成
│       │   ├── movie_xfade.sh             # 电影片段 xfade
│       │   ├── env_check.sh               # 环境检测
│       │   ├── cleanup_project.sh         # 项目清理
│       │   └── validate_schema.py         # Schema 校验
│       └── components/                    # 视觉组件库（13 个）
│           ├── hero_card.html             # 首屏英雄卡片
│           ├── project_full_card.html     # 项目完整信息卡
│           ├── text_reveal.html           # 文字揭示动画
│           ├── code_rain.html             # 代码雨特效
│           ├── particle_burst.html        # 粒子爆发
│           ├── pulse_orb.html             # 脉冲光球
│           ├── star_counter.html          # 星标计数器
│           ├── timeline_flow.html         # 时间线流动
│           ├── compare_split.html         # 对比分屏
│           ├── data_viz.html              # 数据可视化
│           ├── speech_bubble.html         # 气泡对话
│           ├── char_overlay.html          # 角色叠加
│           └── three_scene.html           # Three.js 3D 场景
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
