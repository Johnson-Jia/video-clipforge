---
name: stage7-delivery
description: 交付 — 封面生成 + 视频首帧嵌入 + 抖音文案
version: "1.0.0"
type: EXECUTIVE
rigor: STANDARD
dependencies: ["clipforge.stage6-production"]
---

# Stage 7: 交付 + 封面 + 抖音文案

> 当 `output.mp4` 已存在且 `final.mp4` 不存在时触发。

## Intent
> 生成封面、嵌入视频第一帧、产出抖音文案。
> 成功标准：封面 cover.png 存在且通过结构检查、双版本 final 存在且有时长/音频、文案合规。

## Boundary — 行为准则

### 必须遵守（HARD 规则 · 正向重述）

1. **使用 assemble_final.sh** — 封面嵌入必须通过脚本执行，内置时长/音频断言 ← `R-STAGE7-001`
   ↳ 校验：脚本调用记录存在
2. **产出双版本 final** — final.mp4 + final_no_bgm.mp4 都必须存在 ← `R-STAGE7-002`
   ↳ 校验：两个文件都存在且非空
3. **封面白屏检查** — 封面渲染后必须检查是否白屏 ← `R-STAGE7-003`
   ↳ 校验：白屏检查步骤已执行
4. **文案合规** — 抖音文案不含广告敏感词 ← `R-GLOBAL-001`
   ↳ 校验：文案中无"必装""神器"等词
5. **评论区不放链接** — 评论区只列名称+搜索指引 ← `R-GLOBAL-012`
   ↳ 校验：评论区无 URL
6. **时长不膨胀** — final.mp4 时长 ≤ output.mp4 + 5s ← `R-STAGE7-007`
   ↳ 校验：ffprobe 比较时长差 ≤ 5s
7. **音频轨完整** — 两个 final 文件都有音频轨道 ← `R-STAGE7-008`
   ↳ 校验：ffprobe 检测音频轨道存在

### 建议参考（偏好）
- 文案首选爆款钩子型（量化锚定 + 反直觉）（HIGH）
- CTA 使用通用时间表述 ← `R-GLOBAL-009`（SOFT）

## Guard — 认知守卫

| 当你产生这个念头 | 现实是 | 触发行为 |
|---|---|---|
| "封面只有一帧不用检查白屏" | 封面 HTML 复杂度高，同样可能白屏 | 执行白屏检查 |
| "我自己写 ffmpeg 拼接更快" | 历史事故：自行拼接导致 361s 无音频 | 使用 assemble_final.sh |
| "放个链接方便用户" | 评论区禁止放完整链接 | 只放名称 |
| "文案用'必装神器'更有吸引力" | 广告审查敏感词导致限流或下架 | 使用限定性表述 |

### Spirit vs Letter
| 规则 | 解释模式 | 真实意图 |
|---|---|---|
| R-STAGE7-001 | SPIRIT | 防止自行拼接导致时长膨胀和音频丢失 |
| R-STAGE7-002 | SPIRIT | 确保用户有无 BGM 两个版本可选 |

## Gate — 通过标准

### 流程门禁（自动化检查，不通过 = 驳回，max_retries: 2）
- [ ] `cover_existence` — cover.html 和 cover.png 都存在且非空
- [ ] `dual_final_output` — final.mp4 和 final_no_bgm.mp4 都存在
- [ ] `assembly_script` — 通过 assemble_final.sh 执行
- [ ] `duration_check` — final.mp4 时长 ≤ output.mp4 + 5s
- [ ] `audio_track` — 两个 final 文件都有音频轨道

### 合规门禁（关键词/正则匹配，不通过 = 驳回）
- [ ] `no_sensitive_words` — 抖音文案不含 R-GLOBAL-001 广告敏感词
- [ ] `no_url_in_copy` — 文案和评论区无完整 URL（R-GLOBAL-010/012）
- [ ] `hashtags_count` — 标签数量 ≥ 5 个
- [ ] `no_engagement_bait` — 文案不含"点赞关注""一键三连"等诱导互动语（R-GLOBAL-006）
- [ ] `no_specific_time` — CTA 不含具体更新时间（如"每天7点"，R-GLOBAL-009）
- [ ] `cover_no_url` — 封面中不包含任何网址
- [ ] `cover_chinese_date` — 封面包含中文日期标识
- [ ] `cover_readability` — 封面缩小到 100px 宽时主标题仍可辨认

