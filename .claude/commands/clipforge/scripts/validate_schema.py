#!/usr/bin/env python3
"""ClipForge schema.yaml 校验脚本。

校验内容：
1. artifact ID 唯一性
2. requires / requires_any / requires_optional 中引用的 ID 全部存在
3. condition 字段仅出现在有 requires 的 artifact 上
4. generates 和 template 字段非空
5. DFS 检测循环依赖（仅对 requires 和 requires_any 建硬依赖图）

用法：
    python .claude/commands/clipforge/scripts/validate_schema.py [schema.yaml 路径]
    # 默认路径: .claude/commands/clipforge/schema.yaml
"""

import sys
import os
from pathlib import Path

try:
    import yaml
except ImportError:
    print("错误: 需要安装 PyYAML — pip install pyyaml")
    sys.exit(1)


def load_schema(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        print(f"错误: schema 文件格式不正确（期望 dict，得到 {type(data).__name__}）")
        sys.exit(1)
    return data


def validate_schema(schema: dict) -> list[str]:
    errors: list[str] = []
    artifacts_raw = schema.get("artifacts", [])

    if not artifacts_raw:
        errors.append("错误: artifacts 为空")
        return errors

    # 兼容两种 YAML 格式：
    # 格式 A（当前）: artifacts 是 dict，key = ID，value = 属性 dict
    # 格式 B（备选）: artifacts 是 list of dict，每个元素有 id 字段
    artifact_map: dict[str, dict] = {}

    if isinstance(artifacts_raw, dict):
        for art_id, art_def in artifacts_raw.items():
            if not isinstance(art_def, dict):
                errors.append(f"错误: artifact '{art_id}' 的值不是 dict（得到 {type(art_def).__name__}）")
                continue
            artifact_map[art_id] = art_def
    elif isinstance(artifacts_raw, list):
        for i, art in enumerate(artifacts_raw):
            if not isinstance(art, dict):
                errors.append(f"错误: artifacts[{i}] 不是 dict（得到 {type(art).__name__}）")
                continue
            art_id = art.get("id", "")
            if not art_id:
                errors.append(f"错误: artifacts[{i}] 缺少 id 字段")
                continue
            if art_id in artifact_map:
                errors.append(f"错误: artifact ID 重复: '{art_id}'")
            artifact_map[art_id] = art
    else:
        errors.append(f"错误: artifacts 类型不正确（期望 dict 或 list，得到 {type(artifacts_raw).__name__}）")
        return errors

    ids = set(artifact_map.keys())

    # 逐 artifact 校验
    for art_id, art in artifact_map.items():
        # generates 非空
        generates = art.get("generates")
        if not generates:
            errors.append(f"错误: '{art_id}' 缺少 generates 字段")
        elif isinstance(generates, str) and not generates.strip():
            errors.append(f"错误: '{art_id}' 的 generates 为空字符串")
        elif isinstance(generates, list):
            for j, g in enumerate(generates):
                if not g or not str(g).strip():
                    errors.append(f"错误: '{art_id}' 的 generates[{j}] 为空")

        # template 非空
        template = art.get("template", "")
        if not template or not str(template).strip():
            errors.append(f"错误: '{art_id}' 缺少 template 字段")

        # 引用完整性
        for field in ("requires", "requires_any", "requires_optional"):
            refs = art.get(field, [])
            if not isinstance(refs, list):
                continue
            for ref in refs:
                if ref not in ids:
                    errors.append(
                        f"错误: '{art_id}' 的 {field} 引用了不存在的 artifact '{ref}'"
                    )

        # condition 字段合理性
        condition = art.get("condition")
        if condition and not art.get("requires"):
            errors.append(
                f"警告: '{art_id}' 有 condition 但无 requires，条件依赖可能无意义"
            )

    # 循环依赖检测（DFS）
    cycle = _detect_cycle(artifact_map)
    if cycle:
        errors.append(f"错误: 检测到循环依赖: {' → '.join(cycle)}")

    return errors


def _detect_cycle(artifact_map: dict[str, dict]) -> list[str] | None:
    """用 DFS 检测硬依赖图中的循环。"""
    visited: set[str] = set()
    in_stack: set[str] = set()
    parent: dict[str, str] = {}

    def dfs(node: str) -> list[str] | None:
        visited.add(node)
        in_stack.add(node)

        art = artifact_map.get(node, {})
        # 只对硬依赖建图
        deps = art.get("requires", []) + art.get("requires_any", [])

        for dep in deps:
            if dep not in artifact_map:
                continue  # 引用不存在的 ID 已在上层报错
            if dep not in visited:
                parent[dep] = node
                result = dfs(dep)
                if result:
                    return result
            elif dep in in_stack:
                # 找到循环 — 重建路径
                path = [dep]
                current = node
                while current != dep:
                    path.append(current)
                    current = parent.get(current, dep)
                path.append(dep)
                path.reverse()
                return path

        in_stack.discard(node)
        return None

    for art_id in sorted(artifact_map.keys()):
        if art_id not in visited:
            result = dfs(art_id)
            if result:
                return result

    return None


def main():
    # 默认路径: 脚本所在目录的上一级（clipforge/）下的 schema.yaml
    script_dir = os.path.dirname(os.path.abspath(__file__))
    default_path = os.path.join(os.path.dirname(script_dir), "schema.yaml")
    schema_path = sys.argv[1] if len(sys.argv) > 1 else default_path

    if not os.path.exists(schema_path):
        print(f"错误: 文件不存在: {schema_path}")
        sys.exit(1)

    print(f"校验 schema: {schema_path}")
    schema = load_schema(schema_path)
    errors = validate_schema(schema)

    if errors:
        print(f"\n发现 {len(errors)} 个问题:")
        for err in errors:
            print(f"  {err}")
        sys.exit(1)
    else:
        print("校验通过: 所有 artifact 定义正确，无循环依赖。")


if __name__ == "__main__":
    main()
