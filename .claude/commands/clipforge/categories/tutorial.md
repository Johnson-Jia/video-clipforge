---
name: "专业教程"
description: "横屏16:9企业级技术教程视频，10分钟+深度解析"
id: "tutorial"
---

<!-- CONFIG-START: 机器可解析的配置值 -->
orientation:
  orientation_hint: "landscape"

design:
  default_style: "清爽专业科技风"
  color_bias: "深蓝为主（#0F172A 底 / #1E3A8A 主色），强调色蓝白（#3B82F6 / #E0E7FF），干净不花哨"

narration:
  word_count_range: [1500, 2500]
  hook_example: "80人研发团队3个月人均产出+104%，怎么做到的？"
  hook_anchors:
    - "翻倍"
    - "怎么做到的"
    - "第一步"
    - "三步"
    - "实操"
    - "落地"
  cta_purpose: "教程合集引导 + 关注转化"

audio:
  default_voice: "zh-CN-YunjianNeural"
  default_rate: "+0%"
  voice_override: true

delivery:
  hashtags: "#AI转型 #程序员 #ClaudeCode #企业级 #研发提效"
  cover_badge: "AI 转型实战"
  cover_scene_label: "企业级教程"
<!-- CONFIG-END -->

# 专业教程分类配置

> 横屏 16:9 企业级技术教程。与 github（竖屏短视频盘点）不同：教程类要**横屏专业呈现 + 长文案 + 屏录实操**。

## orientation

强制横屏 16:9（1920×1080）。教程类视频在 B 站横屏播放，观众要读代码/文字/流程图，竖屏装不下。
- `orientation_hint: landscape`
- Stage 2 读取此值直接写入 design.md（orientation_source=category_hint）
- **⛔ design.md 必须显式写 `orientation: landscape` + `resolution: 1920x1080`**：s6_assemble **只读 design.md 不读 tutorial.md**，缺 orientation 字段默认 portrait（竖屏 1080×1920）→ concat 后画面压缩（E07 事故）。SubAgent 验证 output：`ffprobe -select_streams v -show_entries stream=width,height` 必须 `1920x1080`，非此则失败重做

## content

### data_source
教程文档：`D:/AI-Agent/ai-landing-tutorial/`（index.html + pages/stage0-6 + demos/）。每集对应一个 stage 或 demo，读对应 HTML/MD 提炼脚本。

### selection_strategy
按合集规划（`workspace/ai-landing-tutorial-series/合集规划.md`）的 12 集顺序，每周 1 集。不自动抓取，按规划顺序创作。

## design

