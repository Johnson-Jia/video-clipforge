---
name: "创业淘金者"
description: "从创业失败残骸淘教训+可复用点子：1 个失败案例深挖 + 相关失败对比，淘金者第一人称复盘"
id: "goldminer"
---

<!-- CONFIG-START: 机器可解析的配置值，供 render_stage.py 和引擎模块加载 -->
audio:
  default_voice: "zh-CN-YunjianNeural"
  default_rate: "+15%"
  voice_override: true

narration:
  hook_example: "淘金！开淘！今天这家烧了 9 亿美金才明白"
  topic_example: "烧光上亿才懂的教训"
  hook_json_example: "淘金！开淘！今天这家烧了 9 亿美金才明白"
  cta_purpose: "站队/讨论"
  word_count_range: [410, 640]
  hook_anchors:
    - "淘金"
    - "开淘"
    - "烧光"
    - "归零"
    - "教训"
    - "翻车"
    - "淘到"

delivery:
  hashtags: "#创业淘金者 #创业失败 #商业复盘 #创业 #财经"
  cover_badge: "创业淘金者"
  cover_scene_label: "失败·淘金复盘"

design:
  default_style: "淘金暖金风（残骸淘金=宝藏意象）"
  color_bias: "暖金/琥珀火光为主（区别主轨冷色科技风），深色底"

shared_rules:
  data_example: "烧掉 $944M / 4 年死亡 / 233 家同类"
  hook_data_example: "烧光 9 亿美金才明白的道理"
  hook_emotion_example: "淘金！开淘！这个教训值 9 个亿"
<!-- CONFIG-END -->

# 创业淘金者分类配置

> **定位转型（2026-06-20）**：技术淘金者（淘 GitHub 开源项目）→ **创业淘金者**（从创业失败残骸淘教训 + 可复用点子）。"淘金"意象更贴失败案例——loot-drop.io 本身就是 "Loot the wreckage"（从残骸捡漏）+ "Ideas to Steal"（可偷的点子）。暖金视觉 IP 保留（宝藏/残骸淘金）。

## content

### data_source — loot-drop.io 失败案例库

数据源：**loot-drop.io**（1,749 个失败创业案例，$535B+ 烧掉）。`robots.txt` Allow /，`sitemap.xml` 含全部案例 URL，详情页 SSR 可 requests 抓取。

```bash
python scripts/fetch_lootdrop.py --output-dir "${PROJECT_DIR}" --region 中国 --limit 3
```

产出 `raw_failures.json`，每案例字段：
- `name`（公司名）/ `region`（地区）/ `funding`（融资额）/ `overview`（业务叙述含融资+技术+伙伴）
- `failure_analysis`（死因，钩子核心）/ `startup_learnings`（教训）/ `market_analysis`
- `pivot_concept`（重建点子，淘金核心）/ `related`（相关失败，对比段素材）

### selection_strategy — 失败案例选取（中国公司起步）

**首批策略（2026-06-20）**：中国公司起步 → 逐步全球知名。`fetch_lootdrop --region 中国` 优先。

| 优先级 | 选取条件 | 钩子潜力 |
|--------|---------|---------|
| **1 — 受众熟悉** | 中国受众知道的公司（教培 VIPKid/猿辅导、共享单车、P2P、生鲜电商） | 共鸣强 |
| **2 — 数据震撼** | 融资额大（>$100M）/ 死亡周期长 / 烧钱离谱 | 数字锚定 |
| **3 — 死因反直觉** | 技术炫但生意死 / 监管一刀切 / 60% 被偷破坏 | 反直觉钩子 |
| **4 — 教训可淘** | Learnings 清晰 + Rebuild pivot 有可偷点子 | 淘金价值 |

**选取流程**：
1. `fetch_lootdrop --region 中国 --limit 8` 抓 8 个候选（候选池扩大，避免前几个全做过）
2. **跑 `scripts/goldminer_history.py --filter-candidates raw_failures.json`**（HARD 防重复）：过滤已做过企业，主角从未做过清单选
3. 从未做过清单按钩子潜力 + 淘金价值选 1 个主角 + 2-3 个 related（相关失败）作对比
4. 候选全部已做过 → 扩大 `--limit` 或换 `--region`（美国/印度/欧洲）重抓，直到有未做过的新企业

**⛔ 跨期去重（HARD + SOFT）**：
- **HARD 同企业零容忍**：主角企业不得与历史任何一期重复（中英文别名等同，`goldminer_history.py` 检测）。重复 = 停止重选，不可"换个角度讲同一公司"
- **SOFT 同行业连续 ≤2 期**：同一行业（教培/共享出行/P2P/生鲜电商等）不连续做超 2 期，第 3 期强制换行业。行业 key 取 `content_ready.txt` 主角行第 4 字段（行业），由 `goldminer_history.py --report` 自动检测
- **历史快照**：每次跑写 `workspace/evolution/goldminer_done.json`（企业频次 + 行业频次），供 LLM 选题参考

