---
id: "clipforge.cleanup-rules"
description: ClipForge 项目清理规则（Stage 8）— 白名单保护 + 中间产物清理
version: "2.0.0"
type: EXECUTIVE
rigor: LITE
trace_level: SUMMARY
rules_lib_ref: "_rules-lib/cleanup-rules.yaml"
---

# ClipForge 项目清理规则（Stage 8）

> 当 `final.mp4` 已存在且项目目录未清理时触发。清理中间产物，保留核心产出。

## Intent
> 按白名单策略清理项目中间产物，保留核心产出物和重渲染所需文件。
> 成功标准：仅保留清单文件存在，必删文件已清除，磁盘 < 30MB。

## Boundary — 行为准则

### 必须遵守（HARD 规则 · 正向重述）

1. **使用白名单清理** — 只删除"必删文件"列表中明确列出的文件，不在列表中的文件一律不动 ← `R-CLEANUP-001`
   ↳ 校验：删除的文件全部在必删列表中
2. **逐条删除** — 按必删文件列表逐条删除，不使用通配符 ← `R-CLEANUP-002`
   ↳ 校验：无 `rm -f *.md` / `rm -f *.json` 等通配符命令
3. **通过脚本或步骤执行** — 只通过清理脚本（首选）或逐条删除步骤执行 ← `R-CLEANUP-003`
   ↳ 校验：未使用手动 `rm -f` 批量删除
4. **先检查后删除** — 执行删除前完成 5 步检查点 ← `R-CLEANUP-004`
   ↳ 校验：ls → 对照保留清单 → 记录删除名单 → 确认 → 逐删
5. **保留重渲染源文件** — output.mp4 和 output_no_bgm.mp4 作为换封面的源文件必须保留 ← `R-CLEANUP-005`
   ↳ 校验：output.mp4 和 output_no_bgm.mp4 存在

### 强制执行声明（2026-05-27 加固）

> **⛔ 清理只允许通过以下两种方式执行，禁止任何其他方式：**
>
> 1. **运行清理脚本**（首选）：`bash .claude/commands/clipforge/scripts/cleanup_project.sh "$PROJECT_DIR"`
> 2. **本文件下方的逐条删除步骤**：先执行 §清理前检查点，再按 §必删文件 逐条删除
>
> **严禁手动 `rm -f` 批量删除文件。** 2026-05-22 和 2026-05-27 两次事故均因手动 `rm -f` 删除了保留清单中的文件。

### Spirit vs Letter

| 规则 | 模式 | 真实意图 |
|------|------|---------|
| R-CLEANUP-001 | SPIRIT | 防止误删核心产出物导致微调需重跑整个阶段 |
| R-CLEANUP-003 | SPIRIT | 防止批量操作中的不可逆误操作 |

## Gate — 通过标准

### 流程门禁（自动化检查，不通过 = 驳回）
- [ ] `cleanup_completeness` — 所有必删文件已清除
- [ ] `retention_completeness` — 所有保留清单文件仍存在
- [ ] `disk_usage` — 单项目 < 30MB

## Trace — 采集点
- **执行开始**：记录项目目录文件列表
- **执行结束**：记录删除的文件数、保留的文件数、磁盘用量
- **写入**：`{project_dir}/trace/cleanup-{timestamp}.yaml`

## 操作指令

### 第一原则

> **白名单机制，不是黑名单机制。**
> 只删除"必删文件"列表中**明确列出**的文件。不在必删列表中的文件，**一律不动**。

### 清理前检查点

```
1. 列出当前目录所有文件: ls -la ${PROJECT_DIR}/
2. 逐个对照下方 §视频项目保留清单，确认每个文件的去留
3. 将要删除的文件名单记录下来（只在必删文件列表中的）
4. 删除前再次确认：要删除的文件不在保留清单中
5. 按记录的名单逐条删除（不用通配符）
```

### 执行时机

- **视频项目**：Stage 7 交付 final.mp4 后
- **文章项目**：文章生成 + 封面完成后
- **定时任务**：全自动流程末尾自动执行
- **手动触发**：用户说"清理"、"整理"时执行

### 保留规则

#### 视频项目保留清单

| 文件 | 说明 | 保留原因 |
|------|------|---------|
| `final.mp4` | 最终成品视频（含 BGM） | 核心产出物 |
| `final_no_bgm.mp4` | 无 BGM 版本（仅旁白） | 核心产出物，供自定义配乐 |
| `cover.png` | 封面图 | 核心产出物 + 平台发布 |
| `cover.html` | 封面 HTML | 封面修改后需重新渲染 |
| `index.html` | HTML 组合 | 修改视觉/场景后重新渲染必需 |
| `design.md` | 视觉风格定义 | 换风格需回退到此文件 |
| `narration_segments.json` | 分段旁白定义 | 改旁白/TTS 必需 |
| `narration.txt` | 完整旁白文案 | 改文案必需 |
| `segment_durations.json` | 分段实际时长 | A/V 同步校准必需 |
| `douyin.md` | 抖音发布文案 | 核心产出物 |
| `content.md` | 内容摘要（如有） | 重新理解项目内容 |