### 质量门禁（创意评价，不通过 = 记录但放行，evaluator: HUMAN）
- `cover_quality`: 评分 ≥ 0.7（人类评价：整体视觉冲击力、信息层次清晰度、与视频风格一致性）
- `copy_engagement`: 评分 ≥ 0.7（人类评价：文案吸引力、钩子强度、与目标受众的契合度）

## Trace — 采集点
- **执行开始**：记录 output.mp4 时长和文件大小
- **封面完成**：记录渲染方式（A/B/C 降级）、结构检查结果、设计方案描述
- **嵌入完成**：记录 final.mp4/final_no_bgm.mp4 时长
- **文案完成**：记录文案风格选择、标签列表
- **执行结束**：记录 gate_report，写入 `{project_dir}/trace/stage7-{timestamp}.yaml`

## 操作指令

### 7.0 前置检查（进入 Stage 7 前必须通过）

```bash
# 检查 Stage 6 产出物完整性
[ -s output.mp4 ] || { echo "FAIL: output.mp4 缺失，Stage 6 未完成"; exit 1; }
[ -s output_no_bgm.mp4 ] || { echo "FAIL: output_no_bgm.mp4 缺失，Stage 6 未完成（必须渲染双版本）"; exit 1; }
[ -s index.html ] || { echo "FAIL: index.html 缺失"; exit 1; }
echo "Stage 7 前置检查通过"
```

> **如果 `output_no_bgm.mp4` 不存在，必须回退到 Stage 6 的 §6.7 补充渲染，不得跳过。**

### 7.1 封面生成（必须执行）

视频发布前，**必须生成一张封面图**。封面是用户刷到视频时的第一印象，决定了是否点击观看。

#### 封面设计原则

> **视觉风格复用 `design.md` 的配色和字体变量**（与视频保持一致）。

##### 结构约束（流程层 — 必须遵守）

- **尺寸**：HTML 使用 2160×3840（2x 超采样），最终输出 1080×1920 PNG
- **必要元素**：封面必须包含以下信息元素（具体布局自由设计）：
  - 日期标识（中文格式，如"2026年5月20日"）
  - 主标题（与视频主题相关）
  - 至少 1 个数据亮点（如涨星数、项目数等）
- **背景**：必须有背景层（渐变/纯色/纹理），不可纯白或纯黑
- **文字可读性**：缩小到 100px 宽时主标题仍可辨认
- **无 URL**：封面不包含任何网址
- **渲染方案**：HyperFrames 隔离渲染 > Chrome headless > ffmpeg 提取（降级顺序）

##### 创意空间（内容层 — Agent 自主决策）

Agent 根据当天内容特点自由设计封面布局，包括但不限于：

- **布局结构**：纵向排列、网格、卡片式、杂志式等均可
- **层数和元素**：根据信息密度决定，简单内容可 3-4 层，丰富内容可 7+ 层
- **字号/间距**：根据标题长度和信息量自主调整
- **配色方案**：复用 design.md 的 color_direction，具体明暗/冷暖比例自主决定
- **装饰元素**：光晕、渐变线、徽章、卡片等按需使用

##### 参考模板（来自爆款案例，供参考而非强制）

以下 7 层结构来自 05-19 爆款案例（11万播放），是一种验证有效的设计方案：

1. 中文日期（~80px，主强调色）
2. 场景标签（~64px，浅蓝色）
3. 胶囊徽章（~64px，主强调色背景+文字）
4. 主标题（~220px，双色，字重 900）
5. 渐变分隔线（~900px 宽）
6. 数据说明（~88px，浅蓝色）
7. 双数据卡片（数字 ~120px + 标签 ~52px）

> **这不是唯一正确的设计。** Agent 可以根据内容创作不同的封面方案。但如果缺乏设计灵感，此模板是安全的默认选择。

#### 封面尺寸

**HTML 使用 2160×3840（2x 超采样），最终输出 1080×1920 PNG。**

在项目目录下创建 `cover.html`（2160×3840），所有字号/间距/圆角同步翻倍，渲染后缩放至 1080×1920 输出为 `cover.png`。封面 HTML 和 PNG 均存放在项目目录内。

