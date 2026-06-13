"""一次性迁移：traces 的 project_dir 字段绝对→相对 + 目录按相对 slug 聚合。

边界重构后 traces 在 workspace/evolution/traces，但历史 trace 的 project_dir 字段
仍是绝对路径（D:\\...），且目录用旧绝对 slug / basename 索引。本脚本：
1. 收集所有 trace，project_dir 字段转相对（对齐 performance.json）
2. 按 _slug(相对) 聚合（旧绝对 slug / basename / 新相对 slug 目录的同项目 trace 合并）
3. 按 trace id 去重（惰性 copy 可能让同一 trace 在新旧目录各一份）
4. 写入相对 slug 目录，删除旧目录

copy 合并到新目录后删旧目录（traces 数据整理，gitignore 可重生成）。
幂等：字段已相对的 trace 不变。

用法：cd .claude/commands/clipforge && python scripts/migrate_trace_rel.py
"""
from __future__ import annotations
import json
import shutil
import sys
from pathlib import Path
from collections import defaultdict

CLIPFORGE_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(CLIPFORGE_ROOT))
from engine.lib.data_paths import traces_dir
from engine.trace import _to_rel_project_dir, _slug

TRACES = traces_dir()


def main():
    if not TRACES.exists():
        print("traces 目录不存在"); return
    # 1. 收集所有 trace，字段转相对，按 id 去重
    by_id: dict[str, dict] = {}
    total = 0
    for tf in sorted(TRACES.rglob("trace.json")):
        try:
            data = json.loads(tf.read_text("utf-8"))
            traces = data if isinstance(data, list) else [data]
        except Exception:
            continue
        for t in traces:
            if not isinstance(t, dict):
                continue
            t["project_dir"] = _to_rel_project_dir(t.get("project_dir", ""))
            tid = t.get("id", f"no-id-{total}")
            total += 1
            if tid not in by_id:           # 去重（惰性 copy 可能让同 trace 在多目录）
                by_id[tid] = t
    # 2. 按相对 slug 分组
    groups: dict[str, list] = defaultdict(list)
    for t in by_id.values():
        groups[_slug(t["project_dir"])].append(t)
    # 3. 写入相对 slug 目录
    new_slugs = set()
    for slug, traces in groups.items():
        dst = TRACES / slug
        dst.mkdir(parents=True, exist_ok=True)
        (dst / "trace.json").write_text(
            json.dumps(traces, ensure_ascii=False, indent=2), encoding="utf-8")
        new_slugs.add(slug)
    # 4. 删除旧目录（非新相对 slug —— 旧绝对 slug / basename）
    removed = 0
    for d in list(TRACES.iterdir()):
        if d.is_dir() and d.name not in new_slugs:
            shutil.rmtree(d)
            removed += 1
    print(f"迁移完成：读取 {total} 条（去重后 {len(by_id)}）→ {len(groups)} 个相对 slug 目录，删 {removed} 个旧目录")


if __name__ == "__main__":
    main()
