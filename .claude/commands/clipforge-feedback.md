# /clipforge-feedback — 自进化（全自动）

将各平台导出的播放数据放入 `workspace/sources/视频数据/YYYY-MM-DD/`，然后运行：

```bash
cd .claude/commands/clipforge
python scripts/auto_evolve.py
```

**全自动执行，无需人工操作。** 脚本依次执行：

1. **数据采集** — 扫描所有日期目录，解析四平台数据，匹配到项目目录
2. **批量分析** — 跨项目统计，计算 hook 类型/内容模式/收藏率与播放量的相关性
3. **模式提炼** — 从高分案例自动提取经验模式，保存到 `patterns/`
4. **Delta 生成** — 数据驱动的规则变更，安全规则自动生效
5. **阈值校准** — 根据实际数据分布更新 `engine/lib/thresholds.yaml`

## 数据目录

将平台导出数据放到 `workspace/sources/视频数据/YYYY-MM-DD/`：

| 平台 | 导出路径 | 文件名 |
|------|----------|--------|
| 抖音 | 创作者中心 → 数据中心 → 作品分析 → 投稿作品 → 投稿列表 → 选择全部 → 导出 | `抖音作品列表.xlsx` |
| B站 | 创作中心 → 数据概览 → 近期稿件对比 → 导出（每次10条，多次导出） | `哔哩哔哩近期稿件对比.csv` |
| 视频号 | 视频号助手 → 数据中心 → 视频数据 → 单篇视频 → 下载表格 | `微信视频号动态数据明细.csv` |
| 小红书 | 创作服务平台 → 数据看板 → 内容分析 → 笔记数据 → 全部 → 导出 | `小红书笔记列表明细表.xlsx` |

## 输出

- `patterns/*.yaml` — 新增/更新的经验模式
- `deltas/*.yaml` — 数据驱动的 Delta 规则
- `engine/lib/thresholds.yaml` — 更新的性能阈值
- `workspace/sources/evolution-report-YYYYMMDD.json` — 进化报告

## 手动模式（可选）

如需对单个项目进行人工评分校准：

```bash
python scripts/collect_performance.py --scan --backfill
```

然后读取 `stages/stage8-feedback.md` 执行人工评分流程。
