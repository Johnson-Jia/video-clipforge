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

**色彩优先级规则（冲突时必须遵守）：**

当 `design.md` 的 `color_direction` 与 `immersion_mode` 配色速查表冲突时：
- **`color_direction` 优先。** `color_direction` 是 Stage 2 基于内容主题推导的定制配色，比 `immersion_mode` 的通用配色表更精准。
- `immersion_mode` 配色速查表作为**兜底默认值**，仅在 `color_direction` 未明确指定色值时生效。
- `immersion_mode` 的**风格方向**（暗度、饱和度、对比度特征）仍然有效，只是具体色值让位于 `color_direction`。
- 实践：先从 `immersion_mode` 查表获取 `:root` CSS 变量，再用 `color_direction` 中明确的色值覆盖对应变量。

**设计决策链：**
1. `immersion_mode` → `stage6-components.md` 配色速查 → `:root` CSS 变量（兜底）
2. `color_direction` → 覆盖 `:root` 中冲突的色值（优先）
3. 每个场景的**具体内容** → 读内容想画面（格言引导 + 反面清单兜底） → 背景层 + 特效层 + 内容层的视觉方案
4. `character_presence` + 每段 `character_expression` → CharOverlay 组件选择

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

1. **读取 `narration_segments.json`** — 每段的 `scene`、`text`（旁白内容）、`visual_phases`、`character_expression`、`humor_type`
2. **读取 `design.md` 的 `storyboard`** — 沉浸模式、叙事模板、情感曲线
3. **读取 `stage6-components.md`** — 视觉推导系统 + CSS 特效参考库 + 组件模板
4. **设计视觉（每个场景独立创作）** — 读场景内容，像导演一样构思画面：
   - 这段内容在说什么？观众该感受到什么？什么视觉能强化这个感受？
   - 参考 `stage6-components.md` 的设计格言（5 条正面引导）
   - 对照反面清单（10 条红线），确保不踩雷
   - 用 CSS 特效参考库的工具实现你的构思
   - **不查表、不套公式、每个场景独立思考**
5. **装配 HTML** — 按 HyperFrames composition 结构组装

### 场景 → 组件参考

> **这是参考映射，不是固定分配。** 根据场景内容选择最合适的组件组合，允许跨场景复用和变体。

| 场景类型 | 常用组件 | 视觉方向参考 |
|---------|---------|------------|
| hook | HeroCard | 震撼开场：高力度视觉、聚焦元素 |
| 数据/规模 | DataViz, CompareSplit | 数据呈现：结构化、清晰、有科技感 |
| 对比/竞争 | CompareSplit | 双视角：冷暖分割、对冲视觉 |
| 时间线/路径 | TimeLineFlow | 叙事推进：轨道感、节点连线 |
| 突出/揭示 | TextReveal | 悬念展示：渐进揭示、聚光灯效果 |
| 标准模式项目介绍 | ProjectFullCard | 单项目全屏 8 层信息 |
| CTA | TextReveal | 收束聚焦：温暖引导、行动号召 |

> **标准模式项目介绍场景：** 使用 ProjectFullCard 组件（§13），一个项目占满一屏，包含 8 层信息。数据来自 `narration_segments.json` 的 `selling_points`、`commentary` 字段和 content 数据。

### 角色和幽默组件插入

- `character_expression` 非 null 的场景 → 添加 `CharOverlay` 组件（对应表情 SVG）
- `humor_type` 非 null 的场景 → 添加 `SpeechBubble` 组件（文案从 narration 提取幽默句）
- 角色定位：画面左下角，占 15-20%
- 气泡定位：画面右下角或角色上方

### 特效填充验证

> `director_gate.py` §6 检查 layer-fx 内容非空，`stage6_gate.sh` 检查空 layer-fx 数量。HTML 写完后直接运行门禁脚本即可。

### 视觉检查（对照反面清单）

