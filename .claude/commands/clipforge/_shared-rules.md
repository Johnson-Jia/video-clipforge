# ClipForge 共享内容规范

> **所有阶段必须遵守。** Stage 1/3/6/7 执行前必须先读取此文件。其他阶段按需引用。

## 1. 措辞规范（防止广告审核）

**语气定位：朋友间分享好东西的自然口吻，不是推销员。**

| 禁止 | 原因 | 替换为 |
|------|------|--------|
| "必装"、"必备"、"神器" | 广告审查敏感词 | "挺好用的"、"值得关注"、"推荐试试" |
| "赶紧去"、"马上去"、"立即下载" | 强诱导行为 | "感兴趣的可以看看"、"开源免费，值得试试" |
| "全网最好"、"第一"、"最强" | 极限用语违规 | "很受欢迎"、"在 XX 领域表现不错" |
| "你一定要"、"千万别错过" | 命令式语气 | "大家可以试试"、"也挺有意思的" |
| "免费领"、"福利"、"白嫖" | 促销词汇 | "开源项目"、"可以免费使用" |
| "点赞关注"、"一键三连" | 诱导互动 | 正文不放，仅在文案末尾自然提及 |

**核心原则：**
- 用"我发现"、"最近看到"、"有个项目"这种分享式开头
- 描述功能和特点，不评价优劣，让用户自己判断
- 可以用数据说话（"33K Star"），但不用主观夸张（"太强了"）
- 保持信息密度，去掉情绪注水
- **不点名商业产品/品牌名称**：不说"GPT"、"DeepSeek"、"通义千问"等具体品牌，改说技术类别（如"大语言模型"、"AI 助手"）。点名品牌会被判定为商业推广/软广

### 1.1 反直觉描述技巧（提高点击率）

> **数据来源：** 爆款视频分析（05-19，11万播放）中，"用 WiFi 信号做空间感知，完全不用摄像头"是点击率最高的钩子句。

**反直觉 = 用常见事物做不常见的事。** 句式模板：

| 句式 | 示例 |
|------|------|
| 用 XX 做 XX，完全不用 XX | "用 WiFi 信号做空间感知，完全不用摄像头" |
| 不装 XX 就能 XX | "不装任何 App 就能实时追踪飞机" |
| XX 竟然能 XX | "Rust 写的个人 AI 大脑竟然能离线运行" |
| 只用 XX 就搞定了 XX | "只用家用路由器就能监测老人跌倒" |

**适用范围：** 旁白文案（Stage 3）、发布文案（Stage 7）、钩子句（§5）。每个视频至少 1 个项目使用反直觉描述。

## 2. 画面文字语言规范

视频画面文字**必须以中文为主**：
- 标题、副标题、标签、CTA 等画面可见文字全部用中文
- 仅以下情况用英文：项目名称（如 openhuman、scrcpy）、技术缩写（如 API、TTS、SDK）、编程语言名
- 示例：
  - 正确："今天最热门"、"前三名"、"关注每天更新"
  - 禁止："TRENDING TODAY"、"TOP 3"、"FOLLOW FOR DAILY"
  - 例外：项目名（scrcpy、agentmemory）和技术缩写（API、Rust）保留英文

## 3. CTA 时间规范

- **CTA 不提及具体更新时间**：不说"每天7点更新"、"每晚8点"等，改用通用表述如"每天更新"、"关注获取每日热门"

## 4. 视频内容安全

- **视频内不放网址/URL**（抖音审查敏感）。只展示项目名称/产品名称，链接放评论区
  - 正确：`financial-services`、`Claude Code`
  - 禁止：`github.com/xxx`、`https://xxx.com`

### 4.1 禁止引导脱离平台（限流高危）

**旁白 + 画面文字禁止：**

| 禁止 | 替换为 |
|------|--------|
| "下载安装包"、"双击安装" | "本地运行"、"开箱即用" |
| "下载桌面应用" | "桌面应用"、"本地运行" |
| "打开浏览器就能用" | "在线就能用"、"直接在线用" |
| "前往/访问 github.com/xxx" | "搜项目名就能找到" |

**评论区禁止：**

