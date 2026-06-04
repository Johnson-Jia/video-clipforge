#!/usr/bin/env python3
"""CLI: 生成 HTML 骨架。

用法:
  python scripts/generate_skeleton.py --project-dir workspace/2026/05/30/my-project
  python scripts/generate_skeleton.py --project-dir . --output index_skeleton.html --slots-json slots.json
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from engine.skeleton_builder import render_skeleton


def main():
    import argparse
    parser = argparse.ArgumentParser(description="生成 ClipForge HTML 骨架")
    parser.add_argument("--project-dir", required=True)
    parser.add_argument("--output", default=None, help="输出 HTML 路径（默认 stdout）")
    parser.add_argument("--slots-json", default=None, help="同时输出插槽清单 JSON")
    args = parser.parse_args()

    project_dir = Path(args.project_dir).resolve()
    output_path = Path(args.output) if args.output else None

    html, skeletons = render_skeleton(project_dir, output_path)

    if output_path:
        print(f"[OK] Skeleton generated: {output_path}")
        print(f"  Scenes: {len(skeletons)}")
        total_slots = sum(len(s.slots) for s in skeletons)
        print(f"  Creative slots: {total_slots}")
    else:
        print(html)

    if args.slots_json:
        import json
        slots_data = []
        for sk in skeletons:
            for slot in sk.slots:
                slots_data.append({
                    "slot_id": slot.slot_id,
                    "scene_id": slot.scene_id,
                    "layer": slot.layer,
                    "slot_type": slot.slot_type,
                    "scene_duration": slot.scene_duration,
                    "emotion_tags": slot.emotion_tags,
                    "emotion_intensity": slot.emotion_intensity,
                    "rhythm_guidance": slot.rhythm_guidance[:120] if slot.rhythm_guidance else "",
                    "narration_text": slot.narration_text[:80] if slot.narration_text else "",
                    "has_multiple_phases": slot.has_multiple_phases,
                    "phase_breakpoints": slot.phase_breakpoints,
                })
        Path(args.slots_json).write_text(
            json.dumps(slots_data, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"[OK] Slots JSON: {args.slots_json} ({len(slots_data)} slots)")


if __name__ == "__main__":
    main()
