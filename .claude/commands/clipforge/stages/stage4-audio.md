# Stage 4: 音频生产（TTS + BGM）

当 `narration_segments.json` 已存在且 `segment_durations.json` 不存在时触发。生成 TTS 旁白音频和背景配乐，产出逐段时长数据。

## 4.1 旁白 TTS（分段模式）

### 一键执行（推荐）

```bash
# TTS 管线：分段生成 → 合并 → loudnorm → 校验（全自动）
bash .claude/commands/clipforge/scripts/tts_pipeline.sh "$VOICE" "$RATE"
```

> 音色：`{{audio.default_voice|zh-CN-YunjianNeural}}`，语速：`{{audio.default_rate|+25%}}`。分类配置优先，未指定时用默认值。
>
> **禁止使用播报腔音色。** `zh-CN-YunyangNeural`（新闻主播风）禁止用于任何短视频项目。

### 产出文件

| 文件 | 用途 |
|------|------|
| `narration_seg_0.mp3` ~ `narration_seg_N.mp3` | 分段旁白音频（中间产物） |
| `segment_durations.json` | **每段实际时长**（Stage 6 用此设置 `data-duration`） |
| `narration.mp3` | 合并后的完整旁白（**Stage 6 嵌入 HTML `<audio>`**） |
| `narration.srt` | 合并后的完整字幕 |

> **`segment_durations.json` 格式为 `{meta: {voice, rate}, segments: [...]}`。** Stage 6 读取时长时取 `segments[i].actual_duration`。

### 手动步骤参考

> 管线脚本已包含以下所有步骤。仅在脚本失败需要逐步排查时参考。

1. **分段 TTS**: `python .claude/commands/clipforge/scripts/tts_segments.py "$VOICE" "$RATE"`
2. **合并**: `ffmpeg -y -f concat -safe 0 -i concat.txt -c copy narration.mp3`
3. **合并 SRT**: `python .claude/commands/clipforge/scripts/merge_srt.py`
4. **loudnorm 标准化**: `bash .claude/commands/clipforge/scripts/loudnorm.sh narration.mp3`
   > 严禁使用 jq — Windows 环境不预装，jq 失败会导致 pass 2 静默跳过
5. **loudnorm 校验**: max_volume 必须 >= -10 dB

### 输出文件

| 文件 | 用途 |
|------|------|
| `narration_seg_0.mp3` ~ `narration_seg_N.mp3` | 分段旁白音频（中间产物） |
| `segment_durations.json` | **每段实际时长**（Stage 6 用此设置 `data-duration`） |
| `narration.mp3` | 合并后的完整旁白（**Stage 6 嵌入 HTML `<audio>`**） |
| `narration.srt` | 合并后的完整字幕 |

> **关键：`segment_durations.json` 是 Stage 6 设置场景 `data-duration` 的唯一权威来源。** 不再用预估时长。

### 推荐：edge-tts

国内直连、免费、速度快。

```bash
python -m edge_tts -f narration.txt -v <VOICE> --rate=<RATE> --write-media narration.mp3 --write-subtitles narration.srt
```

> Kokoro TTS 在国内网络可能超时，不推荐。

### 声音选择

> **音色：`{{audio.default_voice|zh-CN-YunjianNeural}}`，语速：`{{audio.default_rate|+25%}}`。** 分类配置优先，未指定时用默认值。

> **禁止使用播报腔音色。** 短视频需要"我在跟你聊/分析"的叙事感，不是"我在念稿子"的播报感。`zh-CN-YunyangNeural`（新闻主播风）禁止用于任何短视频项目。

## 4.2 配乐

### AI 选曲 + BGM 管线（两阶段）

**阶段 A — AI 选曲**（需人工决策）：

1. 根据 `design.md` 的 `music_mood` 推导搜索策略
2. 从来源优先级获取 BGM 文件，保存为 `bgm.wav` 到项目目录
3. 截取精华片段（跳过前奏，取有节奏的段落）

**阶段 B — BGM 管线**（选曲完成后全自动）：

```bash
# BGM 管线：音量校验 → 查表校准 → 峰值间距 → 时长对齐（全自动）
bash .claude/commands/clipforge/scripts/bgm_pipeline.sh
```

