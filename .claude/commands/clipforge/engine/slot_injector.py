"""创意内容注入器 — 将 LLM 自由创作的 CSS/HTML/GSAP 代码注入骨架的创意插槽。

LLM 输出格式（自由灵活）：
  可以输出完整的创意内容 JSON，也可以直接输出包含标记的代码片段。
  注入器会自动匹配 CREATIVE_SLOT 标记并替换。

设计原则：
  - 注入器不做任何内容过滤或修改，LLM 写什么就注入什么
  - 每个插槽可包含任意数量的元素（多层背景叠加、多个特效组合等）
  - 注入失败（找不到标记）会报错但不损坏骨架其他部分
"""
from __future__ import annotations
import json
import re
import sys
from pathlib import Path


SLOT_PATTERN = re.compile(r'(<!--\s*CREATIVE_SLOT:(\S+)\s*-->)')


def find_slots(html: str) -> dict[str, str]:
    """扫描 HTML 找到所有创意插槽标记，返回 {slot_id: marker}。"""
    slots = {}
    for match in SLOT_PATTERN.finditer(html):
        marker = match.group(1)
        slot_id = match.group(2)
        slots[slot_id] = marker
    return slots


def inject_content(html: str, contents: dict[str, str]) -> tuple[str, list[str]]:
    """将创意内容注入骨架。

    Args:
        html: 骨架 HTML 字符串
        contents: {slot_id: creative_content} 映射

    Returns:
        (注入后的 HTML, 未匹配的 slot_ids)
    """
    slots = find_slots(html)
    unmatched = []

    for slot_id, content in contents.items():
        if slot_id in slots:
            marker = slots[slot_id]
            html = html.replace(
                marker,
                f"<!-- INJECTED:{slot_id} -->\n{content}\n<!-- END_INJECTED:{slot_id} -->",
                1,
            )
        else:
            unmatched.append(slot_id)

    return html, unmatched


def inject_from_creative_file(skeleton_path: Path, creative_path: Path, output_path: Path | None = None) -> str:
    """从 LLM 输出的创意文件注入骨架。

    creative_file 支持两种格式：
    1. JSON 格式: [{"slot_id": "s1-bg-html", "content": "<div>..."}]
    2. 标记格式: 代码中直接包含 <!-- CREATIVE_SLOT:s1-bg-html --> 标记
    """
    skeleton_html = skeleton_path.read_text(encoding="utf-8")
    creative_raw = creative_path.read_text(encoding="utf-8")

    # 尝试 JSON 格式
    try:
        creative_data = json.loads(creative_raw)
        if isinstance(creative_data, list):
            contents = {item["slot_id"]: item["content"] for item in creative_data if "slot_id" in item and "content" in item}
        elif isinstance(creative_data, dict):
            contents = {k: v for k, v in creative_data.items() if isinstance(v, str)}
        else:
            raise ValueError("unexpected format")
    except (json.JSONDecodeError, ValueError, KeyError):
        # 非JSON：直接用标记替换
        contents = _parse_marked_content(creative_raw)

    result_html, unmatched = inject_content(skeleton_html, contents)

    if unmatched:
        print(f"WARNING: {len(unmatched)} 个插槽未匹配: {', '.join(unmatched[:5])}", file=sys.stderr)

    if output_path:
        output_path.write_text(result_html, encoding="utf-8")
        print(f"注入完成: {output_path} ({len(contents)} 个插槽已注入)")

    return result_html


def _parse_marked_content(raw: str) -> dict[str, str]:
    """解析包含 CREATIVE_SLOT 标记的自由格式内容。

    格式示例：
      <!-- CREATIVE_SLOT:s1-bg-html -->
      <div class="nebula">...</div>
      <!-- END_SLOT:s1-bg-html -->
    """
    contents = {}
    pattern = re.compile(
        r'<!--\s*CREATIVE_SLOT:(\S+)\s*-->\s*\n(.*?)(?=<!--\s*(?:END_SLOT|CREATIVE_SLOT):)',
        re.DOTALL,
    )
    for match in pattern.finditer(raw):
        slot_id = match.group(1)
        content = match.group(2).strip()
        contents[slot_id] = content

    return contents


def validate_injection(html: str) -> tuple[bool, list[str]]:
    """验证所有 CREATIVE_SLOT 标记都已被注入。

    Returns:
        (all_injected, remaining_empty_slots)
    """
    remaining = SLOT_PATTERN.findall(html)
    empty_slots = [match[1] for match in remaining if match[1]]
    return len(empty_slots) == 0, empty_slots


def main():
    import argparse
    parser = argparse.ArgumentParser(description="ClipForge 创意内容注入器")
    parser.add_argument("--skeleton", required=True, help="骨架 HTML 路径")
    parser.add_argument("--creative", required=True, help="创意内容文件路径")
    parser.add_argument("--output", default=None, help="输出路径（默认覆盖骨架）")
    parser.add_argument("--validate", action="store_true", help="仅验证注入完整性")
    args = parser.parse_args()

    skeleton_path = Path(args.skeleton)
    creative_path = Path(args.creative)
    output_path = Path(args.output) if args.output else skeleton_path

    if args.validate:
        html = skeleton_path.read_text(encoding="utf-8")
        all_done, remaining = validate_injection(html)
        if all_done:
            print(f"✓ 所有创意插槽已注入")
        else:
            print(f"✗ {len(remaining)} 个插槽未注入: {', '.join(remaining)}")
        sys.exit(0 if all_done else 1)

    inject_from_creative_file(skeleton_path, creative_path, output_path)


if __name__ == "__main__":
    main()
