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
  7. **双数据卡片**：2 个深色圆角卡片并排，每卡包含一个大数字 + 小标签（如{{delivery.cover_data_examples|核心数据}}），数字用主强调色约 120px，标签灰色约 52px
- **背景三层**：深色渐变背景 + 暖色大光晕（左上） + 冷色大光晕（右下），与视频场景风格统一
- **参考示例**：`workspace/covers/cover-test.jpg` — 后续所有封面严格参照此布局，仅替换文案和具体数字

### 封面尺寸

**竖屏：** HTML 使用 2160×3840（2x 超采样），最终输出 1080×1920 PNG。
**横屏：** HTML 使用 3840×2160（2x 超采样），最终输出 1920×1080 PNG。

方向由 `output.mp4` 分辨率决定：`h > w` 为竖屏，`w > h` 为横屏。

在项目目录下创建 `cover.html`（2x 尺寸），所有字号/间距/圆角同步翻倍，渲染后缩放至 1x 尺寸输出为 `cover.png`。封面 HTML 和 PNG 均存放在项目目录内。

横屏封面所有内容限制在水平居中的 **3:4 安全区**（HTML 1620×2160，输出 810×1080）内，背景装饰（光晕、网格）填充全画布。
- 安全区通过 `.safe-zone` 包裹层实现（`width:1620px; margin:0 auto; height:100%`）
- 7 层在安全区内**垂直堆叠**（与竖屏一致），不使用水平分组
- 抖音封面展示区域为 3:4（1080×1440），横屏封面裁切后只有中间 ~810px 可见
- 字号使用横屏标准（director-toolkit.md 横屏排版表）

**渲染方案优先级：**
1. **HyperFrames 隔离渲染**（首选）：复制 `cover.html` 到临时目录 → `npx hyperframes render .` → 提取第一帧 → Lanczos 缩放
2. **Chrome headless 截图**（降级）：`chrome --headless --screenshot` → 直接输出 PNG
3. **ffmpeg 提取视频首帧**（最后降级）：`ffmpeg -i output.mp4 -vframes 1 cover.png`

### 封面 HTML 模板

> **封面铁律：布局严格按模板，创意体现在内容层。**
>
> **不可变更（结构性）：** `.cover` 包裹容器、7 层的 CSS class 名（`.date` `.scene-label` `.badge` `.main-title` `.divider` `.data-subtitle` `.cards`）、光晕定位（`.glow-warm` 左上 / `.glow-cool` 右下 / `blur(200px)`）、字体族（`Inter` + `JetBrains Mono`）、`:root` CSS 变量机制、`data-composition-id` + `data-width` + `data-height` 结构。
>
> **AI 创意域（内容层）：** CSS 变量的色值（从 `design.md` 读取填充）、主标题文案及分色方案（单色/双色/三色）、数据卡片数量（1-3 个）及内容、光晕透明度、分隔线渐变方向、场景标签和徽章文案。
>
> **禁止：** 将 `.cover` 改名为 `.container` 或其他名称、绕过 CSS 变量直接硬编码色值、更换字体族、重新排列 7 层顺序、添加模板中没有的额外层、删除任何一层。
>
> **封面是纯静态文档。** 封面被渲染为 PNG 截图，动画永远不会播放。`fromTo opacity:0` 等初始隐藏动画会导致截图白屏。规则：
> - 所有视觉效果必须通过纯 CSS 实现（渐变、box-shadow、filter、opacity 直接设值）
> - **禁止 `<script src="...">` 外部脚本引用**（GSAP、anime.js 等动画库）
> - **禁止内联 GSAP/JS 动画代码**（fromTo、to、set 等）
> - 唯一允许的 `<script>` 是模板中的 HyperFrames 兼容声明（`window.__hf`），不得修改或扩展

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

### 横屏封面模板（3:4 安全区）

> 横屏封面画布 3840×2160（2x），所有内容通过 `.safe-zone` 限制在水平居中的 1620px 宽度内。背景装饰（光晕、网格）填充全画布。不可变更项与竖屏一致，额外增加 `.safe-zone` 为横屏必选。

