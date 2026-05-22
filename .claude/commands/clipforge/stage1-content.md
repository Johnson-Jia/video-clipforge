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

## 文件内容提取（依赖 ppt-master）

当用户提供的文件不是纯文本格式时，调用 ppt-master 的 `source_to_md` 工具转换：

```bash
PPT_SCRIPTS="ppt-master/skills/ppt-master/scripts"
```

| 文件类型 | 转换命令 | 依赖 |
|---------|---------|------|
| PDF | `python "$PPT_SCRIPTS/source_to_md/pdf_to_md.py" <file>` | `pip install PyMuPDF` |
| Word (.docx) | `python "$PPT_SCRIPTS/source_to_md/doc_to_md.py" <file>` | `pip install python-docx` |
| Excel (.xlsx) | `python "$PPT_SCRIPTS/source_to_md/excel_to_md.py" <file>` | `pip install openpyxl` |
| PPT (.pptx) | `python "$PPT_SCRIPTS/source_to_md/ppt_to_md.py" <file>` | `pip install python-pptx` |
| 网页 URL | `python "$PPT_SCRIPTS/source_to_md/web_to_md.py" <url>` | `pip install requests` |

> 转换依赖缺失时，提示安装对应的 pip 包。ppt-master 本体已自动克隆。

## PPT 转视频（特殊场景）

用户已有 PPT 并想转成短视频时，可以直接将幻灯片转成 SVG 再嵌入 HyperFrames：

```bash
python "$PPT_SCRIPTS/pptx_to_svg.py" <pptx_file> -o <project-dir>/slides/ --embed-images
```

产出：每张幻灯片一个 SVG 文件，嵌入 HyperFrames HTML 中作为场景画面。

**适用场景：**
- 用户有现成 PPT 想快速转抖音视频
- 企业宣传材料已有 PPT 版本
- 教育课件转短视频

**获取后：** 提炼核心信息点，准备进入 Stage 2 风格推导。

## 分类数据获取（当有分类配置时）

当用户指定了内容分类（如 GitHub、漫画、小说等），读取对应的分类配置文件获取数据获取策略：

```
clipforge/categories/{category}.md
```

分类配置中的 `content` 段定义了该分类特有的数据获取方式、选取策略和兜底方案。通用部分（文件提取、URL 读取等）在本文件前面已覆盖。

**如果没有分类配置**（用户直接提供文字/文件/URL），则只使用本文件前面的通用内容获取流程。

---

## Red Flags（停止信号）

| 信号 | 说明 |
|------|------|
| 分类数据未按配置验证 | 分类配置中的数据验证规则（如双源交叉验证）必须遵守 |
| 内容量不足以支撑视频 | 信息密度不够时停止，要求用户提供更多内容 |
| web-reader 未禁缓存 | 必须设置 `no_cache: true`，否则可能获取过期数据 |

## Common Rationalizations（常见借口反驳）

| 借口 | 事实 |
|------|------|
| "这些数据看起来合理" | 看起来合理 ≠ 数据准确。分类配置中的验证规则必须遵守 |
| "跳过数据验证，直接开始" | 错误数据进入视频 → 观众纠正 → 伤害频道可信度 |
| "内容不够但先做着" | 内容不足会导致视频空洞、节奏拖沓，必须补充后再继续 |