> `bgm_pipeline.sh` 自动执行：音量守恒校验 → 查表获取推荐 volume → 峰值间距双向校验 → 写入 `segment_durations.json` → **BGM 时长对齐**（以旁白总时长为基准，concat 拼接 + 裁剪 + 淡入淡出）。无需手动查表或写 JSON。
>
> **时长对齐保证：** Step 3 将 bgm.wav 对齐到旁白时长 + 1s 缓冲，添加 1.5s 淡入 + 2s 淡出。使用 concat 拼接（非 stream_loop），确保 WAV 格式下 100% 有声覆盖。

### 来源优先级（唯一权威）

| 优先级 | 来源 | 说明 |
|--------|------|------|
| **1** | 用户提供 | 用户自带音乐文件，优先使用 |
| **2** | BGM 素材库 | 从 `workspace/bgm/` 选取已有 BGM（**首选**） |
| **3** | 音乐库下载 | yt-dlp 从 YouTube 下载无版权音乐，存入 BGM 素材库 |
| **4** | 音乐库搜索 | Pixabay / Mixkit / 爱给网 的热门曲目 |
| **5** | AI 二创 | MusicGen 基于现有爆火音乐二次创作（**必须有参考样本**，无样本时跳过此来源） |

> **BGM 素材库**（`workspace/bgm/`）集中管理所有已下载的 BGM。下载新 BGM 时同步存入此目录，方便后续项目复用。

### BGM 搜索策略

根据 `design.md` 的 `music_mood` 生成英文搜索词——风格描述 + royalty free + music（如"cyberpunk royalty free music"、"warm acoustic royalty free"）。AI 自主推导搜索词，不查表。

### 推荐无版权音乐频道（YouTube）

| 频道 | 风格 | 使用条件 |
|------|------|---------|
| **White Bat Audio** (Karl Casey) | 赛博朋克、暗黑合成波 | 署名即可 |
| **Aim to Head** | 电子、科技 | 免费使用 |
| **DEEP GROUND** | 氛围、电子 | 免费使用 |
| **Audio Library** | 多风格合集 | 免费使用 |

### 方法 A：yt-dlp 下载（推荐）

```bash
# 下载音频（自动转 wav，保存到 BGM 库）
yt-dlp -x --audio-format wav -o "workspace/bgm/<bgm_name>.%(ext)s" "<YouTube URL>"

# 截取精华片段（跳过前奏，取有节奏的段落）
ffmpeg -y -i bgm_source.wav -ss 10 -to 35 -af "afade=t=in:st=0:d=2,afade=t=out:st=21:d=2" bgm.wav
```

> **截取技巧：** 从曲目中段截取（跳过前 5-15 秒的前奏），选择节奏感最强的部分。

### 方法 B：Pixabay 批量下载（推荐）

> **详细流程见 `clipforge/shared/bgm-pixabay`。** 以下为快速操作指引。

**核心原理：** Pixabay CDN 直链需 `Referer: https://pixabay.com/` 头，否则 403。通过浏览器搜索页提取 CDN URL，curl 批量下载。

```bash
# 1. 浏览器导航到搜索页（Chrome MCP）
#    URL: https://pixabay.com/music/search/<关键词>/

# 2. 从保存的 HTML 提取 CDN URL
grep -oP 'cdn\.pixabay\.com/audio/[^"'\''\\s]+\.mp3' <html文件> | head -5

# 3. 下载（必须带 Referer 头）
#    如需代理，先设置 https_proxy / http_proxy 环境变量
curl -sL -o workspace/bgm/<主题名>-1.mp3 \
  -H "Referer: https://pixabay.com/" \
  -H "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36" \
  "https://cdn.pixabay.com/audio/YYYY/MM/DD/audio_xxxxxx.mp3"
```

> **批量补全：** 对每个需要的风格执行「导航→提取→下载」三步，每个风格 5 首。详见 `clipforge/shared/bgm-pixabay`。

### 方法 C：其他音乐库

Mixkit / 爱给网等浏览试听后手动下载。

```bash
# 下载后截取
ffmpeg -i source.mp3 -ss 0:10 -t 0:30 -af "afade=t=in:d=2,afade=t=out:st=27:d=3" bgm.wav
```

### BGM 预处理注意

> **旁白清晰度 > 一切。** 不对 `bgm.wav` 做任何 gain/volume 处理。保持原始音量，音量由 HTML `<audio data-volume>` 控制。预处理 + data-volume 叠加 = 几乎静音。