### default_style
清爽专业科技风。教程类要**干净、可读**（观众要读代码/文字/流程图），不要花哨动画抢注意力。
- 背景：深蓝（#0F172A）或干净白底（按内容切换）
- 主色：蓝（#1E3A8A / #3B82F6）
- 强调：蓝白渐变 / 数据高亮用金（#FBBF24）
- 字体：无衬线粗体（思源黑 / Inter），代码用等宽（JetBrains Mono）
- **⛔ fx 装饰规则（HARD）**：教程视频**禁用划过类 fx**（fx-scan 上下扫描 / fx-stream 下落 / fx-beam 左右扫）——眼睛追线不看内容不听旁白，影响观看体验。用**静态/脉冲发光类**（fx-aura 光晕 / fx-pulse-ring 脉冲环 / fx-particle 漂浮粒子 / fx-blink 闪烁锚点，不划过不追线）。教程重内容轻视觉，fx 只做氛围点缀（静态发光/呼吸），不做动态划过
- **⛔ fx 色彩规则（暖色低 alpha）**：fx 优先**冷色**（蓝 hsl215 / 紫 hsl255 / 绿 hsl150）沉稳；**暖色**（金 hsl43 / 红 hsl0 / 橙 hsl28）**alpha ≤ 0.22**——暖色高 alpha（≥0.5）光晕在深蓝底太跳，文字浮/不舒服（E03 事故）。教程主色（标题渐变/数据/卡片边框）可继续用金，但**背景层 fx 暖色要弱**（alpha ≤ 0.22），让前景文字突出
- **⛔ text-shadow 规则（极淡 0.08，禁发光）**：渐变文字 text-shadow 三难——发光（`0 0 Xpx`）泛光刺眼 / 黑色触发 R-S6-023 / 深蓝（0.6）拖暗 / 淡白（0.18）OLED 过曝。**极淡 drop `text-shadow: 0 2px 6px rgba(30,41,59,0.08)`**（几乎看不见）。**⛔ 禁发光 `0 0 Xpx rgba(...)`**（E04 claudemd 事故：金色 `0 0 10px rgba(251,191,36,0.20)` 致 PascalCase/camelCase 泛光）。修复：`sed -i -E 's/text-shadow:[^;]*;/text-shadow: 0 2px 6px rgba(30,41,59,0.08);/g' creative/style.css`
- **⛔ 渐变文字配色（禁白色端点 + 同色系，参照 EX-cover.png）**：background-clip:text 渐变**禁白色端点**（#fff/white/rgba(255,255,255)——OLED 过曝泛光）。用**同色系高饱和**（domain→lighten→domain）：金 `#FBBF24→#F59E0B→#FCD34D` / 蓝 `#60A5FA→#3B82F6→#93C5FD` / 绿 `#34D399→#10B981→#6EE7B7` / 红 `#FCA5A5→#EF4444→#F87171` / 紫 `#C4B5FD→#A78BFA→#DDD6FE`。**参照封面**（E04-cover.png）：标题金→蓝同色系、终端语法高亮（蓝/绿/紫/金各色无白端点）、5 件套各色边框——正确配色范本
- **清晰度规则（concat crf 14）**：各段 output.mp4 高码率（~4.9 Mbps），但 filter concat re-encode crf 18 → final 降 1.16 Mbps（模糊）。**重拼用 crf 14**（不是 18）→ final 2.79 Mbps 文字锐利。`ffmpeg ... -crf 14 ...`
- 动画：克制——流程图逐步展开、数据飞升、代码高亮，不要粒子/光晕过载

### layout — 横屏布局规则（禁为居中而居中）

> **核心**：横屏 1920×1080 不要默认全居中堆叠。**根据内容类型推导布局**，让画布利用率从 50% 提到 80-85%。

| 内容类型 | 推导布局 | ✗ 反面（挤中间）|
|---------|---------|----------------|
| 卡片列表 / 详情 | 左对齐或网格均分 | 全 `center` 垂直堆叠 |
| 对比图 / 两概念 | 左右分栏均衡 | 上下居中叠 |
| 数据 / 决策项 | 2×2 grid 或左对齐 + 留白 | 纵向居中挤 |
| 流程 / 步骤（六阶段流水线等）| 横向均分撑满宽度，节点 `flex:1` | 缩在中心 60% |
| 标题 + 正文 | 标题左对齐建锚点，正文按内容 | 标题 + 正文全 `center` |

**布局范式**：
1. `justify-content:center` → `space-between`（顶/中/底三段不挤垂直中心）
2. 标题区 `align-items:center` → `flex-start` + `text-align:left`（左对齐建视觉锚点，打破为居中而居中）
3. 卡片去 `min-width` 改 `flex:1` / `grid` 撑满画布宽度
4. padding/gap 加大增加呼吸感
5. **⛔ safezone padding-top ≥60px**：`space-between` 把首个 region 顶到 padding-box 边缘，padding-top <60px 触发安全区顶部溢出（`content_y<60` hard violation）。50px 必触发，建议 72px 留余量

**收尾段例外**（cta / 合集标识）：可保持居中（收尾段居中合理），但内容区放松（预告卡 + CTA 卡分栏，不全堆垂直中心）。

### container_text — 容器内文字适配（防溢出）

> 圆/胶囊/小容器内的文字，先算 **字符数 × 字号 < 容器内径 × 0.7**，放不下就移容器外或换行。

- 圆形节点（TDD 循环 / 阶段圈）：长词（≥6 字符如 REFACTOR/SUPERPOWERS）放圆**外**（圆内仅 letter 缩写或短词），圆内字符宽度 × 字号 < 圆内径 × 0.7
- 胶囊标签：单行文字宽度 < 胶囊 padding 后可用宽度，超了换行或简化措辞
- 卡片标题：长标题算字符 × 字号 < 卡片宽，按需 `word-break` / `white-space:nowrap`
- 字号 ≥32px（教程门禁下限）前提下，长词优先**移容器外**（而非缩字号）