**渲染方案优先级：**
1. **HyperFrames 隔离渲染**（首选）：复制 `cover.html` 到临时目录 → `npx hyperframes render .` → 提取第一帧 → Lanczos 缩放
2. **Chrome headless 截图**（降级）：`chrome --headless --screenshot` → 直接输出 PNG
3. **ffmpeg 提取视频首帧**（最后降级）：`ffmpeg -i output.mp4 -vframes 1 cover.png`

#### 封面 HTML 模板

> **模板使用 CSS 变量控制配色，从 `design.md` 的 `color_direction` 读取色值填入 `:root`。** 以下是一个参考 HTML 模板（7 层结构），Agent 可根据内容自由调整层数、布局和元素。

```html
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800;900&family=JetBrains+Mono:wght@500;700&display=swap');
* { margin: 0; padding: 0; box-sizing: border-box; }

/* ── 从 design.md color_direction 读取色值 ── */
:root {
  --accent-warm: #FF8C32;      /* 主强调色（橙/金），来自 design.md */
  --accent-warm-soft: #FFA040; /* 主强调色柔化版 */
  --accent-cool: #6CB4EE;     /* 辅助色（蓝/青），来自 design.md */
  --accent-cool-mid: #4DA8DA; /* 辅助色中间色 */
  --bg-dark: #080820;         /* 深色背景，来自 design.md */
  --text-white: #FFFFFF;
  --text-muted: #8899BB;
  --card-bg: rgba(20,20,50,0.85);
  --glow-warm-opacity: 0.18;  /* 光晕强度可调 */
  --glow-cool-opacity: 0.10;
}

body { background: #050510; overflow: hidden; font-family: 'Inter', 'PingFang SC', 'Microsoft YaHei', sans-serif; }

.cover {
  position: relative; width: 2160px; height: 3840px;
  background: linear-gradient(180deg, var(--bg-dark) 0%, #0d0d2a 40%, #080818 100%);
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  overflow: hidden;
}
.glow-warm {
  position: absolute; width: 1400px; height: 1400px; border-radius: 50%;
  background: radial-gradient(circle, rgba(255,140,50,var(--glow-warm-opacity)), transparent 70%);
  filter: blur(200px); top: -200px; left: -400px; pointer-events: none;
}
.glow-cool {
  position: absolute; width: 1200px; height: 1200px; border-radius: 50%;
  background: radial-gradient(circle, rgba(0,180,255,var(--glow-cool-opacity)), transparent 70%);
  filter: blur(200px); bottom: -200px; right: -400px; pointer-events: none;
}

/* 第1层：中文日期 */
.date { position: relative; font-size: 80px; font-weight: 800;
  color: var(--accent-warm); letter-spacing: 8px; margin-bottom: 40px; }

/* 第2层：场景标签 */
.scene-label { position: relative; font-size: 64px; font-weight: 600;
  color: var(--accent-cool); letter-spacing: 6px; margin-bottom: 80px; }

/* 第3层：胶囊徽章 */
.badge { position: relative; display: inline-block;
  background: linear-gradient(135deg, rgba(255,140,50,0.15), rgba(255,107,53,0.25));
  border: 2px solid rgba(255,140,50,0.4); border-radius: 100px;
  padding: 28px 100px; font-size: 64px; font-weight: 700;
  color: var(--accent-warm-soft); letter-spacing: 8px; margin-bottom: 120px;
  box-shadow: 0 0 60px rgba(255,140,50,0.1);
}

/* 第4层：主标题（双色） */
.main-title { position: relative; text-align: center; line-height: 1.2; margin-bottom: 64px; }
.main-title .white { font-size: 220px; font-weight: 900; color: var(--text-white); letter-spacing: -4px; }
.main-title .accent { font-size: 220px; font-weight: 900; color: var(--accent-warm); letter-spacing: -4px;
  text-shadow: 0 0 80px rgba(255,140,50,0.4), 0 0 160px rgba(255,140,50,0.15); }

/* 第5层：渐变分隔线 */
.divider { position: relative; width: 900px; height: 10px; border-radius: 5px;
  background: linear-gradient(90deg, var(--accent-warm), var(--accent-cool-mid)); margin-bottom: 80px; }

/* 第6层：数据说明 */
.data-subtitle { position: relative; font-size: 88px; font-weight: 600;
  color: var(--accent-cool); letter-spacing: 4px; margin-bottom: 100px; }

/* 第7层：数据卡片 */
.cards { position: relative; display: flex; gap: 80px; }
.card { background: var(--card-bg);
  border: 2px solid rgba(255,140,50,0.2); border-radius: 48px;
  padding: 64px 100px; text-align: center; min-width: 480px;
  box-shadow: 0 8px 40px rgba(0,0,0,0.3);
}
.card .num { font-family: 'JetBrains Mono', monospace; font-size: 120px;
  font-weight: 700; color: var(--accent-warm-soft); line-height: 1; }
.card .label { font-size: 52px; color: var(--text-muted); margin-top: 24px; letter-spacing: 2px; }
</style>
</head>
<body>
<div data-composition-id="cover" data-width="2160" data-height="3840" data-start="0" data-duration="1">
<div class="clip" data-start="0" data-duration="1">
<div class="cover">
  <div class="glow-warm"></div>
  <div class="glow-cool"></div>

  <!-- 第1层：中文日期 -->
  <div class="date">{{YYYY年M月D日}}</div>
  <!-- 第2层：场景标签 -->
  <div class="scene-label">{{场景标签}}</div>
  <!-- 第3层：胶囊徽章 -->
  <div class="badge">{{徽章文案}}</div>
  <!-- 第4层：主标题 — 可单色/双色/三色，AI根据内容决定 -->
  <div class="main-title">
    <span class="white">{{白色标题}}</span><br>
    <span class="accent">{{强调色标题}}</span>
  </div>
  <!-- 第5层：渐变分隔线 -->
  <div class="divider"></div>
  <!-- 第6层：数据说明 -->
  <div class="data-subtitle">{{数据说明}}</div>
  <!-- 第7层：数据卡片 — 数量可变(1-3)，AI根据内容决定 -->
  <div class="cards">
    <div class="card">
      <div class="num">{{数字1}}</div>
      <div class="label">{{标签1}}</div>
    </div>
    <div class="card">
      <div class="num">{{数字2}}</div>
      <div class="label">{{标签2}}</div>
    </div>
  </div>
</div>
</div>
</div>
<script>window.__hf = { duration: 1, seek: function(t) {} };window.__timelines = {};</script>
</body>
</html>
```

