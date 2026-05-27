---
name: stage0-env
description: 环境检测与新手引导 — 校验并安装运行时依赖
version: "1.0.0"
type: EXECUTIVE
rigor: LITE
dependencies: []
---

# Stage 0: 环境检测与新手引导

## Intent
> 确认所有运行时依赖就绪，缺失时自动安装或提示安装。
> 成功标准：所有必须依赖已安装且版本满足要求，`workspace/.env-checked` 标记文件已创建。

## Boundary — 行为准则

### 必须遵守（HARD 规则 · 正向重述）

1. **确认 Node.js ≥ 22** — 检测 Node.js 版本，低于 v22 时提示安装命令 ← `R-STAGE0-001`
   ↳ 校验：`node --version` 输出 ≥ v22
2. **确认 FFmpeg 已安装** — 检测 FFmpeg 可用性，缺失时提示安装命令 ← `R-STAGE0-002`
   ↳ 校验：`ffmpeg -version` 可执行
3. **确认 edge-tts 已安装** — TTS 旁白核心工具，缺失时提示 `pip install edge-tts` ← `R-STAGE0-003`
   ↳ 校验：`edge-tts --version` 可执行
4. **确认 yt-dlp 已安装** — BGM 下载依赖，缺失时提示 `pip install yt-dlp` ← `R-STAGE0-004`
   ↳ 校验：`yt-dlp --version` 可执行
5. **创建标记文件** — 检测全部通过后创建 `workspace/.env-checked` ← `R-STAGE0-005`
   ↳ 校验：文件存在

### 建议参考（偏好）

- 推荐安装 GitHub CLI (`gh`) 以获取精确的项目实时数据（MEDIUM）
  - 缺失时 Stage 1 降级到智谱 MCP 或 Web 抓取
- 推荐安装 `jq` 以实现两遍精确 loudnorm 音量标准化（MEDIUM）
  - 缺失时 Stage 4 loudnorm 降级为单遍处理

## Guard — 认知守卫

| 当你产生这个念头 | 现实是 | 触发行为 |
|---|---|---|
| "之前的视频跑过了，不用再检查" | 环境可能被更新或卸载破坏 | 执行 env_check.sh |
| "跳过环境检测，直接开始制作" | 一个缺失依赖导致30分钟后渲染失败 | 执行 env_check.sh |
| "jq 不是必须的，跳过就行" | Stage 4 loudnorm 降级，精度下降 | 提示安装 jq |

### Spirit vs Letter

| 规则 | 模式 | 真实意图 |
|---|---|---|
| R-STAGE0-005 | SPIRIT | 确保后续阶段不会因缺少依赖而中途失败 |

## Gate — 通过标准

### 流程门禁（自动化检查，不通过 = 停止，不可重试）
- [ ] `dependency_completeness` — Node.js≥22 + FFmpeg + edge-tts + yt-dlp 全部就绪
- [ ] `marker_file_created` — `workspace/.env-checked` 存在

## Trace — 采集点
- **执行开始**：记录检测时间
- **执行结束**：记录每个依赖的检测结果（通过/缺失/自动安装/手动提示）
- **写入**：`{project_dir}/trace/stage0-{timestamp}.yaml`

## 操作指令

### 守卫机制

```bash
# 检测标记文件，已通过则跳过
mkdir -p workspace
if [ -f "workspace/.env-checked" ]; then
  echo "✅ 环境已验证（跳过 Stage 0）"
  exit 0
fi
```

### 依赖清单

| 依赖 | 最低版本 | 用途 | 必须 | 缺失处理 |
|------|---------|------|------|---------|
| Node.js | >= 22 | HyperFrames CLI | 是 | 提示安装 |
| FFmpeg | 任意 | 音视频处理 | 是 | 提示安装 |
| edge-tts | 任意 | TTS 旁白 | 是 | 提示安装 |
| yt-dlp | 任意 | 从 YouTube 下载免费音乐 | 是 | 提示安装 |
| GitHub CLI (`gh`) | 任意 | GitHub 项目实时数据获取 | 推荐 | 提示安装 |
| jq | 任意 | loudnorm 两遍精确音量标准化 | 推荐 | 降级单遍处理 |
| HyperFrames Skills | 最新 | 视频编排技能组 | 是 | **自动安装** |
| Python | >= 3.12 | MusicGen BGM（仅二创时需要） | 否 | 跳过 |

### 一键检测 + 自动安装

```bash
bash .claude/commands/clipforge/scripts/env_check.sh
```

### 自动安装行为

| 依赖 | 自动安装命令 | 说明 |
|------|------------|------|
| HyperFrames Skills | `npx skills add heygen-com/hyperframes` | 视频编排技能 |
| 工具脚本 | `curl` 下载到 `scripts/` | generate_bgm.py + merge_video_audio.sh |

### 手动安装命令（无法自动安装）

| 依赖 | 安装命令 |
|------|---------|
| Node.js >= 22 | `winget install OpenJS.NodeJS.LTS` (Win) / `brew install node@22` (Mac) |
| FFmpeg | `winget install Gyan.FFmpeg` (Win) / `brew install ffmpeg` (Mac) |
| edge-tts | `pip install edge-tts` |
| yt-dlp | `pip install yt-dlp` |
| jq | `winget install jqlang.jq` (Win) / `brew install jq` (Mac) |
| Python + MusicGen | `pip install torch transformers scipy`（仅 AI 配乐二创时需要） |

### 检测结果处理

- **全部通过** → 创建 `workspace/.env-checked`，进入 Stage 1
- **Node/FFmpeg/edge-tts/yt-dlp 缺失** → 提示安装命令，安装后重新运行检测
- **gh 缺失** → 提示安装命令（Stage 1 降级到智谱 MCP 或 Web 抓取）
- **jq 缺失** → 提示安装命令（Stage 4 loudnorm 降级为单遍处理）
- **HyperFrames Skills 缺失** → 自动安装，失败则提示手动命令
- **MusicGen 缺失** → 不影响，使用音乐库 + yt-dlp 下载现成曲目

## Red Flags

| 信号 | 说明 |
|------|------|
| Node.js < 22 | HyperFrames CLI 最低要求，版本不够导致渲染失败 |
| FFmpeg 缺失 | 音视频处理核心依赖，缺失时全部无法执行 |
| edge-tts 缺失 | TTS 旁白唯一工具，Stage 4 无法生成旁白 |
| yt-dlp 缺失 | BGM 下载依赖，只能使用本地已有音乐 |
| `.env-checked` 未创建 | 检测未完成就跳到 Stage 1 |

## Common Rationalizations

| 借口 | 事实 |
|------|------|
| "之前的视频跑过了，不用再检查" | 环境可能被更新或卸载破坏。标记文件不存在 = 必须重新检查 |
| "跳过环境检测，直接开始制作" | 一个缺失依赖就能导致 30 分钟后的渲染失败 |
| "jq 不是必须的，跳过就行" | 缺失时 Stage 4 loudnorm 降级为单遍处理，精度下降 |
