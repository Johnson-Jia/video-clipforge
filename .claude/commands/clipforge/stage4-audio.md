# Stage 4: 音频生产（TTS + BGM）

当 `narration_segments.json` 已存在且 `segment_durations.json` 不存在时触发。生成 TTS 旁白音频和背景配乐，产出逐段时长数据。

## 4.1 旁白 TTS（分段模式）

### 分段生成流程

读取 Stage 3 产出的 `narration_segments.json`，逐段生成 TTS：

```bash
# 逐段生成 TTS + SRT
python -c "
import json, subprocess, os

with open('narration_segments.json', 'r', encoding='utf-8') as f:
    segments = json.load(f)

# === TTS 参数记录（写入 segment_durations.json 的 meta 字段） ===
VOICE = '$VOICE'       # 替换为实际声音
RATE = '$RATE'         # 替换为实际语速

durations = []
for i, seg in enumerate(segments):
    text_file = f'narration_seg_{i}.txt'
    mp3_file = f'narration_seg_{i}.mp3'
    srt_file = f'narration_seg_{i}.srt'

    with open(text_file, 'w', encoding='utf-8') as f:
        f.write(seg['text'])

    subprocess.run([
        'python', '-m', 'edge_tts',
        '-f', text_file,
        '-v', VOICE,
        '--rate', RATE,
        '--write-media', mp3_file,
        '--write-subtitles', srt_file
    ], check=True)

    # 测量实际时长
    result = subprocess.run([
        'ffprobe', '-v', 'quiet', '-show_entries', 'format=duration',
        '-of', 'csv=p=0', mp3_file
    ], capture_output=True, text=True)
    dur = float(result.stdout.strip())
    durations.append({'scene': seg['scene'], 'actual_duration': round(dur, 2)})
    print(f'[Seg {i}] {seg[\"scene\"]}: {dur:.2f}s')

# 输出每段实际时长，供 Stage 6 使用
output = {
    'meta': {'voice': VOICE, 'rate': RATE},
    'segments': durations
}
with open('segment_durations.json', 'w', encoding='utf-8') as f:
    json.dump(output, f, indent=2, ensure_ascii=False)
print(f'Total: {sum(d[\"actual_duration\"] for d in durations):.2f}s')
print(f'Voice: {VOICE}, Rate: {RATE}')
"
```

> **`segment_durations.json` 格式为 `{meta: {voice, rate}, segments: [...]}`。** Stage 6 读取时长时取 `segments[i].actual_duration`。

### 合并为完整旁白（HTML 音频源）

合并后的 `narration.mp3` 将作为 `<audio>` 元素嵌入 HTML，由 HyperFrames 自动混入视频。

```bash
# 生成 concat 文件列表
echo "" > concat.txt
for i in $(seq 0 $(($(ls narration_seg_*.mp3 | wc -l) - 1))); do
    echo "file 'narration_seg_${i}.mp3'" >> concat.txt
done

# 合并所有片段为完整旁白
ffmpeg -y -f concat -safe 0 -i concat.txt -c copy narration.mp3

# 合并 SRT 字幕（重新编号时间戳）
python -c "
import re, glob

srt_files = sorted(glob.glob('narration_seg_*.srt'))
offset = 0
all_lines = []
idx = 1

for sf in srt_files:
    with open(sf, 'r', encoding='utf-8') as f:
        content = f.read().strip()
    if not content:
        continue
    blocks = content.split('\n\n')
    for block in blocks:
        lines = block.strip().split('\n')
        if len(lines) >= 3:
            time_match = re.match(r'(\d{2}:\d{2}:\d{2},\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2},\d{3})', lines[1])
            if time_match:
                def add_offset(t):
                    h, m, s = t.replace(',', '.').split(':')
                    return offset + int(h)*3600 + int(m)*60 + float(s)
                start = add_offset(time_match.group(1))
                end = add_offset(time_match.group(2))
                def fmt(t):
                    h = int(t // 3600); m = int((t % 3600) // 60); s = t % 60
                    return f'{h:02d}:{m:02d}:{int(s):02d},{int((s%1)*1000):03d}'
                all_lines.append(f'{idx}\n{fmt(start)} --> {fmt(end)}\n' + '\n'.join(lines[2:]))
                idx += 1
    # 用 ffprobe 获取本段时长作为偏移
    import subprocess
    mp3 = sf.replace('.srt', '.mp3')
    r = subprocess.run(['ffprobe', '-v', 'quiet', '-show_entries', 'format=duration', '-of', 'csv=p=0', mp3], capture_output=True, text=True)
    offset += float(r.stdout.strip())

with open('narration.srt', 'w', encoding='utf-8') as f:
    f.write('\n\n'.join(all_lines))
"
```

### 音量标准化

