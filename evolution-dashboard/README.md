# ClipForge 自进化可视化仪表盘

独立于 clipforge 技能包的运营工具——可视化自进化数据 + 手动调权重干预。
单向消费 clipforge 数据（patterns/deltas/thresholds/regression/performance），写仅限 dimension_weights + pattern weight。

## 启动

```bash
cd evolution-dashboard
python server.py
```
浏览器开 **http://127.0.0.1:8765**

## 功能

| 标签 | 内容 |
|------|------|
| **Pattern 权重** | 按维度（题材/hook/封面/旁白）分组；维度权重滑块（0~2）+ 单 pattern weight（LOW/MEDIUM/HIGH）+ status（启用/禁用）；effective_rank 实时显示 |
| **回归归因** | 各协变量净效应条形图（statsmodels OLS，p<0.1 显著高亮）+ R²/N |
| **视频数据** | 61 视频 reach 分布柱状图 + 维度广度对比 + 明细表 |
| **阈值** | 各平台 success 阈值（douyin c5s/save_rate 等） |
| **Delta** | 规则 delta 列表（target/confidence/safe） |

## 权重生效机制

```
effective_rank = WEIGHT_RANK[pattern.weight] × dim_weight[维度]
  WEIGHT_RANK: HIGH=3, MEDIUM=2, LOW=1；范围 0~6
  inject 注入时按 effective 降序：
    ≥3 → 文本标注 [优先采用]
    ≤1.5 → 文本标注 [次要参考]
```

调权重立即写回 `dimension_weights.yaml` / pattern yaml，下次 `engine/inject.py` 立即按新权重排序注入。

## 架构

- **后端** `server.py`：Python 标准库 `http.server`（无 Flask 依赖），JSON API
- **前端** `templates/index.html`：原生 JS + ECharts 图表（本地 `static/echarts.min.js`，离线）
- **数据根**：相对路径 `../.claude/commands/clipforge`（patterns/deltas/thresholds/dimension_weights）+ `../workspace`（performance.json）

## 依赖

- ECharts 5（已下载到 `static/echarts.min.js`，离线）
- 复用 clipforge `engine.lib`（thresholds/delta loader）+ `auto_evolve` 分类器 + `success_analyzer` 评分
