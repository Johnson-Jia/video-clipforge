"""成功分析引擎 — 高分案例采集、经验模式提炼、约束放宽提案。"""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from engine.trace import query_traces, TRACES_DIR
from engine.lib.delta import create_delta, save_delta, DELTAS_DIR


PATTERNS_DIR = Path(__file__).parent.parent / "patterns"
DEFAULT_THRESHOLD = 0.85


def find_high_score_traces(traces_dir: Path | None = None, threshold: float = DEFAULT_THRESHOLD) -> list[dict]:
    all_traces = query_traces(traces_dir=traces_dir, last=500)
    high_score: list[dict] = []
    for t in all_traces:
        gate = t.get("result", {}).get("gate_report", {})
        if gate and gate.get("hard_passed") is True:
            score = gate.get("soft_score", 0.0)
            if score >= threshold:
                high_score.append(t)
    return high_score


def extract_patterns(high_score_traces: list[dict], min_samples: int = 3) -> list[dict]:
    if len(high_score_traces) < min_samples:
        return []

    skill_groups: dict[str, list[dict]] = {}
    for t in high_score_traces:
        sid = t.get("skill_id", "unknown")
        skill_groups.setdefault(sid, []).append(t)

    patterns: list[dict] = []
    for sid, traces in skill_groups.items():
        if len(traces) < min_samples:
            continue
        avg_score = sum(
            t.get("result", {}).get("gate_report", {}).get("soft_score", 0) for t in traces
        ) / len(traces)
        pattern = {
            "id": f"P-{sid}",
            "skill_scope": sid,
            "description": f"Skill {sid} 连续 {len(traces)} 次高分通过",
            "evidence": {
                "sample_size": len(traces),
                "avg_soft_score": round(avg_score, 3),
                "confidence": min(0.5 + len(traces) * 0.1, 0.95),
            },
            "as_preference": {
                "text": f"Skill {sid} 的执行路径高效，可直接复用",
                "weight": "MEDIUM",
                "source_pattern": f"P-{sid}",
            },
        }
        patterns.append(pattern)
    return patterns


def save_pattern(pattern: dict, patterns_dir: Path | None = None) -> Path:
    patterns_dir = patterns_dir or PATTERNS_DIR
    patterns_dir.mkdir(parents=True, exist_ok=True)
    filepath = patterns_dir / f"{pattern['id']}.yaml"

    import yaml
    with open(filepath, "w", encoding="utf-8") as f:
        yaml.dump(pattern, f, allow_unicode=True, default_flow_style=False)
    return filepath


def main():
    parser = argparse.ArgumentParser(description="ClipForge 成功分析引擎")
    parser.add_argument("--traces-dir", default=None)
    parser.add_argument("--min-score", type=float, default=DEFAULT_THRESHOLD)
    parser.add_argument("--min-samples", type=int, default=3)
    parser.add_argument("--save", action="store_true", help="保存提炼的模式")
    args = parser.parse_args()

    traces_dir = Path(args.traces_dir) if args.traces_dir else None
    high_score = find_high_score_traces(traces_dir, args.min_score)
    patterns = extract_patterns(high_score, args.min_samples)

    output = {
        "high_score_count": len(high_score),
        "patterns_found": len(patterns),
        "patterns": patterns,
    }

    if args.save and patterns:
        for p in patterns:
            path = save_pattern(p)
            output["saved"] = output.get("saved", [])
            output["saved"].append(str(path))

    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