**对合并后的 `narration.mp3` 执行 loudnorm 标准化：**

```bash
# loudnorm 标准化（两遍处理）
ffmpeg -i narration.mp3 -af "loudnorm=I=-16:TP=-2:LRA=11:print_format=json" -f null /dev/null 2>&1 | tail -12 > loudnorm_stats.json
ffmpeg -y -i narration.mp3 -af "loudnorm=I=-16:TP=-2:LRA=11:measured_I=$(jq -r '.input_i' loudnorm_stats.json):measured_TP=$(jq -r '.input_tp' loudnorm_stats.json):measured_LRA=$(jq -r '.input_lra' loudnorm_stats.json):measured_thresh=$(jq -r '.input_thresh' loudnorm_stats.json):linear=true" narration_norm.mp3 && mv narration_norm.mp3 narration.mp3
```

> 标准化后无需重新测量分段时长——loudnorm 只改变响度不改变时长。

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

> **如果分类配置中指定了 `audio.default_voice` 和 `audio.default_rate`，优先使用分类配置。** 未指定时按以下规则选择。

> **禁止使用播报腔音色。** 短视频需要"我在跟你聊/分析"的叙事感，不是"我在念稿子"的播报感。`zh-CN-YunyangNeural`（新闻主播风）禁止用于任何短视频项目。

| 场景类型 | 推荐声音 | 特点 |
|---------|---------|------|
| **默认首选** | `zh-CN-YunjianNeural` | 有叙事张力和穿透力，适合观点输出、安利种草、行业分析 |
| **科普/教程** | `zh-CN-YunxiNeural` | 沉稳温和，适合纯知识讲解（无观点输出） |
| **活泼/轻松** | `zh-CN-XiaoxiaoNeural` | 女声活力，适合生活类 |

### 语速建议

> **如果分类配置中指定了 `audio.default_rate`，优先使用分类配置。** 未指定时按以下表格选择。

| 内容类型 | 建议速率 |
|---------|---------|
| 短视频（25-60s） | `+25%` ~ `+30%` |
| 深度解读（3-10min） | `+10%` ~ `+15%` |
| 教程讲解 | `+10%` ~ `+15%` |

## 4.2 配乐

### 来源优先级（唯一权威）

| 优先级 | 来源 | 说明 |
|--------|------|------|
| **1** | 用户提供 | 用户自带音乐文件，优先使用 |
| **2** | BGM 素材库 | 从 `workspace/bgm/` 选取已有 BGM（**首选**） |
| **3** | 音乐库下载 | yt-dlp 从 YouTube 下载无版权音乐，存入 BGM 素材库 |
| **4** | 音乐库搜索 | Pixabay / Mixkit / 爱给网 的热门曲目 |
| **5** | AI 二创 | MusicGen 基于现有爆火音乐二次创作（**必须有参考样本**，无样本时跳过此来源） |

> **BGM 素材库**（`workspace/bgm/`）集中管理所有已下载的 BGM。下载新 BGM 时同步存入此目录，方便后续项目复用。

### 情绪→搜索关键词映射

| 情绪 | YouTube 搜索词 | Pixabay 搜索词 |
|------|---------------|---------------|
| 科技/赛博 | `royalty free cyberpunk music` | `cyberpunk`, `synthwave` |
| 激励/振奋 | `royalty free upbeat corporate` | `upbeat technology` |
| 神秘/悬疑 | `royalty free dark ambient` | `mysterious`, `suspense` |
| 温暖/治愈 | `royalty free warm piano` | `warm`, `acoustic` |
| 史诗/震撼 | `royalty free epic orchestral` | `epic`, `cinematic` |
| 欢快/轻松 | `royalty free happy pop` | `happy`, `fun` |
| 国风/传统 | `royalty free chinese traditional music` | `chinese`, `traditional`, `guzheng` |
| 玄幻/神秘 | `royalty free ethereal ambient` | `ethereal`, `fantasy`, `mystical` |

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

> **详细流程见 `clipforge/_bgm-pixabay`。** 以下为快速操作指引。

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

**主题→搜索词映射（对应 HyperFrames 视觉主题）：**

| 主题名 | 搜索词 | 主题名 | 搜索词 |
|--------|--------|--------|--------|
| `bold-energetic` | `energetic upbeat` | `monochrome` | `minimal ambient piano` |
| `clean-corporate` | `corporate clean business` | `nature-earth` | `nature acoustic folk` |
| `dark-premium` | `dark cinematic dramatic` | `neon-electric` | `synthwave electronic neon` |
| `jewel-rich` | `luxury elegant cinematic` | `pastel-soft` | `soft gentle ambient calm` |
| — | — | `warm-editorial` | `warm acoustic cozy` |