## narration

### word_count_range
1500-2500 字（10-15 分钟深度解析）。教程类长文案，信息密度高，每分钟约 150-180 字。

### special_rules
- **专业 + 口语**：不是短视频的"炸/霸榜/最猛"，是"这一步我们做的是…""关键在哪呢"。教程类要让人跟上，不是刺激。
- **统一结构**：钩子 30s → 这集讲什么 30s → 主体 7min → 案例证明 1.5min → CTA 30s
- **数据严谨**：+104% 等标注"事后统计、相关性非因果"（教程的规范）
- **不夸大**：用"数倍"不用"2-3 倍"（无口径）；模型能力加时间限定
- **⛔ 多音字读音（edge-tts 修正，HARD）**：edge-tts 单字多音字默认读音常错，narration 措辞**避免单字多音字**：
  - **"转"（转型/转变义，zhuǎn 三声）一律用"转型"**——edge-tts 单字"转"读 zhuàn（四声"转动"）。如"必须转"→"必须转型"、"为什么转"→"为什么转型"、"先转过去"→"先转型"
  - **"藏"（隐藏义，cáng 二声）用"隐藏"**——edge-tts 单字"藏"常读 zàng（四声"宝藏"）。如"藏在"→"隐藏在"、"藏身"→"隐藏身"、"藏着"→"隐藏着"。画面文字同步改
  - **"2 天/2 人/2 个"用"两天/两人/两个"**（liǎng）——edge-tts 数字"2"读 èr（二），但量词前应读 liǎng（两）。如"2 天培训"→"两天培训"、"2 人"→"两人"、"2 个"→"两个"。画面文字同步改
  - 画面文字（creative 碎片 + content）同步改，保持视觉与配音一致
  - 其他多音字按需补充（撰写 narration 时主动规避单字多音）
- **⛔ 段间衔接（多段拼接视频 HARD）**：合集拆段拼接（如 E01 开场段+钩子+介绍段+段1-4），各段 narration 首尾**保持合集脚本原文连贯**，拼接后像一个连续讲解：
  - **禁承接预告**（"接下来讲 X"/"下一段讲 Y"/"接下来拆"）—— 合成一个视频会冗余重复 + SA1 独立写预告内容跟下段实际不符（断裂事故：段1尾预告"思想转变"但段2首讲"7阶段"，段2尾预告"阶段细讲"但段3首讲"5demo"）
  - **禁回顾上段**（"上一段讲了 Y"/"刚才提到 X"）—— 合成视频重复
  - **各段尾自然结束本段内容**（不预告下段），**下段首自然进入新内容**（不回顾上段），靠内容逻辑自然过渡（如"为什么转型"讲完→"7 阶段方法论"自然开始）
  - **段间衔接检测**（HARD，拼接前必跑）：检测各段尾（最后1-2句）+ 下段首（最前1-2句），确保无词/语义重复 + 无逻辑断裂 + 拼接后连贯如一整段讲解

### hook_templates
教程类钩子（痛点/数据/反常识，30 秒抓人）：
- "80 人团队 3 个月人均产出翻倍，怎么做到的？"（数据钩子）
- "AI 转型第一步不是上工具，是转变思想"（反常识）
- "怎么向老板要预算？AI 转型立项实操"（痛点）
- "Claude Code 装不上？三步搞定网络与接入"（痛点）

## audio

### default_voice
教程类**建议自己配音**（专业感 + 可信度 > AI 配音）。如用 TTS：zh-CN-YunjianNeural，语速 +0%（教程类不快，让观众跟上）。

### bgm_style
教程类 BGM 定位是**低调衬底**——观众要听清讲解，不能抢旁白。

**⛔ BGM 集中规划**（E05+，HARD）：每集开始**主 agent** 基于文案推导 3-5 首候选 BGM，写 `workspace/ai-landing-tutorial-series/E0X-bgm-plan.json`，各段 stage4 读 plan 分配，**禁各段独立选曲**（E05 事故：A/B/C 组各选 warm-editorial/chill-lofi/monochrome 混搭）。

