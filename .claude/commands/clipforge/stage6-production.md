# Stage 6: 视频制作（委托 HyperFrames）

当 `segment_durations.json` + 音频文件已存在且 `output.mp4` 不存在时触发。编写 HTML 组合并渲染为视频。

## 6.1 项目初始化

```bash
# 创建日期目录（如不存在）+ 项目目录（纯英文路径）
mkdir -p "workspace/<YYYY>/<MM>/<DD>/<project-name>"
npx hyperframes init "workspace/<YYYY>/<MM>/<DD>/<project-name>" --example blank --non-interactive
```

项目目录结构为 `workspace/<YYYY>/<MM>/<DD>/<项目名>/`，日期格式为纯数字（如 `workspace/2026/05/18/github-trending/`）。详见 `clipforge.md` 的「项目目录结构」段。

## 6.2 读取 design.md（由 Stage 2 写入）

Stage 2 已将视觉风格方向写入 `design.md`。**本阶段只读取方向，不重写。** 根据 `design.md` 的 `style`、`mood`、`color_direction` 字段，结合本文件内置的场景配色规则，确定每个场景的具体配色方案。

**设计决策链：**
1. `design.md` 的 `style` 和 `color_direction` → 确定整体风格方向（如"科技赛博"、"暗色暗调"）
2. 本文件的场景独立配色规则 → 确定 hook 暖色、features 冷色、CTA 暖冷搭配
3. 两者的交集 → 每个场景的具体色值

```css
/* 示例：根据 design.md "科技赛博" 方向 + 场景配色规则 */
:root {
  --bg-dark: #080818;        /* 来自 color_direction: 深色暗调 */
  --bg-mid: #12122e;         /* 同上 */
  --accent-warm: #f0b429;    /* 来自 color_direction: 金色/琥珀 */
  --accent-cool: #00e5a0;    /* 来自 color_direction: 霓虹青/翠绿 */
  --text-primary: #ffffff;
  --text-secondary: #a0a0c0;
}
```

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

## 6.4 编写 HTML 组合

**调用 `/hyperframes` 技能**，传入：视觉风格方向、场景脚本、design.md 路径、输出尺寸、`segment_durations.json` 中的实际时长、音频嵌入参数。

如果 Stage 5 已制备素材，将 `assets/manifest.md` 中列出的文件路径作为 prompt 上下文传入 HyperFrames，让其在 HTML 中嵌入：

- **背景图**：用 `background-image: url(assets/xxx.jpg)` 设为场景背景，加 `background-size: cover` + 半透明遮罩层保证文字可读
- **图表 SVG**：用 `<img src="assets/chart.svg">` 嵌入，或 inline SVG 以便 GSAP 控制动画
- **图标 SVG**：用 `<img src="assets/icons/xxx.svg">` 或 CSS mask 方式嵌入
- **AI 生成图**：同背景图用法，适合定制化场景

> **素材交接方式：** 读取 `assets/manifest.md`，将每个素材的文件名和用途描述写入 HyperFrames 的 prompt。HyperFrames 不解析 manifest.md，由编排者负责桥接。

### 降级触发条件

以下任一情况发生时，从 HyperFrames 委托模式降级为自行编写 HTML：

| 触发条件 | 判断方式 |
|---------|---------|
| HyperFrames 技能不可用 | Skill 工具调用 `/hyperframes` 失败或找不到技能 |
| 技能调用超时/报错 | Skill 调用返回错误，或渲染命令 `npx hyperframes` 执行失败 |
| lint 检查不通过 | 产出的 HTML 运行 `npx hyperframes lint` 报错且无法快速修复 |

降级时向用户说明原因（如"HyperFrames 渲染暂不可用，将手动编写 HTML"），然后继续执行。

降级自行编写时，**严格遵守以下规则**：

### 内容规则

> **以下全部规则（内容、结构、CSS、视觉设计、动画、字体、渲染）同样适用于 HyperFrames 委托模式产出的 HTML。** 无论哪种模式，最终 HTML 都必须满足这些标准。

0. **内容安全规范**（措辞、画面文字、CTA、URL）遵守 `clipforge/_shared-rules` 全部条款。
   - 视频内不放 URL（§4）；画面文字以中文为主（§2）；CTA 不写具体时间（§3）；自然分享口吻，不点名品牌（§1）

### 结构规则