```html
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800;900&family=JetBrains+Mono:wght@500;700&display=swap');
* { margin: 0; padding: 0; box-sizing: border-box; }

:root {
  --accent-warm: #FF8C32;
  --accent-warm-soft: #FFA040;
  --accent-cool: #6CB4EE;
  --accent-cool-mid: #4DA8DA;
  --bg-dark: #080820;
  --text-white: #FFFFFF;
  --text-muted: #8899BB;
  --card-bg: rgba(20,20,50,0.85);
  --glow-warm-opacity: 0.18;
  --glow-cool-opacity: 0.10;
}

body { background: #050510; overflow: hidden; font-family: 'Inter', 'PingFang SC', 'Microsoft YaHei', sans-serif; }

.cover {
  position: relative; width: 3840px; height: 2160px;
  background: linear-gradient(180deg, var(--bg-dark) 0%, #0d0d2a 40%, #080818 100%);
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

/* 3:4 安全区（1620×2160 水平居中） */
.safe-zone {
  position: relative; z-index: 5;
  width: 1620px; height: 100%;
  margin: 0 auto;
  display: flex; flex-direction: column;
  align-items: center; justify-content: center;
}

/* 第1层：中文日期 */
.date { position: relative; font-size: 56px; font-weight: 800;
  color: var(--accent-warm); letter-spacing: 6px; margin-bottom: 24px; }

/* 第2层：场景标签 */
.scene-label { position: relative; font-size: 44px; font-weight: 600;
  color: var(--accent-cool); letter-spacing: 4px; margin-bottom: 48px; }

/* 第3层：胶囊徽章 */
.badge { position: relative; display: inline-block;
  background: linear-gradient(135deg, rgba(255,140,50,0.15), rgba(255,107,53,0.25));
  border: 2px solid rgba(255,140,50,0.4); border-radius: 100px;
  padding: 20px 72px; font-size: 44px; font-weight: 700;
  color: var(--accent-warm-soft); letter-spacing: 6px; margin-bottom: 72px;
  box-shadow: 0 0 40px rgba(255,140,50,0.1);
}

/* 第4层：主标题（双色） */
.main-title { position: relative; text-align: center; line-height: 1.2; margin-bottom: 40px; }
.main-title .white { font-size: 160px; font-weight: 900; color: var(--text-white); letter-spacing: -3px; }
.main-title .accent { font-size: 160px; font-weight: 900; color: var(--accent-warm); letter-spacing: -3px;
  text-shadow: 0 0 60px rgba(255,140,50,0.4), 0 0 120px rgba(255,140,50,0.15); }

/* 第5层：渐变分隔线 */
.divider { position: relative; width: 600px; height: 8px; border-radius: 4px;
  background: linear-gradient(90deg, var(--accent-warm), var(--accent-cool-mid)); margin-bottom: 48px; }

/* 第6层：数据说明 */
.data-subtitle { position: relative; font-size: 60px; font-weight: 600;
  color: var(--accent-cool); letter-spacing: 3px; margin-bottom: 60px; }

/* 第7层：数据卡片 */
.cards { position: relative; display: flex; gap: 48px; }
.card { background: var(--card-bg);
  border: 2px solid rgba(255,140,50,0.2); border-radius: 36px;
  padding: 40px 72px; text-align: center; min-width: 320px;
  box-shadow: 0 8px 32px rgba(0,0,0,0.3);
}
.card .num { font-family: 'JetBrains Mono', monospace; font-size: 88px;
  font-weight: 700; color: var(--accent-warm-soft); line-height: 1; }
.card .label { font-size: 36px; color: var(--text-muted); margin-top: 16px; letter-spacing: 2px; }
</style>
</head>
<body>
<div data-composition-id="cover" data-width="3840" data-height="2160" data-start="0" data-duration="1">
<div class="clip" data-start="0" data-duration="1">
<div class="cover">
  <div class="glow-warm"></div>
  <div class="glow-cool"></div>

  <!-- 3:4 安全区：所有内容层限制在此 -->
  <div class="safe-zone">
    <!-- 第1层：中文日期 -->
    <div class="date">{{YYYY年M月D日}}</div>
    <!-- 第2层：场景标签 -->
    <div class="scene-label">{{场景标签}}</div>
    <!-- 第3层：胶囊徽章 -->
    <div class="badge">{{徽章文案}}</div>
    <!-- 第4层：主标题 -->
    <div class="main-title">
      <span class="white">{{白色标题}}</span><br>
      <span class="accent">{{强调色标题}}</span>
    </div>
    <!-- 第5层：渐变分隔线 -->
    <div class="divider"></div>
    <!-- 第6层：数据说明 -->
    <div class="data-subtitle">{{数据说明}}</div>
    <!-- 第7层：数据卡片 -->
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
</div>
<script>window.__hf = { duration: 1, seek: function(t) {} };window.__timelines = {};</script>
</body>
</html>
```

### 配色来源

**`:root` 变量从 `design.md` 的 `color_direction` 填充：**

| CSS 变量 | 来源 | 默认值 |
|---------|------|--------|
| `--accent-warm` | design.md `color_direction.warm` | `#FF8C32` |
| `--accent-cool` | design.md `color_direction.cool` | `#6CB4EE` |
| `--bg-dark` | design.md `color_direction.bg_dark` | `#080820` |

**创意域边界（严格区分）：**

