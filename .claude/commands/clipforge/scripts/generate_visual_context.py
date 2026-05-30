#!/usr/bin/env python3
"""CLI: 生成视觉节奏上下文。

为每个场景的创意插槽提供"不单调、不突兀"的视觉节奏上下文。
包含 emotion curve 位置、前序场景指纹、节奏引导文字。

用法:
  python scripts/generate_visual_context.py --project-dir .
  python scripts/generate_visual_context.py --project-dir . --output visual_context.json
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from engine.visual_context import generate_context_for_slots


def main():
    import argparse
    parser = argparse.ArgumentParser(description="生成视觉节奏上下文")
    parser.add_argument("--project-dir", required=True)
    parser.add_argument("--output", default=None, help="输出 JSON 路径（默认 stdout）")
    args = parser.parse_args()

    project_dir = Path(args.project_dir).resolve()
    contexts = generate_context_for_slots(project_dir)

    import json
    output = json.dumps(contexts, ensure_ascii=False, indent=2)

    if args.output:
        Path(args.output).write_text(output, encoding="utf-8")
        print(f"[OK] Visual context generated: {args.output} ({len(contexts)} scenes)")
    else:
        print(output)


if __name__ == "__main__":
    main()
