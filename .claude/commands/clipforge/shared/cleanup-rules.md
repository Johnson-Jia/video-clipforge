# ClipForge 项目清理规则

> delivery + machine-scoring 完成后自动执行。清理中间产物，保留核心产出。

当 `final.mp4` 已存在且项目目录未清理时触发。清理中间产物，保留核心产出。

## §1 强制执行

> **⛔ 清理只允许通过以下两种方式执行，禁止任何其他方式：**
>
> 1. **运行清理脚本**（首选）：`bash .claude/commands/clipforge/scripts/cleanup_project.sh "$PROJECT_DIR"`
> 2. **本文件下方的逐条删除步骤**：先执行 §清理前检查点，再按 §必删文件 逐条删除
>
> **严禁手动 `rm -f` 批量删除文件。** 手动 `rm -f` 会误删保留清单中的文件（cover.html、index.html、design.md、narration_segments.json 等），导致微调视频需要重跑整个阶段。

## §2 第一原则

> **白名单机制，不是黑名单机制。**
> 只删除"必删文件"列表中**明确列出**的文件。不在必删列表中的文件，**一律不动**。
> **严禁使用通配符批量删除保留清单中的文件类型**（如 `rm -f *.md`、`rm -f *.json`）。
> 保留清单中的每个文件都有不可替代的作用，删除任何一个都会导致后续微调需要重跑整个阶段。

## §3 清理前检查点

> **执行任何删除操作前，必须先完成此检查点。**

```
0. 确认 score_report.json 已存在：
   test -f "${PROJECT_DIR}/score_report.json" || \
     python .claude/commands/clipforge/engine/gate.py --generate-report --project-dir "$PROJECT_DIR"
   如果不存在，立即生成后再继续。
1. 列出当前目录所有文件: ls -la ${PROJECT_DIR}/
2. 逐个对照下方 §视频项目保留清单，确认每个文件的去留
3. 将要删除的文件名单记录下来（只在必删文件列表中的）
4. 删除前再次确认：要删除的文件不在保留清单中
5. 按记录的名单逐条删除（不用通配符）
```

## §4 执行时机

- **视频项目**：Stage 7 交付 + machine-scoring 完成后
- **文章项目**：文章生成 + 封面完成后
- **定时任务**：全自动流程末尾自动执行
- **手动触发**：用户说"清理"、"整理"时执行

## §5 保留规则

以下文件**必须保留**，是核心产出物或重新生成的必要输入：

### 视频项目保留清单

| 文件 | 说明 | 保留原因 |
|------|------|---------|
| `final.mp4` | 最终成品视频（含 BGM） | 核心产出物 |
| `final_no_bgm.mp4` | 无 BGM 版本（仅旁白） | 核心产出物，供用户自定义配乐 |
| `cover.png` | 封面图 | 核心产出物 + 平台发布需要 |
| `cover.html` | 封面 HTML | 封面修改后需重新渲染为 cover.png |
| `index.html` | HTML 组合 | 修改视觉/调整场景后重新渲染必需 |
| `creative/` | 创意碎片化源目录（style.css + sNN.html 碎片 + FILL_SPEC.md） | 单场景独立修改 + 确定性重组装必需；删了退化为在 105K 单文件里改视觉，碎片化改造价值归零 |
| `design.md` | 视觉风格定义 | 换风格需回退到此文件 |
| `narration_segments.json` | 分段旁白定义 | 改旁白/TTS 必需 |
| `narration.txt` | 完整旁白文案 | 改文案必需 |
| `segment_durations.json` | 分段实际时长 | A/V 同步校准必需 |
| `sentence_timestamps.json` | 句子级时间戳（Edge TTS SRT） | Phase 时间校准的测量源数据 |
| `phase_timings.json` | Phase 精确切换时间 | GSAP timeline 自动注入的数据源 |
| `douyin.md` | 抖音发布文案 | 核心产出物 |
| `score_report.json` | 机器评分报告 | Stage 8 反馈校准输入 |
| `content.md` | 内容摘要（如有） | 重新理解项目内容 |
| `content_summary.md` | 内容摘要备选名 | 同 content.md |
| `cover_params.json` | 封面生成参数 | 换配色/内容时重生成封面需要 |
| `raw_trending.json` | 原始趋势数据（GitHub） | 数据溯源，重跑 content 阶段需要 |
| `content_ready.txt` | 内容筛选结果 | 记录选中项目和反共识角度 |