| 类别 | 项目 | 规则 |
|------|------|------|
| **不可变更** | CSS class 名 | 必须使用模板中的 `.cover` `.date` `.scene-label` `.badge` `.main-title` `.divider` `.data-subtitle` `.cards` `.card`（横屏额外必须包含 `.safe-zone`） |
| **不可变更** | 容器结构 | 竖屏：`.cover` 根容器 → 7 层按模板顺序。横屏：`.cover` 根容器 → `.safe-zone` 安全区 → 7 层按模板顺序 |
| **不可变更** | 光晕定位 | `.glow-warm` 左上 `top:-200px;left:-400px` / `.glow-cool` 右下 `bottom:-200px;right:-400px` / `blur(200px)` |
| **不可变更** | 字体族 | `Inter`（正文）+ `JetBrains Mono`（数字），通过 Google Fonts 引入 |
| **不可变更** | 配色机制 | 色值通过 `:root` CSS 变量控制，禁止在子元素中硬编码 `color:` 覆盖变量 |
| **不可变更** | 7 层完整性 | 每一层必须存在且按顺序排列，不可省略或调换 |
| **AI 创意域** | 色值 | `:root` 变量的值从 `design.md` 的 `color_direction` 读取填充 |
| **AI 创意域** | 主标题（第4层） | 单色/双色/三色方案自由选择；字号 180-260px |
| **AI 创意域** | 数据卡片（第7层） | 1-3 个卡片；内容和标签自由填写 |
| **AI 创意域** | 光晕强度 | `--glow-warm-opacity` 0.1-0.25，`--glow-cool-opacity` 0.05-0.15 |
| **AI 创意域** | 分隔线渐变 | 渐变方向和色值可变（但必须用 CSS 变量） |

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
| 7 层完整性 | `.date` ✓ `.scene-label` ✓ `.badge` ✓ `.main-title` ✓ `.divider` ✓ `.data-subtitle` ✓ `.cards` ✓ |
| 容器结构 | 根元素使用 `.cover` class（非 `.container` 或其他名称）；横屏封面必须包含 `.safe-zone` 包裹层 |
| CSS 变量 | `:root` 中定义了 `--accent-warm` `--accent-cool` `--bg-dark` 等变量，子元素引用变量而非硬编码色值 |
| 字体引入 | HTML 包含 Google Fonts `Inter` 和 `JetBrains Mono` 的 `@import` |
| 光晕定位 | `.glow-warm` 位于左上、`.glow-cool` 位于右下、均使用 `blur(200px)` |
| 背景三层 | 渐变背景 ✓ 双色光晕 ✓ |
| 文字可读性 | 缩小到 100px 宽仍能看清主标题 |
| 日期标识 | 封面包含中文日期（"YYYY年M月D日"格式） |
| 字号足够 | 主标题 ≥ 80px，副标题 ≥ 40px，日期 ≥ 28px |
| 无 URL | 封面中不出现任何网址 |
| 无多余层 | 除了模板定义的 7 层 + 2 个光晕 + 背景渐变外，不存在额外装饰层 |

### 封面渲染自动降级

> **§7.1 完成后 `cover.png` 必须存在。** 如果首选渲染方案失败，按以下优先级自动降级，不允许跳过封面。

```bash
# 封面渲染自动降级（HyperFrames → ffmpeg 首帧）
bash .claude/commands/clipforge/scripts/render_cover.sh
```

## 7.2 封面嵌入前门禁（必须通过）

> **门禁目的：** 确保 §7.1 封面生成不会遗漏。

```bash
# 门禁 1：cover.html 和 cover.png 必须同时存在
[ -s cover.html ] || { echo "FAIL: cover.html 缺失，请先执行 §7.1 生成封面 HTML"; exit 1; }
[ -s cover.png ] || { echo "FAIL: cover.png 缺失，请先执行 §7.1 渲染封面"; exit 1; }
echo "封面存在性检查通过"

# 门禁 2：封面 7 层完整性检查（IRON LAW）
python .claude/commands/clipforge/scripts/cover_check.py cover.html
# 退出码非 0 = 封面不合规，必须重建 cover.html 后重新渲染
```

**如果门禁失败**：
1. 先回退执行 §7.1（创建 `cover.html` + 渲染 `cover.png`）
2. 门禁通过后再执行 §7.3
3. **禁止用 `ffmpeg -i output.mp4 -vframes 1 cover.png` 替代 §7.1** — 视频首帧不是封面，封面是独立设计的高品质视觉图

## 7.3 封面嵌入视频第一帧（双版本，必须执行）

> **前置依赖：§7.2 门禁已通过（`cover.html` + `cover.png` 均存在）。**

将封面作为视频第一帧嵌入，产出两个版本：`final.mp4`（含 BGM）和 `final_no_bgm.mp4`（仅旁白）。

### 必须使用脚本，禁止自行拼接