| 禁止 | 替换为 |
|------|--------|
| 放完整链接 | 只列名称 + 搜索指引（"搜名字就能找到"） |
| "下载地址：xxx" | "搜名字就能找到" |

**核心原则：**
- 只描述能力，不描述获取路径：说"能做什么"，不说"去哪下载/怎么安装"
- 评论区只放名称，不放链接
- "下载"、"安装"、"浏览器"在推荐/CTA场景中禁止出现

## 5. 黄金 3 秒法则（内容 + 画面）

> **用户划走一个视频只需 1-3 秒。** 前 3 秒决定生死，3-5 秒之后才能进入正文。

### 5.1 旁白文案

- **hook 场景的旁白必须是纯钩子**：震撼数据、反问、强对比、悬念，不含任何信息性内容
- 钩子句 ≤ 12 个字，口语化，一击即中
- "正文"（项目介绍、功能说明等）从第 2 个场景开始，绝不提前
- 钩子句模板（按优先级排序）：
  - **数据震撼（首选）**："今天涨星最猛的 N 个项目"、"N 个热门项目，AI 占了一半"
  - 反直觉描述（次选）："你见过用 WiFi 信号感知人体的吗"
  - 强对比："别人还在 XX，这个已经 YY"
  - 悬念留白："这个项目，直接炸了"

### 5.2 画面视觉

- **hook 场景必须是全片视觉最强烈的画面**：字号最大、对比最强、动画最干脆
- 前 3 秒画面元素 ≤ 3 个（文字/数字/徽章），信息极简，视觉极强
- 主标题字号 ≥ 100px（竖屏基准），搭配光晕/发光效果
- 配色自由搭配：根据文案内容主题选择合适色系（科技用冷色、生活用暖色等），主色 + 强调色双色体系，禁止超过 3 种颜色，禁止荧光色堆砌
- 必须包含双色光晕：一暖一冷两个大尺寸模糊光球，颜色随主题变化
- 布局固定模板：元素间距均匀、对齐严整、留白充裕（画面 30% 以上为留白）
- 入场动画 0.3-0.5 秒内完成，干脆利落不拖泥带水

### 5.3 音频开场（禁止淡入）

- **视频开头禁止任何形式的音频淡入**——旁白和 BGM 都必须在第一帧立即全音量播放
- 旁白 TTS 第一段不做 `afade=t=in` 处理，保持原始开头
- BGM 不做开场淡入，`data-start="0"` + `data-volume` 直接生效
- **原因：** 前 3 秒是钩子生死线，淡入会让观众在最重要的时刻听到渐强的声音而非冲击性的信息，直接削弱 hook 效果
- 尾巴可以淡出：视频最后 1 秒 BGM 淡出是允许的

## 7. HyperFrames 渲染安全规范

> **多次出现过"只有背景没有内容"的线上事故。** 以下规则均为事故复盘总结，必须严格遵守。

### 7.1 禁止 CSS `.anim-in` 及任何 CSS `opacity: 0` 入场动画

- **绝不使用 `.anim-in` CSS 类**或任何在 CSS 中设置 `opacity: 0` 的入场机制
- HyperFrames 基于 seek 驱动渲染（逐帧推进），**不触发 CSS animation/transition**，CSS 入场动画永远不会执行，导致内容永远 `opacity: 0`
- **所有内容元素必须默认可见**（`opacity: 1`），不做任何 CSS 入场动画
- 入场动画由 GSAP timeline 的 `.from({opacity:0})` 实现（见 §7.6），不依赖 CSS
- HyperFrames clip 切换由 `data-start`/`data-duration` 控制

### 7.2 禁止 HTML 实体字符

- **不在画面文字中使用 HTML 实体**（如 `&#9733;`、`&#10084;`、`&amp;` 等）
- HyperFrames 无头浏览器对实体字符的解析不可靠，可能导致整段内容不渲染
- **改用 Unicode 字符直接输入**（如 `★`、`❤`）或纯文本替代

### 7.3 scene-wrap 必须有 padding

- 每个场景的 `.scene-wrap`（或等效内容容器）**必须显式设置四方向 padding**
- 推荐值：`padding: 120px 95px`（上下 120px，左右 95px）
- 水平 padding 确保内容不贴视频边缘，防止手机端文字被裁切
- 缺少 padding 可能导致内容区域在 HyperFrames 渲染中塌陷不显示