### BGM 音量守恒铁律

- `bgm_volume` 必须 ≥ 0.10 且 ≤ 0.50。`bgm_pipeline.sh` Step 2.5 自动校验此范围。
- **禁止手动设置 `bgm_volume`**，只能由 `bgm_pipeline.sh` 通过 `bgm_gap_check.py` 查表自动确定。
- `bgm_pipeline.sh` 执行后，必须验证 `segment_durations.json` 的 `meta.bgm_volume` 在 [0.10, 0.50] 范围内。

> **Red Flag — bgm_volume < 0.10**：BGM 全程听不见，等于没有配乐。
>
> **Red Flag — 跳过 bgm_pipeline.sh**：手动写 volume 值未经过峰值间距校验。

### BGM 全程有声门禁（IRON LAW — 每次必须执行）

> **IRON LAW：** BGM 必须全程覆盖旁白时长，禁止出现后半段静音。`bgm_pipeline.sh` 内置静音尾段检测。

**bgm.wav 生成后、进入 Stage 6 之前，必须执行此门禁：**

```bash
# 获取旁白总时长
NARR_DUR=$(python -c "import json; d=json.load(open('segment_durations.json')); print(sum(s['actual_duration'] for s in d['segments']))")

# 执行全程有声门禁
python .claude/commands/clipforge/scripts/bgm_silence_check.py bgm.wav "$NARR_DUR"
```

**通过条件（全部满足才可通过）：**
- 旁白时长范围内无连续 >= 3 秒静音段（< -45 dB）
- 音频覆盖率 >= 80%

**不通过 = 禁止进入 Stage 6。** 必须更换 BGM 源文件或修复 bgm.wav 后重新检测。

> 此门禁独立于 `bgm_pipeline.sh` 的 Step 2.7，是最后一道防线。即使 bgm_pipeline.sh 已执行，也必须再跑此门禁。SubAgent 不得跳过。

## 4.3 电影音频处理（电影解读模式）

> **仅在电影解读模式触发。** 当场景中包含 `video_clip` 类型时执行。
> **依赖 `shared/movie-clips` 阶段产出的 `clip_durations.json`。**

### 旁白静音填充

`video_clip` 场景的 `narration_segment` 为 `null`，表示该场景无旁白。构建完整旁白时，需在对应位置插入与片段等长的静音。

**构建 `narration_new.mp3` 流程：**

1. 读取 `narration_segments.json`（含 `null` 段）和 `clip_durations.json`
2. 按场景顺序拼接：
   - 有旁白的场景 → 对应的 `narration_seg_{i}.mp3`
   - `video_clip` 场景 → 生成与片段等长的静音文件
3. loudnorm 标准化

```bash
# 自动构建电影模式旁白（静音填充 + 合并 + loudnorm）
python .claude/commands/clipforge/scripts/movie_narration.py
```

> **电影解读模式下，`narration_new.mp3` 替代 `narration.mp3` 嵌入 HTML `<audio>`。** 标准模式直接使用 `narration.mp3`。

### movie_audio.wav

**由 `shared/movie-clips` 阶段产出，本阶段不消费。** Stage 6 处理电影原音的三路混音。

---

## 约束声明

**Iron Law:** 旁白未经 loudnorm 校验通过 = 音频阶段未完成。BGM 音量未写入 `segment_durations.json` = 音频阶段未完成。**BGM 未通过全程有声门禁 = 音频阶段未完成。**

**TTS 分段顺序校验：** TTS 生成必须按 `narration_segments.json` 的场景顺序执行，输出的 `segment_durations.json` 中各段顺序必须与 `narration_segments.json` 一致。校验：segment_durations.json 第 N 段的 scene 字段 = narration_segments.json 第 N 个对象的 scene 字段。

| 当你产生这个念头 | 现实是 | 触发行为 |
|---|---|---|
| "TTS 分段顺序无所谓，HTML 用时间戳定位" | 顺序混乱导致审核时无法按场景检查旁白，且与 narration.srt 字幕时间轴不匹配 | 按 narration_segments.json 顺序逐个生成 |

> 本阶段的结构化约束（HARD/SOFT 规则 + Guard Red Flags）由引擎注入提供。执行前运行 `python engine/inject.py --skill stage4-audio` 获取完整约束 prompt。