### ⛔ 合规红线（HARD，失败案例必读，诽谤风险）

> loot-drop.io 声明内容是 **AI 辅助总结**（"may contain errors/hallucinations"）。失败案例涉真实公司，**视频必须**：

| 规则 | 要求 | 违反后果 |
|------|------|---------|
| **来源标注** | 文案/评论区注明数据来自 loot-drop.io；片尾可加"数据来源：loot-drop.io 创业坟场" | HARD 失败 |
| **客观转述** | 死因忠实 `failure_analysis` 字段，**禁杜撰/禁夸大/禁添油加醋** | HARD 失败 |
| **不点名创始人个人** | 只讲公司+商业模式+宏观原因，**禁点名创始人姓名/个人攻击** | HARD 失败（诽谤） |
| **教育目的** | 调性是"淘教训"非"吃瓜嘲讽"；rebuild pivot 是"可学的"非"抄它" | SOFT |

> stage1（来源标注+不杜撰）/ stage3（不点名创始人）/ stage7（文案声明）门禁强制。

### preparation_rules — content_ready.txt 格式

```
【主角】公司名 | 地区 | 融资 | 行业 | 中文一句话死因（原: <failure_analysis 原文>）
受众熟悉度: 高/中/低
死因类型: 烧钱/监管/竞争/单位经济/产品/无市场
教训: <startup_learnings 提炼，1-2句>
可淘点子: <pivot_concept 提炼，1句话>
数据来源: loot-drop.io

【对比1】公司名 | 死因 | 教训（related[0]）
【对比2】公司名 | 死因 | 教训（related[1]）
```

> 每个案例的 failure_analysis **原文内嵌**（保真锚点，禁从公司名杜撰死因）。

## narration

### hook_templates — 开场签名「淘金！开淘！」+ 失败钩子

> **⛔ 开场铁律（HARD）**：每期 hook 必以「淘金！开淘！」主锚开头。这是创业淘金者的听觉识别符。后接数据/反直觉钩子。
>
> **📌 hook 字数豁免（本分类专属）**：豁免 stage3 通用「hook ≤12 字」约束——签名「淘金！开淘！」固定占 6 字 + 数据/反直觉钩子，完整 hook 句约 20-30 字（如「淘金！开淘！1500万美金烧出一个共享单车墓地」）。gate 对 goldminer 分类豁免 hook 字数 checker（签名识别符优先于字数约束）。

**钩子库（按死因选，数据锚定 + 反直觉）：**

| 死因 | 钩子模板 |
|------|---------|
| 烧钱（Bonfire） | 「淘金！开淘！这家烧了 X 亿美金才明白 ___」 |
| 监管（Outlaw） | 「淘金！开淘！一纸文件，X 亿生意一夜归零」 |
| 竞争（Crushed） | 「淘金！开淘！它做得没错，还是被巨头碾死了」 |
| 单位经济（Math） | 「淘金！开淘！越做越亏的生意，烧 X 亿才看懂」 |
| 无市场（Hallucination） | 「淘金！开淘！建了个没人要的东西，烧了 X 亿」 |
| 产品（Lemon） | 「淘金！开淘！技术炸裂，生意却死了」 |

**利益翻译铁律**：含数字的钩子必须配一句观众能懂的利益/教训（"X 亿买来的教训是 ___"），禁裸报数字。

### special_rules — 淘金者人设 + 失败复盘五段结构

**① 淘金者人设（固定内核）：**
- **第一人称强制**：全程"我"——"我扒了这家""我淘到一个教训"。禁第三人称中立播报
- **态度强制**：惋惜在哪 / 教训是什么 / 点子能不能偷 / 值不值得做。没态度=退稿
- **淘金底色**：不是吃瓜嘲讽，是"从失败里淘有价值的东西"（教训 + 可复用点子）。失败=素材，淘金=目的
- **客观保真**：死因忠实 failure_analysis，不杜撰；数据（融资/年限）以 raw_failures.json 为准

**② 失败复盘五段结构（一条视频，70-110s）：**

| 段 | 场景 | 内容 | 时长 |
|----|------|------|------|
| 1. 钩子 | hook | 「淘金！开淘！」+ 数据/反直觉钩子 | 6s |
| 2. 是什么 | what | 公司做什么 + 融资 + 规模（overview 提炼） | 20-30s |
| 3. 为什么死 | why_fail | **死因**（failure_analysis，反直觉钩子核心） | 20-30s |
| 4. 淘什么 | loot | **教训**（learnings）+ **可偷的点子**（rebuild pivot）= 淘金核心 | 15-25s |
| 5. 对比+CTA | compare | 相关失败（related）对比衬托 + 讨论问题 | 10-15s |