> **批量补全：** 对每个主题执行「导航→提取→下载」三步，每个主题 5 首。详见 `clipforge/_bgm-pixabay`。

### 方法 C：其他音乐库

Mixkit / 爱给网等浏览试听后手动下载。

```bash
# 下载后截取
ffmpeg -i source.mp3 -ss 0:10 -t 0:30 -af "afade=t=in:d=2,afade=t=out:st=27:d=3" bgm.wav
```

### BGM 预处理 + 音量分析（必须执行）

**核心原则：旁白清晰度 > 一切。** BGM 宁可偏小不可偏大。

```bash
# 检查时长和格式
ffprobe -v quiet -show_entries format=duration -of csv=p=0 bgm.wav

# 分析 BGM 原始音量（必须执行，结果写入 segment_durations.json）
ffmpeg -i bgm.wav -af "volumedetect" -f null /dev/null 2>&1 | grep volume
```

根据 BGM 的 `mean_volume` 选择混音音量值（Stage 6 ffmpeg `amix` filter 的 `volume` 参数）：

> **混音方式已从 HyperFrames `data-volume` 切换为 ffmpeg `amix` filter。** ffmpeg 的 volume 值需要比旧 HyperFrames 值更高，因为两个引擎对音量的处理方式不同。

| BGM mean_volume | 推荐 volume | 说明 |
|----------------|------------|------|
| > -15 dB（很响） | `0.08`     | 响度高的配乐需较大衰减 |
| -15 ~ -20 dB | `0.10`     | 中等偏响 |
| -20 ~ -25 dB | `0.15`     | 中等音量（最常见）→ **默认推荐** |
| -25 ~ -30 dB | `0.18`     | 偏安静 |
| < -30 dB（很安静） | `0.22`     | 需要较大提升 |

**将推荐 volume 值写入 `segment_durations.json`：**

```bash
BGM_VOL=0.15  # 根据上面查表结果替换，默认推荐 0.15

python -c "
import json
with open('segment_durations.json', 'r') as f:
    data = json.load(f)
data['meta']['bgm_volume'] = $BGM_VOL
with open('segment_durations.json', 'w') as f:
    json.dump(data, f, indent=2, ensure_ascii=False)
print(f'bgm_volume={data[\"meta\"][\"bgm_volume\"]}')
"
```

> **不要对 `bgm.wav` 做 gain/volume 处理。** 保持原始音量，Stage 6 的 `<audio data-volume>` 控制混音时的衰减。预处理会破坏原始音量参考。
>
> **双重衰减防护**：如果 Stage 4 对 bgm.wav 做了音量衰减（如 `-af volume=0.08`），然后 Stage 6 的 `data-volume` 再乘一次，实际音量 = 0.08 × 0.08 = 0.0064（几乎听不到）。这是一个已知的致命 bug。唯一正确的做法是：bgm.wav 保持原始音量，所有音量控制通过 HTML `data-volume` 完成。

### BGM 音量守恒校验（必须执行）

生成 `bgm.wav` 后，确认文件未被意外衰减：

```bash
# 检查 bgm.wav 音量是否在正常范围（原始 BGM 通常 -15 ~ -30 dB）
BGM_MEAN=$(ffmpeg -i bgm.wav -af "volumedetect" -f null /dev/null 2>&1 | grep mean_volume | grep -oP '[\-\d.]+(?= dB)')
echo "bgm.wav mean_volume: ${BGM_MEAN} dB"

# 如果 mean_volume < -35 dB，说明 bgm.wav 已被意外衰减，必须重新生成
if [ "$(echo "$BGM_MEAN < -35" | bc 2>/dev/null)" -eq 1 ]; then
  echo "ERROR: bgm.wav 音量异常偏低 (${BGM_MEAN} dB)，疑似被预衰减。必须从原始来源重新生成。"
  echo "正确做法：bgm.wav 保持原始音量，Stage 6 通过 data-volume 控制混音。"
fi
```

### BGM 循环规则（必须执行）

**当 BGM 时长 < 视频时长时，必须用 FFmpeg 将 BGM 循环扩展至覆盖完整视频时长。** 不要依赖 HTML `<audio loop>` 属性——HyperFrames 对 `loop` 属性的支持不可靠。

```bash
# 获取旁白总时长（即视频时长）
NARRATION_DUR=$(ffprobe -v quiet -show_entries format=duration -of csv=p=0 narration.mp3)

# 获取 BGM 时长
BGM_DUR=$(ffprobe -v quiet -show_entries format=duration -of csv=p=0 bgm.wav)

# 如果 BGM 短于旁白，循环扩展（+1 秒余量用于淡出）
if [ "$(echo "$BGM_DUR < $NARRATION_DUR" | bc)" -eq 1 ]; then
  TARGET_DUR=$(echo "$NARRATION_DUR + 1" | bc)
  ffmpeg -y -stream_loop -1 -i bgm.wav -t "$TARGET_DUR" -c:a pcm_s16le -ar 48000 bgm_looped.wav
  mv bgm.wav bgm_orig.wav
  mv bgm_looped.wav bgm.wav
  echo "BGM 已循环: ${BGM_DUR}s → ${TARGET_DUR}s"
fi
```

