# 字体调色板（技术工具箱）

> **Stage 2/6 读取。** 纯技术参数表。字体选择的情感逻辑见 `director-toolkit.md` 第 2 层「字体气质」。本文件只回答"这个字体怎么加载、怎么注入"。

## 标题展示体

每条视频**只选 1 种**中文展示体（气质由 `director-toolkit.md` 的 Q1 情感内核决定）。

| 字体 | 字重 | Google Fonts family | fallback 链 | 对应气质 |
|------|------|---------------------|------------|---------|
| Ma Shan Zheng | 400（单字重） | `Ma+Shan+Zheng` | `'Ma Shan Zheng','PingFang SC','Microsoft YaHei',cursive` | 毛笔力量 |
| Noto Serif SC | 500 / 700 / 900 | `Noto+Serif+SC:wght@500;700;900` | `'Noto Serif SC','Songti SC','SimSun',serif` | 衬线庄重 |
| ZCOOL XiaoWei | 400（单字重） | `ZCOOL+XiaoWei` | `'ZCOOL XiaoWei','Songti SC','Microsoft YaHei',serif` | 细楷诗意 |
| ZCOOL QingKe HuangYou | 400（单字重） | `ZCOOL+QingKe+HuangYou` | `'ZCOOL QingKe HuangYou','PingFang SC','Microsoft YaHei',sans-serif` | 圆润亲和 |
| JetBrains Mono | 400 / 700 / 800 | `JetBrains+Mono:wght@400;700;800` | `'JetBrains Mono','Consolas',monospace` | 等宽极客 |
| Inter | 400 / 700 / 900 | `Inter:wght@400;700;900` | `'Inter','PingFang SC','Microsoft YaHei',sans-serif` | 几何简洁 |

## 正文可读体

正文层固定用无衬线体，不追求个性。两个选择：

| 字体 | 字重 | Google Fonts family | fallback 链 |
|------|------|---------------------|------------|
| Noto Sans SC | 300 / 400 / 500 / 700 | `Noto+Sans+SC:wght@300;400;500;700` | `'Noto Sans SC','PingFang SC','Microsoft YaHei',sans-serif` |
| Inter | 400 / 500 / 700 | `Inter:wght@400;500;700` | `'Inter','PingFang SC','Microsoft YaHei',sans-serif` |

> 默认用 Noto Sans SC（中文项目正文更协调）。纯英文/数字场景可换 Inter。

## 数据等宽体

数据层固定用等宽体，确保数字对齐、可辨。

| 字体 | 字重 | Google Fonts family | fallback 链 |
|------|------|---------------------|------------|
| JetBrains Mono | 400 / 700 | `JetBrains+Mono:wght@400;700` | `'JetBrains Mono','Consolas',monospace` |

## Google Fonts URL 拼装

一条视频用**一个 `<link>`** 合并所有需要的字体（family 用 `&` 连接，字重用 `;` 分隔）：

```
https://fonts.googleapis.com/css2?family=<F1>:wght@<w1>;<w2>&family=<F2>&family=<F3>:wght@<w1>&display=swap
```

**拼装示例**（标题=Ma Shan Zheng，正文=Noto Sans SC，数据=JetBrains Mono）：
```
https://fonts.googleapis.com/css2?family=Ma+Shan+Zheng&family=Noto+Sans+SC:wght@300;400;500;700&family=JetBrains+Mono:wght@400;700&display=swap
```

## design.md ↔ CSS 变量映射

Stage 2 在 design.md 的 `fonts` 字段声明选择，Stage 6 据此注入 CSS 变量到 `:root`：

| design.md 字段 | CSS 变量 | 用途 |
|---------------|---------|------|
| `fonts.title.family` + fallback | `--font-title` | 标题层 |
| `fonts.title.weight` | `--title-weight` | 标题字重 |
| `fonts.body.family` + fallback | `--font-body` | 正文层 |
| `fonts.data.family` + fallback | `--font-data` | 数据层 |

场景 HTML 用 `font-family: var(--font-title)` 引用，**禁止硬编码字体名**（封面除外，封面有独立字体规则）。

## 加载注意事项

- **CJK 字体文件大（2-10MB）**，首次渲染需 2-5 秒。`&display=swap` 确保加载期间用 fallback 显示，加载完自动切换
- 一条视频**最多加载 1 种中文展示体**（毛笔/宋体/圆体/楷体择一），避免文件体积过大拖慢渲染
- 数据等宽体（JetBrains Mono）文件小，可放心加载多字重
- 网络不通时 fallback 到系统字体（PingFang SC / Microsoft YaHei），不阻塞渲染

## 扩展字体

想加新字体？三步：

1. 本文件对应分类表格加一行（字体名 / 字重 / Google Fonts family / fallback）
2. `director-toolkit.md` 的气质映射表加一行（气质 / 字体 / 适合情感）
3. `scripts/s6_assemble_html.py` 的 `GOOGLE_FONT_MAP` 加一行（family 名 → Google Fonts URL family 参数）

第 3 步缺失会触发门禁：design.md 声明了字体但 `index.html` 的 Google Fonts `<link>` 未加载它时，gate `font_consistency`（SOFT）会告警，渲染降级为系统 fallback。单权重字体写裸 family 名（`"Ma Shan Zheng": "Ma+Shan+Zheng"`），多权重附 `:wght@`（`"Noto Sans SC": "Noto+Sans+SC:wght@300;400;500;700"`）。
