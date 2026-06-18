"""一次性迁移：把技能目录的运行数据 copy 到 workspace/evolution/。

边界重整：技能目录只留静态定义（rules/skills/seed patterns），运行数据全在
workspace/evolution/。本脚本跑一次完成迁移（copy 非删，旧目录保留备份；
幂等，.migrated 标记防重复）。

迁移内容：
  clipforge/traces/                    → workspace/evolution/traces/
  clipforge/deltas/（含 disputes.json） → workspace/evolution/deltas/
  clipforge/patterns/ seed:true        → clipforge/patterns/seed/
  clipforge/patterns/ seed:false P-*   → workspace/evolution/patterns/
  clipforge/engine/lib/thresholds.yaml → workspace/evolution/thresholds.yaml
  clipforge/dimension_weights.yaml     → workspace/evolution/dimension_weights.yaml
  clipforge/hit_counts.json            → workspace/evolution/hit_counts.json

用法：cd .claude/commands/clipforge && python scripts/migrate_to_evolution.py
"""
from __future__ import annotations
import json
import shutil
from pathlib import Path

CLIPFORGE_ROOT = Path(__file__).resolve().parent.parent          # .claude/commands/clipforge
import sys; sys.path.insert(0, str(CLIPFORGE_ROOT))
from engine.lib.data_paths import WORKSPACE_ROOT as PROJECT_ROOT, EVOLUTION_ROOT  # 四级回退(env>git>config>cwd)
EVOLUTION = EVOLUTION_ROOT
MARKER = EVOLUTION / ".migrated"


def _copy_tree(src: Path, dst: Path) -> int:
    if not src.exists():
        return 0
    dst.mkdir(parents=True, exist_ok=True)
    n = 0
    for fp in src.iterdir():
        if fp.is_file():
            shutil.copy2(fp, dst / fp.name)
            n += 1
        elif fp.is_dir():
            # 递归 copy 子目录（traces/<slug>/trace.json 等嵌套结构）
            for f in fp.rglob("*"):
                if f.is_file():
                    target = dst / f.relative_to(src)
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(f, target)
                    n += 1
    return n


def _copy_file(src: Path, dst: Path) -> bool:
    if src.exists():
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        return True
    return False


def main():
    import yaml
    if MARKER.exists():
        print(f"已迁移过（{MARKER} 存在），跳过。删除该标记可强制重迁。")
        return
    EVOLUTION.mkdir(parents=True, exist_ok=True)
    report = []

    report.append(f"traces: {_copy_tree(CLIPFORGE_ROOT / 'traces', EVOLUTION / 'traces')} 文件")
    report.append(f"deltas: {_copy_tree(CLIPFORGE_ROOT / 'deltas', EVOLUTION / 'deltas')} 文件（含 disputes.json）")

    # patterns：seed:true → patterns/seed/，seed:false → evolution/patterns/
    seed_dst = CLIPFORGE_ROOT / "patterns" / "seed"
    auto_dst = EVOLUTION / "patterns"
    seed_dst.mkdir(parents=True, exist_ok=True)
    auto_dst.mkdir(parents=True, exist_ok=True)
    n_seed = n_auto = 0
    src_patterns = CLIPFORGE_ROOT / "patterns"
    if src_patterns.exists():
        for fp in src_patterns.glob("*.yaml"):
            try:
                d = yaml.safe_load(fp.read_text("utf-8"))
            except Exception:
                continue
            if d and d.get("seed") is True:
                shutil.copy2(fp, seed_dst / fp.name); n_seed += 1
            else:
                shutil.copy2(fp, auto_dst / fp.name); n_auto += 1
    report.append(f"patterns: {n_seed} seed → patterns/seed/, {n_auto} auto → evolution/patterns/")

    for label, src, dst in [
        ("thresholds", CLIPFORGE_ROOT / "engine" / "lib" / "thresholds.yaml", EVOLUTION / "thresholds.yaml"),
        ("dimension_weights", CLIPFORGE_ROOT / "dimension_weights.yaml", EVOLUTION / "dimension_weights.yaml"),
        ("hit_counts", CLIPFORGE_ROOT / "hit_counts.json", EVOLUTION / "hit_counts.json"),
    ]:
        report.append(f"{label}: {'迁移' if _copy_file(src, dst) else '源不存在跳过'}")

    MARKER.write_text(json.dumps({"migrated": True}), encoding="utf-8")
    print("迁移完成（copy 非删，旧目录保留备份）：")
    for r in report:
        print(f"  {r}")
    print(f"目标：{EVOLUTION}")
    print(f"标记：{MARKER}（删除可重迁）")


if __name__ == "__main__":
    main()