### 7.3.1 水平安全边距规则

- **所有场景内容左右各留 95px 边距**（1080px 宽度的 ~8.8%）
- `.pfc-main` 等全宽内容行也必须加 `padding: 0 80px`，防止 `.pfc-rank` 和 `.pfc-stars` 贴边
- `.project-card` / `.hero-card` 等卡片容器加 `padding: 0 60px`
- **禁止** `width: 100%` 的内容行没有水平 padding

### 7.4 渲染前移除所有非 index.html 的 composition 文件

- **HyperFrames 不允许多个 root composition**（`multiple_root_compositions` 警告）
- 项目目录中**任何**含 `data-composition-id` 的 HTML 文件（不止 `cover.html`）都会导致渲染冲突
- 常见冲突文件：`cover.html`、`index_with_bgm.html`（备份）、`cover.html.bak`（未清理的备份）
- **渲染 index.html 前，移除所有非 index.html 的 HTML 文件：**
  ```bash
  for f in cover.html index_with_bgm.html cover.html.bak; do
    [ -f "$f" ] && mv "$f" "$f.renderbak"
  done
  ```
- **渲染完成后恢复需要的文件：** `mv cover.html.renderbak cover.html`
- **临时备份文件渲染后必须删除：** `rm -f index_with_bgm.html.renderbak cover.html.bak.renderbak`

### 7.5 音频文件必须在项目目录内

- `<audio src="bgm.mp3">` 引用的文件**必须存在于 index.html 同级目录**
- HyperFrames 渲染时通过 FileServer 提供文件，路径错误会导致 404 静音
- **渲染前检查：** `ls -la bgm.mp3 narration.mp3` 确认两个音频文件都存在

### 7.6 GSAP timeline 注册是强制要求

- **`window.__timelines = {};`（空对象）会导致全片空白渲染。** HyperFrames 等待 `window.__timelines["main"]` 被注册，超时后渲染空帧
- 必须引入 GSAP CDN 并注册 timeline：
  ```html
  <script src="https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.5/gsap.min.js"></script>
  <script>
  window.__timelines = {};
  const tl = gsap.timeline({paused: true});
  tl.from('.s-hook .element', {opacity:0, y:20, duration:0.3, ease:'power3.out'}, 0.2);
  // ... 每个场景的入场动画
  window.__timelines["main"] = tl;
  </script>
  ```
- GSAP `.from()` 动画是可靠的入场机制：元素 CSS 默认 `opacity:1`，GSAP `.from({opacity:0})` 在 seek 时正确执行
- 动画 offset 必须与场景 `data-start` 对齐（如 hook 场景从 0 开始，what 场景从 hook 时长开始）

## 8. 三层渲染架构

> **每个场景必须严格分离为三层。** 这是结构规则，不是样式建议。违反会导致特效遮挡内容或背景穿透。

### 8.1 层级定义

| 层级 | z-index | 用途 | 内容 |
|------|---------|------|------|
| 底层 `.layer-bg` | 1 | 场景背景 | 渐变色、光晕、网格底纹、纯色填充 |
| 中间层 `.layer-fx` | 2 | 视觉特效 | 粒子、爆炸、矩阵雨、3D、漂浮物等动态装饰 |
| 顶层 `.layer-content` | 3 | 可读内容 | 文字、数字、徽章、卡片、标签等所有用户需要阅读的元素 |

### 8.2 CSS 模板

```css
.scene-wrap { position: relative; overflow: hidden; }
.layer-bg { position: absolute; inset: 0; z-index: 1; }
.layer-fx { position: absolute; inset: 0; z-index: 2; pointer-events: none; }
.layer-content { position: relative; z-index: 3; }
```

### 8.3 规则

- **每个场景必须包含三层**，无例外
- `.layer-fx` 必须 `pointer-events: none`，防止特效遮挡交互
- 特效 opacity 建议 0.3-0.6（不遮挡内容但可见）
- 特效类型不固定，根据场景情绪和内容主题自行推导（见 `stage6-components.md` 情绪映射表）
- `.layer-bg` 至少包含渐变背景 + 1 个光晕
