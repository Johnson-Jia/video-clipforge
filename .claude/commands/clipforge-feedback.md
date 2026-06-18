# /clipforge-feedback — 自进化（全自动）

将各平台导出的播放数据放入 `workspace/sources/视频数据/YYYY-MM-DD/`。**B站 数据自动补全**——执行时检测今日目录若无 B站 文件，自动调 `fetch_bilibili.py` 导出（其他平台仍需手动浏览器导出）：

```bash
TODAY=$(date +%Y-%m-%d)
ROOT=$(git rev-parse --show-toplevel)
source "$HOME/.claude/commands/clipforge/shared/clipforge-env.sh" 2>/dev/null || source "${ROOT}/.claude/commands/clipforge/shared/clipforge-env.sh"  # 设 CF_DIR + cd 技能目录（用户级/项目级自适应）
BILI="${ROOT}/workspace/sources/视频数据/${TODAY}/哔哩哔哩近期稿件对比.csv"
if [ ! -f "$BILI" ]; then
  echo "今日 B站 数据缺失，自动导出..."
  python scripts/fetch_bilibili.py || echo "⚠ B站 抓取失败（cookie 可能过期 -101）：从浏览器 DevTools 复制整段 Cookie 覆盖 ${ROOT}/workspace/sources/视频数据/.bili-cookie 后重跑"
fi
# 刷新采集（fetch_bilibili 刚写入的新文件须 --scan 刷新，否则 auto_evolve 缓存漏采）
python scripts/collect_performance.py --scan
python scripts/auto_evolve.py
```

**全自动执行，无需人工操作。** 脚本依次执行：

1. **数据采集** — 扫描所有日期目录，解析四平台数据，匹配到项目目录
2. **批量分析** — 跨项目统计，计算 hook 类型/内容模式/收藏率与播放量的相关性
3. **模式提炼** — 从高分案例自动提取经验模式，保存到 `workspace/evolution/patterns/`
4. **Delta 生成** — 数据驱动的规则变更，安全规则自动生效
5. **阈值校准** — 根据实际数据分布更新 `workspace/evolution/thresholds.yaml`

## 数据目录

将平台导出数据放到 `workspace/sources/视频数据/YYYY-MM-DD/`：

| 平台 | 导出路径 | 文件名 |
|------|----------|--------|
| 抖音 | 创作者中心 → 数据中心 → 作品分析 → 投稿作品 → 投稿列表 → 选择全部 → 导出 | `抖音作品列表.xlsx` |
| B站 | 创作中心 → 数据概览 → 近期稿件对比 → 导出（每次10条，多次导出） | `哔哩哔哩近期稿件对比.csv` |
| 视频号 | 视频号助手 → 数据中心 → 视频数据 → 单篇视频 → 下载表格 | `微信视频号动态数据明细.csv` |
| 小红书 | 创作服务平台 → 数据看板 → 内容分析 → 笔记数据 → 全部 → 导出 | `小红书笔记列表明细表.xlsx` |

## 输出

运行数据全部写入 `workspace/evolution/`（技能目录只留静态定义，运行数据隔离）：

- `workspace/evolution/patterns/*.yaml` — 新增/更新的经验模式（auto）
- `workspace/evolution/deltas/*.yaml` — 数据驱动的 Delta 规则
- `workspace/evolution/thresholds.yaml` — 更新的性能阈值
- `workspace/sources/evolution-report-YYYYMMDD.json` — 进化报告

## 手动模式（可选）

如需对单个项目进行人工评分校准：

```bash
python scripts/collect_performance.py --scan --backfill
```

然后读取 `stages/stage8-feedback.md` 执行人工评分流程。
