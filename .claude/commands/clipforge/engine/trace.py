"""轨迹采集 — 执行轨迹记录与查询。

支持结构化 execution 字段：
- steps: 决策节点列表 [{decision, chosen, reason, alternatives, ts}]
- path_switches: 路径切换记录 [{from_path, to_path, trigger, ts}]
- token_usage: {prompt, completion, total}

支持发布后播放数据回填：
- performance: {platform, plays, completion_rate, completion_5s_rate, ...}
"""
from __future__ import annotations
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

TRACES_DIR = Path(__file__).parent.parent / "traces"


def record_trace(
    skill_id: str,
    project_dir: str,
    result: str,
    gate_report: dict | None = None,
    execution: dict | None = None,
    context: dict | None = None,
    performance: dict | None = None,
    traces_dir: Path | None = None,
    category: str | None = None,
) -> Path:
    traces_dir = traces_dir or TRACES_DIR
    traces_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    trace_id = f"T-{ts}-{skill_id}"

    exec_data = execution or {}
    trace = {
        "id": trace_id,
        "skill_id": skill_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "project_dir": str(project_dir),
        "context": context or {},
        "execution": {
            "steps": exec_data.get("steps", []),
            "path_switches": exec_data.get("path_switches", []),
            "token_usage": exec_data.get("token_usage"),
        },
        "result": {
            "status": result,
            "gate_report": gate_report,
        },
        "attribution": None,
        "performance": performance,
    }

    project_traces = traces_dir / Path(project_dir).name
    project_traces.mkdir(parents=True, exist_ok=True)
    filepath = project_traces / "trace.json"

    existing: list[dict] = []
    if filepath.exists():
        try:
            existing = json.loads(filepath.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            existing = []
    existing.append(trace)
    filepath.write_text(json.dumps(existing, ensure_ascii=False, indent=2), encoding="utf-8")

    # 规则命中统计
    if result == "pass" and skill_id:
        try:
            from engine.lib.rule_parser import load_rules_by_scope, update_hit_counts
            injected_rules = load_rules_by_scope(skill_id, category)
            update_hit_counts("global", [r.id for r in injected_rules])
        except Exception:
            pass  # 统计失败不阻塞 trace 记录

    return filepath


def backfill_performance(
    project_dir: str,
    performance: dict,
    traces_dir: Path | None = None,
) -> int:
    """回填播放数据到已有 trace。返回更新的 trace 数量。"""
    traces_dir = traces_dir or TRACES_DIR
    project_traces = traces_dir / Path(project_dir).name
    filepath = project_traces / "trace.json"
    if not filepath.exists():
        return 0

    traces = json.loads(filepath.read_text(encoding="utf-8"))
    updated = 0
    for t in traces:
        if t.get("performance") is None:
            t["performance"] = performance
            updated += 1
    if updated:
        filepath.write_text(json.dumps(traces, ensure_ascii=False, indent=2), encoding="utf-8")
    return updated


def query_traces(
    skill_id: str | None = None,
    last: int = 50,
    traces_dir: Path | None = None,
    has_performance: bool = False,
) -> list[dict]:
    traces_dir = traces_dir or TRACES_DIR
    if not traces_dir.exists():
        return []
    all_traces: list[dict] = []
    for tf in traces_dir.rglob("trace.json"):
        try:
            traces = json.loads(tf.read_text(encoding="utf-8"))
            all_traces.extend(traces)
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue
    if skill_id:
        all_traces = [t for t in all_traces if t.get("skill_id") == skill_id]
    if has_performance:
        all_traces = [t for t in all_traces if t.get("performance")]
    all_traces.sort(key=lambda t: t.get("timestamp", ""), reverse=True)
    return all_traces[:last]


def query_traces_with_performance(
    traces_dir: Path | None = None,
    last: int = 200,
) -> list[dict]:
    """查询所有带播放数据的 trace，供归因和成功分析使用。"""
    return query_traces(traces_dir=traces_dir, last=last, has_performance=True)


def main():
    parser = argparse.ArgumentParser(description="ClipForge 轨迹采集")
    sub = parser.add_subparsers(dest="command")

    rec = sub.add_parser("record")
    rec.add_argument("--skill-id", required=True)
    rec.add_argument("--project-dir", required=True)
    rec.add_argument("--result", required=True, choices=["pass", "fail"])
    rec.add_argument("--gate-report", default=None)
    rec.add_argument("--execution", default=None, help="JSON: {steps, path_switches, token_usage}")
    rec.add_argument("--performance", default=None, help="JSON: {platform, plays, ...}")

    q = sub.add_parser("query")
    q.add_argument("--skill-id", default=None)
    q.add_argument("--last", type=int, default=50)
    q.add_argument("--has-performance", action="store_true")

    bf = sub.add_parser("backfill")
    bf.add_argument("--project-dir", required=True)
    bf.add_argument("--performance", required=True, help="JSON: {platform, plays, ...}")

    args = parser.parse_args()
    if args.command == "record":
        gate = json.loads(args.gate_report) if args.gate_report else None
        exec_data = json.loads(args.execution) if args.execution else None
        perf = json.loads(args.performance) if args.performance else None
        path = record_trace(args.skill_id, args.project_dir, args.result, gate, exec_data, performance=perf)
        print(json.dumps({"saved": str(path)}))
    elif args.command == "query":
        traces = query_traces(args.skill_id, args.last, has_performance=args.has_performance)
        print(json.dumps(traces, ensure_ascii=False, indent=2))
    elif args.command == "backfill":
        perf = json.loads(args.performance)
        n = backfill_performance(args.project_dir, perf)
        print(json.dumps({"updated": n}))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
