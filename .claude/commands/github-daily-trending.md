---
name: github-daily-trending
description: 全自动抓取 GitHub 每日热门项目并生成抖音短视频，无需人工确认。完成后自动续期定时任务。
---

# GitHub 每日热门 → 抖音短视频（全自动）

> **全自动执行，不需要人工确认。** 使用 DAG 感知编排 + SubAgent 阶段隔离执行，每个阶段独立上下文窗口。

## 前置：日期 & 目录

```bash
export LANG=zh_CN.UTF-8
TODAY=$(date +%Y-%m-%d)
DATE_DIR="$(date +%Y)/$(date +%m)/$(date +%d)"
PROJECT_DIR="workspace/${DATE_DIR}/github-trending"
```

> **代理：** 如果本机需要代理才能访问 GitHub，请在执行前设置 `https_proxy` / `http_proxy` 环境变量。

> **`export LANG=zh_CN.UTF-8` 必须设置**：Windows Git Bash 默认 locale 可能是 GBK，导致中文目录名编码错乱。
> **路径全英文**：`DATE_DIR` 使用纯数字（如 `2026/05/20`），不使用中文。

## Step 1: 抓取 GitHub Trending（三源交叉验证）

### 1.1 主数据源 — Python 脚本抓取（无缓存）

```bash
TODAY=$(date +%Y-%m-%d)
YESTERDAY=$(date -d 'yesterday' +%Y-%m-%d)
DATE_DIR="$(date +%Y)/$(date +%m)/$(date +%d)"
YESTERDAY_DATE_DIR="$(date -d 'yesterday' +%Y)/$(date -d 'yesterday' +%m)/$(date -d 'yesterday' +%d)"
PROJECT_DIR="workspace/${DATE_DIR}/github-trending"
mkdir -p "${PROJECT_DIR}"

python scripts/github_trending.py \
  --output-dir "${PROJECT_DIR}" \
  --date "${TODAY}" \
  --since daily \
  --yesterday "workspace/${YESTERDAY_DATE_DIR}/github-trending/raw_trending.json"
```

### 1.2 验证源 — web-reader MCP 交叉确认

用 `mcp__web_reader__webReader` 工具（**必须设 `no_cache: true`**）抓取同一页面：

```
url: https://github.com/trending?spoken_language_code=
no_cache: true
```

项目名交集 >= 80% → 验证通过。

### 1.3 数据质量门禁

以下任一条件不满足则**停止执行并报错**：
- Python 脚本获取 >= 8 个项目
- 项目列表与昨日不完全相同（如果昨日数据存在）
- >= 80% 项目在 30 天内有更新

## Step 2: 追加月度清单（数据刚抓到，立即写入）

> **必须在 DAG 编排长流程之前执行。** 原因：长流程消耗大量 context，context 压缩后可能导致此步骤被跳过。

将今日抓取的项目数据追加到月度清单文件：

```bash
MONTH=$(date +%Y-%m)
MONTHLY_FILE="workspace/sources/github-trending/${MONTH}.md"
```

1. 检查 `MONTHLY_FILE` 是否存在，不存在则创建
2. 在文件末尾追加今日日期标题 + 项目表格
3. **写入后必须验证**：用 `Read` 工具读取确认今日日期标题存在

## Step 3: 内容整理

将数据整理为中文短视频素材：
- 项目名保留英文
- 描述翻译成中文（简洁口语化）
- 按热度排序
- 开头用震撼数据做钩子

## Step 4: DAG 编排执行

> **核心机制：** 读取 `schema.yaml` 定义 artifact DAG，按依赖关系推导 SubAgent 批次。每个 SubAgent 从零上下文启动，加载对应 stage 技能文件。状态通过文件系统检测（检查 generates 文件是否存在）。

### DAG 批次调度

以下批次由 schema.yaml 依赖图推导：

