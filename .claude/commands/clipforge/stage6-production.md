# Stage 6: 沉浸式视频制作（委托 HyperFrames）

当 `segment_durations.json` + 音频文件已存在且 `output.mp4` 不存在时触发。基于组件库装配 HTML 组合并渲染为视频。

## 6.1 项目初始化

```bash
# 创建日期目录（如不存在）+ 项目目录（纯英文路径）
mkdir -p "workspace/<YYYY>/<MM>/<DD>/<project-name>"
npx hyperframes init "workspace/<YYYY>/<MM>/<DD>/<project-name>" --example blank --non-interactive
```

项目目录结构为 `workspace/<YYYY>/<MM>/<DD>/<项目名>/`，日期格式为纯数字（如 `workspace/2026/05/18/github-trending/`）。详见 `clipforge.md` 的「项目目录结构」段。

## 6.2 读取 design.md + storyboard

Stage 2 已将视觉风格方向和故事板写入 `design.md`。**本阶段只读取，不重写。**

**读取字段和用途：**

| 字段 | 用途 |
|------|------|
| `style`, `mood` | 整体风格方向 |
| `color_direction` | 配色方案选择 |
| `storyboard.immersion_mode` | 沉浸模式 → 匹配 `stage6-components.md` 的配色速查表 |
| `storyboard.emotion_curve` | 6 拍情感强度 → 影响每个场景的视觉力度 |
| `storyboard.narrative_template` | 叙事模板 → 影响场景布局选择 |
| `storyboard.humor_style` | 幽默策略 → 是否添加 SpeechBubble 组件 |
| `storyboard.character_presence` | 角色出场 → 是否添加 CharOverlay 组件 |

**沉浸模式 → CSS 变量映射：** 从 `stage6-components.md` 的「沉浸模式配色速查」表获取具体色值，写入 `:root` CSS 变量。

```css
/* 示例：immersion_mode = "hyper-pace" */
:root {
  --bg-dark: #080818;
  --bg-mid: #001a33;
  --accent-warm: #00D4FF;
  --accent-cool: #0088CC;
  --text-primary: #ffffff;
  --text-secondary: #a0a0c0;
}
```

**设计决策链：**
1. `immersion_mode` → `stage6-components.md` 配色速查 → `:root` CSS 变量
2. 每个场景的 `emotion` → 视觉力度（粒子密度、光晕强度、动画速度）
3. `character_presence` + 每段 `character_expression` → CharOverlay 组件选择

## 6.3 音频嵌入

> **前置依赖：Stage 4 的 `segment_durations.json` 和音频文件必须已产出。**

HyperFrames 原生支持 `<audio>` 元素：自动发现、多轨混音、AAC 编码、MP4 封装。HTML 中嵌入音频后，`output.mp4` 直接包含完整音轨，无需 FFmpeg 手动合并。

### 嵌入方式

在 composition 根元素内添加 `<audio>` 元素：

```html
<div class="composition" data-composition-id="main" data-start="0">
  <!-- 旁白音轨（track 1）：单条 narration.mp3，从 t=0 播放到结束 -->
  <audio data-track-index="1" data-volume="1"
         src="narration.mp3" preload="auto"></audio>

  <!-- BGM 音轨（track 2）：bgm.wav 循环播放，音量由 Stage 4 分析结果决定 -->
  <audio data-track-index="2" data-volume="0.06"
         src="bgm.wav" preload="auto" loop></audio>

  <!-- 场景 div ... -->
  <div class="clip s-hook" data-start="0" data-duration="4.2">...</div>
  <div class="clip s-solution" data-start="4.2" data-duration="7.8">...</div>
</div>
```

### 参数说明

| 属性 | 值 | 说明 |
|------|-----|------|
| `data-track-index` | `1`（旁白）/ `2`（BGM） | HyperFrames 按轨分组混音 |
| `data-volume` | 旁白 `1`，BGM 从 `segment_durations.json` 的 `meta.bgm_volume` 读取 | HyperFrames 混音时的音量系数 |
| `loop` | 仅 BGM 添加 | BGM 循环播放直到视频结束 |
| `preload="auto"` | 必须 | 确保 HyperFrames 预加载音频 |

### 电影解读模式

电影模式使用 `narration_new.mp3`（含静音填充），并在电影片段场景使用 `<video>` 元素（见 `_movie-clips` 的嵌入规则）。

### 对齐机制

