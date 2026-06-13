"""探索-利用决策器（epsilon-greedy，种子化确定性）。

哲学：纯利用（exploitation）系统会收敛到局部最优——只加权已知高表现维度，
永远发现不了下一个爆款（multi-armed bandit 的 exploitation 死锁）。冷启动维度
永远无数据 → 永远不分析 → 冷启动死锁。本模块用 epsilon-greedy 打破死锁：
约 85% 视频走 exploit（注入当前最强 pattern 组合），15% 走 explore（刻意注入
低数据 pattern 主动采集数据）。

决策种子化（date+project_dir 的 sha1），保证：
- 同一视频同一天决策一致（交互 /clipforge 与 cron 模式调用同一函数，禁止内联分叉）
- 全 DAG 各 SubAgent 读同一份 exploration_directive.yaml，注入策略一致

输出 {project_dir}/exploration_directive.yaml，inject.py 读取后据此：
- explore 模式：force 注入 target_patterns（绕过 skill_scope 过滤，把冷门维度推到 LLM 面前）
- exploit 模式：注入策略引导（优先采用高权重经验）
"""
from __future__ import annotations
import argparse
import hashlib
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from engine.lib.data_paths import auto_patterns_dir
PATTERNS_DIR = auto_patterns_dir()
EPSILON = 0.15          # explore 概率（85% exploit / 15% explore）
WEIGHT_RANK = {"HIGH": 3, "MEDIUM": 2, "LOW": 1}
TOP_N = 3               # exploit/explore 各选多少 pattern


def _norm_path(project_dir: str) -> str:
    """规范化项目路径为种子输入：取 workspace 相对路径，避免绝对/相对路径差异致种子不一致。"""
    p = str(project_dir).replace("\\", "/")
    if "/workspace/" in p:
        p = p.split("/workspace/", 1)[1]
    else:
        parts = [x for x in p.split("/") if x]
        p = "/".join(parts[-3:]) if len(parts) >= 3 else "/".join(parts)
    return p


def _seed(project_dir: str, date_str: str) -> int:
    """确定性种子：sha1(date|norm_path) → int。同 project+date 永远同决策。"""
    key = f"{date_str}|{_norm_path(project_dir)}"
    return int(hashlib.sha1(key.encode("utf-8")).hexdigest()[:8], 16)


def decide(project_dir: str, date_str: str, category: str = "github",
           patterns_dir: Path | None = None) -> dict:
    """决定本次视频 explore/exploit + 选中的 target_patterns（只处理 seed:false 的 auto pattern）。

    explore：选 sample_size 最低的 active pattern（主动采集冷门维度数据）
    exploit：选 weight 最高的 active pattern（用当前最强组合）
    seed pattern（人工经验）不参与探索-利用，始终经 inject 正常注入。
    """
    patterns_dir = patterns_dir or PATTERNS_DIR
    candidates = []
    for fp in sorted(patterns_dir.glob("P-*.yaml")):
        try:
            import yaml
            data = yaml.safe_load(fp.read_text("utf-8"))
        except Exception:
            continue
        if not data or data.get("seed") is True:
            continue
        if data.get("status") == "deprecated":
            continue
        if category and data.get("category") and data.get("category") != category:
            continue
        ev = data.get("evidence") or {}
        candidates.append({
            "id": data.get("id") or fp.stem,
            "weight": (data.get("as_preference") or {}).get("weight", "MEDIUM"),
            "sample_size": ev.get("sample_size", 0),
            "skill_scope": data.get("skill_scope", ""),
        })
    seed = _seed(project_dir, date_str)
    rng = random.Random(seed)
    is_explore = rng.random() < EPSILON
    if is_explore:
        chosen = sorted(candidates, key=lambda p: p["sample_size"])[:TOP_N]
        mode = "explore"
    else:
        chosen = sorted(candidates, key=lambda p: -WEIGHT_RANK.get(p["weight"], 2))[:TOP_N]
        mode = "exploit"
    target_patterns = [{
        "id": p["id"],
        "weight": p["weight"],
        "skill_scope": p["skill_scope"],
        "reason": (f"explore-sampling(sample_size={p['sample_size']})" if is_explore
                   else f"exploit-strongest(weight={p['weight']})"),
        "force": is_explore,   # explore 时 inject force 注入（绕 skill_scope）；deprecated 已在上面排除
    } for p in chosen]
    return {
        "mode": mode,
        "seed": seed,
        "epsilon": EPSILON,
        "norm_path": _norm_path(project_dir),
        "date": date_str,
        "target_patterns": target_patterns,
    }


def write_directive(project_dir: str, date_str: str, category: str = "github") -> Path:
    """生成 exploration_directive.yaml 写入项目目录。"""
    import yaml
    result = decide(project_dir, date_str, category)
    proj = Path(project_dir)
    proj.mkdir(parents=True, exist_ok=True)
    fp = proj / "exploration_directive.yaml"
    fp.write_text(yaml.dump(result, allow_unicode=True, default_flow_style=False), encoding="utf-8")
    return fp


def main():
    parser = argparse.ArgumentParser(description="ClipForge 探索-利用决策器（种子化确定性）")
    parser.add_argument("--project-dir", required=True)
    parser.add_argument("--date", required=True, help="YYYY-MM-DD")
    parser.add_argument("--category", default="github")
    parser.add_argument("--stdout", action="store_true", help="打印 directive JSON 到 stdout（不写盘）")
    args = parser.parse_args()
    if args.stdout:
        import json
        print(json.dumps(decide(args.project_dir, args.date, args.category), ensure_ascii=False, indent=2))
    else:
        result = decide(args.project_dir, args.date, args.category)
        fp = write_directive(args.project_dir, args.date, args.category)
        print(f"exploration_directive: {fp}")
        print(f"  mode={result['mode']} seed={result['seed']} targets={[p['id'] for p in result['target_patterns']]}")


if __name__ == "__main__":
    main()