1. `window.__timelines` 是 `{}` 不是 `[]`
2. timeline 必须 `{ paused: true }`
3. 注册 key 匹配根元素的 `data-composition-id`
4. **`data-composition-id` 只在根元素上**，scene div 不要加
5. 根元素必须有 `data-start="0"`
6. **`data-start` 和 `data-duration` 使用秒（不是毫秒）**
   - 正确：`data-start="4" data-duration="12"`（4 秒开始，持续 12 秒）
   - 禁止：`data-start="4000" data-duration="12000"`（会被理解为 4000 秒）
   - 小数也用秒：`data-duration="2.304"`
7. **`window.__hf` 必须定义 + GSAP timeline 必须注册（白屏/空白防护）**
   - HyperFrames 依赖 `__hf` 对象驱动渲染时序，**缺少 `__hf` 会导致白屏**
   - `window.__timelines = {};`（空对象）会导致**空白渲染**——HyperFrames 等待 `window.__timelines["main"]` 注册超时
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
       // ... 继续为每个场景添加入场动画
     ;
     window.__timelines["main"] = tl;
     </script>
     ```
   - `TOTAL_DURATION` = 根元素 `data-duration` 的值
   - GSAP `.from()` 动画 offset 必须与各场景的 `data-start` 值对齐

### CSS 规则

7. **`.clip` 只设 `position: absolute` + 尺寸**，不要加 `opacity`
   - HyperFrames 框架通过 `data-start`/`data-duration` 自动管理 clip 可见性
   - 手动在 `.clip` 上设 `opacity: 0` 会导致黑屏
   - 正确的 `.clip` CSS：`position: absolute; top: 0; left: 0; width: 1080px; height: 1920px;`

8. **禁止 `.anim-in` 等 CSS 入场动画类**（事故复盘 §7.1）
   - 任何在 CSS 中将元素设为 `opacity: 0` 的入场机制**都禁止使用**
   - HyperFrames 基于 seek 驱动渲染，不触发 CSS animation/transition
   - 入场动画由 GSAP `.from({opacity:0})` 实现（见结构规则 §7），元素 CSS 默认 `opacity:1`
   - GSAP timeline 在 HyperFrames 中可靠执行，CSS 动画不可靠

9. **画面文字禁止 HTML 实体**（事故复盘 §7.2）
   - 禁止使用 `&#9733;`、`&#10084;` 等 HTML 实体
   - 改用 Unicode 字符直接输入（如 `★`、`❤`）或纯文本

10. **每个 scene-wrap 必须设 padding**（事故复盘 §7.3）
    - 所有 `.scene-wrap` 必须显式设置 `style="padding-top:120px;padding-bottom:120px;"`
    - 缺少 padding 可能导致内容区域在渲染中塌陷

### 视觉设计规则（必须遵守）

以下规则确保视频画面不是"能看就行"的简陋排版，而是有视觉冲击力的精美画面。**每条规则都是硬性要求，不允许省略。**

#### 视觉密度要求（每场景最少元素数）

> **"画面空"是观众划走的第二大原因（仅次于钩子不吸引）。** 每个场景必须有足够的视觉元素支撑。

每个场景的可见视觉元素（文字、卡片、标签、图标、数据面板、分隔线、徽章等）**不得少于 8 个**：

| 场景类型 | 最低元素数 | 推荐范围 | 典型元素组合 |
|---------|-----------|---------|------------|
| hook | 5-7 | 5-8 | 主标题 + 副标题 + 徽章 + 2个光晕 + 网格背景 |
| what/how | 8-10 | 8-15 | 标题 + 3-4张卡片 + 标签 + 分隔线 + 数据面板 |
| capabilities/features | 10-15 | 10-20 | 标题 + 6-8个标签/药丸 + 图标 + 分组标题 + 对比面板 |
| usecases | 8-12 | 8-15 | 标题 + 3-4张用例卡片 + 图标 + 副标题 |
| tech | 8-12 | 8-15 | 标题 + 技术栈标签/图标 + 架构图 + 数据面板 |
| compare | 10-15 | 10-20 | 标题 + 两列对比卡片 + 数据 + 标签 + 高亮标记 |
| CTA | 5-7 | 5-8 | 主标题 + 副标题 + 3-4个标签药丸 + 光晕 + 网格 |