**场景连续无间隔 + 旁白连续无间隔 → 单条 `narration.mp3` 天然与场景序列对齐。** 每个 scene div 的 `data-duration` 取自 `segment_durations.json` 的对应段落实测时长，画面时长 = 语音时长，零偏移计算。

HyperFrames 的 `resolveMediaDuration()` 还会用 ffprobe 自动检测 `<audio>` 时长，`mediaDurationFloor` 确保视频时间线不短于音频。

## 6.4 编写 HTML 组合（组件装配模式）

**调用 `/hyperframes` 技能**，传入：视觉风格方向、故事板、design.md 路径、`stage6-components.md` 组件库、`segment_durations.json` 时长、`narration_segments.json` 情感标记、音频嵌入参数。

如果 Stage 5 已制备素材，将 `assets/manifest.md` 中列出的文件路径作为 prompt 上下文传入 HyperFrames，让其在 HTML 中嵌入：

- **背景图**：用 `background-image: url(assets/xxx.jpg)` 设为场景背景，加 `background-size: cover` + 半透明遮罩层保证文字可读
- **图表 SVG**：用 `<img src="assets/chart.svg">` 嵌入，或 inline SVG 以便 GSAP 控制动画
- **图标 SVG**：用 `<img src="assets/icons/xxx.svg">` 或 CSS mask 方式嵌入
- **AI 生成图**：同背景图用法，适合定制化场景

> **素材交接方式：** 读取 `assets/manifest.md`，将每个素材的文件名和用途描述写入 HyperFrames 的 prompt。HyperFrames 不解析 manifest.md，由编排者负责桥接。

### 组件装配流程

1. **读取 `narration_segments.json`** — 每段的 `scene`、`emotion`、`character_expression`、`humor_type`
2. **读取 `design.md` 的 `storyboard`** — 沉浸模式、叙事模板、情感曲线
3. **读取 `stage6-components.md`** — 选择匹配的组件模板
4. **选择组件** — 每个场景根据 `emotion` 和内容类型选择组件
5. **装配 HTML** — 按 HyperFrames composition 结构组装

### 场景 → 组件映射

| 场景类型 | 主组件 | 辅助组件 | 特效 |
|---------|--------|---------|------|
| hook | HeroCard | StarCounter | PulseOrb |
| what/how | DataViz | CompareSplit | CodeRain(背景) |
| capabilities | DataViz | TextReveal | ParticleBurst(揭示时) |
| features | DataViz | CompareSplit | PulseOrb + ParticleBurst |
| usecases | TimeLineFlow | DataViz | — |
| tech | DataViz | CodeRain(背景) | — |
| CTA | TextReveal | — | ParticleBurst(结尾) |

### 角色和幽默组件插入

- `character_expression` 非 null 的场景 → 添加 `CharOverlay` 组件（对应表情 SVG）
- `humor_type` 非 null 的场景 → 添加 `SpeechBubble` 组件（文案从 narration 提取幽默句）
- 角色定位：画面左下角，占 15-20%
- 气泡定位：画面右下角或角色上方

### 呼吸帧插入

在场景切换点插入 0.3-0.5s 的视觉呼吸：

```javascript
tl.to('.current-scene .scene-content', { scale: 1.02, duration: 0.15, ease: 'power1.inOut' })
  .to('.current-scene .scene-content', { scale: 1.0, duration: 0.15, ease: 'power1.inOut' });
```

### Canvas 粒子和 Three.js 3D

根据沉浸模式决定是否使用 3D 场景：

| 沉浸模式 | Canvas 效果 | Three.js 3D |
|---------|------------|-------------|
| hyper-pace | CodeRain + ParticleBurst | 否 |
| hidden-gem | PulseOrb | 否 |
| mega-update | ParticleBurst | ThreeScene(旋转立方体群) |
| versus | PulseOrb | 否 |
| story-time | — | 否 |
| fun-tool | ParticleBurst | 否 |

Three.js 使用 `window.__hfThreeTime` 驱动，注册到 GSAP timeline 的 seek 回调。详见 `stage6-components.md` 的 ThreeScene 组件。

### 降级触发条件

以下任一情况发生时，从 HyperFrames 委托模式降级为自行编写 HTML：

| 触发条件 | 判断方式 |
|---------|---------|
| HyperFrames 技能不可用 | Skill 工具调用 `/hyperframes` 失败或找不到技能 |
| 技能调用超时/报错 | Skill 调用返回错误，或渲染命令 `npx hyperframes` 执行失败 |
| lint 检查不通过 | 产出的 HTML 运行 `npx hyperframes lint` 报错且无法快速修复 |