#### 配色来源

**`:root` 变量从 `design.md` 的 `color_direction` 填充：**

| CSS 变量 | 来源 | 默认值 |
|---------|------|--------|
| `--accent-warm` | design.md `color_direction.warm` | `#FF8C32` |
| `--accent-cool` | design.md `color_direction.cool` | `#6CB4EE` |
| `--bg-dark` | design.md `color_direction.bg_dark` | `#080820` |

**布局变化允许（Agent 自主决定）：**

| 元素 | 允许的变化 |
|------|----------|
| 层数 | 3-7+ 层均可，根据内容密度决定 |
| 主标题 | 单色/双色/三色；字号自由调整 |
| 数据卡片 | 0-3 个卡片；内容格式可变 |
| 光晕 | 数量、强度、位置自由调整 |
| 装饰元素 | 渐变线、徽章、标签等按需添加 |

#### 渲染命令（3 级降级）

**方案 A — HyperFrames 隔离渲染（首选）**

```bash
mkdir -p /tmp/cover-render
cp cover.html /tmp/cover-render/index.html
cd /tmp/cover-render
npx hyperframes render . --output cover_temp.mp4 --video-bitrate 5M
ffmpeg -y -i cover_temp.mp4 -vf "select=eq(n\,0),scale=1080:1920:flags=lanczos" -vframes 1 -update 1 <项目目录>/cover.png
rm -rf /tmp/cover-render
```

**方案 B — Chrome headless 截图（降级）**

```bash
"/c/Program Files/Google/Chrome/Application/chrome.exe" \
  --headless --disable-gpu --screenshot=cover.png \
  --window-size=2160,3840 \
  "file:///$(cygpath -m $(pwd)/cover.html)"
```

**方案 C — 从视频提取首帧（最后降级）**

```bash
ffmpeg -y -i output.mp4 -vf "select=eq(n\,0)" -vframes 1 -update 1 cover.png
```

#### 封面生成后的检查

| 检查项 | 类型 | 通过标准 |
|--------|------|---------|
| 文件存在 | 流程 | `cover.html` 和 `cover.png` 都存在且非空 |
| 中文日期 | 合规 | 封面包含中文日期标识（"YYYY年M月D日"格式） |
| 无 URL | 合规 | 封面中不出现任何网址 |
| 文字可读性 | 合规 | 缩小到 100px 宽仍能看清主标题 |
| 背景存在 | 流程 | 有背景层（非纯白/纯黑） |
| 数据亮点 | 流程 | 至少包含 1 个数据亮点元素 |