> HTML 写完后，快速扫一遍 `stage6-components.md` 的 10 条反面清单，确保没有踩雷。无需额外检查流程——反面清单已经编码了所有已知的视觉质量问题。

### 导演自审（Layer 3 — HTML 写完后、渲染前必须执行）

> **目的**：像导演审看每日样片，逐场景检查 HTML 是否实现了导演决策。这是最后一道"导演看监视器"关卡。

读取 `_director-toolkit.md` 的"导演 5 个必答题"，逐 `.clip` 场景自审：

| # | 必答题 | 检查点 |
|---|--------|--------|
| Q1 | 核心情绪是什么？ | 旁白文本 → 情绪词 → HTML 配色/光晕是否匹配 |
| Q2 | 观众该感受到什么？ | `narration_segments.json` 情感标记 → 视觉力度是否对等 |
| Q3 | 什么视觉能放大？ | 情绪 → 视觉词汇（暖冷/明暗/动静）→ HTML 是否实现 |
| Q4 | 相邻场景反差够不够？ | 上下 `.clip` 的背景渐变/配色是否不同 |
| Q5 | 眼睛该被引导到哪里？ | 字号最大/颜色最亮的元素 = 旁白的信息重点？ |

**对标 `narration_segments.json`**：

- `visual_phases[n].focus` → HTML 有对应内容元素？
- `visual_phases[n].key_data` → 画面数据完整呈现？
- 相邻场景配色雷同 → 调整背景渐变
- hook 缺乏冲击力 → 加强光晕/字号/对比度

**发现偏差立即修复。自审不通过的禁止渲染。**

## 6.4a 视觉分镜（Visual Phasing）

> **当场景时长 >15 秒时必须使用。** 完整规范见 `clipforge/_visual-phasing`。

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
0. **渲染安全规范**遵守 `clipforge/_render-safety` 全部条款（Stage 6 必读）。

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

> **CSS 渲染安全规则全部在 `_render-safety.md` §1 中定义。** 以下仅列 Stage 6 独有规则，不重复渲染安全内容。

8. **`.clip` 只设 `position: absolute` + 尺寸**，不要加其他样式（上140 / 右90 / 下260 / 左70）

### 视觉设计规则（必须遵守）

#### 视觉密度要求（分级规则）

| 场景类型 | 最低元素数 | 说明 |
|---------|-----------|------|
| 内容场景（项目介绍等） | ≥ 5 | 排名 + 名称 + 数据 + 描述 + 标签（+ 卖点/角色 可选） |
| Hook/CTA | ≥ 3 | 主标题 + 装饰 + 标识（不强凑，保持极简冲击力） |
| 高潮场景 | ≥ 5 | 额外添加视觉强化元素（特效爆发 + 数据强调） |

每个场景的元素计数不包含背景装饰（光晕、网格等），只计入 `.layer-content` 中的可读/可交互元素。

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
16. **渲染后白屏/空白检查**：`frame_analysis.py`（Layer 2）自动执行暗帧和亮度检测，`stage6_gate.sh` 调用

## 6.5 默认竖屏

默认输出 **竖屏（1080×1920）**。如用户要求横屏再额外生成。

### 动画设计原则（HyperFrames 时长模型）

采用"快入+静止"动画策略：入场 0.3-0.7s，之后静止到场景结束。

竖屏字号参考：hero 约 80-100px、title 约 56-72px、body 约 36-44px、tag 约 26-34px。

### 竖屏垂直居中规则

> **居中已内置到 `.phase` CSS 中**：`.phase` 统一使用 `display:flex;flex-direction:column;justify-content:center`，所有 phase 内容自动垂直居中。不需要在 `.scene-wrap` 或 inline style 上手动添加 flex 居中。

**禁止在 `.scene-wrap` 上加 flex 居中**：Phase 模式下 `.phase` 是 `position:absolute`，不参与 `.scene-wrap` 的 flex 布局，在 scene-wrap 上加 flex 无效。