**bgm_plan.json 结构**（主 agent 填）：
```json
{
  "episode": "E0X", "mood": "情绪/内容描述", "series": "monochrome",
  "candidates": ["monochrome-4.mp3", "monochrome-2.mp3", "monochrome-5.mp3", "monochrome-6.mp3"],
  "main": "monochrome-4.mp3",
  "main_duration": 82.94, "total_duration": 318.8, "one_cover_all": false,
  "version1_segment_bgm": {"hook": "...", "intro": "...", "...": "..."},
  "version2_extend": ["monochrome-2.mp3", "monochrome-5.mp3", "monochrome-6.mp3"],
  "volume": 0.35
}
```

**规划流程**（主 agent，派各段 subagent 前）：
1. 分析文案情绪/节奏 → 匹配教程首选系列（clean-corporate/warm-editorial/monochrome/chill-lofi）
2. 选 3-5 首候选（**同系列优先**，保证 acrossfade 自然；候选总时长 ≥ 整集）
3. 定 main + 算 one_cover_all（main 时长 ≥ 整集 → true；否则 false）
4. 填 version1_segment_bgm（one_cover_all=true → 各段都填 main；false → 各段从候选分配，按时长+情绪）+ version2_extend（候选去 main）

**⛔ 双版本输出**（E04+，每集必须产出两个版本）：

**版本 1：`E0X-final.mp4`**（各段读 bgm_plan 分配 BGM，**调固定脚本 concat，禁手写 ffmpeg**）
- 各段 stage4 读 `E0X-bgm-plan.json` 的 `version1_segment_bgm[段名]` → `cp workspace/bgm/<bgm> → bgm.wav`（**不跑 bgm_history 去重**，规划已定）
- 各段 output.mp4（含分配 BGM，HyperFrames 混音，stereo）
- **固定脚本 concat**（各段 output.mp4 + 开场）：
```bash
bash .claude/commands/clipforge/scripts/assemble_segments.sh \
  --segments-dir workspace/2026/07/06 --episode E0X \
  --segments "hook intro pain rag graph1 graph2 skill mcp cta" \
  --opening workspace/ai-landing-tutorial-series/tutorial-opening/output.mp4 \
  --output workspace/2026/07/06/E0X-final.mp4
```
脚本内部：concat demuxer + re-encode crf 14 + stereo + 声道/振幅验证。

**版本 2：`E0X-final-pierce.mp4`**（一首贯穿 BGM，**调固定脚本，禁手写 ffmpeg**）
- 主体 = 各段 `output_no_bgm.mp4` concat → 加一首贯穿 BGM（main + version2_extend **每首 loudnorm I=-20:TP=-2 后 bass=g=-6:f=80 降重低音鼓点 + acrossfade**（统一响度 + 降 80Hz 低频 6dB，教程类 BGM 重低音不抢旁白）+ **volume 0.35** + **bypass Mastering**（教程类保留 mix 响度 ~-19dB，BGM 降不被 Mastering linear 增益抵消；平台二次 loudnorm 弱于 two-pass linear））→ 开头拼开场
- **⛔ 教程类 volume 0.35**（E06 验证）：教程类 BGM 衬底要弱（旁白为主），0.60 偏大（重低音鼓点抢旁白），0.35 + bass 滤波（assemble_pierce.sh Step 5 已固化）双管齐下。降 volume 被 Mastering 锁整体抵消（mean_volume 几乎不变），但 BGM/旁白占比实际降（0.35→25.9%），靠听感验证非 mean_volume
- **固定脚本**（修复声道乱跳 + double volume + BGM 丢失三大坑）：
```bash
bash .claude/commands/clipforge/scripts/assemble_pierce.sh \
  --segments-dir workspace/2026/07/06 --episode E0X \
  --segments "hook intro pain rag graph1 graph2 skill mcp cta" \
  --bgm-plan workspace/ai-landing-tutorial-series/E0X-bgm-plan.json \
  --opening workspace/ai-landing-tutorial-series/tutorial-opening/output.mp4 \
  --output workspace/2026/07/06/E0X-final-pierce.mp4
```
脚本内部（10 步）：逐段 stereo（修 mono/stereo 乱跳）+ 单次 `[1:a]volume=$VOL`（修 double）+ amix normalize=0 + BGM 振幅验证（修丢失）+ Mastering。