#### 封面渲染自动降级

> **§7.1 完成后 `cover.png` 必须存在。** 如果首选渲染方案失败，按以下优先级自动降级，不允许跳过封面。

```bash
# 封面渲染自动降级（HyperFrames → ffmpeg 首帧）
bash .claude/commands/clipforge/scripts/render_cover.sh
```

### 7.2 封面嵌入前门禁（必须通过）

> **门禁目的：** 确保 §7.1 封面生成不会遗漏。

```bash
# 门禁：cover.html 和 cover.png 必须同时存在
[ -s cover.html ] || { echo "FAIL: cover.html 缺失，请先执行 §7.1 生成封面 HTML"; exit 1; }
[ -s cover.png ] || { echo "FAIL: cover.png 缺失，请先执行 §7.1 渲染封面"; exit 1; }
echo "封面门禁通过：cover.html + cover.png 均存在"
```

**如果门禁失败**：
1. 先回退执行 §7.1（创建 `cover.html` + 渲染 `cover.png`）
2. 门禁通过后再执行 §7.3
3. **禁止用 `ffmpeg -i output.mp4 -vframes 1 cover.png` 替代 §7.1** — 视频首帧不是封面，封面是独立设计的高品质视觉图

### 7.3 封面嵌入视频第一帧（双版本，必须执行）

> **前置依赖：§7.2 门禁已通过（`cover.html` + `cover.png` 均存在）。**

将封面作为视频第一帧嵌入，产出两个版本：`final.mp4`（含 BGM）和 `final_no_bgm.mp4`（仅旁白）。

#### 必须使用脚本，禁止自行拼接

```bash
# 封面嵌入视频第一帧，产出 final.mp4 + final_no_bgm.mp4
bash .claude/commands/clipforge/scripts/assemble_final.sh
```

> **禁止绕过 `assemble_final.sh` 自行编写 ffmpeg 拼接命令。** 历史事故：自行拼接曾导致视频时长膨胀至 6 分钟 + 音频丢失。脚本内置 TS concat + stream copy（无损拼接）+ 输出验证（时长/音频断言），能防止此类问题。

> **脚本内含硬性断言：** final.mp4 时长不得超过 output.mp4 + 5 秒，两个文件都必须有音频轨道。断言失败会 exit 1。

### 7.4 视频交付

```
视频已生成完毕（双版本）：

版本一（含 BGM）：<path>/final.mp4  (XX MB, XXs, XXX×XXXX)
版本二（无 BGM）：<path>/final_no_bgm.mp4  (XX MB, XXs, XXX×XXXX)
封面：已嵌入视频第一帧（cover.png 同步保留）

视觉风格：<从内容推导的风格>
配乐情绪：<配乐的核心情绪>
配乐来源：<yt-dlp 下载 / 音乐库 / 用户提供> — <曲目名> by <艺术家>
旁白声音：<TTS 声音名称> @ <语速>
封面标题：<钩子标题文案>

提示：无 BGM 版本（final_no_bgm.mp4）仅含旁白，可自行添加背景音乐后使用。
```

#### 磁盘用量提醒（交付时输出）

```bash
DATE_DIR="$(date +%Y)/$(date +%m)/$(date +%d)"
echo "workspace 磁盘用量：$(du -sh workspace/ 2>/dev/null | cut -f1)"
echo "   今日项目：$(ls -d workspace/${DATE_DIR}/*/ 2>/dev/null | wc -l)"
echo "   总月目录：$(ls -d workspace/????/??/ 2>/dev/null | wc -l)"
echo "   如空间不足，可执行 Stage 8 自动清理（详见 clipforge/_cleanup-rules）"
```

### 7.5 抖音文案生成

根据视频内容，生成 **3 套不同风格** 的发布文案。

**文案必须保存到 `douyin.md`**，包含 3 套文案、标签列表、评论区自评。

#### 文案风格模板

**选项 1 — 爆款钩子型（首选）**（量化锚定 + 反直觉钩子）

> **数据来源：** 爆款视频分析（05-19，11万播放）的发布文案全部用数字锚定 + 反直觉描述，播放量是纯 FOMO 型文案的 3 倍。
> **关联 Pattern：** `P-001`（量化钩子）、`P-002`（反直觉描述）

