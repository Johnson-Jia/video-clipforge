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

## 概述

ClipForge 将任意内容 — 文字、URL、PDF、GitHub 数据等 — 转换为竖屏短视频（1080x1920），包含：

- **DAG 编排 8 阶段流水线** — 每个阶段是自包含技能文件，有明确的输入/输出和错误恢复路径
- **分类系统** — 通过可插拔的分类配置文件定义内容特有规则（数据获取、风格、音色、标签等）
- **三种视频模式** — 标准模式（25-55s）、单主题深度解析（45-60s）、电影解读（3-5min）
- **音频内嵌** — 旁白和 BGM 通过 `<audio>` 嵌入 HTML，HyperFrames 原生混音
- **分段精确 A/V 同步** — 分段 TTS + 每段时长追踪，消除音画漂移
- **定时任务自动化** — 每日/每周内容视频无人值守运行，定时任务自动续期
- **自动清理** — 交付后删除中间产物，每个项目保持 < 30MB

### 阶段流水线

| 阶段 | 产出 | 说明 |
|------|------|------|
| Stage 0 | env-check | 依赖检测 + 自动安装 |
| Stage 1 | content | 内容获取（文字/文件/URL/分类数据源） |
| Stage 2 | design | 视觉风格推导（情绪 → 配色 → 排版） |
| Stage 3 | narration | 场景拆解 + 分段旁白文案 |
| Stage 4 | audio | 分段 TTS 旁白 + 配乐 + BGM 音量分析 |
| Stage 5 | assets | 视觉素材制备（可选，纯 CSS/HTML 渲染） |
| Stage 6 | video | HTML + `<audio>` 嵌入 → HyperFrames 渲染 |
| Stage 7 | delivery | 封面帧嵌入 + 3 套抖音文案 |
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
│   ├── clipforge.md                       # 主控制器
│   ├── github-daily-trending.md           # 每日定时任务
│   ├── github-weekly-trending.md          # 每周定时任务
│   ├── github-weekly-zhihu.md             # 每周知乎文章
│   └── clipforge/
│       ├── schema.yaml                    # Artifact DAG（唯一事实来源）
│       ├── categories/                    # 分类配置
│       │   ├── _category-schema.md        # 分类配置格式规范
│       │   └── github.md                  # GitHub 分类（首个分类）
│       ├── stage0-env.md ... stage7-delivery.md   # 阶段技能文件
│       ├── _shared-rules.md               # 内容规范
│       ├── _cleanup-rules.md              # 文件保留规则
│       ├── _cron-renew.md                 # 定时任务续期
│       ├── _movie-clips.md                # 电影片段提取（条件阶段）
│       └── _bgm-pixabay.md                # BGM 下载工具
│       ├── scripts/                       # 工具脚本
│       │   ├── github_trending.py         # GitHub Trending 抓取
│       │   ├── generate_bgm.py            # MusicGen BGM 生成
│       │   ├── merge_video_audio.sh       # 音视频合并工具
│       │   └── quality_gate.sh            # 视频质量门禁
│       └── components/                    # 视觉组件库
│           ├── hero_card.html             # 首屏展示
│           └── ...（共 13 个组件）
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
