# /clipforge-feedback — 播放数据分析与评分校准

手动触发视频播放数据采集和机器评分校准。

## 执行流程

### 1. 数据采集

```bash
cd .claude/commands/clipforge
python scripts/collect_performance.py --scan --backfill
```

扫描 `workspace/sources/视频数据/` 下所有日期目录，自动解析四平台数据、匹配到项目目录、回填 `performance.json`。

可选参数：
- `--date 2026-05-29` — 只处理指定日期
- `--dry-run` — 只看匹配结果，不写入
- `--json` — JSON 格式输出

### 2. 选择项目进行校准

展示所有已匹配到播放数据的项目列表，用户选择要分析的项目。

### 3. 进入 Stage 8 反馈流程

读取 `stages/stage8-feedback.md`，执行：
1. 读取项目的 `performance.json` + `score_report.json`
2. 收集人类主观评分（交互模式）
3. 运行机器评分校准（`attribution.py calibrate_machine_scoring()`）
4. 产出 `feedback.yaml`
5. 如有校准 Delta，写入 `deltas/` 并提示人工确认

### 数据目录

将平台导出数据放到 `workspace/sources/视频数据/YYYY-MM-DD/`：

| 平台 | 导出路径 | 文件名 |
|------|----------|--------|
| 抖音 | 创作者中心 → 数据中心 → 作品分析 → 投稿作品 → 投稿列表 → 选择全部 → 导出 | `抖音作品列表.xlsx` |
| B站 | 创作中心 → 数据概览 → 近期稿件对比 → 导出（每次10条，多次导出） | `哔哩哔哩近期稿件对比.csv` |
| 视频号 | 视频号助手 → 数据中心 → 视频数据 → 单篇视频 → 下载表格 | `微信视频号动态数据明细.csv` |
| 小红书 | 创作服务平台 → 数据看板 → 内容分析 → 笔记数据 → 全部 → 导出 | `小红书笔记列表明细表.xlsx` |
