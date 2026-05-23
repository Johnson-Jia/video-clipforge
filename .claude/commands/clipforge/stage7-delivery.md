# Stage 7: 交付 + 封面 + 抖音文案

当 `output.mp4` 已存在且 `final.mp4` 不存在时触发。生成封面、嵌入视频首帧、输出抖音文案。

## 7.0 前置检查（进入 Stage 7 前必须通过）

```bash
# 检查 Stage 6 产出物完整性
[ -s output.mp4 ] || { echo "FAIL: output.mp4 缺失，Stage 6 未完成"; exit 1; }
[ -s output_no_bgm.mp4 ] || { echo "FAIL: output_no_bgm.mp4 缺失，Stage 6 未完成（必须渲染双版本）"; exit 1; }
[ -s index.html ] || { echo "FAIL: index.html 缺失"; exit 1; }
echo "Stage 7 前置检查通过"
```

> **如果 `output_no_bgm.mp4` 不存在，必须回退到 Stage 6 的 §6.7 补充渲染，不得跳过。**

## 7.1 封面生成（必须执行）

视频发布前，**必须生成一张封面图**。封面是用户刷到视频时的第一印象，决定了是否点击观看。

### 封面设计原则

> **视觉风格复用 `design.md` 的配色和字体变量**（与视频保持一致），此处仅定义封面独有的结构和规则。

- **7 层视觉层次**（从上到下，缺一不可）：
  1. **中文日期**：中文格式（如"2026年5月20日"），主强调色，字号约 80px（2x 基准）
  2. **场景标签**：辅助说明（分类配置中的 `delivery.cover_scene_label`，或根据内容自定义），浅蓝色，字号约 64px
  3. **胶囊徽章**：圆角药丸形标签（分类配置中的 `delivery.cover_badge`，或根据内容自定义），主强调色半透明背景 + 主强调色文字，字号约 64px
  4. **主标题**：双色大标题，前半白色后半主强调色（如"AI编程"白 + "直接霸榜"橙），字号约 220px，字重 900
  5. **渐变分隔线**：主强调色→辅助色渐变横条（如橙→蓝），宽约 900px
  6. **数据说明**：一行辅助文案（如"9个热门项目 · AI占一半"），浅蓝色，字号约 88px
  7. **双数据卡片**：2 个深色圆角卡片并排，每卡包含一个大数字 + 小标签（如"+3973 最高涨星"、"198K 最高总星"），数字用主强调色约 120px，标签灰色约 52px
- **背景三层**：深色渐变背景 + 暖色大光晕（左上） + 冷色大光晕（右下），与视频场景风格统一
- **参考示例**：`workspace/covers/cover-test.jpg` — 后续所有封面严格参照此布局，仅替换文案和具体数字

### 封面尺寸

**HTML 使用 2160×3840（2x 超采样），最终输出 1080×1920 PNG。**

在项目目录下创建 `cover.html`（2160×3840），所有字号/间距/圆角同步翻倍，渲染后缩放至 1080×1920 输出为 `cover.png`。封面 HTML 和 PNG 均存放在项目目录内。

**渲染方案优先级：**
1. **HyperFrames 隔离渲染**（首选）：复制 `cover.html` 到临时目录 → `npx hyperframes render .` → 提取第一帧 → Lanczos 缩放
2. **Chrome headless 截图**（降级）：`chrome --headless --screenshot` → 直接输出 PNG
3. **ffmpeg 提取视频首帧**（最后降级）：`ffmpeg -i output.mp4 -vframes 1 cover.png`

### 封面 HTML 模板

> **模板严格对应 7 层视觉层次。** 替换占位符即可使用，不要删除任何层。所有封面参照 `workspace/covers/cover-test.jpg` 布局。