| 批次 | Artifact | SubAgent 加载 |
|------|----------|--------------|
| SubAgent-1 | env-check → content → design → narration | stage0-env + stage1-content + stage2-analysis + stage3-scenes |
| SubAgent-2 | audio | stage4-audio |
| SubAgent-3 | video | stage6-production |
| SubAgent-4 | delivery → cleanup | stage7-delivery + _cleanup-rules |

> **movie-clips：** GitHub Trending 视频为标准模式，不含 `video_clip` 场景，movie-clips 条件不触发，跳过。
> **assets：** GitHub Trending 视频通常不需要外部素材，assets 为 optional，跳过。

### 4.1 SubAgent-1: content → design → narration

**SubAgent-1 prompt 核心内容：**

```
你是 ClipForge 短视频制作流程的阶段执行者。按顺序完成以下四个阶段。

## 项目上下文
- 项目目录: ${PROJECT_DIR}（cd 到此目录后再执行所有操作）
- **技能库符号链接**：cd 到项目目录后立即执行 `ln -sf "$(git rev-parse --show-toplevel)/.agents" .agents`
- 视频模式: 标准模式（4-5 场景，20-45s）
- 内容类型: GitHub Trending 项目盘点
- 视频内不放 URL，项目名称用英文展示
- 不涉及 _movie-clips（电影片段）

## 执行步骤

### 1. env-check
用 Read 工具读取 .claude/commands/clipforge/stage0-env.md，按指引执行。环境通常已就绪。

### 2. content
1. 读取 .claude/commands/clipforge/categories/github.md（GitHub 分类配置，含数据获取策略、选取规则、数据验证）
2. 读取 .claude/commands/clipforge/stage1-content.md，按指引执行
3. 内容来源: 项目目录下的 raw_trending.json（数据已准备好）
4. 按 categories/github.md 中的 selection_strategy 选取 5-6 个项目

### 3. design
读取 .claude/commands/clipforge/stage2-analysis.md，按指引执行。
参考 categories/github.md 中的 design.default_style（暗色科技风），写入 design.md。

### 4. narration
1. 读取 .claude/commands/clipforge/_shared-rules.md（§1 措辞规范、§5 黄金3秒法则）
2. 读取 .claude/commands/clipforge/stage3-scenes.md，按指引执行
3. 读取 design.md 获取风格方向
4. 产出 narration_segments.json + narration.txt

## 完成后
确认以下文件存在: design.md, narration_segments.json, narration.txt
报告状态: DONE / DONE_WITH_CONCERNS / BLOCKED
```

**验证：** `ls -la ${PROJECT_DIR}/design.md ${PROJECT_DIR}/narration_segments.json ${PROJECT_DIR}/narration.txt`

### 4.2 SubAgent-2: audio

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

### 4.3 SubAgent-3: video

**SubAgent-3 prompt 核心内容：**

```
你是 ClipForge 短视频制作流程的阶段执行者。

## 项目上下文
- 项目目录: ${PROJECT_DIR}（cd 到此目录后再执行所有操作）
- **技能库符号链接**：cd 到项目目录后立即执行 `ln -sf "$(git rev-parse --show-toplevel)/.agents" .agents`
- 输出尺寸: 竖屏 1080×1920
- 视频内不放 URL，项目名称用英文展示

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

### 4.4 SubAgent-4: delivery → cleanup

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

## Step 5: 自续期（必须执行，无论前序步骤成败）

> **无论 Step 1-4 是否成功，都必须执行此步骤。**

执行 `clipforge/_cron-renew` 定时任务自续期模式，任务关键词为 `github-daily-trending`。

## 输出

完成后汇报：
```
📊 GitHub 每日热门视频已生成
日期：YYYY-MM-DD
文件：workspace/<YYYY>/<MM>/<DD>/github-trending/final.mp4
时长：XXs | 大小：XX MB
项目数：X 个
月度文档：✅ workspace/sources/github-trending/YYYY-MM.md
抖音文案：[文案内容摘要]
定时任务续期：✅ Job ID xxxxx
```
