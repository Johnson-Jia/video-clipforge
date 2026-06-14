"""播放量预测（P2）—— 启发式 v1 + 训练升级钩子（不遗忘机制）。

数据 < MIN_SAMPLES(100)：启发式（freshness + hook 模式 + 项目数）
数据 ≥ MIN_SAMPLES：auto_evolve 自动触发 train_if_ready → Ridge 回归 → 持久化
predict_plays_score 优先用训练模型，启发式兜底

不遗忘（数据达标自动升级，无需人工记得）：
- 模型持久化 workspace/evolution/models/plays_model.joblib + meta.json
- auto_evolve 每次 Phase 6 调 train_if_ready：<100 样本返回「待训练」，≥100 自动训练
- meta 记 version/samples/r2/训练分布分位数，predict 据此把 log_plays 归一化到 0-1
"""
from __future__ import annotations
import json
import re
from pathlib import Path

# 启发式权重（343 数据定性洞察）
W_FRESHNESS = 0.40
W_HOOK_CONTRARIAN = 0.15
W_HOOK_NUMBER = 0.10
W_PROJECT_COUNT = 0.10
BASE = 0.25
MIN_SAMPLES = 100

CONTRARIAN_WORDS = ("居然", "竟然", "不用", "无需", "砍掉", "翻车", "泄露", "免费", "零", "亲自", "下场")
NUMBER_RE = re.compile(r"\d")

FEAT_NAMES = ["freshness", "hook_contrarian", "hook_number", "project_count"]


def _models_dir() -> Path:
    """workspace/evolution/models/（与 auto patterns 同级 evolution 下）。"""
    from engine.lib.data_paths import auto_patterns_dir
    return auto_patterns_dir().parent / "models"


def _model_file() -> Path:
    return _models_dir() / "plays_model.joblib"


def _meta_file() -> Path:
    return _models_dir() / "plays_model_meta.json"


def _load_model():
    """返回 (bundle, meta) 或 (None, None)。bundle={model, features}。"""
    try:
        mf, meta_f = _model_file(), _meta_file()
        if mf.exists() and meta_f.exists():
            import joblib
            return joblib.load(mf), json.loads(meta_f.read_text("utf-8"))
    except Exception:
        pass
    return None, None


def _heuristic_score(freshness, contra, num, pcount):
    score = BASE
    score += W_FRESHNESS * (freshness if freshness is not None else 0.5)
    if contra:
        score += W_HOOK_CONTRARIAN
    if num:
        score += W_HOOK_NUMBER
    if 4 <= pcount <= 7:
        score += W_PROJECT_COUNT
    return round(min(max(score, 0), 1), 3)


def train_if_ready(samples):
    """训练钩子：auto_evolve 每次调用。

    samples = [{freshness, hook_contrarian, hook_number, project_count, log_plays}, ...]
    ≥ MIN_SAMPLES → Ridge 训练 + 持久化模型/meta（含训练分布分位数）→ 升级 model_version
    < MIN_SAMPLES → 返回待训练状态（不遗忘：auto_evolve 每日 check，达标自动训练）

    Returns: {trained, samples, needed?, r2?, version?, note?}
    """
    n = len(samples)
    if n < MIN_SAMPLES:
        return {"trained": False, "samples": n, "needed": MIN_SAMPLES,
                "note": f"样本不足 {n}/{MIN_SAMPLES}，继续启发式；auto_evolve 每日检查，达标自动训练"}

    try:
        import joblib
        import numpy as np
        from sklearn.linear_model import Ridge
        from sklearn.model_selection import train_test_split
        from datetime import datetime, timezone

        X = np.array([[float(s[f]) for f in FEAT_NAMES] for s in samples])
        y = np.array([float(s["log_plays"]) for s in samples])
        X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.2, random_state=42)
        model = Ridge(alpha=1.0).fit(X_tr, y_tr)
        r2 = model.score(X_te, y_te)
        # 训练分布分位数（predict 把 log_plans 归一化到 0-1 用）
        qs = {f"P{p}": round(float(np.percentile(y, p)), 3) for p in (10, 50, 90)}

        d = _models_dir()
        d.mkdir(parents=True, exist_ok=True)
        joblib.dump({"model": model, "features": FEAT_NAMES}, _model_file())
        version = f"trained-v{datetime.now(timezone.utc).strftime('%Y%m%d')}"
        _meta_file().write_text(json.dumps({
            "version": version, "samples": n, "r2": round(float(r2), 3),
            "trained_at": datetime.now(timezone.utc).isoformat(),
            "features": FEAT_NAMES, "log_plays_quantiles": qs,
        }, ensure_ascii=False, indent=2), "utf-8")
        return {"trained": True, "samples": n, "r2": round(float(r2), 3), "version": version}
    except Exception as e:
        return {"trained": False, "error": str(e), "samples": n,
                "note": "训练失败（sklearn/joblib 未装或数据问题），继续启发式"}


def predict_plays_score(project_dir, history_n: int = 10) -> dict:
    """预测播放潜力分 ∈ [0,1]。

    优先用训练模型（log_plays → 按 P10/P90 线性映射到 0.1-0.9）；
    模型不存在/预测失败 → 启发式兜底。
    """
    from engine.freshness import compute_freshness, _hook_text, _project_set
    p = Path(project_dir)
    fr = compute_freshness(p, history_n)
    hook = _hook_text(p)
    contra = any(w in hook for w in CONTRARIAN_WORDS)
    num = bool(NUMBER_RE.search(hook))
    pcount = len(_project_set(p))
    features = {
        "freshness": fr.get("freshness_score", 0.5),
        "hook_contrarian": contra, "hook_number": num, "project_count": pcount,
    }

    bundle, meta = _load_model()
    if bundle and meta:
        try:
            import numpy as np
            feats = bundle["features"]
            x = np.array([[float(features[f]) for f in feats]])
            log_pred = float(bundle["model"].predict(x)[0])
            qs = meta.get("log_plays_quantiles", {})
            p10, p90 = qs.get("P10", 7.0), qs.get("P90", 12.0)
            score = 0.1 + 0.8 * (log_pred - p10) / max(p90 - p10, 0.01)
            return {
                "predicted_plays_score": round(min(max(score, 0), 1), 3),
                "features": features, "model_version": meta.get("version"),
                "log_plays_pred": round(log_pred, 3),
                "note": f"训练模型预测（r2={meta.get('r2')}）",
            }
        except Exception:
            pass  # 预测失败，兜底启发式

    return {
        "predicted_plays_score": _heuristic_score(features["freshness"], contra, num, pcount),
        "features": features, "model_version": "heuristic-v1",
        "note": "启发式（auto_evolve 积累≥100 join 样本后自动训练升级）",
    }


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="播放量潜力预测")
    ap.add_argument("--project-dir", required=True)
    ap.add_argument("--history-n", type=int, default=10)
    args = ap.parse_args()
    print(json.dumps(predict_plays_score(args.project_dir, args.history_n), ensure_ascii=False, indent=2))