```html
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800;900&family=JetBrains+Mono:wght@500;700&display=swap');
* { margin: 0; padding: 0; box-sizing: border-box; }
body { background: #050510; overflow: hidden; font-family: 'Inter', 'PingFang SC', 'Microsoft YaHei', sans-serif; }

.cover {
  position: relative; width: 2160px; height: 3840px;
  background: linear-gradient(180deg, #080820 0%, #0d0d2a 40%, #080818 100%);
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  overflow: hidden;
}
.glow-warm {
  position: absolute; width: 1400px; height: 1400px; border-radius: 50%;
  background: radial-gradient(circle, rgba(255,140,50,0.18), transparent 70%);
  filter: blur(200px); top: -200px; left: -400px; pointer-events: none;
}
.glow-cool {
  position: absolute; width: 1200px; height: 1200px; border-radius: 50%;
  background: radial-gradient(circle, rgba(0,180,255,0.1), transparent 70%);
  filter: blur(200px); bottom: -200px; right: -400px; pointer-events: none;
}

/* 第1层：中文日期 */
.date { position: relative; font-size: 80px; font-weight: 800;
  color: #FF8C32; letter-spacing: 8px; margin-bottom: 40px; }

/* 第2层：场景标签 */
.scene-label { position: relative; font-size: 64px; font-weight: 600;
  color: #6CB4EE; letter-spacing: 6px; margin-bottom: 80px; }

/* 第3层：胶囊徽章 */
.badge { position: relative; display: inline-block;
  background: linear-gradient(135deg, rgba(255,140,50,0.15), rgba(255,107,53,0.25));
  border: 2px solid rgba(255,140,50,0.4); border-radius: 100px;
  padding: 28px 100px; font-size: 64px; font-weight: 700;
  color: #FFA040; letter-spacing: 8px; margin-bottom: 120px;
  box-shadow: 0 0 60px rgba(255,140,50,0.1);
}

/* 第4层：主标题（双色） */
.main-title { position: relative; text-align: center; line-height: 1.2; margin-bottom: 64px; }
.main-title .white { font-size: 220px; font-weight: 900; color: #FFFFFF; letter-spacing: -4px; }
.main-title .orange { font-size: 220px; font-weight: 900; color: #FF8C32; letter-spacing: -4px;
  text-shadow: 0 0 80px rgba(255,140,50,0.4), 0 0 160px rgba(255,140,50,0.15); }

/* 第5层：渐变分隔线 */
.divider { position: relative; width: 900px; height: 10px; border-radius: 5px;
  background: linear-gradient(90deg, #FF8C32, #4DA8DA); margin-bottom: 80px; }

/* 第6层：数据说明 */
.data-subtitle { position: relative; font-size: 88px; font-weight: 600;
  color: #6CB4EE; letter-spacing: 4px; margin-bottom: 100px; }

/* 第7层：双数据卡片 */
.cards { position: relative; display: flex; gap: 80px; }
.card { background: rgba(20,20,50,0.85);
  border: 2px solid rgba(255,140,50,0.2); border-radius: 48px;
  padding: 64px 100px; text-align: center; min-width: 480px;
  box-shadow: 0 8px 40px rgba(0,0,0,0.3);
}
.card .num { font-family: 'JetBrains Mono', monospace; font-size: 120px;
  font-weight: 700; color: #FFA040; line-height: 1; }
.card .label { font-size: 52px; color: #8899BB; margin-top: 24px; letter-spacing: 2px; }
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
  <!-- 第4层：主标题（双色） -->
  <div class="main-title">
    <span class="white">{{白色标题}}</span><br>
    <span class="orange">{{强调色标题}}</span>
  </div>
  <!-- 第5层：渐变分隔线 -->
  <div class="divider"></div>
  <!-- 第6层：数据说明 -->
  <div class="data-subtitle">{{数据说明}}</div>
  <!-- 第7层：双数据卡片 -->
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

### 渲染命令（3 级降级）

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

### 封面生成后的检查

| 检查项 | 通过标准 |
|--------|---------|
| 文件存在 | `cover.html` 和 `cover.png` 都存在且非空 |
| 7 层完整性 | 日期区 ✓ 场景标签 ✓ 胶囊徽章 ✓ 主标题 ✓ 渐变分隔线 ✓ 数据说明 ✓ 数据卡片 ✓ |
| 背景三层 | 渐变背景 ✓ 双色光晕 ✓ 网格底纹 ✓ |
| 文字可读性 | 缩小到 100px 宽仍能看清主标题 |
| 日期标识 | 封面包含中文日期（"YYYY年M月D日"格式） |
| 字号足够 | 主标题 ≥ 80px，副标题 ≥ 40px，日期 ≥ 28px |
| 无 URL | 封面中不出现任何网址 |

### 封面渲染自动降级

> **§7.1 完成后 `cover.png` 必须存在。** 如果首选渲染方案失败，按以下优先级自动降级，不允许跳过封面。

```bash
# 检查封面是否已生成
if [ ! -s cover.png ]; then
  echo "cover.png 缺失，尝试降级渲染..."

  # 方案 A: HyperFrames 隔离渲染
  mkdir -p /tmp/cover-render 2>/dev/null || mkdir -p "$TEMP/cover-render"
  cp cover.html "$TEMP/cover-render/index.html" 2>/dev/null
  if npx hyperframes render "$TEMP/cover-render" --output "$TEMP/cover-render/cover.mp4" --video-bitrate 5M 2>/dev/null; then
    ffmpeg -y -i "$TEMP/cover-render/cover.mp4" -vf "select=eq(n\,0),scale=1080:1920:flags=lanczos" -vframes 1 -update 1 cover.png 2>/dev/null
    rm -rf "$TEMP/cover-render"
  fi

  # 方案 B: ffmpeg 从视频首帧提取（最后降级）
  if [ ! -s cover.png ]; then
    ffmpeg -y -i output.mp4 -vf "select=eq(n\,0)" -vframes 1 -update 1 cover.png 2>/dev/null
    echo "WARNING: 使用视频首帧作为封面降级方案，建议手动制作正式封面"
  fi

  [ -s cover.png ] || { echo "FAIL: 所有封面渲染方案失败"; exit 1; }
  echo "cover.png 已生成（降级方案）"