| 用途 | 分类（workspace/bgm/ 库名前缀） | 说明 |
|------|--------------------------------|------|
| ✅ 首选 | clean-corporate / warm-editorial / monochrome | 低调不抢，跨期 5 天去重 |
| ⚠️ 节制 | chill-lofi / pastel-soft | 轻情绪点缀，不连续用 |
| 🆘 fallback | pastel-soft | 首选档 5 天内全用过 + chill-lofi 也用过时用（选未用过的），柔和衬底教程合适（E07：首选档全用过→pastel-soft）|
| ⛔ 避开 | bold-energetic / epic-* / neon-electric | 激昂/电子抢旁白 |

> 主 agent 规划 bgm_plan.json（基于文案推导候选），各段读分配。教程合集段**跳过 bgm_history 去重**（故意同系列）。如自己配音则无需 BGM 衬底。

## delivery

### hashtags
固定 5 个 + 集数专属：
- 固定：`#AI转型` `#程序员` `#ClaudeCode` `#企业级` `#研发提效`
- 集数专属：`#AI原理`（E02）/ `#OpenSpec`（E06）/ `#自动化测试`（E07）等

### cover_strategy — 合集统一封面模板（每集复用风格，内容不同）

每集封面统一模板（合集识别符固定，内容每集不同），让观众一眼认出同合集：

**固定（合集识别符）**：
- badge：`AI 转型实战`（合集标识，固定）
- 集数角标：`E0X`（左上大字，固定位置）
- 配色：深蓝底 `#0F172A` + 金 `#FBBF24` + 蓝 `#3B82F6` + 绿 `#10B981`（固定）
- 字体：Inter + 思源黑（固定）
- 尺寸：**3 比例版本**（每集都生成，多平台发布）：
  - `E0X-cover.html`（16:9 / 1920×1080）：B 站标准横屏
  - `E0X-cover-43.html`（4:3 / 1440×1080）：通用横屏（更方）
  - `E0X-cover-34.html`（3:4 / 1080×1440）：抖音/小红书竖屏
- 风格：清爽专业，不加夸张表情/大字
- **避断层**（3 比例通用）：内容区（stages/conclusion）固定 margin 紧跟上方，`margin-top:auto` 只用在 footer（推底），避免内容被推到底导致中间大空白断层
- **布局适配**：16:9/4:3 数据/原理卡横排；3:4 改垂直堆叠（原理垂直列表、阶段 grid、数据垂直或横排）
- 渲染：playwright retina（device_scale_factor=2）→ 3840×2160 / 2880×2160 / 2160×2880 PNG

**变化（每集不同）**：
- 主标题：本集钩子（如"为什么必须转型"）
- 数据角标：本集核心数据（如 +104%/76.6%）
- 集数：E01-E12

cover_params.json 每集用统一 `badge="AI 转型实战"` + `colors`（固定）+ 本集 `title`/`cards`/`episode`（变化）。

### 合集封面（独立，B站合集列表用）

独立合集封面（代表整个合集，1 张）：`workspace/ai-landing-tutorial-series/series-cover.png`
- 合集名：AI 提效转型实战 · 带研发团队从 0 到人均产出翻倍
- **7 阶段方法论标题**：阶段0 总纲（思想转变）→ 阶段1 战略启动 → 阶段2 全员赋能 → 阶段3 基础设施 → 阶段4 闭环试点 → 阶段5 推广度量 → 阶段6 沉淀复用
- 数据：+104% 人均产出 / 76.6% AI代码 / -16.4pp Bug / 5个可运行demo
- 12 集深度解析 + 合集标识

### comment_template
评论区置顶（⛔ 不放完整 URL/域名 `github.com/`，规避 stage7 no_url 门禁；用 owner/repo 文本路径 + 主页引导，同 github 分类的 owner/repo 写法）：
```
教程仓库（所有 demo 可 clone 即跑）：Johnson-Jia/ai-landing-tutorial
合集地址：看我主页合集（主页有教程合集入口）
本集对应教程：stage0.html（总纲）
```

## 片段制作指引（三工具混合，A 方案）

> tutorial 按 `workspace/ai-landing-tutorial-series/合集规划.md` 是**混合制作**——三工具各司其职，剪映合成整片。**不是全自动整片**（教程"真跑给人看"靠屏录 + PPT 主体专业感）。

