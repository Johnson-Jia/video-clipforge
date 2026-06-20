---
name: "技术淘金者"
description: "对比式淘金专栏：1主角深挖 + 同主题对比衬托，淘金者第一人称评测"
id: "goldminer"
---

<!-- CONFIG-START: 机器可解析的配置值 -->
audio:
  default_voice: "zh-CN-YunjianNeural"
  default_rate: "+20%"
  voice_override: true

narration:
  hook_example: "开淘！今天这个我直接吹爆"
  topic_example: "同类4个，只有它让我掏钱"
  hook_json_example: "开淘！今天这个我直接吹爆"
  cta_purpose: "站队对比"
  word_count_range: [300, 650]
  hook_anchors:
    - "开淘"
    - "同类"
    - "对比"
    - "站谁"
    - "差距"

delivery:
  hashtags: "#GitHub星探 #技术淘金者 #开源 #程序员 #AI"
  cover_badge: "技术淘金者"
  cover_scene_label: "淘金·对比评测"

design:
  default_style: "淘金暖金风"
  color_bias: "暖金/沙金为主（区别主轨冷色科技风），深色底"

shared_rules:
  data_example: "主角 12K★ 同类平均 3K★"
  hook_data_example: "同类4个，它单日涨星第一"
  hook_emotion_example: "开淘！今天这个我直接吹爆"
<!-- CONFIG-END -->

# 技术淘金者分类配置

## content

### data_source — 对比式淘金的数据基础

每期 = **1 个主角项目 + 2-3 个同主题对比项**。主角深挖，对比项衬托差距。数据源沿用 GitHub（`gh api` / `scripts/github_trending.py`），但选取逻辑不同于主轨榜单。

### selection_strategy — 主角 + 对比项选取

**主角（1 个）选取优先级：**
1. **反直觉/颠覆性**：用非常规技术做常见事（最强钩子，如"WiFi 感知人体"）
2. **单日涨星爆发**：涨星速率明显加速
3. **平民化可用**：普通人能直接用（A 档 GUI/Docker/桌面 app）
4. **有故事**：独立开发者坚持 / 老项目复兴（情怀档素材）

**对比项（2-3 个）选取规则：**
- 必须与主角**同主题/同类别**（同领域解决同类问题）
- 用 `gh api repos/{owner}/{repo} --jq '{topics}'` 取主角 topics，搜索同 topics 项目
- 对比项要有**梯度**：一个主流大牌（衬托主角差异化）+ 一个同类竞品（直接对比）+ 可选一个老牌（衬托新）
- 对比项数据同样用 `gh api` 实时获取（沿用主轨 `data_validation` 三源交叉验证 + `authenticity_verification` 真实性验证，**全部继承主轨 github.md 的 Red Flags**）

**对比项挖掘问题（写入 content_ready.txt 每个对比项）：**
1. 主角比它强在哪？（性能/易用/隐私/门槛/活跃度/价格）
2. 它比主角强在哪？（诚实，制造可信度）
3. 谁该选谁？（场景化推荐）

### preparation_rules — content_ready.txt 格式

```
【主角】owner/repo | 语言 | Star(±涨幅) | 中文描述（原: <英文 description>）
用途: <4-6字利益>
情绪档位: <惊艳/稳健/翻车/猎奇/情怀>
对比差距: <一句话，主角强在哪>

【对比1】owner/repo | ... | 强项: X | 弱项: Y | 适合: <场景>
【对比2】...
【对比3】...
```

> ⛔ 描述保真铁律、原始英文内嵌、avatar 下载 —— **全部继承主轨 github.md `preparation_rules`**，不重复声明。

## narration

### hook_templates — 开场签名「开淘！」+ 情绪档位变体

> **⛔ 开场铁律（HARD）**：每期 hook 必须以「开淘！」主锚开头 + 情绪档位变体。这是淘金者的听觉识别符，禁用主轨的"涨星最猛/杀入榜单"类钩子（那是主轨中立播报，不是淘金者）。

按情绪档位选开场变体（LLM 据主角特点选档）：

| 档位 | 触发（主角特点） | 开场变体 |
|------|-----------------|---------|
| 惊艳 | 反直觉/颠覆/暴涨 | 「开淘！今天这个我直接吹爆」 |
| 稳健 | 扎实工程/实用工具 | 「开淘！今天挖到个靠谱的」 |
| 翻车 | 刷星/名不副实/体验差 | 「开淘！但这个，别买账」 |
| 猎奇 | 黑科技/跨界/脑洞 | 「开淘！这也能行？」 |
| 情怀 | 老项目/独立开发者坚持 | 「开淘！这个故事得说说」 |