**"2-3 个文字元素就交差"的场景必须重写。** 增加视觉元素的方法：
- 将纯文字拆为"标签 + 描述"的组合卡片
- 为数据项添加带颜色的标签药丸（pill badge）
- 添加分组标题和分隔线
- 在列表项旁添加小图标或编号徽章
- 使用多列网格布局代替单列列表

#### hook 场景 — 黄金 3 秒视觉（最高优先级）

> **hook 是全片视觉最强烈的画面。** 用户划走一个视频只需 1-3 秒，hook 必须在视觉上"砸"到用户。

hook 场景必须满足以下**全部**要求，缺一不可：

| 要求 | 标准 | 原因 |
|------|------|------|
| 信息极简 | ≤ 3 个视觉元素（如：1 个主标题 + 1 个副标题 + 1 个徽章） | 信息越多越不容易被记住 |
| 字号最大 | 主标题 ≥ 100px，副标题 ≥ 48px | 远大于其他场景，一眼抓住 |
| 对比最强 | 主标题纯白/亮色 + 深色背景，对比度 > 15:1 | 暗背景下白字最醒目 |
| 光晕加倍 | 2 个大光晕球，尺寸 ≥ 画面宽度 50%，opacity 20%-30% | 营造氛围感和深度 |
| 发光效果 | 主标题加 `text-shadow: 0 0 40px <accent-color>` | 文字自带光晕，视觉聚焦 |
| 配色优雅 | 主色 + 强调色双色体系，≤ 3 种颜色，禁止荧光色堆砌 | 颜色过多 = 杂乱 = 廉价感 |
| 布局精致 | 元素间距均匀、对齐严整、画面留白 ≥ 30% | 留白 = 呼吸感 = 高级感 |
| 动画干脆 | 0.3-0.5 秒入场完成，easing `power3.out` | 慢吞吞 = 用户已划走 |

```html
<!-- hook 场景参考结构 -->
<div class="clip s-hook" data-start="0" data-duration="4.2">
  <div class="hook-wrap">
    <div class="glow glow-warm"></div>    <!-- 暖色大光晕 -->
    <div class="glow glow-cool"></div>    <!-- 冷色大光晕 -->
    <div class="grid-bg"></div>
    <div class="badge">今日 GitHub 榜单</div>
    <div class="hook-title">AI 项目<span class="accent">直接霸榜</span></div>
    <div class="hook-sub">8 个热门 · 6 个 AI 相关</div>
  </div>
</div>
```

```css
/* hook 场景关键样式 */
.hook-wrap {
  display: flex; flex-direction: column;
  align-items: center; justify-content: center;
  width: 100%; height: 100%;
}
.hook-title {
  font-size: 120px; font-weight: 900; color: #fff;
  letter-spacing: -2px; line-height: 1.15;
  text-shadow: 0 0 60px rgba(240,180,41,0.5);
}
.hook-sub {
  font-size: 48px; font-weight: 600;
  color: var(--accent-cool); margin-top: 48px;
}
```

#### 背景：渐变 + 光晕 + 网格三件套

每个场景必须同时包含以下三层背景：

1. **渐变背景**：场景容器必须使用 `linear-gradient` 渐变背景，不能用纯色。
   ```css
   /* 正确：渐变背景 */
   background: linear-gradient(180deg, #080818 0%, #12122e 50%, #080818 100%);
   /* 禁止：纯色背景 */
   background: #0d1117;  /* ✗ 太扁平，无氛围感 */
   ```

2. **光晕装饰**：每个场景必须有 1-2 个大尺寸模糊光晕球（`border-radius: 50%; filter: blur(140px)`），营造科技氛围。光晕颜色使用场景强调色，透明度 15%-25%，尺寸 ≥ 画面宽度的 40%。
   ```css
   .glow {
     position: absolute; width: 500px; height: 500px;
     background: #00e5a0; border-radius: 50%; filter: blur(140px);
     opacity: 0.2; top: 300px; right: -80px;
   }
   ```

3. **网格底纹**：全屏覆盖极低透明度网格线（3%-5%），增加科技质感。
   ```css
   .grid-bg {
     position: absolute; width: 100%; height: 100%;
     background-image:
       linear-gradient(rgba(0,229,160,0.04) 1px, transparent 1px),
       linear-gradient(90deg, rgba(0,229,160,0.04) 1px, transparent 1px);
     background-size: 40px 40px;
     pointer-events: none;
   }
   ```

#### 场景独立配色

每个场景类型有自己的强调色，不能全片只用一种颜色：