### 文章项目保留清单

| 文件 | 说明 | 保留原因 |
|------|------|---------|
| `article.md` | 文章正文 | 核心产出物 |
| `cover.png` | 封面图 | 核心产出物 |
| `content.md` | 内容摘要 | 文章素材 |
| `raw_trending.json` | 原始数据（GitHub 项目） | 数据溯源 |

### 可选保留

| 文件 | 条件 | 说明 |
|------|------|------|
| `narration.mp3` | 如后续需调整音量 | 合并旁白，可从分段重新生成 |
| `bgm.wav` | 如 BGM 是项目定制/一次性 | 项目专属配乐；来自素材库的可删除 |
| `assets/` 目录 | 如后续需修改 HTML 中的图片/图表 | 修改 index.html 引用的素材需要 |

## §6 清理规则

以下文件**必须删除**（中间产物，可从保留文件重新生成）：

### 必删文件

```
# TTS 分段中间产物
narration_seg_*.txt
narration_seg_*.mp3
narration_seg_*.srt

# 音频中间产物
loudnorm_stats.json
concat.txt
concat_new.txt
silence_*.mp3           # 电影模式静音填充
bgm_orig.wav            # BGM 管线备份（标准化前原始文件）
bgm_pre_norm.wav        # BGM 管线备份（标准化前备份）

# ffmpeg 合成中间产物
output_silent.mp4       # 无音频版本（合成中间步骤）
output_with_audio.mp4   # 含音频版本（合成中间步骤）
cover_1frame.mp4        # 1帧封面视频
cover_1frame_audio.mp4  # 含静音音轨的1帧封面
cover.ts                # TS 格式封面
output.ts               # TS 格式输出
cover_segment.mp4       # 封面片段
cover_clip.mp4          # 封面剪辑
cover_final.png         # 封面中间版本

# HyperFrames 工作产物
hyperframes.json
frame_check.png

# 视频验证截图
verify_*.png
check_*.png              # 门禁/码率检测截图
frame_*.png              # 逐帧抽检截图
v2_*.png                 # 修复后重检截图

# 电影片段中间产物
clips_16x9/             # 提取的单段片段（可从源视频重新提取）

# 场景拆解（信息已在 narration_segments.json 和 index.html 中）
scenes.yaml

# 流程控制文件
stage-handoff.json
skills-lock.json
webreader_checklist.json
narration.srt

# 清理标记（清理完成后重新生成）
.cleaned
.assemble_marker.json   # assemble_final.sh 门禁标记
.bgm_pipeline_marker.json  # bgm_pipeline.sh 门禁标记
```

### 必须保留（封面重生成需要）

以下文件虽然看起来是中间产物，但**封面重生成或视频重新合成都需要它们**，不得删除：

| 文件 | 保留原因 |
|------|---------|
| `cover.html` | 封面修改后需重新渲染为 cover.png |
| `output.mp4` | 重新合成 final.mp4（换封面）的源文件。**final.mp4 已包含封面帧，无法反向提取纯净视频流** |
| `output_no_bgm.mp4` | 重新合成 final_no_bgm.mp4 的源文件。同 output.mp4 原理 |


### 必删目录

```
work-*/                 # HyperFrames 工作临时目录
.agents/                # SubAgent Skill 工具就地创建的技能库副本
renders/                # HyperFrames 历史渲染产物（带时间戳的多次重试 mp4）
snapshots/              # HyperFrames 渲染前 HTML 预览截图（0%/25%/50%/75%/100%）
backup/                 # 渲染过程备份的旧版 HTML（骨架、早期 index、cover）
lib/                    # HyperFrames 渲染时下载的本地 JS 库（gsap.min.js 等）
frames/                 # 帧分析/提取临时帧
frames_check/           # 帧检查临时帧
segments/               # 音频分段临时目录
raw_tts/                # TTS 原始输出（合并前）
```

### 按条件删除

| 文件/目录 | 删除条件 | 原因 |
|-----------|---------|------|
| `bgm.wav` | BGM 来自 `workspace/bgm/` 素材库 | 项目目录的副本，素材库已有原始文件 |
| `assets/` | 素材全部来自模板库/搜索结果 | 可重新搜索/生成；如是 AI 定制图片则保留 |
| `movie_audio.wav` | 电影模式交付后 | 可从 clips 重新构建 |

## §7 执行脚本