开场后接对比悬念句（≤14字）：「同类 4 个，只有它让我 ___」「这个领域我试了一圈，站 ___」

### special_rules — 淘金者人设 + 对比式五段结构

**① 淘金者人设（固定内核，永不变）：**
- **第一人称强制**：全程"我"——"我挖到""我试了""我站这个"。禁第三人称中立播报（那是主轨）。中立=退回主轨，不是淘金者。
- **态度强制（每期必有）**：惊艳在哪 / 坑在哪 / 值不值 / 站谁。**没态度 = 退稿**。
- **诚实底色**：翻车档不全盘否定，指出具体问题；惊艳档不夸大数据；**没用过的项目不装用过**（第一人称"我试了"是体验承诺，装用过=失信）。开源精神：有理有据地评。
- **描述保真**：继承主轨 `description` 保真铁律，不从 owner/repo 名杜撰。

**② 对比式五段结构（一条视频，60-100s）：**

| 段 | 场景类型 | 内容 | 时长 |
|----|---------|------|------|
| 1. 钩子 | hook | 「开淘！」+ 档位变体 + 对比悬念 | 5s |
| 2. 主角深度 | what→how→capabilities | 是什么/为什么惊艳(反直觉)/怎么用 | 30-45s |
| 3. 对比衬托 | capabilities(use compare) | 同类 X/Y/Z 怎么做，**主角强在哪**（差距感） | 15-25s |
| 4. 我的判断 | usecases | 为什么选它/适不适合你/站队 | 10-15s |
| 5. CTA | cta | 站队问题（主角 vs 对比项）+ 「关注 GitHub星探·技术淘金者」 | 5s |

> **对比衬托段（第3段）是 goldminer 区别于主轨的核心**：必须用 `visual_phases` 的 `compare` 类型（双栏：主角 vs 对比项），列出差距点。没有对比段 = 不是对比式淘金 = 退稿。

**③ 项目名必报（HARD，继承深度解析铁律）**：what 场景报主角名 + 画面大字；对比段报对比项名；CTA 强化；全程 ≥3 次接触。hook（第1段）不报名（前5秒纯钩子）。

**④ 站队 CTA**：结尾 1 个站队问题（主角 vs 主要对比项），如「tmux 和 Zellij 你站谁」。站队问题评论率高 3-5×。

### 情绪档位系统

> 情绪由**主角特点驱动**（有根据的真实反应），不是随机心情（显假）。LLM 读主角特征选档，全期语气、开场、判断话术统一在该档。

| 档位 | 语气 | 旁白示例 | humor_type |
|------|------|---------|-----------|
| 惊艳 | 激动强推 | "这个绝了，我直接吹爆" | analogy |
| 稳健 | 平和客观 | 清晰推荐不夸 | null |
| 翻车 | 犀利吐槽 | "别被 star 数骗了" | sarcasm |
| 猎奇 | 惊讶好奇 | "这也能行？" | trivia |
| 情怀 | 敬意温情 | 延续开源理想底色 | null |

### word_count_range

300-650 字（对比式 60-100s，比主轨标准模式长，比深度解析短）。

### 措辞/画面/CTA

遵守 `shared/shared-rules` 全部条款 + 主轨 github.md 的 `jargon_translation`（黑话→利益翻译表）。对比段用观众语言讲"强在哪"，不堆技术术语。

## narrative

### default_template

`showdown` — 对比式淘金天然是交锋结构（紧张→交锋→揭晓→结论）。副轨固定用 showdown，不用主轨的 contrast-arc。

### humor_rules

继承主轨 github.md `humor_rules`（生活类比、开发者文化梗、中等偏轻吐槽），但按情绪档位调节：翻车档 sarcasm 可加重，情怀档禁幽默。

### character_presence

true — 启用码力角色。淘金者人设通过码力角色的表情承载：惊艳=explode、思考=think、酷功能=cool、翻车调侃=tease、情怀=moved。

### immersion_mapping

| 情绪档位 | 沉浸模式 | 视觉风格 |
|---------|---------|---------|
| 惊艳 | hyper-pace | 快剪+密集粒子+琥珀火光 #FF6B00 |
| 稳健 | contrast-arc（默认） | 稳定对比+暖金 #FFB800 |
| 翻车 | versus | 分屏对比+硬朗 #FF3B30 |
| 猎奇 | hidden-gem | 渐进揭示+复古 #FFB800 |
| 情怀 | story-time | 插画风+柔和过渡+暖色 #34C759 |

