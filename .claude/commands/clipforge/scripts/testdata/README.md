# 测试 fixture

从 B站创作中心抓包的真实响应样本（脱敏：去掉 cover URL）。不含 cookie。

- `bili_index_p1.json` — `archive/index` 第1页响应（含 stat:null 用 real_stat 的稿件 + 字符串值字段）
- `bili_compare.json` — `archive_diagnose/compare` 响应（含 not_ready 稿件 + 全就绪稿件）

供 `fetch_bilibili.py --self-test` 使用，验证解析/合并/CSV 逻辑。