```
<量化开场：项目数 + 关键比例>（如"今天涨星最猛的 6 个项目，AI 占了一半"）
<最震撼项目的数据或反直觉描述>（如"一个 Rust 写的个人 AI 大脑，一天涨近四千星"）
<1-2 个反直觉/颠覆性特征>（如"用 WiFi 信号做空间感知，完全不用摄像头"）
<剩余项目一句话概括>
<软性号召>

#<标签1> #<标签2> #<标签3> #<标签4> #<标签5>
```

**量化锚定规则：**
- 第一句必须包含 ≥2 个数字（项目数、比例、星数等）
- 至少 1 句使用反直觉描述（参见 `_shared-rules/writing.md` §1.1）
- 不用"太强了""炸了"等情绪词，用数据代替

**选项 2 — 信息差型**（紧迫感、引导互动）

```
<注意/警告开头>
<核心信息差，口语化 1-2 句>
@<互动引导>

#<标签>
```

**选项 3 — 极简型**（短平快）

```
<一句话概括核心价值>
<一句号召关注>

#<3-5 个标签>
```

#### 文案要求

- **标题/开场**：用数字、反问、感叹开头
- **正文**：口语化短句，每句不超过 15 字
- **标签**：混合大流量 + 精准标签
- **不放网址**：链接统一放评论区自评
- **措辞规范**遵守 `clipforge/_shared-rules/writing.md` §1

#### 标签策略

> **如果分类配置中指定了 `delivery.hashtags`，优先使用分类配置的标签列表。** 未指定时按以下通用策略。

> **数据来源：** 爆款视频分析（05-19）用 5 个标签覆盖 5 个不同圈层（GitHub/开源/AI/程序员/科技），播放量是 3 标签视频的 3 倍。
> **关联 Pattern：** `P-004`（5标签跨圈覆盖）

**跨圈覆盖要求：** 标签数 ≥ 5，每个标签命中不同的受众圈层。

| 类型 | 示例 | 用途 |
|------|------|------|
| 核心圈标签 | #GitHub | 命中目标受众 |
| 领域标签 | #开源 | 命中开源圈 |
| 热点标签 | #AI | 命中当前热点圈层 |
| 身份标签 | #程序员 | 命中职业身份圈 |
| 泛流量标签 | #科技 | 获取泛流量触达 |

## Red Flags（停止信号）

| 信号 | 规则 ID | 说明 |
|------|---------|------|
| 封面嵌入跳过白屏检查 | R-STAGE7-003 | 封面 HTML 复杂度高，同样可能白屏 |
| 缺少 `final_no_bgm.mp4` | R-STAGE7-002 | 双版本输出不可省略 |
| 抖音文案含广告审查敏感词 | R-GLOBAL-001 | "必装"、"神器"等会导致审核不通过 |
| 评论区放完整链接 | R-GLOBAL-012 | 抖音审查敏感，只放项目英文名 |
| CTA 提及具体更新时间 | R-GLOBAL-009 | 禁止"每天7点更新"等具体时间 |
| 绕过 assemble_final.sh 自行拼接 | R-STAGE7-001 | 必须使用脚本，脚本内置时长/音频断言 |
| final.mp4 时长 > output.mp4 + 5s | R-STAGE7-007 | 封面拼接异常，封面帧被 loop 成长视频 |
| final.mp4 无音频轨道 | R-STAGE7-008 | 拼接时音频轨丢失 |

## Common Rationalizations（常见借口反驳）

| 借口 | 事实 |
|------|------|
| "封面只有一帧不用检查白屏" | 封面 HTML 可能包含复杂 CSS，不检查同样会出白屏事故 |
| "放个链接方便用户" | §4.1 评论区禁止放完整链接，只放名称 + 搜索指引 |
| "文案用'必装神器'更有吸引力" | §1 广告审查敏感词会导致视频被限流或下架 |
| "说'每天7点更新'能增加关注" | §3 禁止提及具体更新时间，改用通用表述"每天更新" |
| "我自己写 ffmpeg 拼接更快" | 历史事故：自行拼接导致 361s 无音频视频。必须用 assemble_final.sh 脚本 |
| "filter_complex concat 也能用" | filter_complex 会重编码主视频，导致质量损失 + PTS 错乱。TS concat + stream copy 才是正确方式 |