降级时向用户说明原因，然后继续执行。降级自行编写时，**严格遵守以下规则**：

### 内容规则

> **以下全部规则同样适用于 HyperFrames 委托模式产出的 HTML。**

0. **内容安全规范**遵守 `clipforge/_shared-rules` 全部条款。

### 结构规则

1. `window.__timelines` 是 `{}` 不是 `[]`
2. timeline 必须 `{ paused: true }`
3. 注册 key 匹配根元素的 `data-composition-id`
4. **`data-composition-id` 只在根元素上**，scene div 不要加
5. 根元素必须有 `data-start="0"`
6. **`data-start` 和 `data-duration` 使用秒（不是毫秒）**
7. **`window.__hf` 必须定义 + GSAP timeline 必须注册**
   - 缺少 `__hf` 会导致白屏
   - `window.__timelines = {};`（空对象）会导致空白渲染
   - 必须在 `</body>` 前添加：
     ```html
     <script src="https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.5/gsap.min.js"></script>
     <script>
     window.__timelines = {};
     window.__hf = { duration: TOTAL_DURATION, seek: function(t) {} };
     const tl = gsap.timeline({paused: true});
     // 每个场景的入场动画，offset 与 data-start 对齐
     tl.from('.s-hook .title', {opacity:0, y:20, duration:0.3, ease:'power3.out'}, 0.1)
       .from('.s-what .card', {opacity:0, y:30, duration:0.3, ease:'power3.out', stagger:0.15}, HOOK_DURATION)
     ;
     window.__timelines["main"] = tl;
     </script>
     ```

### CSS 规则

8. **`.clip` 只设 `position: absolute` + 尺寸**，不要加 `opacity`
9. **禁止 `.anim-in` 等 CSS 入场动画类**（事故复盘 §7.1）
10. **画面文字禁止 HTML 实体**（事故复盘 §7.2）
11. **每个 scene-wrap 必须设 padding** `style="padding-top:120px;padding-bottom:120px;"`

### 视觉设计规则（必须遵守）

#### 视觉密度要求

每个场景的可见视觉元素**不得少于 8 个**（hook/CTA ≥ 5 个）。组件装配后检查元素数。

#### hook 场景 — 黄金 3 秒视觉

hook 必须满足全部要求：信息极简（≤3 元素）、字号最大（主标题 ≥100px）、对比最强、光晕加倍（2 个大光晕 ≥画面 50%）、发光效果、配色优雅（≤3 色）、布局精致（留白 ≥30%）、动画干脆（0.3-0.5s）。

#### 背景：渐变 + 光晕 + 网格三件套

每个场景必须同时包含：渐变背景（`linear-gradient`）、光晕装饰（1-2 个 `filter: blur(140px)` 球）、网格底纹（3%-5% 透明度）。

#### 场景独立配色

| 场景类型 | 强调色方向 |
|---------|-----------|
| hook | 暖色（金/琥珀/橙） |
| solution/top | 暖色 → 冷色过渡 |
| features/more | 冷色（翠绿/青） |
| CTA | 暖色主调 + 冷色辅 |

#### 项目卡片设计

展示项目的卡片必须包含：排名数字（≥40px）、项目名（等宽 34-42px）、中文描述（浅灰 26-32px）、语言标签（药丸 20-24px）、星数（右对齐 28-32px）。

#### CTA 场景

CTA 必须：中心光晕 + 大标题（72px+）+ 副标题（36px+）+ 3-4 个标签药丸。

#### 整体品质检查

渲染前对照清单：背景三层、光晕、卡片三栏、配色区分、CTA 完整、字号达标、安全区、居中（flexbox）、`__hf` + GSAP、音频、无 anim-in、无 HTML 实体、scene-wrap padding、视觉密度、无多余 composition。

### 动画规则

8. 入场动画时长 **0.3-0.7 秒**（"快入+静止"模式）
9. stagger 间隔 **0.2-0.3 秒**
10. easing: `power3.out` 用于入场
11. 场景间由框架 transitions 处理，不手动 exit
12. **动画设计原则：** 每个场景的动画在 1 秒内完成入场，之后保持最终状态静止直到 `data-duration` 结束。

### 字体规则