| 场景类型 | 强调色方向 | 用途 |
|---------|-----------|------|
| hook | 暖色（金/琥珀/橙） | 数字、标签、光晕 |
| solution/top | 暖色 → 冷色过渡 | 项目卡片的星级用冷色 |
| features/more | 冷色（翠绿/青） | 卡片边框、星级 |
| CTA | 暖色主调 + 冷色辅 | 标题用暖色，副标题用冷色 |

#### 项目卡片设计

展示项目的卡片必须包含以下元素，**不能省略**：

1. **排名数字**：左对齐的大号加粗排名（如 `1`、`2`），强调色，最小字号 40px
2. **项目名**：等宽字体，白色/亮色，字号 34-42px
3. **中文描述**：无衬线字体，浅灰色（`text_secondary`），字号 26-32px
4. **语言标签**：小号药丸标签（如 `Rust`、`TypeScript`），强调色半透明背景，字号 20-24px
5. **星数**：右对齐，强调色，字号 28-32px

```html
<!-- 标准卡片结构 -->
<div class="project-card">
  <div class="rank">1</div>
  <div class="info">
    <div class="name">oven-sh/bun</div>
    <div class="desc">极速 JS 运行时，打包测试一体化</div>
    <div class="lang-badge">Rust</div>
  </div>
  <div class="stars">+910</div>
</div>
```

#### 迷你卡片（more 场景）

使用左边框条 + 三栏（排名 | 信息 | 星数）的紧凑布局：

```css
.mini-card {
  border-left: 4px solid #00e5a0;  /* 左边框条 = 视觉节奏 */
  display: flex; align-items: center; gap: 20px;
}
```

#### CTA 场景设计

CTA 不能只有纯文字，必须包含：

1. **中心光晕**：画面中央一个大的强调色模糊光晕
2. **大标题**：主强调色，字号 72px+，粗体
3. **副标题**：辅助强调色，字号 36px+
4. **标签药丸**：3-4 个小号圆角标签（从分类配置的 `delivery.hashtags` 或根据内容生成），半透明背景

```html
<div class="cta-title">关注我<br><span class="accent">每天更新</span></div>
<div class="cta-sub">{{内容主题}}</div>
<div class="tags">
  <div class="tag">#标签1</div>
  <div class="tag">#标签2</div>
  <div class="tag">#标签3</div>
  <div class="tag">#标签4</div>
</div>
```

#### 整体品质检查

渲染前对照以下清单，**任何一项不满足都要修改 HTML**：

| 检查项 | 标准 |
|--------|------|
| 背景 | 每个场景都是渐变 + 光晕 + 网格三层 |
| 光晕 | 每个场景有 ≥1 个大尺寸模糊光晕球 |
| 卡片 | 有排名数字 + 语言标签 + 星数三栏 |
| 配色 | 不同场景类型使用不同强调色 |
| CTA | 有光晕 + 大标题 + 副标题 + 标签药丸 |
| 字号 | hero ≥ 80px，项目名 ≥ 34px，描述 ≥ 26px |
| 安全区 | 核心内容在 200px-1600px 范围内 |
| **居中** | **所有内容元素使用 flexbox 文档流，禁止 `position: absolute` + 固定 `top` 值** |
| **__hf + GSAP** | **`window.__hf` 必须定义 + `window.__timelines["main"]` 必须注册 GSAP timeline** |
| **音频** | **`<audio>` 元素存在且 `data-volume` 正确** |
| **无 anim-in** | **禁止 `.anim-in` 或任何 CSS `opacity: 0` 入场类** |
| **无 HTML 实体** | **画面文字中无 `&#XXXX;` 实体，改用 Unicode 直接输入** |
| **scene-wrap padding** | **每个场景内容容器必须有 `padding-top/padding-bottom: 120px`** |
| **视觉密度** | **每场景可见元素 ≥ 8 个（hook/CTA ≥ 5 个），禁止只有 2-3 个文字** |
| **无多余 composition** | **项目目录中除 index.html 外无其他含 data-composition-id 的文件** |

### 动画规则

8. 入场动画时长 **0.3-0.7 秒**（"快入+静止"模式）
9. stagger 间隔 **0.2-0.3 秒**
10. easing: `power3.out` 用于入场
11. 场景间由框架 transitions 处理，不手动 exit
12. **动画设计原则：** 每个场景的动画在 1 秒内完成入场，之后保持最终状态静止直到 `data-duration` 结束。不试图让动画精确填满整个场景时长——场景时长由 TTS 实际时长决定，HTML 编写时直接使用 `segment_durations.json` 的实际值。