fi
```

## 7.2 封面嵌入前门禁（必须通过）

> **事故复盘 05-22**：执行时跳过了 §7.1 封面生成，直接从视频提取首帧嵌入，导致无 `cover.html` 和 `cover.png`。以下门禁确保封面不会遗漏。

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

## 7.3 封面嵌入视频第一帧（双版本，必须执行）

> **前置依赖：§7.2 门禁已通过（`cover.html` + `cover.png` 均存在）。**

将封面作为视频第一帧嵌入，产出两个版本：`final.mp4`（含 BGM）和 `final_no_bgm.mp4`（仅旁白）。

### 封面片段制备（共用）

```bash
# 1. 探测视频帧率，计算 1 帧时长
FPS=$(ffprobe -v quiet -show_entries stream=r_frame_rate -select_streams v -of csv=p=0 output.mp4 | head -1)
FPS_NUM=$(echo "$FPS" | cut -d/ -f1)
FRAME_DUR=$(awk "BEGIN {printf \"%.4f\", 1/$FPS_NUM}")

# 2. 将封面 PNG 转为 1 帧视频片段
ffmpeg -y -loop 1 -i cover.png -c:v libx264 -b:v 5M -t $FRAME_DUR \
  -pix_fmt yuv420p -r $FPS_NUM cover_clip.mp4
```

### 版本一：含 BGM（final.mp4）

```bash
ffmpeg -y -i cover_clip.mp4 -i output.mp4 \
  -filter_complex "[0:v][1:v]concat=n=2:v=1:a=0[outv]" \
  -map "[outv]" -map 1:a \
  -c:v libx264 -b:v 5M -c:a copy \
  final.mp4
```

### 版本二：无 BGM（final_no_bgm.mp4）

```bash
ffmpeg -y -i cover_clip.mp4 -i output_no_bgm.mp4 \
  -filter_complex "[0:v][1:v]concat=n=2:v=1:a=0[outv]" \
  -map "[outv]" -map 1:a \
  -c:v libx264 -b:v 5M -c:a copy \
  final_no_bgm.mp4
