#!/usr/bin/env python3
"""发布时机建议写入项目目录 — 交付时给用户发布参考。

读 workspace/evolution/publish_timing_advice.json，渲染 publish_note.md 到项目目录。
运营决策维度，关联非因果，不进创作 pattern。

用法:
  python scripts/write_publish_note.py --project-dir workspace/2026/06/20/github-trending
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
CLIPFORGE_DIR = SCRIPT_DIR.parent
sys.path.insert(0, str(CLIPFORGE_DIR))

from engine.lib.data_paths import WORKSPACE_ROOT as PROJECT_ROOT  # noqa: E402
from engine.publish_time import render_publish_note  # noqa: E402


def _default_advice_path() -> Path:
    """advice 默认路径：与 auto_evolve 写入位置一致（项目根/workspace/evolution/）。"""
    return PROJECT_ROOT / "workspace" / "evolution" / "publish_timing_advice.json"


def main() -> int:
    ap = argparse.ArgumentParser(description="写 publish_note.md 到项目目录（发布时机建议）")
    ap.add_argument("--project-dir", required=True, help="项目目录绝对路径")
    ap.add_argument("--advice-file", default=None,
                    help="advice 文件路径（默认 workspace/evolution/publish_timing_advice.json）")
    args = ap.parse_args()

    advice_path = Path(args.advice_file) if args.advice_file else _default_advice_path()
    advice = None
    if advice_path.exists():
        try:
            advice = json.loads(advice_path.read_text(encoding="utf-8"))
        except Exception:
            advice = None

    note = render_publish_note(advice)
    out = Path(args.project_dir) / "publish_note.md"
    out.write_text(note, encoding="utf-8")
    best = advice.get("best_hour_bucket") if advice else None
    conf = advice.get("confidence") if advice else "low"
    print(f"publish_note 写入: {out} (best={best}, confidence={conf})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
