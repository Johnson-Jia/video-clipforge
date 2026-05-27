<div align="center">

# ClipForge

**AI 驱动的短视频制作管线 — 弱引导 · 强边界 · 双闭环反馈**

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)

从任意内容到抖音竖屏视频，全自动。由 [HyperFrames](https://github.com/heygen-com/hyperframes) 提供渲染。

</div>

---

## 核心思路

不教 Agent "怎么做"，而是定义"不能做什么"和"做成什么样算合格"，把创造空间留给 Agent。从失败和成功中自动进化规则，基于 58 条抖音真实播放数据持续优化。

## 快速开始

```bash
git clone https://github.com/Johnson-Jia/video-clipforge.git
cd video-clipforge
claude          # 启动 Claude Code，技能自动加载
/clipforge 制作一个关于 XXX 的视频
```

**前置依赖：** Node.js >= 22、FFmpeg、edge-tts、yt-dlp。详见 [安装指南](docs/getting-started.md)。

## 8 阶段管线

```
内容获取 → 导演设计 → 旁白文案 → 音频制备 → 素材制备 → 视频渲染 → 交付输出 → 自动清理
```

| 阶段 | 产出 | 说明 |
|------|------|------|
| Stage 1 | content | 文字/URL/PDF/GitHub 数据获取 |
| Stage 2 | design | 情感内核 → 配色 → 沉浸模式 → 故事板 |
| Stage 3 | narration | 场景拆解 + 分段旁白文案 |
| Stage 4 | audio | 分段 TTS + BGM 选取 + 音量校准 |
| Stage 5 | assets | 视觉素材制备（可选） |
| Stage 6 | video | HTML + 组件 + 动画 → HyperFrames 渲染 |
| Stage 7 | delivery | 封面 + 文案 + 双版本输出 |
| Stage 8 | cleanup | 删除中间产物 |

DAG 定义在 [`schema.yaml`](.claude/commands/clipforge/schema.yaml)。中断后重新运行自动跳过已完成阶段。

## 使用方式

| 命令 | 用途 |
|------|------|
| `/clipforge` | 交互式视频制作 |
| `/github-daily-trending` | 每日 GitHub 趋势视频（全自动） |
| `/github-weekly-trending` | 每周 GitHub 趋势汇总（全自动） |
| `/github-weekly-zhihu` | 每周 GitHub 知乎文章（全自动） |

## 设计哲学

- **Schema 即真相** — `schema.yaml` 定义所有 artifact 依赖和状态，状态即文件存在
- **委托不重写** — HTML 渲染和混音委托 HyperFrames
- **双域分离** — 流程层零自由度（LETTER），内容层最大自由度（SPIRIT）
- **双闭环反馈** — 失败归因收紧规则 + 成功分析沉淀模式

## 项目结构

```
.claude/commands/
├── clipforge.md                   # 主控制器（DAG、模式选择、错误恢复）
├── github-*.md                    # 定时任务编排
└── clipforge/
    ├── schema.yaml                # Artifact DAG（唯一真相源）
    ├── stage0-env.md ~ stage7-delivery.md  # 阶段执行指南
    ├── categories/                # 分类配置（GitHub、漫画等）
    ├── components/                # 视觉组件库（13 个）
    ├── scripts/                   # 工具脚本
    ├── engine/                    # 自进化引擎（门禁/归因/Trace）
    ├── rules/                     # 约束规则库
    ├── skills/                    # 技能声明（四原子模型）
    └── patterns/                  # 经验模式（数据驱动）
```

## 扩展

- **新内容源：** 添加 cron 文件，参照 `github-daily-trending.md`
- **新分类：** 在 `categories/` 下创建配置文件
- **新规则：** 在 `rules/` 下添加 YAML，引擎自动加载
- **新阶段：** 更新 `schema.yaml` + 创建 stage 文件

详见 [CONTRIBUTING.md](CONTRIBUTING.md) 和 [架构文档](docs/architecture.md)。

## 依赖

| 依赖 | 用途 | 安装 |
|------|------|------|
| HyperFrames | HTML 转视频渲染 | 首次运行自动安装 |
| Node.js >= 22 | HyperFrames CLI | `winget install OpenJS.NodeJS.LTS` |
| FFmpeg | 音视频处理 | `winget install Gyan.FFmpeg` |
| edge-tts | 中文 TTS 旁白 | `pip install edge-tts` |
| yt-dlp | YouTube 免版税音乐 | `pip install yt-dlp` |

## 赞赏支持

如果 ClipForge 帮你做出了满意的视频，欢迎请创作者喝杯咖啡 ☕

<div align="center">

| 支付宝 | 微信 |
|:---:|:---:|
| <img src="docs/images/ali_pay_qrcode.jpg" width="200" alt="支付宝"> | <img src="docs/images/wechat_pay_qrcode.png" width="200" alt="微信"> |

</div>

## 许可证

[Apache License 2.0](LICENSE)
