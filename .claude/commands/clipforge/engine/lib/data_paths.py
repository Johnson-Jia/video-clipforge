"""数据路径统一收口：技能静态定义层 + workspace/evolution 演化层。

路径定位（四级回退，支持技能 install 到用户级 ~/.claude/）：
  1. CLIPFORGE_WORKSPACE 环境变量（临时覆盖，测试/CI）
  2. ~/.claude/clipforge-config.json 的 workspace_default（用户显式指定，优先于 git）
  3. git rev-parse --show-toplevel（项目内自动，cd 即切换工作目录）
  4. cwd

技能目录 CLIPFORGE_ROOT 由 __file__ 自定位（用户级/项目级自适应），与工作目录解耦。
"""
from __future__ import annotations
import json
import os
import subprocess
from datetime import datetime
from pathlib import Path

CLIPFORGE_ROOT = Path(__file__).resolve().parents[2]              # 技能目录（~/.claude 或 项目 .claude 下的 commands/clipforge）
USER_CONFIG = Path.home() / ".claude" / "clipforge-config.json"


def _git_toplevel() -> str | None:
    """git rev-parse --show-toplevel，失败/非 git 返回 None。"""
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "--show-toplevel"],
            stderr=subprocess.DEVNULL,
        ).strip().decode()
        return out or None
    except Exception:
        return None


def resolve_workspace_root() -> Path:
    """定位工作目录根（workspace 落在 <根>/workspace）。

    回退顺序：env > config(用户显式) > git(当前项目) > cwd。
    config 优先于 git——用户用 clipforge-switch-workspace 显式指定的工作目录根，
    优先于自动推断的当前项目根。git 仅在用户未设置时作为默认（当前项目下创建 workspace）。
    各分支均防御 basename=="workspace"（误传 workspace 本身时向上找父，避免 workspace/workspace 嵌套）。
    """
    # 1. 环境变量（临时覆盖，最高优先）
    env = os.environ.get("CLIPFORGE_WORKSPACE")
    if env and Path(env).exists():
        p = Path(env).resolve()
        return p.parent if p.name == "workspace" else p
    # 2. 用户配置（clipforge-switch-workspace 显式设置，优先于 git）
    cfg = get_config()
    ws = cfg.get("workspace_default")
    if ws and Path(ws).exists():
        p = Path(ws).resolve()
        return p.parent if p.name == "workspace" else p
    # 3. git 项目根（用户未设置时的默认：当前项目下创建 workspace）
    root = _git_toplevel()
    if root:
        root = Path(root)
        if root.name == "workspace":
            root = root.parent
        return root
    # 4. cwd（兜底）
    cwd = Path.cwd().resolve()
    return cwd.parent if cwd.name == "workspace" else cwd


def get_config() -> dict:
    """读 ~/.claude/clipforge-config.json，不存在/损坏返回 {}。"""
    if USER_CONFIG.exists():
        try:
            return json.loads(USER_CONFIG.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def set_workspace_default(path: str) -> Path:
    """切换工作目录默认（写 USER_CONFIG），返回解析后的路径。"""
    resolved = Path(path).resolve()
    cfg = get_config()
    cfg["workspace_default"] = str(resolved)
    cfg["configured_at"] = datetime.now().isoformat()
    USER_CONFIG.parent.mkdir(parents=True, exist_ok=True)
    USER_CONFIG.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
    return resolved


# === 解析后的路径常量（脚本 import 用）===
WORKSPACE_ROOT = resolve_workspace_root()
PROJECT_ROOT = WORKSPACE_ROOT                                            # 别名，脚本兼容
EVOLUTION_ROOT = WORKSPACE_ROOT / "workspace" / "evolution"
SEED_PATTERNS_DIR = CLIPFORGE_ROOT / "patterns" / "seed"
VIDEO_DATA_DIR = WORKSPACE_ROOT / "workspace" / "sources" / "视频数据"
BILI_COOKIE = VIDEO_DATA_DIR / ".bili-cookie"


# === evolution 层路径函数（原样保留）===
def traces_dir() -> Path:
    return EVOLUTION_ROOT / "traces"

def deltas_dir() -> Path:
    return EVOLUTION_ROOT / "deltas"

def auto_patterns_dir() -> Path:
    return EVOLUTION_ROOT / "patterns"

def seed_patterns_dir() -> Path:
    return SEED_PATTERNS_DIR

def all_pattern_files() -> list[Path]:
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
    ap = auto_patterns_dir()
    for d in (ap, SEED_PATTERNS_DIR):
        fp = d / f"{pid}.yaml"
        if fp.exists():
            return fp
    return ap / f"{pid}.yaml"

def hit_counts_file() -> Path:
    return EVOLUTION_ROOT / "hit_counts.json"

def disputes_file() -> Path:
    return EVOLUTION_ROOT / "deltas" / "disputes.json"

def thresholds_file() -> Path:
    return EVOLUTION_ROOT / "thresholds.yaml"

def dimension_weights_file() -> Path:
    return EVOLUTION_ROOT / "dimension_weights.yaml"
