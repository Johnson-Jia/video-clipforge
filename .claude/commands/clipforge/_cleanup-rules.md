# ClipForge 项目清理规则（Stage 8）

当 `final.mp4` 已存在且项目目录未清理时触发。清理中间产物，保留核心产出。

## 执行时机

- **视频项目**：Stage 7 交付 final.mp4 后
- **文章项目**：文章生成 + 封面完成后
- **定时任务**：全自动流程末尾自动执行
- **手动触发**：用户说"清理"、"整理"时执行

## 保留规则

以下文件**必须保留**，是核心产出物或重新生成的必要输入：

### 视频项目保留清单

| 文件 | 说明 | 保留原因 |
|------|------|---------|
| `final.mp4` | 最终成品视频（含 BGM） | 核心产出物 |
| `final_no_bgm.mp4` | 无 BGM 版本（仅旁白） | 核心产出物，供用户自定义配乐 |
| `cover.png` | 封面图 | 核心产出物 + 平台发布需要 |
| `cover.html` | 封面 HTML | 封面修改后需重新渲染为 cover.png |
| `index.html` | HTML 组合 | 修改视觉/调整场景后重新渲染必需 |
| `design.md` | 视觉风格定义 | 换风格需回退到此文件 |
| `narration_segments.json` | 分段旁白定义 | 改旁白/TTS 必需 |
| `narration.txt` | 完整旁白文案 | 改文案必需 |
| `segment_durations.json` | 分段实际时长 | A/V 同步校准必需 |
| `douyin.md` | 抖音发布文案 | 核心产出物 |
| `content.md` | 内容摘要（如有） | 重新理解项目内容 |

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

## 清理规则

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

# HyperFrames 工作产物
hyperframes.json
frame_check.png

# 视频验证截图
verify_*.png

# 电影片段中间产物
clips_16x9/             # 提取的单段片段（可从源视频重新提取）

# 场景拆解（信息已在 narration_segments.json 和 index.html 中）
scenes.yaml
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
```

### 按条件删除

| 文件/目录 | 删除条件 | 原因 |
|-----------|---------|------|
| `bgm.wav` | BGM 来自 `workspace/bgm/` 素材库 | 项目目录的副本，素材库已有原始文件 |
| `assets/` | 素材全部来自模板库/搜索结果 | 可重新搜索/生成；如是 AI 定制图片则保留 |
| `narration.srt` | 确认不再需要字幕文件 | 可从 narration_segments 重新生成 |
| `movie_audio.wav` | 电影模式交付后 | 可从 clips 重新构建 |

## 执行脚本

```bash
cd "${PROJECT_DIR}"

echo "=== Stage 8: 项目清理 ==="

# 1. 删除必删文件
rm -f narration_seg_*.txt narration_seg_*.mp3 narration_seg_*.srt
rm -f loudnorm_stats.json concat.txt concat_new.txt
rm -f output_silent.mp4 output_with_audio.mp4
rm -f silence_*.mp3 hyperframes.json frame_check.png
rm -f verify_*.png scenes.yaml
rm -f stage-handoff.json skills-lock.json webreader_checklist.json
rm -f cover_final.png cover_segment.mp4 narration.srt
# 注意：cover.html 和 output.mp4 不删除 — 封面/BGM 重生成需要

# 2. 删除工作临时目录和技能库副本
rm -rf work-*/
rm -rf .agents/