**禁止紧贴顶部**：不能用 `top: 80px` 等小值。场景内容容器禁止 `position: absolute` + 小 top 值。

### 布局推导（两级体系）

**垂直方向强制居中**（`.phase` flex 内置），水平方向由布局推导决定：

#### Level 1：visual_type → 布局框架

每个 phase 的布局从 `narration_segments.json` 的 `visual_phases[].visual_type` 推导，不套固定模板。完整规格表见 `stage6-components.md` 的「布局推导体系」章节。

**水平对齐推导规则：**

| visual_type | 水平对齐 | 说明 |
|------------|---------|------|
| hero | 全部居中 | 标题 + 数字 + 副标题，间距 generous |
| list | 标题居中，条目区 width:85% 内部左对齐 | 序号 + 文字条目 |
| data | 标题居中，数据行 width:85% | label-value 行 |
| compare | flex-direction:row，双栏各 flex:1 | 左冷右暖对比色 |
| timeline | 标题居中，步骤区 width:85% 内部左对齐 | 时间标签 + 文字 |
| highlight | 全部居中 | 大号文字 + 可选徽章 |

#### Level 2：内容字数 → 元素尺寸

primary/标题元素根据文本长度缩放：≤4 字 = 1.0×，5-8 字 = 0.85×，9-14 字 = 0.7×，15-24 字 = 0.55×，≥25 字 = 0.45×。具体基准字号见 `stage6-components.md`。

#### 密度控制

- `visual_phases[].layout_hint.density` 可微调间距（compact ×0.7 / standard ×1.0 / generous ×1.3）
- 不指定时从 visual_type 自动推导：hero/highlight → generous，list/timeline → standard，data/compare → compact

#### 渲染顺序原则

- 水平：从左到右（排名 → 名称 → 数据）
- 垂直：从上到下（标签 → 标题 → 描述 → 卖点）
- 不强制所有元素居中，让内容和 visual_type 决定最美观的布局

### 平台安全区域

- 顶部危险区：上 200px
- 底部危险区：下 300px
- 水平安全边距：左 80px / 右 80px（兼容抖音/小红书/微信视频号三平台）
- 安全内容区：180px ~ 1700px（垂直），80px ~ 1000px（水平）

## 6.6 渲染

### 渲染前检查（必须执行）

```bash
cd workspace/<YYYY>/<MM>/<DD>/<project-dir>

# 1. 确认音频文件存在
ls -la narration.mp3 bgm.mp3

# 2. 导演门禁 — HTML 设计意图验证（Layer 1）
python3 .claude/commands/clipforge/scripts/director_gate.py .
# 未通过则修复 HTML 后重新执行，不得跳过

# 3. 移除所有非 index.html 的 composition 文件
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

## 6.7 单次渲染 + ffmpeg 合成

> **HyperFrames 只渲染一次 output.mp4（旁白 + BGM 混合）。** output_no_bgm.mp4 由 ffmpeg 从 output.mp4 视频轨 + narration.mp3（纯旁白源文件）合成，无需二次渲染。

### 渲染前准备

```bash
cd workspace/<YYYY>/<MM>/<DD>/<project-dir>

# 从 segment_durations.json 读取 BGM 音量，写入 HTML
BGM_VOL=$(python -c "import json; print(json.load(open('segment_durations.json'))['meta'].get('bgm_volume', 0.15))")
sed -i "s/id=\"bgm\" data-volume=\"[^\"]*\"/id=\"bgm\" data-volume=\"${BGM_VOL}\"/" index.html
echo "HTML BGM data-volume set to ${BGM_VOL}"
```

### 渲染（仅一次）

```bash
# ── 渲染: 完整 HTML → output.mp4（旁白 + BGM）──
npx hyperframes render . --output output.mp4 --video-bitrate 5M
```

### 合成 output_no_bgm.mp4（ffmpeg，不渲染）

> **禁止**从 output.mp4 提取音频轨（只有 1 条混合轨，BGM 无法分离）。
> **必须**用 narration.mp3（纯旁白源文件）作为音频源。

```bash
# ── output_no_bgm.mp4 = output.mp4 视频轨 + narration.mp3 音频轨 ──
ffmpeg -y -i output.mp4 -i narration.mp3 \
  -map 0:v -map 1:a \
  -c:v copy -c:a aac -b:a 128k \
  -shortest \
  output_no_bgm.mp4
