#!/usr/bin/env python3
"""CLI: 注入创意内容到骨架。

用法:
  python scripts/inject_creative.py --skeleton index_skeleton.html --creative creative.json
  python scripts/inject_creative.py --skeleton index_skeleton.html --creative creative.json --output index.html
  python scripts/inject_creative.py --skeleton index.html --validate
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from engine.slot_injector import inject_from_creative_file, validate_injection


def main():
    import argparse
    parser = argparse.ArgumentParser(description="注入创意内容到 ClipForge HTML 骨架")
    parser.add_argument("--skeleton", required=True, help="骨架 HTML 文件路径")
    parser.add_argument("--creative", default=None, help="创意内容文件路径")
    parser.add_argument("--output", default=None, help="输出路径（默认覆盖骨架文件）")
    parser.add_argument("--validate", action="store_true", help="仅验证注入完整性")
    args = parser.parse_args()

    skeleton_path = Path(args.skeleton).resolve()

    if args.validate:
        html = skeleton_path.read_text(encoding="utf-8")
        all_done, remaining = validate_injection(html)
        if all_done:
            print("[OK] All creative slots injected")
        else:
            print(f"[FAIL] {len(remaining)} slots not injected:")
            for slot in remaining:
                print(f"  - {slot}")
        sys.exit(0 if all_done else 1)

    if not args.creative:
        print("ERROR: 需要 --creative 或 --validate", file=sys.stderr)
        sys.exit(1)

    creative_path = Path(args.creative).resolve()
    output_path = Path(args.output) if args.output else skeleton_path

    inject_from_creative_file(skeleton_path, creative_path, output_path)
    print(f"[OK] Creative content injected: {output_path}")


if __name__ == "__main__":
    main()
