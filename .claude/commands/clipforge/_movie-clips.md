# 电影片段提取与拼接（电影解读模式条件阶段）

> 当 `narration_segments.json` 中包含 `video_clip` 类型场景时触发。提取和拼接电影片段，产出时长数据。
> **在 audio 之前执行。** audio stage 构建 `narration_new.mp3` 时需要读取本阶段产出的 `clip_durations.json` 来确定静音填充时长。
> 可与 assets stage 并行。

## 概述

从源视频文件提取指定时间码片段，拼接并添加交叉溶解转场，提取原音构建时间轴音频。

## 1. 片段提取

从 `source_clips` 逐段提取，统一编码为项目分辨率（1920x1080 横屏 或 1080x1920 竖屏）。

```bash
mkdir -p clips_16x9  # 或 clips_9x16（竖屏项目）

# 单段提取模板
ffmpeg -y -i "video/SOURCE_FILE.mp4" -ss START -to END \
  -c:v libx264 -b:v 5M -c:a aac -b:a 192k \
  -pix_fmt yuv420p -r 30 \
  "clips_16x9/clip_{scene_id}_seg_{N}.mp4"
```

**时间码格式：** 支持 `MM:SS`、`HH:MM:SS`、纯秒数。`"end"` 表示到文件结尾（省略 `-to` 参数）。

**提取后测量每段实际时长：**

```bash
ffprobe -v quiet -show_entries format=duration -of csv=p=0 "clips_16x9/clip_{scene_id}_seg_{N}.mp4"
```

## 2. 转场拼接（xfade）

多个片段用 ffmpeg `xfade` + `acrossfade` 拼接，添加交叉溶解转场消除硬切。

### 单段（无需拼接）

```bash
cp clips_16x9/clip_{scene_id}_seg_0.mp4 clips_16x9/clip_{scene_id}_xfade.mp4
```

### 两段拼接

```bash
XF=0.5
D0=$(ffprobe -v quiet -show_entries format=duration -of csv=p=0 clips_16x9/clip_{scene_id}_seg_0.mp4)
OFFSET=$(awk "BEGIN {printf \"%.2f\", $D0 - $XF}")

ffmpeg -y \
  -i clips_16x9/clip_{scene_id}_seg_0.mp4 \
  -i clips_16x9/clip_{scene_id}_seg_1.mp4 \
  -filter_complex \
    "[0:v][1:v]xfade=transition=fade:duration=$XF:offset=$OFFSET[vout];\
     [0:a][1:a]acrossfade=d=$XF[aout]" \
  -map "[vout]" -map "[aout]" \
  -c:v libx264 -b:v 5M -c:a aac -b:a 192k \
  clips_16x9/clip_{scene_id}_xfade.mp4
```

### 多段链式拼接（3 段及以上）

offset 递推计算：`offset_N = sum(D_1..D_N) - N * xfade_duration`

```bash
XF=0.5
# offset 递推：O0=D0-XF, O1=D0+D1-2*XF, O2=D0+D1+D2-3*XF ...

ffmpeg -y \
  -i clips_16x9/clip_{scene_id}_seg_0.mp4 \
  -i clips_16x9/clip_{scene_id}_seg_1.mp4 \
  -i clips_16x9/clip_{scene_id}_seg_2.mp4 \
  -i clips_16x9/clip_{scene_id}_seg_3.mp4 \
  -i clips_16x9/clip_{scene_id}_seg_4.mp4 \
  -filter_complex \
    "[0:v][1:v]xfade=transition=fade:duration=$XF:offset=$O0[v01];\
     [v01][2:v]xfade=transition=fade:duration=$XF:offset=$O1[v02];\
     [v02][3:v]xfade=transition=fade:duration=$XF:offset=$O2[v03];\
     [v03][4:v]xfade=transition=fade:duration=$XF:offset=$O3[vout];\
     [0:a][1:a]acrossfade=d=$XF[a01];\
     [a01][2:a]acrossfade=d=$XF[a02];\
     [a02][3:a]acrossfade=d=$XF[a03];\
     [a03][4:a]acrossfade=d=$XF[aout]" \
  -map "[vout]" -map "[aout]" \
  -c:v libx264 -b:v 5M -c:a aac -b:a 192k \
  clips_16x9/clip_{scene_id}_xfade.mp4
```