```

### 文件逻辑

```
output.mp4      = 视频 + 旁白 + BGM（HyperFrames 渲染）
output_no_bgm.mp4 = output.mp4 的视频 + narration.mp3 的音频（ffmpeg 合成）
final.mp4      = cover.png + output.mp4
final_no_bgm.mp4 = cover.png + output_no_bgm.mp4
```

## 6.8 封面帧拼接

> **ffmpeg concat filter 拼接封面帧 + 正片视频，不碰音频。**

```bash
cd workspace/<YYYY>/<MM>/<DD>/<project-dir>

# ── 创建封面帧（1帧 H264）──
ffmpeg -y -loop 1 -i cover.png -c:v libx264 -b:v 5M -t 0.0333 \
  -pix_fmt yuv420p -r 30 cover_clip.mp4

# ── 拼接：封面帧 + 正片 ──
# final.mp4 = cover + output.mp4（含 BGM）
ffmpeg -y -i cover_clip.mp4 -i output.mp4 \
  -filter_complex "[0:v][1:v]concat=n=2:v=1:a=0[outv]" \
  -map "[outv]" -map 1:a \
  -c:v libx264 -b:v 5M -c:a copy \
  final.mp4

# final_no_bgm.mp4 = cover + output_no_bgm.mp4（仅旁白）
ffmpeg -y -i cover_clip.mp4 -i output_no_bgm.mp4 \
  -filter_complex "[0:v][1:v]concat=n=2:v=1:a=0[outv]" \
  -map "[outv]" -map 1:a \
  -c:v libx264 -b:v 5M -c:a copy \
  final_no_bgm.mp4

# ── 清理临时文件 ──
rm -f cover_clip.mp4
```

### BGM 音量

> BGM 音量由 Stage 4 的 `bgm_gap_check.py` 自动查表校准，值存储在 `segment_durations.json` 的 `meta.bgm_volume`。渲染前从该文件读取并写入 HTML `data-volume`。

### 致命约束

| 约束 | 违反后果 |
|------|---------|
| **output_no_bgm.mp4 必须用 narration.mp3 合成** | 用 `-map 0:a:0` 从 output.mp4 提取只得到混合轨，BGM 无法消除 |
| **ffmpeg 只做封面帧拼接，不碰 output.mp4/output_no_bgm.mp4 的音频** | concat filter 只拼接视频流，音频从源文件直接 copy |
| **BGM 音量在渲染前写入 HTML** | 渲染后无法修改 HyperFrames 已混入的 BGM 音量 |

> **封面帧仅增加 1/30 秒（~33ms），对音画同步无感知影响。** `cover.png` 仍作为独立封面图上传平台。

## 6.10 Stage 6 完成门禁

```bash
# ── Stage 6 完成门禁 ──
bash .claude/commands/clipforge/scripts/stage6_gate.sh

# ── 渲染帧视觉分析（Layer 2）──
python3 .claude/commands/clipforge/scripts/frame_analysis.py .
```

**如果任何检查失败，修复问题后重新执行，不得跳过。**

---

## 约束声明

**Iron Law:** 渲染前未移除 cover.html = 渲染必冲突。GSAP timeline 未注册 = 全片空白。output_no_bgm.mp4 未从 narration.mp3 合成 = 双版本输出失败。

> 本阶段的结构化约束（HARD/SOFT 规则 + Guard Red Flags）由引擎注入提供。执行前运行 `python engine/inject.py --skill stage6-production` 获取完整约束 prompt。