> **原理：** `-stream_loop -1` 无限循环输入流，`-t` 限制输出时长到目标值。循环后的 BGM 是一个完整的 WAV 文件，HyperFrames 渲染时无需任何循环支持。

## 4.3 电影音频处理（电影解读模式）

> **仅在电影解读模式触发。** 当场景中包含 `video_clip` 类型时执行。
> **依赖 `_movie-clips` 阶段产出的 `clip_durations.json`。**

### 旁白静音填充

`video_clip` 场景的 `narration_segment` 为 `null`，表示该场景无旁白。构建完整旁白时，需在对应位置插入与片段等长的静音。

**构建 `narration_new.mp3` 流程：**

1. 读取 `narration_segments.json`（含 `null` 段）和 `clip_durations.json`
2. 按场景顺序拼接：
   - 有旁白的场景 → 对应的 `narration_seg_{i}.mp3`
   - `video_clip` 场景 → 生成与片段等长的静音文件
3. loudnorm 标准化

```bash
# 为每个 video_clip 场景生成静音文件
# DURATION 从 clip_durations.json 中对应场景的 actual_duration 读取
ffmpeg -y -f lavfi -i "anullsrc=r=44100:cl=stereo" -t $DURATION -c:a libmp3lame silence_{scene_id}.mp3

# 按场景顺序生成 concat 文件列表
echo "file 'narration_seg_0.mp3'"  > concat_new.txt
echo "file 'narration_seg_1.mp3'" >> concat_new.txt
echo "file 'silence_wives_video.mp3'" >> concat_new.txt
echo "file 'narration_seg_2.mp3'" >> concat_new.txt
echo "file 'silence_huaan_video.mp3'" >> concat_new.txt
# ...按实际场景顺序排列

# 合并为完整旁白（含静音填充）
ffmpeg -y -f concat -safe 0 -i concat_new.txt -c copy narration_new.mp3

# loudnorm 标准化
ffmpeg -i narration_new.mp3 -af "loudnorm=I=-16:TP=-2:LRA=11:print_format=json" -f null /dev/null 2>&1 | tail -12 > loudnorm_stats.json
ffmpeg -y -i narration_new.mp3 -af "loudnorm=I=-16:TP=-2:LRA=11:measured_I=$(jq -r '.input_i' loudnorm_stats.json):measured_TP=$(jq -r '.input_tp' loudnorm_stats.json):measured_LRA=$(jq -r '.input_lra' loudnorm_stats.json):measured_thresh=$(jq -r '.input_thresh' loudnorm_stats.json):linear=true" narration_new_norm.mp3 && mv narration_new_norm.mp3 narration_new.mp3
```

> **电影解读模式下，`narration_new.mp3` 替代 `narration.mp3` 嵌入 HTML `<audio>`。** 标准模式直接使用 `narration.mp3`。

### movie_audio.wav

**由 `_movie-clips` 阶段产出，本阶段不消费。** Stage 6 处理电影原音的三路混音。

---

## Red Flags（停止信号）

| 信号 | 说明 |
|------|------|
| 用 `estimated_duration` 替代 `actual_duration` | 事故：预估偏差累计 8 秒导致视频出现空白 |
| BGM 音量未写入 `segment_durations.json` | 此文件是 BGM 音量传递到 Stage 6 的唯一通道 |
| `narration.mp3` 未做 loudnorm | 不标准化会影响最终混音质量，部分段过响或过轻 |
| 视频开头做了音频淡入 | §5.3 前 3 秒禁止淡入，削弱 hook 冲击力 |
| `segment_durations.json` 缺失 | Stage 6 无法设置 `data-duration`，渲染必失败 |

## Common Rationalizations（常见借口反驳）

| 借口 | 事实 |
|------|------|
| "预估时长够用了" | 事故：预估偏差累计 8 秒导致全片空白。必须用分段 TTS 实测 `actual_duration` |
| "BGM 音量后面再调" | `segment_durations.json` 是唯一传递通道，不写入 Stage 6 就无法控制音量 |
| "听起来差不多就行" | loudnorm 标准化不是"差不多"，是防止部分段过响或过轻影响混音 |
| "开头加个淡入更自然" | §5.3 前 3 秒禁止淡入。淡入让钩子时刻声音渐强，直接削弱冲击力 |