> **关键约束：只删除"必删文件"列表中明确列出的文件。** 不在必删列表中的文件一律不动。绝不使用通配符批量删除非必删文件。

```bash
# 执行项目清理（白名单保护 + 清理后验证）
bash .claude/commands/clipforge/scripts/cleanup_project.sh "$PROJECT_DIR"
```

## §8 清理后项目目录结构

视频项目清理后仅包含：

```
workspace/<YYYY>/<MM>/<DD>/<项目名>/
├── final.mp4              # 最终视频（含 BGM）
├── final_no_bgm.mp4       # 无 BGM 版本（仅旁白）
├── output.mp4             # 渲染原始（含 BGM，换封面需要）
├── output_no_bgm.mp4      # 渲染原始（无 BGM，换封面需要）
├── cover.html             # 封面 HTML（可重渲染）
├── cover.png              # 封面图
├── cover_params.json      # 封面生成参数（换配色/内容需要）
├── index.html             # HTML 组合（可重渲染）
├── creative/              # 创意碎片化源（style.css + sNN.html，单场景微调必需）
├── design.md              # 视觉风格
├── narration_segments.json # 分段旁白定义
├── narration.txt          # 旁白文案
├── segment_durations.json # 分段时长
├── sentence_timestamps.json # 句子级时间戳
├── phase_timings.json    # Phase 切换时间
├── narration.mp3          # 合并旁白（可选）
├── douyin.md              # 抖音文案
├── raw_trending.json      # 原始趋势数据（GitHub 项目）
├── content_ready.txt      # 内容筛选结果（选中项目+角度）
└── score_report.json      # 机器评分报告
```

文章项目清理后仅包含：

```
workspace/<YYYY>/<MM>/<DD>/<项目名>/
├── article.md             # 文章正文
├── cover.png              # 封面图
├── content.md             # 内容摘要
└── raw_trending.json      # 原始数据（GitHub 项目）
```

## §9 磁盘用量监控

清理完成后输出磁盘用量：

```bash
DATE_DIR="$(date +%Y)/$(date +%m)/$(date +%d)"
echo "workspace 磁盘用量：$(du -sh workspace/ 2>/dev/null | cut -f1)"
echo "今日项目数：$(ls -d workspace/${DATE_DIR}/*/ 2>/dev/null | wc -l)"
echo "总月目录：$(ls -d workspace/????/??/ 2>/dev/null | wc -l)"
```

> **目标：** 单个项目清理后占用 < 30 MB（视频 + 核心文件）。确保 workspace 在 500 MB 以内可控增长。

---

## §10 Red Flags（停止信号）

| 信号 | 说明 |
|------|------|
| 清理了 `final.mp4` 或 `final_no_bgm.mp4` | 核心产出不可删除，否则视频制作白费 |
| 清理了 `douyin.md` | 抖音发布文案需要用于发布，删除后需重新生成 |
| 清理了 `cover.png` | 封面图可能用于发布，不应删除 |
| 清理了 `cover.html`、`index.html`、`output.mp4` | 封面/视频重渲染必需，删了微调视频就要重跑整个阶段 |
| 清理了 `design.md`、`narration_segments.json`、`segment_durations.json` | 改风格/改旁白/校音必需，删了就要重跑对应阶段 |
| 使用 `rm -f *.md` / `rm -f *.json` 等通配符批量删除 | 通配符会误删保留清单中的文件，必须逐条按必删列表删除 |

## §11 Common Rationalizations（常见借口反驳）

| 借口 | 事实 |
|------|------|
| "这个文件很大可以删" | `final.mp4`/`final_no_bgm.mp4`/`output.mp4` 是核心产出或重渲染源，再大也不能删 |
| "清理完就完了，不用验证" | 必须确认保留清单中的文件仍然存在，否则后续微调需要重跑整个阶段 |
| "中间文件先留着可能有用" | 中间产物（raw_clips、分段 TTS）会持续占空间，但只删必删列表中的 |
| "用 rm -f *.xx 一次性删干净" | 通配符会误删保留文件。必须只删除"必删文件"列表中明确列出的文件名模式 |
| "这些 json/md 文件是中间产物" | `design.md`、`narration_segments.json`、`segment_durations.json` 是重渲染核心输入，不是中间产物 |
| "反正能重新生成" | 重新生成需要重跑整个 SubAgent 阶段，浪费时间 5-10 分钟，而保留它们只占几 KB |
