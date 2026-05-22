---
name: github-weekly-trending
description: 全自动抓取 GitHub 每周热门项目汇总并生成抖音短视频，无需人工确认。完成后自动续期定时任务。
---

# GitHub 每周热门汇总 → 抖音短视频（全自动）

> **全自动执行，不需要人工确认。** 使用 DAG 感知编排 + SubAgent 阶段隔离执行，每个阶段独立上下文窗口。

## 前置：日期 & 目录

```bash
TODAY=$(date +%Y-%m-%d)
DATE_DIR="$(date +%Y)/$(date +%m)/$(date +%d)"
PROJECT_DIR="workspace/${DATE_DIR}/github-trending-weekly"
```

> **代理：** 如果本机需要代理才能访问 GitHub，请在执行前设置 `https_proxy` / `http_proxy` 环境变量。

## Step 1: 抓取 GitHub Weekly Trending（三源交叉验证）

### 1.1 主数据源 — Python 脚本抓取（无缓存）

```bash
TODAY=$(date +%Y-%m-%d)
DATE_DIR="$(date +%Y)/$(date +%m)/$(date +%d)"
PROJECT_DIR="workspace/${DATE_DIR}/github-trending-weekly"
mkdir -p "${PROJECT_DIR}"

python scripts/github_trending.py \
  --output-dir "${PROJECT_DIR}" \
  --date "${TODAY}" \
  --since weekly
```

### 1.2 验证源 — web-reader MCP 交叉确认

用 `mcp__web_reader__webReader`（**必须设 `no_cache: true`**）抓取：

```
url: https://github.com/trending?since=weekly&spoken_language_code=
no_cache: true
```

与 `raw_trending.json` 比对项目列表，交集 >= 80% 即通过。

### 1.3 数据质量门禁

同每日命令：项目数 >= 8、活跃度 >= 80%。

### 1.4 读取最终数据

从 `raw_trending.json` 提取前 **12-15 个项目**。

## Step 2: 内容整理 & 分类

将数据整理为中文短视频素材：
- 项目名保留英文
- 描述翻译成中文（简洁口语化）
- **按编程语言/领域分类**（如：AI/ML、前端、后端、DevOps 工具、移动端等），每组 3-4 个项目
- 开头钩子：如"本周 GitHub 最火的开源项目盘点"
- 每个分类用一句话概括趋势（如"AI 项目持续霸榜"）

## Step 3: DAG 编排执行

> **核心机制：** 读取 `schema.yaml` 定义 artifact DAG，按依赖关系推导 SubAgent 批次。每个 SubAgent 从零上下文启动，加载对应 stage 技能文件。状态通过文件系统检测（检查 generates 文件是否存在）。

### DAG 批次调度

| 批次 | Artifact | 说明 |
|------|----------|------|
| SubAgent-1 | env-check → content → design → narration | 顺序执行，6-7 场景，45-60s |
| SubAgent-2 | audio | TTS + BGM |
| SubAgent-3 | video | HTML + 渲染 |
| SubAgent-4 | delivery → cleanup | 封面 + 交付 + 清理 |

> **movie-clips / assets：** 周汇总为标准模式，均跳过。

### 3.1 SubAgent-1: content → design → narration

**SubAgent-1 prompt 核心内容：**

```
你是 ClipForge 短视频制作流程的阶段执行者。按顺序完成以下四个阶段。

## 项目上下文
- 项目目录: ${PROJECT_DIR}（cd 到此目录后再执行所有操作）
- **技能库符号链接**：cd 到项目目录后立即执行 `ln -sf "$(git rev-parse --show-toplevel)/.agents" .agents`
- 视频模式: 标准模式（6-7 场景，45-60s）
- 内容类型: GitHub 每周热门汇总（按领域分类）
- 视频内不放 URL，项目名称用英文展示
- 不涉及 _movie-clips（电影片段）

## 执行步骤

### 1. env-check
用 Read 工具读取 .claude/commands/clipforge/stage0-env.md，按指引执行。环境通常已就绪。

### 2. content
1. 读取 .claude/commands/clipforge/categories/github.md（GitHub 分类配置，含数据获取策略、选取规则）
2. 读取 .claude/commands/clipforge/stage1-content.md，按指引执行
3. 内容来源: 项目目录下的 raw_trending.json（数据已准备好）
4. 选取 12-15 个项目，按领域/语言分组

### 3. design
读取 .claude/commands/clipforge/stage2-analysis.md，按指引执行。
不同分类可使用不同色彩区分（如 AI 组用冷色系、前端组用暖色系），整体保持协调统一。写入 design.md。

### 4. narration
1. 读取 .claude/commands/clipforge/_shared-rules.md（§1 措辞规范、§5 黄金3秒法则）
2. 读取 .claude/commands/clipforge/stage3-scenes.md，按指引执行
3. 读取 design.md 获取风格方向
4. 场景数 6-7 个（hook → 分类1 → 分类2 → 分类3 → 分类4 → 趋势总结 → CTA）
5. 目标字数: 300-450 字，目标时长: 45-60 秒
6. 产出 narration_segments.json + narration.txt

## 完成后
确认以下文件存在: design.md, narration_segments.json, narration.txt
报告状态: DONE / DONE_WITH_CONCERNS / BLOCKED
```

**验证：** `ls -la ${PROJECT_DIR}/design.md ${PROJECT_DIR}/narration_segments.json ${PROJECT_DIR}/narration.txt`