#### 文章项目保留清单

| 文件 | 说明 | 保留原因 |
|------|------|---------|
| `article.md` | 文章正文 | 核心产出物 |
| `cover.png` | 封面图 | 核心产出物 |
| `content.md` | 内容摘要 | 文章素材 |
| `raw_trending.json` | 原始数据 | 数据溯源 |

#### 可选保留

| 文件 | 条件 | 说明 |
|------|------|------|
| `narration.mp3` | 如后续需调整音量 | 可从分段重新生成 |
| `bgm.wav` | 如 BGM 是项目定制 | 素材库有的可删除 |
| `assets/` 目录 | 如后续需修改 HTML | 修改 index.html 引用的素材 |

#### 必须保留（封面重生成需要）

| 文件 | 保留原因 |
|------|---------|
| `cover.html` | 封面修改后需重新渲染 |
| `output.mp4` | 重新合成 final.mp4 的源文件 |
| `output_no_bgm.mp4` | 重新合成 final_no_bgm.mp4 的源文件 |

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
silence_*.mp3

# ffmpeg 封面帧中间产物
cover_1frame.mp4
cover_1frame_audio.mp4
cover.ts
output.ts

# HyperFrames 工作产物
.hyperframes/
hyperframes.json
frame_check.png

# 视频验证截图
verify_*.png

# 电影片段中间产物
clips_16x9/

# 场景拆解
scenes.yaml
```

### 必删目录

```
work-*/                 # HyperFrames 工作临时目录
.agents/                # SubAgent 技能库副本
```

### 按条件删除

| 文件/目录 | 删除条件 | 原因 |
|-----------|---------|------|
| `bgm.wav` | BGM 来自素材库 | 素材库已有原始文件 |
| `assets/` | 素材来自模板/搜索 | 可重新搜索/生成 |
| `narration.srt` | 不再需要字幕 | 可重新生成 |
| `movie_audio.wav` | 电影模式交付后 | 可从 clips 重新构建 |

### 执行脚本

```bash
bash .claude/commands/clipforge/scripts/cleanup_project.sh "$PROJECT_DIR"
```

### 清理后项目目录结构

**视频项目**（13 个文件）：
```
workspace/<YYYY>/<MM>/<DD>/<项目名>/
├── final.mp4              # 最终视频（含 BGM）
├── final_no_bgm.mp4       # 无 BGM 版本
├── output.mp4             # 渲染原始（换封面需要）
├── output_no_bgm.mp4      # 渲染原始（无 BGM）
├── cover.html             # 封面 HTML
├── cover.png              # 封面图
├── index.html             # HTML 组合
├── design.md              # 视觉风格
├── narration_segments.json # 分段旁白
├── narration.txt          # 旁白文案
├── segment_durations.json # 分段时长
├── narration.mp3          # 合并旁白（可选）
└── douyin.md              # 抖音文案
```

**文章项目**（4 个文件）：
```
workspace/<YYYY>/<MM>/<DD>/<项目名>/
├── article.md
├── cover.png
├── content.md
└── raw_trending.json
```

### 磁盘用量监控

```bash
DATE_DIR="$(date +%Y)/$(date +%m)/$(date +%d)"
echo "workspace 磁盘用量：$(du -sh workspace/ 2>/dev/null | cut -f1)"
echo "今日项目数：$(ls -d workspace/${DATE_DIR}/*/ 2>/dev/null | wc -l)"
```

> **目标：** 单项目 < 30MB，workspace < 500MB。

## Red Flags（停止信号）

| 信号 | 规则 ID | 说明 |
|------|---------|------|
| 清理了 `final.mp4` 或 `final_no_bgm.mp4` | R-CLEANUP-001 | 核心产出不可删除 |
| 清理了 `douyin.md` | R-CLEANUP-001 | 发布文案必需 |
| 清理了 `cover.png` | R-CLEANUP-001 | 封面图必需 |
| 清理了 `cover.html`/`index.html`/`output.mp4` | R-CLEANUP-005 | 重渲染必需 |
| 清理了 `design.md`/`narration_segments.json`/`segment_durations.json` | R-CLEANUP-001 | 改风格/旁白/校音必需 |
| 使用通配符批量删除 | R-CLEANUP-002 | 误删保留清单文件 |

## Common Rationalizations（常见借口反驳）

| 借口 | 事实 |
|------|------|
| "这个文件很大可以删" | final.mp4/output.mp4 是核心产出或重渲染源，再大也不能删 |
| "清理完就完了，不用验证" | 必须确认保留清单文件仍存在 |
| "中间文件先留着可能有用" | 只删必删列表中的，其余不动 |
| "用 rm -f *.xx 一次性删干净" | 通配符会误删保留文件 |
| "这些 json/md 是中间产物" | design.md/narration_segments.json 是重渲染核心输入 |
| "反正能重新生成" | 重新生成需重跑 SubAgent 阶段，浪费 5-10 分钟 |
