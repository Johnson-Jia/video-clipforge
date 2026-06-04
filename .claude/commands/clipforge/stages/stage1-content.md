# Stage 1: 内容获取

当已有原始内容输入（对话/文件/URL）且未产出整理后的内容摘要时触发。获取和整理内容来源。

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

**获取后：** 提炼核心信息点，准备进入 Stage 2 风格推导。

## 完成标记

内容整理完成后，创建阶段完成标记：

```bash
touch content_ready.txt
```

此文件是 `schema.yaml` 中 content artifact 的 `generates` 声明，后续阶段通过检测此文件判断 content 是否完成。

## 分类数据获取（当有分类配置时）

当用户指定了内容分类（如 GitHub、漫画、小说等），读取对应的分类配置文件获取数据获取策略：

```
clipforge/categories/{category}.md
```

分类配置中的 `content` 段定义了该分类特有的数据获取方式、选取策略和兜底方案。通用部分（文件提取、URL 读取等）在本文件前面已覆盖。

**如果没有分类配置**（用户直接提供文字/文件/URL），则只使用本文件前面的通用内容获取流程。

### 产出说明

1. `content_ready.txt` — 空标记文件（`touch content_ready.txt`），仅用于 DAG 状态检测
2. 核心信息点以**对话上下文**形式传递给 Stage 2，不需要额外文件。Stage 1 → Stage 2 在同一会话内顺序执行，LLM 可直接从对话历史中读取内容摘要

---

## 约束声明

> 本阶段的结构化约束（HARD/SOFT 规则 + Guard Red Flags）由引擎注入提供。执行前运行 `python engine/inject.py --skill stage1-content` 获取完整约束 prompt。