### 字体规则

12. 优先使用 HyperFrames 内置字体映射（Inter、JetBrains Mono 等）
13. **中文渲染**：渲染端可能缺少中文字体映射，导致 fallback 为默认字体。应对策略：
    - 先渲染一帧验证中文是否正常显示
    - 如中文显示异常，尝试 `font-family: 'Inter', 'PingFang SC', 'Microsoft YaHei', sans-serif` 等系统字体链
    - 如仍不正常，考虑将中文文字渲染为图片后嵌入

### 渲染规则

14. 渲染传目录路径（`.`），不传文件路径
15. 渲染前确保 `lint` 通过
16. **渲染后白屏/空白检查（必须执行）**：
    ```bash
    # 提取多帧验证不是白屏或空白（无内容）
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
                print(f'ERROR @{ts}s: WHITE SCREEN! Check window.__hf definition.')
                exit(1)
            if all(v < 30 for v in avg):
                print(f'ERROR @{ts}s: BLACK/BLANK SCREEN! Check GSAP timeline registration.')
                exit(1)
            max_v = max(max(c[i] for c in pixels[:50]) for i in range(min(3, len(pixels[0]))))
            print(f'Frame @{ts}s OK: avg={avg}, max≈{max_v}')
        except Exception as e:
            print(f'Frame @{ts}s check failed: {e}')
    "
    rm -f check_*.png
    ```
    **白屏根因：`window.__hf` 未定义或 duration 不匹配。**
    **空白（黑屏有背景但无内容）根因：`window.__timelines = {};` 空对象，未注册 GSAP timeline。** 修复后重新渲染。

## 6.5 默认竖屏

默认输出 **竖屏（1080×1920）**。如用户要求横屏再额外生成。

### 动画设计原则（HyperFrames 时长模型）

HyperFrames 的 `data-duration` 是"硬声明"模式：渲染引擎逐帧 seek 驱动，`data-duration` 决定场景可见时长，GSAP 动画只管视觉变化。当动画时长 < `data-duration` 时，超出部分画面静止在最终帧。

**因此 ClipForge 采用"快入+静止"动画策略：**
- 每个场景的入场动画在 0.3-0.7 秒内完成
- 之后保持最终状态静止直到场景结束
- 不试图让动画精确填满整个场景时长
- `data-duration` 由 Stage 4 的 `segment_durations.json` 实际时长决定，HTML 编写时直接使用

竖屏字号参考（起点值，按内容密度和视觉权重调整）：hero 约 80-100px、title 约 56-72px、body 约 36-44px、tag 约 26-34px。内容多时偏小值，内容少时偏大值。横排布局改纵排（grid 多列改单列或 2 列）。

### 竖屏垂直居中规则（必须遵守）

竖屏高度 1920px，**视觉重心 = 960px（画面正中央）**。所有场景内容必须围绕这个中心点分布，顶部留白 ≈ 底部留白。

**居中方式（按优先级）：**

**首选：flexbox 自动居中**

场景容器用 flexbox，浏览器自动算居中，不需要手动计算 top 值：

```css
.scene-wrap {
  position: absolute;
  width: 1080px; height: 1920px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}
```

场景内的子元素按自然文档流从上到下排列，flexbox 自动将整组内容垂直居中。无论内容多少、高度多少，都天然居中。

**备选：绝对定位 + 手动计算**

仅在 flexbox 无法满足需求时使用（如元素需要重叠或非规则布局）：

1. **先算内容高度，再定起始位置**：估算场景所有元素的总高度，再用居中公式 `起始top = (1920 - 内容总高度) / 2`
2. **最小起始 top 值 300px**：即使内容非常多，最高元素的 top 也不能小于 300px

**禁止事项：**

- **禁止紧贴顶部**：不能用 `top: 80px`、`top: 160px`、`top: 240px` 这种小值
- **场景内容容器禁止用 `position: absolute` + 小 top 值**：会导致内容偏上

### 平台安全区域

抖音等平台播放时会覆盖部分画面：顶部显示用户名/标题，底部显示互动按钮/文案/进度条。核心内容应避开这些区域：

