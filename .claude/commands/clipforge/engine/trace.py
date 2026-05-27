"""轨迹采集 — 执行轨迹记录与查询。

支持结构化 execution 字段：
- steps: 决策节点列表 [{decision, chosen, reason, alternatives, ts}]
- path_switches: 路径切换记录 [{from_path, to_path, trigger, ts}]
- token_usage: {prompt, completion, total}
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
    traces_dir: Path | None = None,
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
    return filepath


def query_traces(
    skill_id: str | None = None,
    last: int = 50,
    traces_dir: Path | None = None,
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
    all_traces.sort(key=lambda t: t.get("timestamp", ""), reverse=True)
    return all_traces[:last]


def main():
    parser = argparse.ArgumentParser(description="ClipForge 轨迹采集")
    sub = parser.add_subparsers(dest="command")

    rec = sub.add_parser("record")
    rec.add_argument("--skill-id", required=True)
    rec.add_argument("--project-dir", required=True)
    rec.add_argument("--result", required=True, choices=["pass", "fail"])
    rec.add_argument("--gate-report", default=None)
    rec.add_argument("--execution", default=None, help="JSON: {steps, path_switches, token_usage}")

    q = sub.add_parser("query")
    q.add_argument("--skill-id", default=None)
    q.add_argument("--last", type=int, default=50)

    args = parser.parse_args()
    if args.command == "record":
        gate = json.loads(args.gate_report) if args.gate_report else None
        exec_data = json.loads(args.execution) if args.execution else None
        path = record_trace(args.skill_id, args.project_dir, args.result, gate, exec_data)
        print(json.dumps({"saved": str(path)}))
    elif args.command == "query":
        traces = query_traces(args.skill_id, args.last)
        print(json.dumps(traces, ensure_ascii=False, indent=2))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
