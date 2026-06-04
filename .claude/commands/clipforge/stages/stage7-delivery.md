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

### 脚本化生成（唯一正确方式）

> **封面 HTML 禁止手写。** 使用 `scripts/generate_cover.py` 从参数 JSON + Jinja2 模板生成。
>
> **LLM 的角色：** 从内容推导色彩方案和文案，输出 `cover_params.json`。脚本负责填充模板。
> **脚本的角色：** 读取 params → 派生调色板 → 填充模板 → 输出 cover.html。
>
> 这种分离确保结构不可破坏（模板锁定），创意自由最大化（LLM 自由选择配色和内容）。

**执行步骤：**

1. 从 `design.md` 读取配色方向，从 `narration_segments.json` / 内容摘要读取数据
2. 创建 `cover_params.json`（schema 见 `shared/cron-template.md` SubAgent-4 段）
3. 运行脚本：
   ```bash
   cd .claude/commands/clipforge && python scripts/generate_cover.py --project-dir <project-dir> --render
   ```
4. 脚本输出 `cover.html` + `cover.png`

**LLM 创意域（自由发挥）：**
- 色彩方案：3 个核心色值（accent_warm / accent_cool / bg_dark），脚本自动派生 12 色调色板
- 标题文案：分色方案（单色/双色/三色），每段可选 `white`/`accent`/`cool` 样式
- 数据卡片：1-3 个，内容和数字自由填写
- 光晕强度：glow_warm_opacity / glow_cool_opacity 微调
- 场景标签、徽章、副标题文案

**禁止（由模板锁定）：**
- 重命名 CSS class、修改布局、更换字体、调整光晕定位、添加/删除层

### 模板参考

> 权威模板：`scripts/templates/cover-portrait.html.j2`（竖屏）和 `scripts/templates/cover-landscape.html.j2`（横屏）。
> 本节仅描述结构概览，不提供内联 HTML。生成封面必须使用脚本。

**7 层结构（从上到下，缺一不可）：**

| 层 | class | 内容 | 字号（竖屏） |
|----|-------|------|------------|
| 1 | `.date` | 中文日期 | 80px |
| 2 | `.scene-label` | 场景分类标签 | 64px |
| 3 | `.badge` | 胶囊徽章 | 64px |
| 4 | `.main-title` | 多色段标题（`.white` / `.accent` / `.cool`） | 220px |
| 5 | `.divider` | 渐变分隔线 | — |
| 6 | `.data-subtitle` | 数据说明文案 | 88px |
| 7 | `.cards` | 1-3 个数据卡片（`.num` + `.label`） | 120px / 52px |

**配色：** 3 个核心色值（`accent_warm` / `accent_cool` / `bg_dark`）→ 脚本自动派生 12 色 CSS 变量。
**背景：** 深色渐变 + `.glow-warm`（左上）+ `.glow-cool`（右下），`blur(200px)`
**字体：** `Inter` + `JetBrains Mono`（Google Fonts）
**画布：** 竖屏 2160×3840 → 输出 1080×1920；横屏 3840×2160 → 输出 1920×1080
**横屏安全区：** `.safe-zone`（1620px 居中），7 层垂直堆叠

### 渲染命令

**脚本已内置渲染（推荐）：**
```bash
cd .claude/commands/clipforge && python scripts/generate_cover.py --project-dir <project-dir> --render
```

**手动渲染降级（脚本 --render 失败时）：**

方案 A — HyperFrames 隔离渲染：
```bash
mkdir -p /tmp/cover-render && cp cover.html /tmp/cover-render/index.html && cd /tmp/cover-render
npx hyperframes render . --output cover_temp.mp4 --video-bitrate 5M
ffmpeg -y -i cover_temp.mp4 -vf "select=eq(n\,0),scale=1080:1920:flags=lanczos" -vframes 1 -update 1 <项目目录>/cover.png
rm -rf /tmp/cover-render
```

方案 B — Chrome headless 截图：
```bash
"/c/Program Files/Google/Chrome/Application/chrome.exe" --headless --screenshot=cover.png --window-size=2160,3840 cover.html
```

方案 C — ffmpeg 首帧（最后降级）：
```bash
ffmpeg -y -i output.mp4 -vf "scale=1080:1920:flags=lanczos" -vframes 1 cover.png
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

> **脚本内含硬性断言：** final.mp4 时长偏差 < 0.2s，两个文件都必须有音频轨道。断言失败会 exit 1。

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

> **（三平台数据验证）：**
> - 抖音：反直觉/冲突标题平均 46K 播放，数字钩子 42K，直接叙述仅 5K
> - 视频号：分享率 4-5% 是增长杠杆
> - 小红书：收藏是点赞的 1.9 倍，内容有参考价值属性

### 文案风格模板

**选项 1 — 爆款钩子型（首选）**（量化锚定 + 反直觉钩子）

> **（爆款案例 + 全量数据验证）。** 数字锚定 + 反直觉描述模式平均播放量是直接叙述的 8 倍。

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
