# Stage 1: 内容获取

当已有原始内容输入（对话/文件/URL）且未产出整理后的内容摘要时触发。获取和整理内容来源。

> **前置：消费 `topic_plan.json`**（由 stage0.5-topic-plan 产出）。按 `topic_plan.angle`（选题方向）/ `novelty_strategy`（差异化策略）/ `avoid_recent`（避开项目）获取内容，不偏离选题规划。若 `topic_plan.json` 不存在（非 GitHub 分类的纯交互模式，或选题规划未触发），按通用流程获取内容。

**来源可能是：**
- 对话中直接描述
- 指定目录下的文件（md/txt/html/json）
- 用户粘贴的文字或 HTML
- 网页 URL
- PDF / Word / Excel / PPT 文件
- 以上组合

**动作：**
1. 用户已给出 → 直接用
2. 指定目录 → 扫描内容文件（跳过 CLAUDE.md / AGENTS.md / README.md）
3. HTML 文件 → 提取 `<body>` 纯文本，忽略标签和样式
4. 不明确 → 询问：「请提供视频内容来源——文字、文件、还是目录？」

**获取后：** 提炼核心信息点，写入 `content.md`（结构化摘要，非空标记），准备进入 Stage 2 风格推导。

## 完成标记

内容整理完成后，将结构化摘要写入 `content.md`：

```markdown
# 内容摘要

## 来源
<来源类型：对话/URL/文件/分类数据>

## 核心主题
<1-2 句话概括>

## 关键信息点
- <信息点 1>
- <信息点 2>
- ...

## 数据（如有）
<具体数据、数字、统计>

## 原始素材路径（如有）
<文件路径或 URL>
```

此文件是 `schema.yaml` 中 content artifact 的 `generates` 声明，后续阶段通过检测此文件判断 content 是否完成。同时作为跨会话的持久化内容，Stage 2 可从 `content.md` 恢复上下文。

## 分类数据获取（当有分类配置时）

当用户指定了内容分类（如 GitHub、漫画、小说等），读取对应的分类配置文件获取数据获取策略：

```
clipforge/categories/{category}.md
```

分类配置中的 `content` 段定义了该分类特有的数据获取方式、选取策略和兜底方案。通用部分（文件提取、URL 读取等）在本文件前面已覆盖。

**如果没有分类配置**（用户直接提供文字/文件/URL），则只使用本文件前面的通用内容获取流程。

---

## 约束声明

> 本阶段的结构化约束（HARD/SOFT 规则 + Guard Red Flags）由引擎注入提供。执行前运行 `python engine/inject.py --skill stage1-content` 获取完整约束 prompt。

**盘点类项目重复硬约束**（gate `project_no_consecutive_repeat`，2026-08-04 airllm 连3期事故）：单个项目**禁同频道近2天连续入选**（昨日/前日同频道已选 → 本期换项目，换角度不算差异化）。**仅同类别校验，不跨频道**（daily/ai-wind 各自独立）。例外：今日 `stars_today` 涨进当日 raw 前3 的真爆款可一句带过。**weekly 周榜豁免**（回顾属性）。详见 `categories/github.md → selection_strategy`。

**daily AI 占比硬约束**（gate `ai_project_cap`，2026-08-05 有 ai-wind 专项后差异化）：**仅 github-trending 综合榜**，AI 项目 **≤ 2 个**（ai-wind 专项承接 AI 深度，daily 回归多元：工具/基建/安全/硬件/前端）。ai-wind/weekly 跳过。AI 判定同 ai_trending.py（topics/description 关键词）。
