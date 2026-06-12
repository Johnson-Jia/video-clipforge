# Stage 0: 环境检测与新手引导

> 当 `workspace/.env-checked` 不存在时触发。检测并安装全部运行时依赖。

## 守卫机制

```bash
# 检测标记文件，已通过则跳过
mkdir -p workspace
if [ -f "workspace/.env-checked" ]; then
  echo "✅ 环境已验证（跳过 Stage 0）"
  exit 0
fi
```

## 依赖清单

| 依赖 | 最低版本 | 用途 | 必须 | 缺失处理 |
|------|---------|------|------|---------|
| Node.js | >= 22 | HyperFrames CLI | 是 | 提示安装 |
| FFmpeg | 任意 | 音视频处理 | 是 | 提示安装 |
| edge-tts | 任意 | TTS 旁白（推荐） | 是 | 提示安装 |
| yt-dlp | 任意 | 从 YouTube 下载免费音乐 | 是 | 提示安装 |
{{IF:content.optional_deps}}
| 分类专有工具 | — | 分类要求 | 推荐 | 提示安装 |
{{ENDIF}}
| jq | 任意 | loudnorm 两遍精确音量标准化 | 推荐 | 提示安装（缺失时降级单遍处理） |
| HyperFrames Skills | 最新 | 视频编排技能组 | 是 | **自动安装** |
| Python | >= 3.12 | MusicGen BGM（仅二创时需要） | 否 | 跳过 |

## 一键检测 + 自动安装

```bash
# 一键环境检测 + 自动安装
bash .claude/commands/clipforge/scripts/env_check.sh
```

## 自动安装行为

执行检测脚本时，以下依赖**自动安装**，无需用户干预：

| 依赖 | 自动安装命令 | 说明 |
|------|------------|------|
| HyperFrames Skills | `npx skills add heygen-com/hyperframes` | 视频编排技能 |

以下依赖**无法自动安装**（需系统级权限），仅提示命令：

| 依赖 | 安装命令 |
|------|---------|
| Node.js >= 22 | `winget install OpenJS.NodeJS.LTS` (Win) / `brew install node@22` (Mac) |
| FFmpeg | `winget install Gyan.FFmpeg` (Win) / `brew install ffmpeg` (Mac) |
| edge-tts | `pip install edge-tts` |
| yt-dlp | `pip install yt-dlp` |
| jq | `winget install jqlang.jq` (Win) / `brew install jq` (Mac) |
| Python + MusicGen | `pip install torch transformers scipy`（仅 AI 配乐二创时需要，可选） |

## 检测结果处理

- **全部通过** → 进入 Stage 1
- **Node/FFmpeg/edge-tts/yt-dlp 缺失** → 提示安装命令，安装后重新运行检测
- **gh 缺失** → 提示安装命令（推荐但非必须，缺失时 Stage 1 降级到智谱 MCP 或 Web 抓取）
- **jq 缺失** → 提示安装命令（推荐但非必须，缺失时 Stage 4 loudnorm 降级为单遍处理）
- **HyperFrames Skills 缺失** → 自动安装，失败则提示手动命令
- **MusicGen 缺失** → 不影响，使用音乐库 + yt-dlp 下载现成曲目

---

> 本阶段的结构化约束（HARD/SOFT 规则 + Guard Red Flags）由引擎注入提供。执行前运行 `python engine/inject.py --skill stage0-env` 获取完整约束 prompt。

## Red Flags（停止信号）

| 信号 | 说明 |
|------|------|
| Node.js < 22 | HyperFrames CLI 最低要求，版本不够会导致渲染失败 |
| FFmpeg 缺失 | 音视频处理核心依赖，缺失时 TTS/合并/渲染全部无法执行 |
| edge-tts 缺失 | TTS 旁白唯一工具，缺失时 Stage 4 无法生成旁白 |
| yt-dlp 缺失 | BGM 下载依赖，缺失时只能使用本地已有音乐 |
| `.env-checked` 未创建 | 检测未完成就跳到 Stage 1，会导致后续阶段工具缺失 |

## Common Rationalizations（常见借口反驳）

| 借口 | 事实 |
|------|------|
| "之前的视频跑过了，不用再检查" | 环境可能被更新或卸载破坏。标记文件不存在 = 必须重新检查 |
| "跳过环境检测，直接开始制作" | 一个缺失依赖就能导致 30 分钟后的渲染失败，不如现在花 10 秒确认 |
| "jq 不是必须的，跳过就行" | 缺失时 Stage 4 loudnorm 降级为单遍处理，音量标准化精度下降 |