> **匹配规则**：按主角情绪档位匹配沉浸模式。无明确匹配时默认用 稳健 / contrast-arc。

## design

### default_style

淘金暖金风。背景深色底（#0A0805），主色暖金/沙金（#FFB800/#D4A017），强调色琥珀火光（#FF6B00）。区别于主轨的冷色科技风（深蓝/深紫），但同属"GitHub星探"品牌（暖金=宝藏意象）。

### visual_signature — 淘金者视觉识别符（弥补无形象短板）

| 元素 | 规范 |
|------|------|
| 开场动画 | hook 场景引用 `components/content/goldminer_intro.html`（「开淘！」3 秒开场：淘金放大镜 + 筛沙闪光 + 大字"开淘！"） |
| 标志符号 | 每期出现的淘金者剪影 / 宝藏箱图标（角落小标） |
| 人名条 | 固定字幕样式「星探·淘金」 |
| 对比呈现 | 对比段用 CompareSplit（`components/content/compare_split.html`）/ ScoreCompare（`components/content/score_compare.html`）（双栏 + WIN 徽章） |

### color_bias

暖金为主，琥珀火光做强调，深色底衬托。禁止纯冷色（那是主轨）。

### bg_pool — bg 组件池（满足 stage6 R-R-009/010 bg 多样性）

> ⛔ **bg 组件选取铁律（HARD，解决 goldminer 暖金风 bg 三件套 fail）**：每个场景从 `components/bg/` 选 **1 个非三件套 bg 组件**（被 gate `_classify_bg_element_types` 识别为含 vignette/beams/wave/dots/contour/scan/noise 等非三件套类型），换暖金色（#FFB800/#D4A017/#FF6B00）。stage6 允许 bg 组件换色（CSS 变量/色值替换），故中性组件换暖金即可。

**✅ 允许（非三件套，换暖金色用）**：

| 组件 | 非三件套类型 |
|------|------------|
| radial_beams | beams + vignette（原生暖金，首选）|
| vignette_glow | vignette |
| ancient_relic | beams |
| light_field | beams（暖中性，stage6 暖色回退默认）|
| gradient_mesh | contour + wave |
| clean_slate | dots + wave |
| contour_lines | contour |
| wave_ripple | contour + wave |
| hex_grid | beams + wave |
| scan_grid | scan |
| noise_field | noise |

**❌ 禁用（纯三件套 glow+gradient，触发 R-R-009）**：ember_glow / diamond_lattice / soft_linen / aurora_flow

**相邻多样性（R-R-010 ≥3 风格）**：相邻场景 bg 组件必须**类型不同**（如 radial_beams[vignette] → gradient_mesh[wave] → clean_slate[dots] 轮换），全片 ≥3 种类型组合，禁连续 2 场景用同类型组件。

## delivery

### hashtags

`#GitHub星探 #技术淘金者 #开源 #程序员 #AI`（含专栏标签 #技术淘金者，区别主轨的 #GitHub热门）

### cover_badge

"技术淘金者"

### cover_scene_label

"淘金·对比评测"

### cover_content_strategy

封面主标题 = 「开淘！」+ 主角利益（如"开淘！这个 AI 工具我直接吹爆"）。副标题 = 对比悬念（"同类 4 个，我站这个"）。封面用淘金暖金风，区别主轨冷色封面。

### comment_template

```
评论区格式：
1. 主角 owner/repo + 一句话（它在同类里强在哪）
2. 对比项列表（owner/repo，标注各自适合谁）
3. 站队引导："主角 vs 对比项，你站谁"
4. 不放完整链接，不提搜索，不提平台名（继承主轨）
```

## audio

### voice_identity — 声音 IP 锚点

> 声音是淘金者第一识别符（spec §1.2 头号短板：公共 TTS 无识别度）。CONFIG `default_voice` 当前为 `zh-CN-YunjianNeural`（fallback）。

**声音克隆（voice_clone，spec §3）为 Plan 2**：用户克隆声训练 + stage4 集成上线后，goldminer 切换为用户独占克隆声（主轨同步换声，两轨共享同一声音 = 统一 IP 锚）。当前 fallback 不阻塞内容管线验证。
