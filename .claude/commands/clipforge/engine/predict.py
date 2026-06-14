"""播放量预测（P2）—— 基于内容特征预测播放潜力分。

当前为启发式版（基于 343 条历史数据的定性洞察）：
- 新鲜度：高新鲜度 → 避免同质疲劳 → 高播放（权重最大）
- hook 模式：反直觉/数字锚定 → 历史高播放（46K/42K 均值 vs 直接叙述 5K）
- 项目数：多项目盘点（5-6）→ 历史高峰（120K+）

待 auto_evolve 数据积累（≥100 条 join 样本）后，升级为训练的回归模型
（特征：题材/hook模式/项目数/时长/平台/周几 → log(播放量)）。

predicted_plays_score ∈ [0,1]，供 gate score 加 predicted_plays 参考分项。
"""
from __future__ import annotations
import re
from pathlib import Path

# 启发式权重（来自 343 数据定性洞察，非训练所得）
W_FRESHNESS = 0.40
W_HOOK_CONTRARIAN = 0.15
W_HOOK_NUMBER = 0.10
W_PROJECT_COUNT = 0.10  # 多项目盘点加成
BASE = 0.25

# 反直觉/冲突 hook 关键词（github.md hook_templates 验证：53.1% 完播率）
CONTRARIAN_WORDS = ("居然", "竟然", "不用", "无需", "砍掉", "翻车", "泄露", "免费", "零", "亲自", "下场")
NUMBER_RE = re.compile(r"\d")


def _hook_features(hook: str) -> tuple[bool, bool]:
    has_contrarian = any(w in hook for w in CONTRARIAN_WORDS)
    has_number = bool(NUMBER_RE.search(hook))
    return has_contrarian, has_number


def _project_count(project_dir: Path) -> int:
    """从 content_ready.txt 估算入选项目数（owner/repo 计数）。"""
    from engine.freshness import _project_set
    ps = _project_set(project_dir)
    return len(ps)


def predict_plays_score(project_dir, history_n: int = 10) -> dict:
    """预测播放潜力分 ∈ [0,1] + 分项明细。

    Returns:
        predicted_plays_score: float [0,1]
        features: {freshness, hook_contrarian, hook_number, project_count}
        note: 模型版本说明
    """
    from engine.freshness import compute_freshness, _hook_text
    p = Path(project_dir)
    fr = compute_freshness(p, history_n)
    hook = _hook_text(p)
    contra, num = _hook_features(hook)
    pcount = _project_count(p)

    score = BASE
    score += W_FRESHNESS * fr.get("freshness_score", 0.5)
    if contra:
        score += W_HOOK_CONTRARIAN
    if num:
        score += W_HOOK_NUMBER
    # 多项目盘点（5-6）加成，超过 6 边际递减
    if 4 <= pcount <= 7:
        score += W_PROJECT_COUNT

    return {
        "predicted_plays_score": round(min(max(score, 0), 1), 3),
        "features": {
            "freshness": fr.get("freshness_score"),
            "hook_contrarian": contra,
            "hook_number": num,
            "project_count": pcount,
        },
        "note": "heuristic-v1（基于343数据定性洞察，待 auto_evolve 积累≥100 join 样本后升级训练回归）",
    }


if __name__ == "__main__":
    import argparse, json
    ap = argparse.ArgumentParser(description="播放量潜力预测")
    ap.add_argument("--project-dir", required=True)
    ap.add_argument("--history-n", type=int, default=10)
    args = ap.parse_args()
    print(json.dumps(predict_plays_score(args.project_dir, args.history_n), ensure_ascii=False, indent=2))
