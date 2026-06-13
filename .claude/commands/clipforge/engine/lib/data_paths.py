"""数据路径统一收口：技能静态定义层 + workspace/evolution 演化层。

边界原则：技能目录（CLIPFORGE_ROOT）只含静态定义（rules/skills/stages/scripts/
engine/components/seed patterns），运行产生的数据全部在 workspace/evolution/。

本模块只做**纯路径解析**（无迁移副作用）。迁移由 scripts/migrate_to_evolution.py
一次性完成。每次调用不触发 copy，保持 data_paths 干净。

加载约定：
- traces/deltas/auto-patterns/thresholds/dimension_weights/hit_counts → workspace/evolution/
  （缺失则调用方代码默认兜底）
- seed patterns → 技能目录 patterns/seed/（静态人工经验）
- 合并读 pattern：all_pattern_files() = seed（技能）+ auto（workspace）
"""
from __future__ import annotations
from pathlib import Path

CLIPFORGE_ROOT = Path(__file__).resolve().parent.parent.parent   # .claude/commands/clipforge
PROJECT_ROOT = CLIPFORGE_ROOT.parent.parent.parent               # video-clipforge
EVOLUTION_ROOT = PROJECT_ROOT / "workspace" / "evolution"
SEED_PATTERNS_DIR = CLIPFORGE_ROOT / "patterns" / "seed"


def traces_dir() -> Path:
    """执行历史目录（gate record_trace 写 / query_traces 读）。"""
    return EVOLUTION_ROOT / "traces"


def deltas_dir() -> Path:
    """规则演化增量目录（auto_evolve/attribution/governance 写 / inject 读）。"""
    return EVOLUTION_ROOT / "deltas"


def auto_patterns_dir() -> Path:
    """auto_evolve 提炼的 P-* pattern（seed:false，运行产生）。"""
    return EVOLUTION_ROOT / "patterns"


def seed_patterns_dir() -> Path:
    """人工 seed pattern（静态定义，入库复用）。"""
    return SEED_PATTERNS_DIR


def all_pattern_files() -> list[Path]:
    """合并 seed（技能）+ auto（workspace）的 pattern 文件，按文件名去重。"""
    files: list[Path] = []
    if SEED_PATTERNS_DIR.exists():
        files += list(SEED_PATTERNS_DIR.glob("*.yaml"))
    ap = auto_patterns_dir()
    if ap.exists():
        files += list(ap.glob("*.yaml"))
    seen, out = set(), []
    for f in files:
        if f.name not in seen:
            seen.add(f.name)
            out.append(f)
    return sorted(out)


def pattern_file(pid: str) -> Path:
    """定位某 pattern 文件：auto 优先，seed 兜底；不存在时返回 auto 路径（写默认 auto）。"""
    ap = auto_patterns_dir()
    for d in (ap, SEED_PATTERNS_DIR):
        fp = d / f"{pid}.yaml"
        if fp.exists():
            return fp
    return ap / f"{pid}.yaml"


def hit_counts_file() -> Path:
    """规则命中计数（trace record 写 / observability 读）。"""
    return EVOLUTION_ROOT / "hit_counts.json"


def disputes_file() -> Path:
    """delta 争议记录（dispute_tracker 写读，deltas 子文件）。"""
    return EVOLUTION_ROOT / "deltas" / "disputes.json"


def thresholds_file() -> Path:
    """平台成功阈值（phase5 校准写 / success_analyzer 读）。"""
    return EVOLUTION_ROOT / "thresholds.yaml"


def dimension_weights_file() -> Path:
    """维度权重（dashboard 调 / inject 读 effective_rank）。"""
    return EVOLUTION_ROOT / "dimension_weights.yaml"
