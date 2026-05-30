#!/usr/bin/env python3
"""CLI: 验证骨架完整性。

检查：
1. 所有必需的结构标记存在（composition-id, __hf, __timelines, gsap.timeline）
2. 创意插槽数量统计
3. --strict 模式下未填充的插槽也报错
"""
import re
import sys
from pathlib import Path


REQUIRED_MARKERS = [
    "data-composition-id",
    "window.__hf",
    "window.__timelines",
    "gsap.timeline",
]


def validate_skeleton_structure(html: str) -> list[str]:
    """验证骨架的基础结构完整性。"""
    issues = []
    for marker in REQUIRED_MARKERS:
        if marker not in html:
            issues.append(f"缺少必要结构: {marker}")
    return issues


def validate_slots(html: str) -> tuple[int, int, list[str]]:
    """验证创意插槽。返回 (total, unfilled, slot_ids)。"""
    slot_pattern = re.compile(r'<!--\s*CREATIVE_SLOT:(\S+)\s*-->')
    filled_pattern = re.compile(r'<!--\s*INJECTED:(\S+)\s*-->')

    all_slots = [m.group(1) for m in slot_pattern.finditer(html)]
    filled = set(m.group(1) for m in filled_pattern.finditer(html))
    unfilled = [s for s in all_slots if s not in filled]
    return len(all_slots), len(unfilled), unfilled


def main():
    import argparse
    parser = argparse.ArgumentParser(description="验证 ClipForge HTML 骨架")
    parser.add_argument("--html", required=True, help="HTML 文件路径")
    parser.add_argument("--strict", action="store_true", help="严格模式：未填充的插槽也报错")
    args = parser.parse_args()

    html = Path(args.html).read_text(encoding="utf-8")

    print("=== Skeleton Structure Validation ===")
    structure_issues = validate_skeleton_structure(html)
    if structure_issues:
        for issue in structure_issues:
            print(f"  [FAIL] {issue}")
    else:
        print("  [OK] Base structure complete (composition-id + __hf + __timelines + gsap.timeline)")

    print("\n=== Creative Slots Validation ===")
    total, unfilled_count, unfilled = validate_slots(html)
    print(f"  Total slots: {total}")
    print(f"  Unfilled: {unfilled_count}")

    if unfilled_count > 0:
        for slot in unfilled[:15]:
            print(f"  - {slot}")
        if unfilled_count > 15:
            print(f"  ... 还有 {unfilled_count - 15} 个")

    if args.strict and unfilled_count > 0:
        print(f"\n[FAIL] Strict mode: {unfilled_count} slots unfilled")
        sys.exit(1)

    if structure_issues:
        print(f"\n[FAIL] Validation failed: {len(structure_issues)} structure issues")
        sys.exit(1)

    if not args.strict or unfilled_count == 0:
        print(f"\n[OK] Validation passed")


if __name__ == "__main__":
    main()