12. 优先使用 HyperFrames 内置字体映射
13. **中文渲染**：先渲染一帧验证，异常时用 `font-family: 'Inter', 'PingFang SC', 'Microsoft YaHei', sans-serif`

### 渲染规则

14. 渲染传目录路径（`.`），不传文件路径
15. 渲染前确保 `lint` 通过
16. **渲染后白屏/空白检查（必须执行）**：
    ```bash
    for ts in 1 5 15 30; do
      ffmpeg -y -i output.mp4 -ss $ts -vframes 1 -f image2 -update 1 "check_${ts}.png" 2>/dev/null
    done
    python -c "
    from PIL import Image
    for ts in [1, 5, 15, 30]:
        try:
            img = Image.open(f'check_{ts}.png')
            pixels = list(img.getdata())[:200]
            avg = [sum(c[i] for c in pixels)//len(pixels) for i in range(min(3, len(pixels[0])))]
            if all(v > 250 for v in avg):
                print(f'ERROR @{ts}s: WHITE SCREEN!')
                exit(1)
            if all(v < 30 for v in avg):
                print(f'ERROR @{ts}s: BLACK SCREEN!')
                exit(1)
            print(f'Frame @{ts}s OK')
        except Exception as e:
            print(f'Frame @{ts}s check failed: {e}')
    "
    rm -f check_*.png
    ```

## 6.5 默认竖屏

默认输出 **竖屏（1080×1920）**。如用户要求横屏再额外生成。

### 动画设计原则（HyperFrames 时长模型）

采用"快入+静止"动画策略：入场 0.3-0.7s，之后静止到场景结束。

竖屏字号参考：hero 约 80-100px、title 约 56-72px、body 约 36-44px、tag 约 26-34px。

### 竖屏垂直居中规则

**首选：flexbox 自动居中**
```css
.scene-wrap {
  position: absolute; width: 1080px; height: 1920px;
  display: flex; flex-direction: column;
  align-items: center; justify-content: center;
}
```

**禁止紧贴顶部**：不能用 `top: 80px` 等小值。场景内容容器禁止 `position: absolute` + 小 top 值。

### 平台安全区域

- 顶部危险区：上 200px
- 底部危险区：下 300px
- 安全内容区：200px ~ 1600px

## 6.6 渲染

### 渲染前检查（必须执行）

```bash
cd workspace/<YYYY>/<MM>/<DD>/<project-dir>

# 1. 确认音频文件存在
ls -la narration.mp3 bgm.mp3

# 2. 移除所有非 index.html 的 composition 文件
for f in cover.html index_with_bgm.html cover.html.bak; do
  [ -f "$f" ] && mv "$f" "$f.renderbak"
done
```

### 渲染命令

```bash
npx hyperframes lint
npx hyperframes render . --output output.mp4 --video-bitrate 5M
```

### 渲染后恢复

```bash
for f in cover.html index_with_bgm.html; do
  [ -f "$f.renderbak" ] && mv "$f.renderbak" "$f"
done
rm -f cover.html.bak.renderbak index_with_bgm.html.renderbak
```

### 渲染后音频验证

```bash
ffprobe -v quiet -show_streams -select_streams a output.mp4 | grep codec_name
ffmpeg -i output.mp4 -af "volumedetect" -f null /dev/null 2>&1 | grep volume
```

## 6.7 无 BGM 版本渲染 — 强制，不可跳过

> 产出 `output.mp4`（含 BGM）和 `output_no_bgm.mp4`（仅旁白）。缺少 `output_no_bgm.mp4` 视为 Stage 6 未完成。

```bash
cd workspace/<YYYY>/<MM>/<DD>/<project-dir>

# 1. 确认 cover.html 已移除
for f in cover.html index_with_bgm.html cover.html.bak; do
  [ -f "$f" ] && mv "$f" "$f.renderbak"
done

# 2. 备份原始 HTML
cp index.html index_with_bgm.html.bak

# 3. 移除 BGM <audio> 元素（将 data-volume 设为 "0"）
python -c "
import re
with open('index.html', 'r', encoding='utf-8') as f:
    html = f.read()
html = re.sub(
    r'(<audio\s[^>]*data-track-index=[\"'\'']2[\"'\''][^>]*data-volume=[\"\x27])([\\d.]+)([\"\x27])',
    r'\g<1>0\g<3>',
    html
)
with open('index.html', 'w', encoding='utf-8') as f:
    f.write(html)
print('BGM audio muted.')
"

# 4. 渲染无 BGM 版本
npx hyperframes render . --output output_no_bgm.mp4 --video-bitrate 5M

# 5. 恢复原始 HTML
cp index_with_bgm.html.bak index.html
rm -f index_with_bgm.html.bak

# 6. 恢复文件
for f in cover.html; do
  [ -f "$f.renderbak" ] && mv "$f.renderbak" "$f"
done
```