```bash
# 封面嵌入视频第一帧，产出 final.mp4 + final_no_bgm.mp4
bash .claude/commands/clipforge/scripts/assemble_final.sh
```

> **禁止绕过 `assemble_final.sh` 自行编写 ffmpeg 拼接命令。** 脚本内置 TS concat + stream copy（无损拼接）+ 输出验证（时长/音频断言）。

> **脚本内含硬性断言：** final.mp4 时长不得超过 output.mp4 + 5 秒，两个文件都必须有音频轨道。断言失败会 exit 1。

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
echo "   如空间不足，可执行 Stage 8 自动清理（详见 clipforge/shared/cleanup-rules）"
```

## 7.5 抖音文案生成

根据视频内容，生成 **3 套不同风格** 的发布文案。

**文案必须保存到 `douyin.md`**，包含 3 套文案、标签列表、评论区自评。

> **数据来源（2026-05-27 三平台分析）：**
> - 抖音：反直觉/冲突标题模式平均 46,596 播放，数字钩子 42,783，直接叙述仅 5,363
> - 视频号：分享率 4-5% 是增长杠杆（30 条视频总分享 6,002）
> - 小红书：收藏是点赞的 1.9 倍（13,150 收藏 vs 6,973 点赞），内容有参考价值属性

### 文案风格模板

**选项 1 — 爆款钩子型（首选）**（量化锚定 + 反直觉钩子）

> **数据来源：** 爆款视频分析（05-19，11万播放）+ 2026-05-27 全量数据验证。数字锚定 + 反直觉描述模式平均播放量是直接叙述的 8 倍。

```
<量化开场：项目数 + 关键比例>（如"{{delivery.hook_template_example|核心发现 + 关键比例}}"）
<最震撼项目的数据或反直觉描述>（如"一个 Rust 写的个人 AI 大脑，一天涨近四千星"）
<1-2 个反直觉/颠覆性特征>（如"用 WiFi 信号做空间感知，完全不用摄像头"）
<剩余项目一句话概括>
<软性号召>

#<标签1> #<标签2> #<标签3> #<标签4> #<标签5>
```

**量化锚定规则：**
- 第一句必须包含 ≥2 个数字（项目数、比例、星数等）
- 至少 1 句使用反直觉描述（参见 `shared/shared-rules` §1.1）
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

### 跨平台发布策略

> **同一视频在不同平台发布时，文案策略应不同。**

| 平台 | 核心指标 | 文案策略 | 互动引导 |
|------|---------|---------|---------|
| 抖音 | 5s 完播率 | 反直觉钩子 + 数字锚定（选项 1） | 自然引导关注 |
| 视频号 | 分享率（4-5% 为优秀） | 加入"转发给做开发的朋友"等分享暗示 | 引导转发/分享 |
| 小红书 | 收藏率（收藏 >> 点赞） | 突出"收藏备用"/"值得存下来"的参考价值 | 引导收藏 |

### 文案要求

- **标题/开场**：用数字、反问、感叹开头
- **正文**：口语化短句，每句不超过 15 字
- **标签**：混合大流量 + 精准标签
- **不放网址**：链接统一放评论区自评
- **必须包含评论区自评**：在 douyin.md 中添加 `## 评论区自评` 段落，包含**两种**项目介绍格式：
  1. **搜索方式**：`GitHub搜索: 项目名`（如 `GitHub搜索: RuView`）
  2. **完整路径**：`owner/repo` 格式（如 `openpli/ruview`）
  每个项目都要同时提供这两种格式，方便不同偏好的用户找到项目。示例：
  ```
  1. RuView — WiFi信号空间感知
     GitHub搜索: RuView
     完整路径: openpli/ruview
     语言: Rust | 68K⭐ | 今日+656
  ```
- **三平台文案必填**：`douyin.md` 必须包含 `## 抖音`、`## 视频号`、`## 小红书` 三个二级标题，每个标题下有完整文案（标题+正文+标签）。校验：`grep -c '^## ' douyin.md` ≥ 3
- **措辞规范**遵守 `clipforge/shared/shared-rules` §1

### 标签策略

> 标签列表：`{{delivery.hashtags|#科技 #AI}}`。分类配置提供完整标签列表时直接使用，未提供时按以下通用策略自行选择。

**跨圈覆盖要求：** 标签数 ≥ 5，每个标签命中不同的受众圈层（核心圈/领域/热点/身份/泛流量）。

{{IF:delivery.tag_strategy}}
{{INJECT:delivery.tag_strategy}}
{{ENDIF}}

---

## 约束声明

> 本阶段的结构化约束（HARD/SOFT 规则 + Guard Red Flags）由引擎注入提供。执行前运行 `python engine/inject.py --skill stage7-delivery` 获取完整约束 prompt。