- **顶部危险区**：约上 200px 范围内不放关键文字或图标（会被平台 UI 遮挡）
- **底部危险区**：约下 300px 范围内不放关键文字或 CTA 按钮（互动按钮区域）
- **安全内容区**：约 200px ~ 1600px，核心视觉元素优先放在此范围内
- **具体遮挡范围因平台而异**，以上为通用参考，重要内容应向中间集中

## 6.6 渲染

**HTML 已使用 TTS 实际时长编写 + 音频已嵌入，直接渲染。** HyperFrames 自动处理音频发现、混音和封装。`output.mp4` 包含完整视频+旁白+BGM。

### 渲染前检查（必须执行）

```bash
cd workspace/<YYYY>/<MM>/<DD>/<project-dir>

# 1. 确认音频文件存在（404 = 无声视频）
ls -la narration.mp3 bgm.mp3

# 2. 移除所有非 index.html 的 composition 文件避免多 composition 冲突
for f in cover.html index_with_bgm.html cover.html.bak; do
  [ -f "$f" ] && mv "$f" "$f.renderbak"
done
```

### 渲染命令

```bash
# lint 检查
npx hyperframes lint

# 渲染（HyperFrames 自动发现 <audio> 元素，混音+封装到 output.mp4）
npx hyperframes render . --output output.mp4 --video-bitrate 5M
```

### 渲染后恢复

```bash
# 恢复文件
for f in cover.html index_with_bgm.html; do
  [ -f "$f.renderbak" ] && mv "$f.renderbak" "$f"
done
rm -f cover.html.bak.renderbak index_with_bgm.html.renderbak
```

> `--video-bitrate 5M` 强制输出高码率源。纯 CSS+文字内容在默认 CRF 模式下码率极低（~300 kbps），上传平台后经二次转码会严重糊化。5M 码率给平台转码留足余量。

### 渲染后音频验证

```bash
# 验证音频流存在
ffprobe -v quiet -show_streams -select_streams a output.mp4 | grep codec_name
# 应输出: codec_name="aac"

# 验证音量
ffmpeg -i output.mp4 -af "volumedetect" -f null /dev/null 2>&1 | grep volume
```

> 如果 `output.mp4` 缺少音频流，说明 HyperFrames 未能发现 `<audio>` 元素。检查 `<audio>` 是否为 composition 根元素的直接子元素，且 `src` 路径正确。

## 6.7 无 BGM 版本渲染（双版本输出）— 强制，不可跳过

> **产出两个视频文件是硬性要求，不可只渲染含 BGM 版本。**
> - `output.mp4`（含 BGM）
> - `output_no_bgm.mp4`（仅旁白，用户可自行替换配乐）
>
> **无论项目类型（标准/深度解析/电影解读）或时长，都必须生成无 BGM 版本。**
> 如果 `output_no_bgm.mp4` 未生成，Stage 6 视为未完成。

§6.6 渲染完成后，**自动执行以下步骤**生成无 BGM 版本：

```bash
cd workspace/<YYYY>/<MM>/<DD>/<project-dir>

# 1. 确认 cover.html 已移除（渲染前检查已处理）
for f in cover.html index_with_bgm.html cover.html.bak; do
  [ -f "$f" ] && mv "$f" "$f.renderbak"
done

# 2. 备份原始 HTML（用 .bak 扩展名避免被 HyperFrames 扫描为 composition）
cp index.html index_with_bgm.html.bak

# 3. 移除 BGM <audio> 元素：将 data-volume 设为 "0"（保留 timeline 结构完整）
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
print('BGM audio muted (data-volume set to 0).')
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

### 无 BGM 版本验证

```bash
# 验证音频流存在（只有旁白）
ffprobe -v quiet -show_streams -select_streams a output_no_bgm.mp4 | grep codec_name

# 对比两个版本文件大小（无 BGM 版本应略小）
ls -lh output.mp4 output_no_bgm.mp4
```

> **如果 `output_no_bgm.mp4` 缺少音频流**，说明移除 BGM `<audio>` 时误删了旁白 `<audio>`。检查 Python 正则是否只移除了 `data-track-index="2"` 的元素。

## 6.8 Stage 6 完成门禁

以下条件**必须全部通过**，否则 Stage 6 视为未完成，不得进入 Stage 7：

```bash
# 检查1: index.html 存在且非空
[ -s index.html ] || echo "FAIL: index.html missing or empty"