# 3. 按条件删除 BGM 副本
# 策略：检查 segment_durations.json 或 index.html 中的 BGM 来源，
# 如果能追溯到 workspace/bgm/ 中的原始文件则删除项目副本
if [ -f bgm.wav ]; then
  BGM_FOUND_IN_LIB=false
  # 方法1: 检查 segment_durations.json 中记录的 bgm_source
  BGM_SOURCE=$(python3 -c "import json; d=json.load(open('segment_durations.json')); print(d.get('meta',{}).get('bgm_source',''))" 2>/dev/null)
  if [ -n "$BGM_SOURCE" ] && [ -f "../../workspace/bgm/${BGM_SOURCE}" ]; then
    BGM_FOUND_IN_LIB=true
  fi
  # 方法2: 检查素材库中是否有同名文件（按项目目录名反推）
  if [ "$BGM_FOUND_IN_LIB" = false ]; then
    # 检查素材库中是否有任何匹配的 mp3/wav 文件
    BGM_DURATION=$(ffprobe -v quiet -show_entries format=duration -of csv=p=0 bgm.wav 2>/dev/null | cut -d. -f1)
    for f in ../../workspace/bgm/*.mp3 ../../workspace/bgm/*.wav; do
      if [ -f "$f" ]; then
        LIB_DUR=$(ffprobe -v quiet -show_entries format=duration -of csv=p=0 "$f" 2>/dev/null | cut -d. -f1)
        if [ "$BGM_DURATION" = "$LIB_DUR" ]; then
          BGM_FOUND_IN_LIB=true
          break
        fi
      fi
    done
  fi
  if [ "$BGM_FOUND_IN_LIB" = true ]; then
    rm -f bgm.wav
    echo "  已删除 bgm.wav（素材库已有原始文件）"
  else
    echo "  保留 bgm.wav（无法确认素材库来源）"
  fi
fi

# 4. 清理电影片段临时目录（仅电影解读模式）
if [ -d clips_16x9 ]; then
  rm -rf clips_16x9/
  echo "  已删除 clips_16x9/"
fi

# 5. 报告清理结果
echo ""
echo "保留文件："
ls -1 | head -20
echo ""
echo "项目大小：$(du -sh . 2>/dev/null | cut -f1)"
echo "=== 清理完成 ==="
```

## 清理后项目目录结构

视频项目清理后仅包含：

```
workspace/<YYYY>/<MM>/<DD>/<项目名>/
├── final.mp4              # 最终视频（含 BGM）
├── final_no_bgm.mp4       # 无 BGM 版本（仅旁白）
├── output.mp4             # 渲染原始（含 BGM，换封面需要）
├── output_no_bgm.mp4      # 渲染原始（无 BGM，换封面需要）
├── cover.html             # 封面 HTML（可重渲染）
├── cover.png              # 封面图
├── index.html             # HTML 组合（可重渲染）
├── design.md              # 视觉风格
├── narration_segments.json # 分段旁白定义
├── narration.txt          # 旁白文案
├── segment_durations.json # 分段时长
├── narration.mp3          # 合并旁白（可选）
└── douyin.md              # 抖音文案
```

文章项目清理后仅包含：

```
workspace/<YYYY>/<MM>/<DD>/<项目名>/
├── article.md             # 文章正文
├── cover.png              # 封面图
├── content.md             # 内容摘要
└── raw_trending.json      # 原始数据（GitHub 项目）
```

## 磁盘用量监控

清理完成后输出磁盘用量：

```bash
DATE_DIR="$(date +%Y)/$(date +%m)/$(date +%d)"
echo "workspace 磁盘用量：$(du -sh workspace/ 2>/dev/null | cut -f1)"
echo "今日项目数：$(ls -d workspace/${DATE_DIR}/*/ 2>/dev/null | wc -l)"
echo "总月目录：$(ls -d workspace/????/??/ 2>/dev/null | wc -l)"
```

> **目标：** 单个项目清理后占用 < 30 MB（视频 + 核心文件）。确保 workspace 在 500 MB 以内可控增长。

---

## Red Flags（停止信号）

| 信号 | 说明 |
|------|------|
| 清理了 `final.mp4` 或 `final_no_bgm.mp4` | 核心产出不可删除，否则视频制作白费 |
| 清理了 `douyin.md` | 抖音发布文案需要用于发布，删除后需重新生成 |
| 清理了 `cover.png` | 封面图可能用于发布，不应删除 |

## Common Rationalizations（常见借口反驳）

| 借口 | 事实 |
|------|------|
| "这个文件很大可以删" | `final.mp4`/`final_no_bgm.mp4`/`douyin.md` 是核心产出，再大也不能删 |
| "清理完就完了，不用验证" | 必须确认核心文件存在，否则用户无法使用成品 |
| "中间文件先留着可能有用" | 中间产物（raw_clips、临时 HTML）会持续占空间，目标 < 30 MB |