## 6.8 Stage 6 完成门禁

```bash
[ -s index.html ] || echo "FAIL: index.html missing"
[ -s output.mp4 ] || echo "FAIL: output.mp4 missing"
ffprobe -v quiet -show_streams output.mp4 | grep -q "codec_name=h264" || echo "FAIL: no video"
ffprobe -v quiet -show_streams output.mp4 | grep -q "codec_name=aac" || echo "FAIL: no audio"
[ -s output_no_bgm.mp4 ] || echo "FAIL: output_no_bgm.mp4 missing"
ffprobe -v quiet -show_streams output_no_bgm.mp4 | grep -q "codec_name=h264" || echo "FAIL: no video (no bgm)"
ffprobe -v quiet -show_streams output_no_bgm.mp4 | grep -q "codec_name=aac" || echo "FAIL: no audio (no bgm)"

VOL_WITH=$(ffmpeg -i output.mp4 -af "volumedetect" -f null /dev/null 2>&1 | grep -oP 'mean_volume: \K[\-\d.]+')
VOL_WITHOUT=$(ffmpeg -i output_no_bgm.mp4 -af "volumedetect" -f null /dev/null 2>&1 | grep -oP 'mean_volume: \K[\-\d.]+')
echo "BGM check: with=${VOL_WITH} dB, without=${VOL_WITHOUT} dB"

echo "=== Stage 6 完成门禁通过 ==="
```

**如果任何检查失败，修复问题后重新执行，不得跳过。**

---

## Red Flags（停止信号）

| 信号 | 说明 |
|------|------|
| 使用 CSS `.anim-in`（§7.1） | 事故：CSS `opacity: 0` 导致 HyperFrames 渲染空白 |
| 使用 HTML 实体（§7.2） | 事故：`&amp;` 等实体在无头浏览器中不解析 |
| scene-wrap 无 padding（§7.3） | 事故：内容区域在渲染中塌陷不显示 |
| GSAP timeline 未注册（§7.6） | 事故：空 `__timelines={}` 导致全片空白 |
| 音频文件不在项目目录内（§7.5） | 事故：渲染引擎只认相对路径，绝对路径 404 静音 |
| 渲染前未移除 cover.html 等（§7.4） | 事故：多个 root composition 导致渲染冲突 |
| 缺少 `output_no_bgm.mp4` | 双版本输出不可省略 |
| 白屏/黑屏渲染结果 | 检查 `window.__hf` 定义和 `data-duration` 值 |
| Canvas 粒子使用 requestAnimationFrame | HyperFrames seek 驱动，独立 rAF 循环导致画面不一致 |
| Three.js 使用 Date.now() | 必须 `__hfThreeTime`，否则 seek 回放时 3D 动画不回溯 |
| 角色遮挡核心内容 | CharOverlay 限制 15-20%，仅在角落 |
| 缺少 stage6-components.md 引用 | 组件库是装配 HTML 的参考来源 |

## Common Rationalizations（常见借口反驳）

| 借口 | 事实 |
|------|------|
| "CSS 动画更简单" | §7.1 事故：CSS `opacity: 0` 入场动画永远不会执行 |
| "`&amp;` 是标准 HTML" | §7.2 事故：无头浏览器对实体字符解析不可靠 |
| "不用 padding" | §7.3 事故：缺少 padding 导致内容区域塌陷 |
| "GSAP 会自动注册" | §7.6 事故：必须显式 `window.__timelines["main"] = tl` |
| "绝对路径也能找到" | §7.5 事故：只认项目目录内相对路径 |
| "cover.html 不影响" | §7.4 事故：含 `data-composition-id` 的 HTML 都会导致冲突 |
| "Canvas 用 rAF 更流畅" | HyperFrames 逐帧 seek 驱动，rAF 与 seek 不同步会导致闪烁 |
| "Three.js 用 performance.now()" | seek 回放时 `performance.now()` 不回溯，3D 动画不倒放 |
| "组件太多不需要都读" | `stage6-components.md` 是组件装配的唯一参考，不读就不知道有哪些组件 |