### 三工具分工

| 片段类型 | 工具 | 优势 |
|---------|------|------|
| **钩子**（数据飞升/视觉冲击）| ClipForge | GSAP 自定义动画冲击力 > PowerPoint 内置 |
| **主体**（方法论/流程图/数据图表）| ppt-master | AI 生成完整 PPTX + 原生图表专业 + 可编辑 + 企业感 |
| **demo 屏录**（实操"真跑给人看"）| screencast.py | Playwright 自动录 web/HTML 报告 |

### 制作流程（每集）

1. **脚本**：从 `workspace/ai-landing-tutorial-series/ENX-脚本.md` 取（已有旁白 + [画面：...] 提示，**不需 stage1-3 创作**）
2. **钩子片段**（30s 数据冲击）：`/clipforge` 指定 `tutorial` 分类
   - 横屏 1920×1080（s6_assemble 读 design.md `orientation: landscape` 自动切，§6.12 横屏视觉增强）
   - GSAP 数据飞升动画（如 +104%/76.6%/-16.4pp 依次弹出）—— 冲击力强于 PowerPoint 内置动画
3. **主体片段**（方法论/流程图/数据图表）：**ppt-master**（`D:/AI-Agent/github-analyze/ppt-master`）
   - 在 ppt-master 项目（Claude Code/AI IDE）从教程内容生成 PPTX（原生可编辑）
   - 选数据可视化强的模板（如 `examples/ppt169_global_ai_capital_2026` 的 Bloomberg dark dashboard 风，chart-driven）
   - 用 `scripts/screencast.py` 录 `viewer.html`（翻页 + slide 动画）→ mp4
4. **demo 屏录**（实操）：`scripts/screencast.py`
   - web demo / 教程页 / HTML 报告：直接录 URL（scroll/click）
   - CLI demo（如 ai-metrics `python main.py`）：先跑命令生成 HTML 报告，再录报告页
5. **旁白**：自己配（专业 + 可信 > AI 配音）。TTS 兜底：YunjianNeural +0%
6. **合成**：剪映/Premiere（钩子 ClipForge + 主体 PPT 录屏 + demo 屏录 + 旁白 + 字幕 + BGM）

### ClipForge 在 tutorial 的角色

**钩子片段生成器**（视觉冲击段）。主体方法论/数据图表用 ppt-master（更专业 + 原生图表 + 可编辑）。整片由用户剪映合成。

### ppt-master 录屏工作流

```bash
# 1. 在 ppt-master 项目用 AI 从教程内容生成 PPTX（Claude Code/AI IDE）
#    输出 projects/<name>/exports/<name>.pptx，viewer.html 可预览

# 2. 用 screencast.py 录 viewer.html（?project=<name> 加载 PPT，next:N 翻页录屏）
python scripts/screencast.py \
  --url "file:///D:/AI-Agent/github-analyze/ppt-master/viewer.html?project=<name>" \
  --output screencast-ppt-main.mp4 \
  --duration 60 \
  --actions "wait:3,next:10,wait:2"   # next:N = 按 N 次 ArrowRight 翻页，每页停留 duration/N
```

### screencast.py 屏录示例

```bash
# 录教程页（缓慢滚动展示）
python scripts/screencast.py --url "file:///D:/AI-Agent/ai-landing-tutorial/index.html" --output screencast-intro.mp4 --duration 15

# 录 ai-metrics 报告（先跑 main.py 生成 HTML 报告，再录报告页）
cd D:/AI-Agent/ai-landing-tutorial/demos/ai-metrics && python main.py
python scripts/screencast.py --url "file:///D:/AI-Agent/ai-landing-tutorial/demos/ai-metrics/report.html" --output screencast-ai-metrics.mp4 --duration 20 --actions "scroll:5000,wait:3"

# 录 ppt-master viewer（PPT 主体，翻页录屏）
python scripts/screencast.py --url "file:///D:/AI-Agent/github-analyze/ppt-master/viewer.html?project=<name>" --output screencast-ppt.mp4 --duration 60 --actions "wait:3,next:10,wait:2"
```

> screencast.py actions 支持：`scroll:距离` / `wait:秒` / `click:选择器` / `type:选择器=文本` / `next:次数`（PPT viewer 翻页，按 ArrowRight）。