> **xfade 转场类型：** `fade`（交叉溶解，默认推荐）、`fadeblack`（通过黑场过渡）、`slidelr`（左滑）。`fade` 最通用。

### 拼接后测量实际时长

```bash
ACTUAL=$(ffprobe -v quiet -show_entries format=duration -of csv=p=0 clips_16x9/clip_{scene_id}_xfade.mp4)
echo "Scene {scene_id}: ${ACTUAL}s"
```

## 3. 原音提取

从每个拼接后的片段提取音频为 PCM WAV：

```bash
ffmpeg -y -i clips_16x9/clip_{scene_id}_xfade.mp4 \
  -vn -acodec pcm_s16le -ar 44100 -ac 2 \
  clips_16x9/clip_{scene_id}_audio.wav
```

## 4. movie_audio.wav 构建

将所有电影片段的音频定位到时间轴对应位置，合并为单轨。

```bash
# 读取 clip_durations.json 获取每个 video_clip 场景的 data-start
# 对每个场景生成 adelay 参数：OFFSET = data-start * 1000（毫秒）

ffmpeg -y \
  -i clips_16x9/clip_wives_audio.wav \
  -i clips_16x9/clip_sign_audio.wav \
  -filter_complex \
    "[0:a]adelay=14760|14760[a0];\
     [1:a]adelay=200120|200120[a1];\
     [a0][a1]amix=inputs=2:duration=longest:dropout_transition=0[movie]" \
  -map "[movie]" \
  -acodec pcm_s16le -ar 44100 -ac 2 \
  movie_audio.wav
```

> **adelay 单位是毫秒。** `data-start` 是秒，需乘 1000。

## 5. 时长报告

输出 `clip_durations.json`，供 Stage 6（设置 `data-duration`）和 Stage 4（静音填充）使用：

```json
[
  {"scene": "wives_video", "actual_duration": 142.29},
  {"scene": "huaan_video", "actual_duration": 13.00},
  {"scene": "code_9527_video", "actual_duration": 9.00},
  {"scene": "sign_video", "actual_duration": 16.52}
]
```

> **Stage 6 用 `actual_duration` 设置 HTML 中 `<video>` 元素的 `data-duration`。** `data-start` 由前面所有场景的 duration 累加得出。

## 6. HTML 中的视频嵌入规则

`<video>` 元素必须是 composition 根元素的直接子元素（HyperFrames 约束）：

```html
<div class="composition" data-composition-id="xxx" data-start="0">
  <div class="clip s-hook" data-start="0" data-duration="4.44">...</div>
  <video id="video-wives" src="clips_16x9/clip_wives_xfade.mp4"
         data-start="4.44" data-duration="142.29" muted playsinline></video>
  <div class="clip s-cta" data-start="146.73" data-duration="4.87">...</div>
</div>
```

- `<video>` 不需要 `class="clip"`
- 必须加 `muted playsinline`（HyperFrames 要求）
- `data-start` 和 `data-duration` 使用**秒**（不是毫秒）

## 输出文件

| 文件 | 用途 |
|------|------|
| `clips_16x9/clip_{scene_id}_seg_N.mp4` | 提取的单段片段（中间产物，可清理） |
| `clips_16x9/clip_{scene_id}_xfade.mp4` | 带转场的拼接视频（**Stage 6 引用**） |
| `clips_16x9/clip_{scene_id}_audio.wav` | 各片段音频（中间产物） |
| `movie_audio.wav` | 所有片段音频定位合并（**Stage 6 引用**） |
| `clip_durations.json` | 每个片段实际时长（**Stage 4/6 引用**） |

---

## Red Flags（停止信号）

| 信号 | 说明 |
|------|------|
| 下载片段未验证完整性 | 部分下载的片段会导致 xfade 拼接失败 |
| `clip_durations.json` 缺失或时长为 0 | audio stage 无法确定静音填充时长，时间轴会错位 |
| 片段分辨率不统一 | 混合分辨率会导致 xfade 拼接失败或画面变形 |

## Common Rationalizations（常见借口反驳）

| 借口 | 事实 |
|------|------|
| "下载成功就行" | 部分下载（文件大小不对）的片段会导致 xfade 拼接报错 |
| "片段时长预估一下" | `clip_durations.json` 必须用 ffprobe 实测，预估时长偏差级联到全片时间轴 |
| "分辨率差不多就行" | xfade 要求所有输入分辨率完全一致，差 1 像素都会报错 |