> **第4段（loot）是创业淘金者的核心**：必须讲清楚"教训 + 可复用点子"。没有 loot 段 = 不是淘金 = 退稿。第5段对比用 related 失败衬托（同行业不同死法）。

**③ 项目名必报（HARD）**：what 场景报公司名 + 画面大字；全程 ≥3 次接触。hook（第1段）不报名（前 6 秒纯钩子）。

**④ 讨论 CTA**：结尾 1 个讨论问题（如"这个点子你觉得能成吗""你站哪家"），评论率比中性高 3-5×。

### 情绪档位系统（失败案例调性）

| 档位 | 触发 | 语气 | 开场变体 |
|------|------|------|---------|
| 警醒 | 烧钱教训/单位经济 | 痛心警示 | 「淘金！开淘！这个教训值 X 亿」 |
| 惋惜 | 好产品败给时代/监管 | 唏嘘感慨 | 「淘金！开淘！技术对了，时机错了」 |
| 猎奇 | 离谱死法（被偷/被砸） | 惊讶 | 「淘金！开淘！这死法你敢信？」 |
| 共鸣 | 普通人懂的失败（双减/一刀切） | 同理 | 「淘金！开淘！一夜归零的滋味」 |
| 理性 | 复杂商业逻辑 | 客观复盘 | 「淘金！开淘！扒一扒这家的账」 |

### word_count_range

410-640 字（匹配失败复盘 70-110s，+15% 约 5.8 字/秒；讲清"是什么+为什么+淘什么"）。

### 措辞/画面/CTA

遵守 `shared/shared-rules` 全部条款。黑话翻译：融资/单位经济/CAC 等术语翻译成观众能懂的（"获客成本"→"拉一个客户要花的钱"）。

## narrative

### default_template

`showdown`（失败 vs 教训的交锋结构）或 `contrast-arc`（惋惜→剖析→淘金）。

### character_presence

true — 码力角色承载淘金者人设：惋惜=moved、警醒=think、猎奇=cool、共鸣=moved。

### immersion_mapping

| 情绪档位 | 沉浸模式 | 视觉风格 |
|---------|---------|---------|
| 警醒 | contrast-arc | 对比复盘+暖金 #FFB800 |
| 惋惜 | story-time | 插画风+柔和过渡+暖色 #34C759 |
| 猎奇 | hidden-gem | 渐进揭示+复古 #FFB800 |
| 共鸣 | story-time | 柔和+暖色 |
| 理性 | versus | 数据对比+硬朗 #FF6B00 |

## design

### default_style

淘金暖金风（保留技术淘金者视觉 IP）。背景深色底（#0A0805），主色暖金/沙金（#FFB800/#D4A017），强调色琥珀火光（#FF6B00）。暖金=残骸里淘到的宝藏意象。

### visual_signature — 淘金者视觉识别符

| 元素 | 规范 |
|------|------|
| 开场动画 | hook 场景引用 `components/content/goldminer_intro.html`（「淘金！开淘！」开场：淘金放大镜+筛沙闪光+大字） |
| 标志符号 | 淘金者剪影 / 宝藏箱图标（角落小标） |
| 对比呈现 | 第5段用 CompareSplit/ScoreCompare（主角 vs related 失败，双栏） |

### color_bias

暖金为主，琥珀火光做强调，深色底衬托。禁止纯冷色（主轨）。

### bg_pool — bg 组件池（满足 stage6 R-R-009/010）

继承原 goldminer bg_pool（非三件套暖金组件）：radial_beams/vignette_glow/gradient_mesh/clean_slate/contour_lines/wave_ripple/hex_grid/scan_grid/noise_field 等。相邻场景类型不同，全片 ≥3 种。

## delivery

### hashtags

`#创业淘金者 #创业失败 #商业复盘 #创业 #财经`（含专栏标签 #创业淘金者）。

### cover_badge / cover_scene_label

"创业淘金者" / "失败·淘金复盘"

### cover_content_strategy

封面主标题 = 「淘金！开淘！」+ 数据钩子（如"淘金！开淘！9 亿美金的教训"）。副标题 = 死因悬念（"技术对了，生意死了"）。暖金风。

### comment_template

```
评论区格式：
1. 公司名 + 一句话死因（数据来源 loot-drop.io）
2. 对比项（related 失败，各自死法）
3. 讨论引导："这个点子你觉得能成吗"
4. 标注：数据来源 loot-drop.io 创业坟场（AI 辅助总结，仅供参考）
5. 不放完整链接，不提搜索，不点名创始人
```

## audio

### voice_identity

CONFIG `default_voice` 当前 `zh-CN-YunjianNeural`（fallback）。voice_clone（用户克隆声）上线后切换为独占克隆声（与主轨共享声音 IP 锚）。当前不阻塞。