# 检查2: output.mp4 存在且含视频+音频
[ -s output.mp4 ] || echo "FAIL: output.mp4 missing"
ffprobe -v quiet -show_streams output.mp4 | grep -q "codec_name=h264" || echo "FAIL: output.mp4 no video"
ffprobe -v quiet -show_streams output.mp4 | grep -q "codec_name=aac" || echo "FAIL: output.mp4 no audio"

# 检查3: output_no_bgm.mp4 存在且含视频+音频（仅旁白）
[ -s output_no_bgm.mp4 ] || echo "FAIL: output_no_bgm.mp4 missing"
ffprobe -v quiet -show_streams output_no_bgm.mp4 | grep -q "codec_name=h264" || echo "FAIL: output_no_bgm.mp4 no video"
ffprobe -v quiet -show_streams output_no_bgm.mp4 | grep -q "codec_name=aac" || echo "FAIL: output_no_bgm.mp4 no audio"

# 检查4: BGM 可感知性验证（双重衰减防护）
# output.mp4（含BGM）应比 output_no_bgm.mp4（仅旁白）响 0.2-2 dB
# 如果差异 < 0.1 dB，说明 BGM 未混入或双重衰减导致不可感知
VOL_WITH=$(ffmpeg -i output.mp4 -af "volumedetect" -f null /dev/null 2>&1 | grep -oP 'mean_volume: \K[\-\d.]+')
VOL_WITHOUT=$(ffmpeg -i output_no_bgm.mp4 -af "volumedetect" -f null /dev/null 2>&1 | grep -oP 'mean_volume: \K[\-\d.]+')
echo "BGM check: with=${VOL_WITH} dB, without=${VOL_WITHOUT} dB"
if [ "$(echo "$VOL_WITH > $VOL_WITHOUT" | bc 2>/dev/null)" -ne 1 ]; then
  echo "WARN: output.mp4 不比 output_no_bgm.mp4 响，BGM 可能未混入"
  echo "排查：(1) bgm.wav 是否被预衰减 (2) HTML data-volume 是否正确 (3) bgm.wav 是否存在"
fi

echo "=== Stage 6 完成门禁通过 ==="
```

> **进入 Stage 7 提醒：** Stage 7 §7.1 必须生成 `cover.html` 和 `cover.png`（封面图），§7.2 门禁会检查这两个文件。不要跳过封面直接进入封面帧嵌入步骤。

**如果任何检查失败，修复问题后重新执行，不得跳过。**

---

## Red Flags（停止信号）

| 信号 | 说明 |
|------|------|
| 使用 CSS `.anim-in`（§7.1） | 事故：CSS `opacity: 0` 导致 HyperFrames 渲染空白 |
| 使用 HTML 实体（§7.2） | 事故：`&amp;` 等实体在无头浏览器中不解析，导致内容不渲染 |
| scene-wrap 无 padding（§7.3） | 事故：内容区域在渲染中塌陷不显示 |
| GSAP timeline 未注册（§7.6） | 事故：空 `__timelines={}` 导致全片空白 |
| 音频文件不在项目目录内（§7.5） | 事故：渲染引擎只认相对路径，绝对路径 404 静音 |
| 渲染前未移除 cover.html 等（§7.4） | 事故：多个 root composition 导致渲染冲突 |
| 缺少 `output_no_bgm.mp4` | 双版本输出不可省略，缺少视为阶段未完成 |
| 白屏/黑屏渲染结果 | 检查 `window.__hf` 定义和 `data-duration` 值 |

## Common Rationalizations（常见借口反驳）

| 借口 | 事实 |
|------|------|
| "CSS 动画更简单" | §7.1 事故：CSS `opacity: 0` 入场动画永远不会执行，内容永远不可见 |
| "`&amp;` 是标准 HTML 写法" | §7.2 事故：HyperFrames 无头浏览器对实体字符解析不可靠 |
| "内容要充满画面，不用 padding" | §7.3 事故：缺少 padding 导致内容区域塌陷 |
| "GSAP timeline 会自动注册" | §7.6 事故：必须显式 `window.__timelines["main"] = tl`，空对象 = 全片空白 |
| "绝对路径也能找到文件" | §7.5 事故：HyperFrames 通过 FileServer 提供文件，只认项目目录内相对路径 |
| "cover.html 不影响渲染" | §7.4 事故：任何含 `data-composition-id` 的 HTML 文件都会导致渲染冲突 |
