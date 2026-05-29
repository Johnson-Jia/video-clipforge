#!/usr/bin/env python3
"""分类配置模板渲染器 — 将通用 stage 模板 + 分类配置 → 领域完整的执行文件。

三种模板指令：
  {{section.field|默认值}}       — 简单替换（单值）
  {{INJECT:section.field}}       — 块注入（多行内容，原样插入）
  {{IF:section.field}}...{{ENDIF}} — 条件块（仅分类有此字段时显示）

用法:
  python engine/render_stage.py --stage stages/stage4-audio.md --category github
  python engine/render_stage.py --stage stages/stage4-audio.md               # 无分类，用默认值
  python engine/render_stage.py --stage stages/stage3-scenes.md --category github --json
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.stdout.reconfigure(encoding="utf-8")

from engine.lib.category_config import load_category_config, resolve_value, get

STAGES_DIR = Path(__file__).parent.parent / "stages"


def render(template: str, config: dict) -> str:
    """三遍扫描渲染模板。"""
    result = template

    # Pass 1: 条件块 {{IF:key}}...{{ENDIF}}
    def replace_conditional(match):
        key = match.group(1)
        body = match.group(2)
        value = get(config, key)
        return body if value is not None else ""

    result = re.sub(
        r"\{\{IF:([\w.]+)\}\}(.*?)\{\{ENDIF\}\}",
        replace_conditional,
        result,
        flags=re.DOTALL,
    )

    # Pass 2: 块注入 {{INJECT:key}}
    def replace_inject(match):
        key = match.group(1)
        value = get(config, key)
        if value is None:
            return ""
        return str(value)

    result = re.sub(r"\{\{INJECT:([\w.]+)\}\}", replace_inject, result)

    # Pass 3: 简单替换 {{section.field|default}} 或 {{section.field}}
    # 引擎变量使用 dotted key 格式（section.field），至少包含一个点号。
    # HTML 模板中的 {{中文占位符}} 不含点号，因此不会被匹配。
    def replace_simple(match):
        key = match.group(1)
        default = match.group(2)  # None if no |default part
        return resolve_value(config, key, default if default is not None else "")

    result = re.sub(r"\{\{([\w]+\.[\w.]+)(?:\|([^}]*))?\}\}", replace_simple, result)

    return result


def validate(rendered: str) -> list[str]:
    """检查渲染结果中是否有未替换的模板变量。"""
    leftovers = re.findall(r"\{\{[\w.]+(?:\|[^}]*)?\}\}", rendered)
    inject_leftovers = re.findall(r"\{\{INJECT:[\w.]+\}\}", rendered)
    if_leftovers = re.findall(r"\{\{IF:[\w.]+\}\}|\{\{ENDIF\}\}", rendered)
    return leftovers + inject_leftovers + if_leftovers


def main():
    parser = argparse.ArgumentParser(description="ClipForge 分类配置模板渲染器")
    parser.add_argument("--stage", required=True, help="Stage 模板文件路径（相对或绝对）")
    parser.add_argument("--category", default=None, help="分类 ID（如 github），不指定则用默认值")
    parser.add_argument("--output", default=None, help="输出文件路径（默认输出到 stdout）")
    parser.add_argument("--json", action="store_true", help="以 JSON 格式输出（含元信息）")
    args = parser.parse_args()

    # 解析 stage 路径
    stage_path = Path(args.stage)
    if not stage_path.is_absolute():
        stage_path = STAGES_DIR / stage_path
    if not stage_path.exists():
        # 也尝试从 clipforge 根目录查找
        alt_path = Path(__file__).parent.parent / args.stage
        if alt_path.exists():
            stage_path = alt_path
        else:
            print(f"错误: stage 文件不存在: {stage_path}", file=sys.stderr)
            sys.exit(1)

    # 读取模板
    template = stage_path.read_text(encoding="utf-8")

    # 加载分类配置
    config = load_category_config(args.category)

    # 渲染
    rendered = render(template, config)

    # 验证
    leftovers = validate(rendered)

    if args.json:
        output = {
            "stage": str(stage_path),
            "category": args.category,
            "config_loaded": bool(config),
            "leftover_variables": leftovers,
            "rendered": rendered,
        }
        print(json.dumps(output, ensure_ascii=False, indent=2))
    else:
        if leftovers:
            print(f"警告: {len(leftovers)} 个未替换变量: {leftovers}", file=sys.stderr)
        if args.output:
            Path(args.output).write_text(rendered, encoding="utf-8")
        else:
            sys.stdout.write(rendered)


if __name__ == "__main__":
    main()