### 3.2 SubAgent-2: audio

**SubAgent-2 prompt 核心内容：**

```
你是 ClipForge 短视频制作流程的阶段执行者。

## 项目上下文
- 项目目录: ${PROJECT_DIR}（cd 到此目录后再执行所有操作）
- **技能库符号链接**：cd 到项目目录后立即执行 `ln -sf "$(git rev-parse --show-toplevel)/.agents" .agents`

## 执行步骤

1. 读取 .claude/commands/clipforge/stage4-audio.md，按指引执行
2. 读取 .claude/commands/clipforge/categories/github.md（audio 配置：固定音色 YunjianNeural +25%）
3. 读取 narration_segments.json（narration artifact 产出）
4. TTS: 按 categories/github.md 的 audio.default_voice 和 audio.default_rate 设置
5. 分段 TTS 输出 segment_durations.json
5. 配乐从 workspace/bgm/ 选取或 yt-dlp 下载
6. BGM 音量写入 segment_durations.json

## 完成后
确认文件: segment_durations.json, narration.mp3, bgm.wav
报告状态: DONE / DONE_WITH_CONCERNS / BLOCKED
```

**验证：** `ls -la ${PROJECT_DIR}/segment_durations.json ${PROJECT_DIR}/narration.mp3 ${PROJECT_DIR}/bgm.wav`

### 3.3 SubAgent-3: video

**SubAgent-3 prompt 核心内容：**

```
你是 ClipForge 短视频制作流程的阶段执行者。

## 项目上下文
- 项目目录: ${PROJECT_DIR}（cd 到此目录后再执行所有操作）
- **技能库符号链接**：cd 到项目目录后立即执行 `ln -sf "$(git rev-parse --show-toplevel)/.agents" .agents`
- 输出尺寸: 竖屏 1080×1920
- 视频内不放 URL，项目名称用英文展示
- 时长可延长至 45-60 秒，每个分类场景 6-10 秒

## 执行步骤

1. 读取 .claude/commands/clipforge/_shared-rules.md（§2 画面文字语言规范、§7 渲染安全规范）
2. 读取 .claude/commands/clipforge/stage6-production.md，按指引执行
3. 读取 design.md（视觉风格方向）
4. 读取 segment_durations.json（实际时长，设置 data-duration）
5. 读取 narration_segments.json（场景定义）
6. 编写 HTML + 嵌入 <audio>（narration.mp3 + bgm.wav）
7. BGM data-volume 从 segment_durations.json 的 meta.bgm_volume 读取
8. 渲染 output.mp4 + output_no_bgm.mp4

## 完成后
确认文件: index.html, output.mp4, output_no_bgm.mp4
报告状态: DONE / DONE_WITH_CONCERNS / BLOCKED
```

**验证：** `ls -la ${PROJECT_DIR}/output.mp4 ${PROJECT_DIR}/output_no_bgm.mp4`

### 3.4 SubAgent-4: delivery → cleanup

**SubAgent-4 prompt 核心内容：**

```
你是 ClipForge 短视频制作流程的阶段执行者。

## 项目上下文
- 项目目录: ${PROJECT_DIR}（cd 到此目录后再执行所有操作）
- **技能库符号链接**：cd 到项目目录后立即执行 `ln -sf "$(git rev-parse --show-toplevel)/.agents" .agents`
- 视频内不放 URL，项目名称用英文展示

## Part A: delivery — 封面 + 交付 + 抖音文案

1. 读取 .claude/commands/clipforge/_shared-rules.md（§1 措辞规范、§2 画面文字语言规范）
2. 读取 .claude/commands/clipforge/stage7-delivery.md，按指引执行
3. 读取 .claude/commands/clipforge/categories/github.md（delivery 配置：标签、评论区模板、封面徽章）
4. 读取 design.md 获取风格方向（封面复用视频风格）
5. 封面: 6 层模板 + 双色光晕 + 渐变背景，2x 超采样 → 缩放
6. 封面嵌入第一帧: final.mp4 + final_no_bgm.mp4
7. 生成 3 套抖音文案，标签使用 categories/github.md 的 delivery.hashtags

确认文件: cover.png, final.mp4, final_no_bgm.mp4, douyin.md

## Part B: cleanup — 项目清理

1. 读取 .claude/commands/clipforge/_cleanup-rules.md，按指引执行完整清理
2. bgm.wav 如来自 workspace/bgm/ 素材库，删除项目副本
3. 报告清理前后磁盘占用

确认项目目录仅含保留文件，磁盘占用 < 30 MB。
报告状态: DONE / DONE_WITH_CONCERNS / BLOCKED
```

**验证：** `ls ${PROJECT_DIR}/` 确认中间文件已清理，`du -sh ${PROJECT_DIR}` 确认 < 30 MB。

## Step 5: 自续期

执行 `clipforge/_cron-renew` 定时任务自续期模式，任务关键词为 `github-weekly-trending`。

## 输出

完成后汇报：
```
📊 GitHub 每周热门汇总视频已生成
周次：YYYY-MM-DD 这周
文件：workspace/<YYYY>/<MM>/<DD>/github-trending-weekly/final.mp4
时长：XXs | 大小：XX MB
项目数：X 个（分 X 类）
抖音文案：[文案内容摘要]
定时任务续期：✅ Job ID xxxxx
```