```

### 清理 + 验证

```bash
rm -f cover_clip.mp4

# 确认两个版本第一帧都是封面
ffmpeg -y -i final.mp4 -vf "select=eq(n\,0)" -vframes 1 verify_cover.png
ffmpeg -y -i final_no_bgm.mp4 -vf "select=eq(n\,0)" -vframes 1 verify_no_bgm.png
rm -f verify_cover.png verify_no_bgm.png
```

> **封面仅占 1 帧**，对视频时长影响可忽略。`-b:v 5M` 与 Stage 6 渲染码率一致，避免拼接降质。

## 7.4 视频交付

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

### 磁盘用量提醒（交付时输出）

```bash
DATE_DIR="$(date +%Y)/$(date +%m)/$(date +%d)"
echo "workspace 磁盘用量：$(du -sh workspace/ 2>/dev/null | cut -f1)"
echo "   今日项目：$(ls -d workspace/${DATE_DIR}/*/ 2>/dev/null | wc -l)"
echo "   总月目录：$(ls -d workspace/????/??/ 2>/dev/null | wc -l)"
echo "   如空间不足，可执行 Stage 8 自动清理（详见 clipforge/_cleanup-rules）"
```

## 7.5 抖音文案生成

根据视频内容，生成 **3 套不同风格** 的发布文案。

**文案必须保存到 `douyin.md`**，包含 3 套文案、标签列表、评论区自评。

### 文案风格模板

**选项 1 — 爆款钩子型（首选）**（量化锚定 + 反直觉钩子）

> **数据来源：** 爆款视频分析（05-19，11万播放）的发布文案全部用数字锚定 + 反直觉描述，播放量是纯 FOMO 型文案的 3 倍。

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
- 至少 1 句使用反直觉描述（参见 `_shared-rules` §1.1）
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

### 文案要求

- **标题/开场**：用数字、反问、感叹开头
- **正文**：口语化短句，每句不超过 15 字
- **标签**：混合大流量 + 精准标签
- **不放网址**：链接统一放评论区自评
- **措辞规范**遵守 `clipforge/_shared-rules` §1

### 标签策略

> **如果分类配置中指定了 `delivery.hashtags`，优先使用分类配置的标签列表。** 未指定时按以下通用策略。

> **数据来源：** 爆款视频分析（05-19）用 5 个标签覆盖 5 个不同圈层（GitHub/开源/AI/程序员/科技），播放量是 3 标签视频的 3 倍。

**跨圈覆盖要求：** 标签数 ≥ 5，每个标签命中不同的受众圈层。

| 类型 | 示例 | 用途 |
|------|------|------|
| 核心圈标签 | #GitHub | 命中目标受众 |
| 领域标签 | #开源 | 命中开源圈 |
| 热点标签 | #AI | 命中当前热点圈层 |
| 身份标签 | #程序员 | 命中职业身份圈 |
| 泛流量标签 | #科技 | 获取泛流量触达 |

---

## Red Flags（停止信号）

| 信号 | 说明 |
|------|------|
| 封面嵌入跳过白屏检查 | 封面 HTML 复杂度高，同样可能白屏 |
| 缺少 `final_no_bgm.mp4` | 双版本输出不可省略 |
| 抖音文案含广告审查敏感词 | "必装"、"神器"等会导致审核不通过（§1） |
| 评论区放完整链接 | 抖音审查敏感，只放项目英文名 |
| CTA 提及具体更新时间 | §3 禁止"每天7点更新"等具体时间 |

## Common Rationalizations（常见借口反驳）

| 借口 | 事实 |
|------|------|
| "封面只有一帧不用检查白屏" | 封面 HTML 可能包含复杂 CSS，不检查同样会出白屏事故 |
| "放个链接方便用户" | §4.1 评论区禁止放完整链接，只放名称 + 搜索指引 |
| "文案用'必装神器'更有吸引力" | §1 广告审查敏感词会导致视频被限流或下架 |
| "说'每天7点更新'能增加关注" | §3 禁止提及具体更新时间，改用通用表述"每天更新" |
