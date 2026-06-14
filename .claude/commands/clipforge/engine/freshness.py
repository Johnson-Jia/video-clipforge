"""新鲜度计算 — 衡量当前视频与近 N 期历史内容的相似度。

背景：score（合规度）与真实播放量在高位负相关（6 月满分期播放崩 99.7%），
根因之一是同质化疲劳——管线越成熟内容越像自己。本模块量化「像历史的程度」，
供 score 加新鲜度分项（P0-2）和 stage1 门禁（P0-3）使用。

freshness_score ∈ [0,1]，越高越新鲜（越不像历史）。
    freshness_score = 1 - max(hook_sim, project_jaccard, template_sim)
    （最像的那期决定新鲜度下限）

三个维度：
- hook_sim: hook 文本相似度（SequenceMatcher，取与历史最像的一期）
- project_jaccard: 入选项目集 Jaccard（owner/repo 重叠）
- template_sim: 叙事模板相似度（emotion/beat 序列按位置匹配率）

CLI: python engine/freshness.py --project-dir <dir> [--history-n 10]
"""
from __future__ import annotations
import json
import re
from difflib import SequenceMatcher
from pathlib import Path


def _workspace_root(project_dir: Path) -> Path | None:
    """从 project_dir 路径上找名为 workspace 的祖先。"""
    p = Path(project_dir).resolve()
    for parent in [p, *p.parents]:
        if parent.name == "workspace":
            return parent
    return None


def _find_recent_projects(current_dir: Path, n: int = 10) -> list[Path]:
    """找近 n 个有 narration_segments.json 的历史项目（排除当前，路径降序≈日期降序）。"""
    ws = _workspace_root(current_dir)
    if not ws:
        return []
    cur = Path(current_dir).resolve()
    projects: list[Path] = []
    for seg in ws.rglob("narration_segments.json"):
        proj = seg.parent
        try:
            if proj.resolve() == cur:
                continue
        except Exception:
            continue
        if "test" in proj.parts:  # 排除 workspace/test/ 验证目录，不污染历史扫描
            continue
        projects.append(proj)
    projects.sort(key=lambda p: str(p), reverse=True)
    return projects[:n]


def _load_segments(proj: Path) -> list[dict]:
    """读 narration_segments.json，兼容 array 与 {segments:[...]} / {scenes:[...]} 三种 schema。"""
    fp = proj / "narration_segments.json"
    if not fp.exists():
        return []
    try:
        data = json.loads(fp.read_text(encoding="utf-8"))
    except Exception:
        return []
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        return data.get("segments") or data.get("scenes") or []
    return []


def _hook_text(proj: Path) -> str:
    """第一段的 hook 文本（兼容 text / narration_segment 字段）。"""
    segs = _load_segments(proj)
    if not segs:
        return ""
    first = segs[0] if isinstance(segs[0], dict) else {}
    return str(first.get("text") or first.get("narration_segment") or "").strip()


def _beat_sequence(proj: Path) -> list[str]:
    """各段情绪序列（兼容 emotion / beat 字段）。"""
    seq: list[str] = []
    for s in _load_segments(proj):
        if not isinstance(s, dict):
            continue
        b = s.get("emotion") or s.get("beat")
        if b:
            seq.append(str(b))
    return seq


_PROJECT_RE = re.compile(r"([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)")


def _project_set(proj: Path) -> set[str]:
    """从 content_ready.txt / content.md 提取 owner/repo 项目集（小写归一）。"""
    for name in ("content_ready.txt", "content.md"):
        fp = proj / name
        if fp.exists():
            try:
                txt = fp.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            found = set(_PROJECT_RE.findall(txt))
            if found:
                return {f.lower() for f in found}
    return set()


def _sequence_sim(a: list[str], b: list[str]) -> float:
    """两个序列按元素位置的匹配率，归一化到较长序列长度。"""
    if not a or not b:
        return 0.0
    n = max(len(a), len(b))
    matches = sum(1 for i in range(min(len(a), len(b))) if a[i] == b[i])
    return matches / n


def compute_freshness(project_dir, history_n: int = 10) -> dict:
    """计算当前项目 vs 近 history_n 期历史的新鲜度。

    Returns:
        freshness_score: float [0,1]，越高越新鲜
        hook_sim / project_jaccard / template_sim: float [0,1]，各维度与历史最像一期的值
        compared_with: int，比对的历史项目数
        most_similar_dim: str，主导相似度的维度（hook/project/template/none）
        note: str，无历史时的说明
    """
    current = Path(project_dir)
    recents = _find_recent_projects(current, history_n)
    if not recents:
        return {
            "freshness_score": 1.0,
            "hook_sim": 0.0, "project_jaccard": 0.0, "template_sim": 0.0,
            "compared_with": 0, "most_similar_dim": "none",
            "note": "无历史可比，视为满分新鲜",
        }

    cur_hook = _hook_text(current)
    cur_projects = _project_set(current)
    cur_beats = _beat_sequence(current)

    max_hook = max_jac = max_tmpl = 0.0
    for r in recents:
        h = _hook_text(r)
        if cur_hook and h:
            max_hook = max(max_hook, SequenceMatcher(None, cur_hook, h).ratio())
        p = _project_set(r)
        if cur_projects and p:
            union = cur_projects | p
            if union:
                max_jac = max(max_jac, len(cur_projects & p) / len(union))
        b = _beat_sequence(r)
        if cur_beats and b:
            max_tmpl = max(max_tmpl, _sequence_sim(cur_beats, b))

    sims = {"hook": max_hook, "project": max_jac, "template": max_tmpl}
    similarity = max(sims.values())
    most_similar = max(sims, key=sims.get) if similarity > 0 else "none"

    return {
        "freshness_score": round(1 - similarity, 3),
        "hook_sim": round(max_hook, 3),
        "project_jaccard": round(max_jac, 3),
        "template_sim": round(max_tmpl, 3),
        "compared_with": len(recents),
        "most_similar_dim": most_similar,
    }


def recent_context(project_dir, n: int = 5) -> dict:
    """近 n 期历史摘要（供 inject 注入，引导 LLM 避开同质化）。

    Returns: {freshness: dict, recent_hooks: list[str], top_projects: list[str]}
    """
    current = Path(project_dir)
    recents = _find_recent_projects(current, n)
    hooks: list[str] = []
    proj_counter: dict[str, int] = {}
    for p in recents:
        h = _hook_text(p)
        if h:
            hooks.append(h[:40])
        for proj_name in _project_set(p):
            proj_counter[proj_name] = proj_counter.get(proj_name, 0) + 1
    top_projects = [p for p, _ in sorted(proj_counter.items(), key=lambda x: -x[1])[:8]]
    return {
        "freshness": compute_freshness(current, n),
        "recent_hooks": hooks,
        "top_projects": top_projects,
    }


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="计算项目新鲜度")
    ap.add_argument("--project-dir", required=True)
    ap.add_argument("--history-n", type=int, default=10)
    args = ap.parse_args()
    print(json.dumps(compute_freshness(args.project_dir, args.history_n), ensure_ascii=False, indent=2))
