# ClipForge 技能解耦改造 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让 ClipForge 技能可 install 到用户级 `~/.claude/`，工作目录保持项目级（视频输出/evolution/播放数据落用户当前项目），首次可配置，cd 即切换。

**Architecture:** `engine/lib/data_paths.py` 作为唯一路径收口点，PROJECT_ROOT 改四级回退（`CLIPFORGE_WORKSPACE` env → `git rev-parse` → `~/.claude/clipforge-config.json` → cwd）；6 脚本弃 `parents[3]` 统一 import；5 命令文档加技能目录探测前缀；stage0-env 引导首次配置；新增 `/clipforge-switch-workspace`。向后兼容（项目级用户 git rev-parse 返回同路径）。

**Tech Stack:** Python 3.12 / pathlib / subprocess(git) / bash / Claude Code slash command

**Spec:** `docs/superpowers/specs/2026-06-18-clipforge-decouple-design.md`

**注：** 计划含 commit 步骤模板，但实际 commit 遵循 memory `feedback-no-commit-without-ask`——需用户明确授权才 commit。

---

## File Structure

| 文件 | 责任 | 动作 |
|------|------|------|
| `engine/lib/data_paths.py` | 唯一路径收口：四级回退 + workspace 全路径 + 配置读写 | 改造（核心） |
| `scripts/auto_evolve.py` | 自进化主流程 | 改 PROJECT_ROOT 来源 |
| `scripts/collect_performance.py` | 播放数据采集 | 改 PROJECT_ROOT 来源 |
| `scripts/fetch_bilibili.py` | B站 数据拉取 | 改 DATA_DIR 来源 |
| `scripts/backfill_cover.py` | 封面回填 | 改 PROJECT_ROOT 来源 |
| `scripts/backfill_injected.py` | 注入回填 | 改 PROJECT_ROOT 来源 |
| `scripts/bgm_history.py` | BGM 历史 | 改 CLIPFORGE_DIR 来源 |
| `engine/lib/test_data_paths.py` | data_paths 单元测试 | 新建 |
| `.claude/commands/clipforge-feedback.md` | 自进化命令 | 加技能目录探测前缀 |
| `.claude/commands/evolve-daily.md` | 每日自进化 | 加前缀 |
| `.claude/commands/github-daily-trending.md` | 每日 trending | 加前缀 |
| `.claude/commands/github-weekly-trending.md` | 每周 trending | 加前缀 |
| `.claude/commands/clipforge-category-setup.md` | 分类 setup | 加前缀 |
| `.claude/commands/clipforge-switch-workspace.md` | 切换工作目录命令 | 新建 |
| `.claude/commands/clipforge/stages/stage0-env.md` | 环境检测 | 加首次配置引导 |
| `shared/clipforge-env.sh` | 技能目录探测 helper（DRY，命令 source） | 新建 |

---

## Task 1: data_paths.py 四级回退核心改造

**Files:**
- Modify: `.claude/commands/clipforge/engine/lib/data_paths.py`
- Create: `.claude/commands/clipforge/engine/lib/test_data_paths.py`

- [ ] **Step 1: 写失败测试（四级回退各路径）**

Create `engine/lib/test_data_paths.py`:

```python
"""data_paths 四级回退 + 配置读写单测。用 monkeypatch 不污染真实环境。"""
import json
import os
import sys
from pathlib import Path
from unittest import mock

# 让 test 能 import engine.lib.data_paths（脚本目录在 engine/lib/）
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # engine/
# 但 data_paths 用 __file__ 定位，需从 engine.lib import
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # clipforge/

import engine.lib.data_paths as dp
import importlib


def _reload_with(monkeypatch_env=None, mock_git_root=None, mock_config=None, monkeypatch_cwd=None):
    """用指定环境重载 data_paths，返回重载后的 WORKSPACE_ROOT。"""
    importlib.reload(dp)
    # 注意：reload 后模块级 WORKSPACE_ROOT 已算完，需重新触发 resolve
    with mock.patch.dict(os.environ, monkeypatch_env or {}):
        with mock.patch.object(dp, '_git_toplevel', return_value=mock_git_root):
            with mock.patch.object(dp, 'USER_CONFIG', mock_config if mock_config is not None else dp.USER_CONFIG):
                with mock.patch.object(dp.Path, 'cwd', staticmethod(lambda: Path(monkeypatch_cwd) if monkeypatch_cwd else Path.cwd())):
                    return dp.resolve_workspace_root()


def test_env_var_wins(tmp_path):
    """1 级：CLIPFORGE_WORKSPACE 环境变量优先。"""
    env_dir = tmp_path / "env_ws"
    env_dir.mkdir()
    root = _reload_with(monkeypatch_env={"CLIPFORGE_WORKSPACE": str(env_dir)},
                        mock_git_root="/some/git", mock_config=None)
    assert root == env_dir.resolve()


def test_git_toplevel_second(tmp_path):
    """2 级：无 env 时 git rev-parse。"""
    git_dir = tmp_path / "git_proj"
    git_dir.mkdir()
    root = _reload_with(monkeypatch_env={}, mock_git_root=str(git_dir), mock_config=None)
    assert root == git_dir.resolve()


def test_config_default_third(tmp_path):
    """3 级：无 env 无 git 时用 USER_CONFIG workspace_default。"""
    cfg_dir = tmp_path / "cfg_proj"
    cfg_dir.mkdir()
    cfg_file = tmp_path / "clipforge-config.json"
    cfg_file.write_text(json.dumps({"workspace_default": str(cfg_dir)}), encoding="utf-8")
    root = _reload_with(monkeypatch_env={}, mock_git_root=None, mock_config=cfg_file)
    assert root == cfg_dir.resolve()


def test_cwd_fallback(tmp_path):
    """4 级：全无时 cwd 兜底。"""
    root = _reload_with(monkeypatch_env={}, mock_git_root=None, mock_config=None,
                        monkeypatch_cwd=str(tmp_path))
    assert root == tmp_path.resolve()


def test_get_set_config(tmp_path):
    """配置读写：set_workspace_default 写 USER_CONFIG。"""
    cfg = tmp_path / "clipforge-config.json"
    with mock.patch.object(dp, 'USER_CONFIG', cfg):
        dp.set_workspace_default(str(tmp_path / "proj"))
        data = json.loads(cfg.read_text(encoding="utf-8"))
        assert data["workspace_default"].endswith("proj")
        assert "configured_at" in data
```

- [ ] **Step 2: 运行测试确认失败**

```bash
cd /d/AI-Agent/video-clipforge/.claude/commands/clipforge
python -m pytest engine/lib/test_data_paths.py -v
```
Expected: FAIL（`resolve_workspace_root` / `set_workspace_default` / `_git_toplevel` 未定义，import 可能报错）

- [ ] **Step 3: 改造 data_paths.py（四级回退 + 配置 + 收口扩展）**

Replace `engine/lib/data_paths.py` 全文为：

```python
"""数据路径统一收口：技能静态定义层 + workspace/evolution 演化层。

路径定位（四级回退，支持技能 install 到用户级 ~/.claude/）：
  1. CLIPFORGE_WORKSPACE 环境变量（临时覆盖，测试/CI）
  2. git rev-parse --show-toplevel（项目内自动，cd 即切换工作目录）
  3. ~/.claude/clipforge-config.json 的 workspace_default（非 git 兜底）
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
    """四级回退定位工作目录（workspace 落这里）。"""
    # 1. 环境变量（临时覆盖）
    env = os.environ.get("CLIPFORGE_WORKSPACE")
    if env and Path(env).exists():
        return Path(env).resolve()
    # 2. git rev-parse（项目内自动）
    root = _git_toplevel()
    if root:
        return Path(root)
    # 3. 用户配置默认（非 git 兜底）
    cfg = get_config()
    ws = cfg.get("workspace_default")
    if ws and Path(ws).exists():
        return Path(ws).resolve()
    # 4. cwd
    return Path.cwd().resolve()


def get_config() -> dict:
    """读 ~/.claude/clipforge-config.json，不存在返回 {}。"""
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
```

- [ ] **Step 4: 运行测试确认通过**

```bash
cd /d/AI-Agent/video-clipforge/.claude/commands/clipforge
python -m pytest engine/lib/test_data_paths.py -v
```
Expected: 5 passed

- [ ] **Step 5: 手动冒烟（当前项目根 = git root，行为应不变）**

```bash
cd /d/AI-Agent/video-clipforge/.claude/commands/clipforge
python -c "from engine.lib.data_paths import WORKSPACE_ROOT, VIDEO_DATA_DIR; print(WORKSPACE_ROOT); print(VIDEO_DATA_DIR)"
```
Expected: `WORKSPACE_ROOT = D:/AI-Agent/video-clipforge`（git root），`VIDEO_DATA_DIR = .../workspace/sources/视频数据`（与改造前一致）

- [ ] **Step 6: Commit（需用户授权）**

```bash
git add .claude/commands/clipforge/engine/lib/data_paths.py .claude/commands/clipforge/engine/lib/test_data_paths.py
# 等用户授权后：git commit -m "refactor(clipforge): data_paths 四级回退，解耦技能目录与工作目录"
```

---

## Task 2: 6 脚本弃 parents[3]，统一 import data_paths

**Files:**
- Modify: `scripts/auto_evolve.py`、`scripts/collect_performance.py`、`scripts/fetch_bilibili.py`、`scripts/backfill_cover.py`、`scripts/backfill_injected.py`、`scripts/bgm_history.py`

每个脚本删掉自算 PROJECT_ROOT/CLIPFORGE_ROOT 的行，改 import data_paths。data_paths 单测（Task 1）已覆盖路径逻辑，本任务只验证脚本 import 后常量正确。

- [ ] **Step 1: auto_evolve.py**

定位（约 line 30-32）：
```python
CLIPFORGE_ROOT = Path(__file__).parent.parent          # .claude/commands/clipforge/
PROJECT_ROOT = CLIPFORGE_ROOT.parent.parent.parent      # video-clipforge/
WORKSPACE = PROJECT_ROOT / "workspace"
```
替换为：
```python
from engine.lib.data_paths import WORKSPACE_ROOT as PROJECT_ROOT, CLIPFORGE_ROOT
WORKSPACE = PROJECT_ROOT / "workspace"
```
（若脚本其他处用到 CLIPFORGE_ROOT，保留 import；grep 确认：`grep -n CLIPFORGE_ROOT scripts/auto_evolve.py`）

- [ ] **Step 2: collect_performance.py**

定位（约 line 28-31）：
```python
SCRIPT_DIR = Path(__file__).resolve().parent
CLIPFORGE_DIR = SCRIPT_DIR.parent
PROJECT_ROOT = CLIPFORGE_DIR.parent.parent.parent
WORKSPACE_ROOT = PROJECT_ROOT / "workspace"
```
替换为：
```python
from engine.lib.data_paths import WORKSPACE_ROOT as PROJECT_ROOT, CLIPFORGE_ROOT as CLIPFORGE_DIR
WORKSPACE_ROOT = PROJECT_ROOT / "workspace"
```
保留 `--workspace-root`/`--data-root` argparse 默认值改为引用 data_paths（line 1115-1116）：
```python
from engine.lib.data_paths import WORKSPACE_ROOT as _WS, VIDEO_DATA_DIR as _VD
parser.add_argument("--workspace-root", default=str(_WS), ...)
parser.add_argument("--data-root", default=str(_VD / "sources" / "视频数据"), ...)
```
注：原 default 用 WORKSPACE_ROOT 局部变量，改 import 别名后保持同名即可，argparse 行可不改（只要局部 WORKSPACE_ROOT 仍指向 data_paths）。

- [ ] **Step 3: fetch_bilibili.py**

定位（约 line 29-33）：
```python
SCRIPT_DIR = Path(__file__).resolve().parent
TESTDATA = SCRIPT_DIR / "testdata"
...
WORKSPACE_ROOT = SCRIPT_DIR.parents[3]
DATA_DIR = WORKSPACE_ROOT / "workspace" / "sources" / "视频数据"
```
替换 WORKSPACE_ROOT/DATA_DIR 两行为：
```python
from engine.lib.data_paths import VIDEO_DATA_DIR as DATA_DIR
```
保留 `SCRIPT_DIR` / `TESTDATA`（fetch 用 testdata，SCRIPT_DIR 仍需）。

- [ ] **Step 4: backfill_cover.py + backfill_injected.py**

各定位 `PROJECT_ROOT = CLIPFORGE_ROOT.parent.parent.parent`（backfill_cover 约 line 17-19，backfill_injected 约 line 20-23），替换为：
```python
from engine.lib.data_paths import WORKSPACE_ROOT as PROJECT_ROOT, CLIPFORGE_ROOT, SCRIPTS_DIR
WORKSPACE = PROJECT_ROOT / "workspace"
```
（backfill_injected 原 `SCRIPTS_DIR = Path(__file__).parent` 保留或用 data_paths；grep 确认用法）

- [ ] **Step 5: bgm_history.py**

定位（约 line 20-21）：
```python
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CLIPFORGE_DIR = os.path.join(SCRIPT_DIR, "..")
```
CLIPFORGE_DIR 改为 data_paths：
```python
from engine.lib.data_paths import CLIPFORGE_ROOT
CLIPFORGE_DIR = str(CLIPFORGE_ROOT)
```
（bgm_history 用 CLIPFORGE_DIR 定位历史文件，grep 确认 history 路径在 evolution 层，应用 data_paths.EVOLUTION_ROOT）

- [ ] **Step 6: 冒烟验证（6 脚本 import 不报错 + WORKSPACE_ROOT 正确）**

```bash
cd /d/AI-Agent/video-clipforge/.claude/commands/clipforge
for s in auto_evolve collect_performance fetch_bilibili backfill_cover backfill_injected bgm_history; do
  echo "=== $s ==="
  python -c "import importlib.util, sys; spec=importlib.util.spec_from_file_location('m','scripts/$s.py'); m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)" 2>&1 | tail -3
done
# 关键：fetch_bilibili 的 DATA_DIR 应指向项目 workspace
python -c "import sys; sys.path.insert(0,'.'); import scripts.fetch_bilibili as f; print('DATA_DIR=', f.DATA_DIR)"
```
Expected: 无 ImportError；DATA_DIR = `D:/AI-Agent/video-clipforge/workspace/sources/视频数据`

- [ ] **Step 7: Commit（需用户授权）**

```bash
git add .claude/commands/clipforge/scripts/auto_evolve.py .claude/commands/clipforge/scripts/collect_performance.py .claude/commands/clipforge/scripts/fetch_bilibili.py .claude/commands/clipforge/scripts/backfill_cover.py .claude/commands/clipforge/scripts/backfill_injected.py .claude/commands/clipforge/scripts/bgm_history.py
# 等用户授权后：git commit -m "refactor(clipforge): 6 脚本统一 import data_paths，弃 parents[3]"
```

---

## Task 3: 命令文档技能目录探测前缀（+ helper）

**Files:**
- Create: `.claude/commands/clipforge/shared/clipforge-env.sh`
- Modify: `.claude/commands/clipforge-feedback.md`、`evolve-daily.md`、`github-daily-trending.md`、`github-weekly-trending.md`、`clipforge-category-setup.md`

- [ ] **Step 1: 写 helper（DRY，命令 source 它定位技能目录）**

Create `.claude/commands/clipforge/shared/clipforge-env.sh`:

```bash
#!/usr/bin/env bash
# clipforge-env.sh — 定位技能目录 + 工作目录（命令 source 用）
# 技能目录 CF_DIR：用户级 ~/.claude 优先，项目级 .claude 兜底
CF_DIR=""
if [ -d "$HOME/.claude/commands/clipforge" ]; then
  CF_DIR="$HOME/.claude/commands/clipforge"
elif [ -n "${GIT_ROOT:-}" ] && [ -d "$GIT_ROOT/.claude/commands/clipforge" ]; then
  CF_DIR="$GIT_ROOT/.claude/commands/clipforge"
else
  GIT_ROOT=$(git rev-parse --show-toplevel 2>/dev/null)
  if [ -n "$GIT_ROOT" ] && [ -d "$GIT_ROOT/.claude/commands/clipforge" ]; then
    CF_DIR="$GIT_ROOT/.claude/commands/clipforge"
  fi
fi
[ -z "$CF_DIR" ] && { echo "FATAL: 找不到 clipforge 技能目录（~/.claude 或项目 .claude）" >&2; exit 1; }
export CF_DIR
```

- [ ] **Step 2: 测试 helper（用户级软链模拟）**

```bash
# 模拟用户级 install：软链（不实际复制）
ln -sf /d/AI-Agent/video-clipforge/.claude/commands/clipforge "$HOME/.claude/commands/clipforge" 2>/dev/null || mkdir -p "$HOME/.claude/commands" && ln -sf /d/AI-Agent/video-clipforge/.claude/commands/clipforge "$HOME/.claude/commands/clipforge"
source /d/AI-Agent/video-clipforge/.claude/commands/clipforge/shared/clipforge-env.sh
echo "CF_DIR=$CF_DIR"
```
Expected: `CF_DIR=/home/.../.claude/commands/clipforge`（用户级优先，软链）或项目级。验证 `$CF_DIR/scripts/auto_evolve.py` 存在。

- [ ] **Step 3: 改 5 命令文档（加 source 前缀，弃 cd .claude/commands/clipforge）**

每个命令文档把开头的 `cd .claude/commands/clipforge` 替换为 source helper。以 `clipforge-feedback.md` 为例（其他 4 个同模式）：

`clipforge-feedback.md` 当前开头执行块改为：
```bash
source "$(git rev-parse --show-toplevel 2>/dev/null)/.claude/commands/clipforge/shared/clipforge-env.sh" 2>/dev/null \
  || source "$HOME/.claude/commands/clipforge/shared/clipforge-env.sh"
TODAY=$(date +%Y-%m-%d)
BILI="${WORKSPACE:-$(git rev-parse --show-toplevel)}/workspace/sources/视频数据/${TODAY}/哔哩哔哩近期稿件对比.csv"
if [ ! -f "$BILI" ]; then
  (cd "$CF_DIR" && python scripts/fetch_bilibili.py) || echo "⚠ B站 抓取失败（cookie 过期？复制浏览器 Cookie 到 .bili-cookie）"
fi
cd "$CF_DIR"
python scripts/collect_performance.py --scan
python scripts/auto_evolve.py
```

对 `evolve-daily.md` / `github-daily-trending.md` / `github-weekly-trending.md` / `clipforge-category-setup.md`：把每个 `cd .claude/commands/clipforge` 替换为：
```bash
source "$(git rev-parse --show-toplevel 2>/dev/null)/.claude/commands/clipforge/shared/clipforge-env.sh" 2>/dev/null \
  || source "$HOME/.claude/commands/clipforge/shared/clipforge-env.sh"
cd "$CF_DIR"
```
用 grep 找全所有 `cd .claude/commands/clipforge` 出现处：`grep -rn "cd \.claude/commands/clipforge" .claude/commands/*.md`

- [ ] **Step 4: 冒烟验证（helper source + CF_DIR 正确）**

```bash
# 项目级场景（技能在项目 .claude）
rm -f "$HOME/.claude/commands/clipforge"  # 移除软链，模拟项目级
source /d/AI-Agent/video-clipforge/.claude/commands/clipforge/shared/clipforge-env.sh
echo "项目级 CF_DIR=$CF_DIR"
# 用户级场景
ln -sf /d/AI-Agent/video-clipforge/.claude/commands/clipforge "$HOME/.claude/commands/clipforge"
source /d/AI-Agent/video-clipforge/.claude/commands/clipforge/shared/clipforge-env.sh
echo "用户级 CF_DIR=$CF_DIR"
```
Expected: 项目级时 CF_DIR 指向项目 .claude；用户级（软链存在）时指向 ~/.claude。

- [ ] **Step 5: Commit（需用户授权）**

```bash
git add .claude/commands/clipforge/shared/clipforge-env.sh .claude/commands/clipforge-feedback.md .claude/commands/evolve-daily.md .claude/commands/github-daily-trending.md .claude/commands/github-weekly-trending.md .claude/commands/clipforge-category-setup.md
# 等用户授权后：git commit -m "feat(clipforge): 命令文档加技能目录探测前缀，支持用户级 install"
```

---

## Task 4: 新命令 /clipforge-switch-workspace

**Files:**
- Create: `.claude/commands/clipforge-switch-workspace.md`

- [ ] **Step 1: 写命令文档**

Create `.claude/commands/clipforge-switch-workspace.md`:

```markdown
# /clipforge-switch-workspace — 切换 ClipForge 工作目录

切换 ClipForge 的工作目录（视频输出 / evolution / 播放数据落哪里）。写入 `~/.claude/clipforge-config.json` 的 `workspace_default`，作为「非 git 目录」时的兜底默认。

> **日常无需此命令**：在 git 项目内跑 `/clipforge` 等命令时，工作目录自动用当前项目根（git rev-parse）。本命令仅用于设「非 git 兜底默认」或显式指定。

## 用法

```bash
source "$CF_DIR/shared/clipforge-env.sh" 2>/dev/null || CF_DIR="$(git rev-parse --show-toplevel)/.claude/commands/clipforge"
cd "$CF_DIR"
python -c "
import sys, os
sys.path.insert(0, '.')
from engine.lib.data_paths import set_workspace_default, get_config, USER_CONFIG
target = sys.argv[1] if len(sys.argv) > 1 else None
if not target:
    cfg = get_config()
    cur = cfg.get('workspace_default', '<未配置>')
    print(f'当前工作目录默认: {cur}')
    target = input('切换到（输入绝对路径，留空取消）: ').strip()
    if not target:
        sys.exit('已取消')
resolved = set_workspace_default(target)
print(f'✅ 工作目录默认已切换为: {resolved}')
print(f'   写入: {USER_CONFIG}')
" "$@"
```

## 验证

切换后，下次在**非 git 目录**跑 `/clipforge-feedback` 时，工作目录用新默认；在 git 项目内跑则仍用该项目（git 优先）。
```

- [ ] **Step 2: 冒烟（设 + 读）**

```bash
cd /d/AI-Agent/video-clipforge/.claude/commands/clipforge
python -c "
import sys; sys.path.insert(0,'.')
from engine.lib.data_paths import set_workspace_default, get_config
p = set_workspace_default('/tmp/test_ws_hint')
print('set:', p)
print('config:', get_config())
"
```
Expected: 写入 ~/.claude/clipforge-config.json，workspace_default=/tmp/test_ws_hint，含 configured_at。

- [ ] **Step 3: 清理测试痕迹（避免污染配置）**

```bash
# 测试用的 hint 清掉（可选，或保留也无害——git 项目内跑会覆盖）
python -c "import sys; sys.path.insert(0,'.'); import engine.lib.data_paths as dp; dp.USER_CONFIG.unlink(missing_ok=True); print('已清测试配置')"
```

- [ ] **Step 4: Commit（需用户授权）**

```bash
git add .claude/commands/clipforge-switch-workspace.md
# 等用户授权后：git commit -m "feat(clipforge): 新增 /clipforge-switch-workspace 切换工作目录命令"
```

---

## Task 5: stage0-env 首次配置引导

**Files:**
- Modify: `.claude/commands/clipforge/stages/stage0-env.md`

- [ ] **Step 1: 读现状定位插入点**

```bash
grep -n "环境检测\|env-check\|首次\|##" .claude/commands/clipforge/stages/stage0-env.md | head -20
```
找到环境检测步骤的合适插入点（在现有 env check 后，进入管线前）。

- [ ] **Step 2: 加首次配置引导段**

在 stage0-env.md 环境检测段后插入：

```markdown
## 工作目录检测（解耦改造后）

技能 install 到用户级时，工作目录（视频输出/evolution 落哪里）由四级回退定位。**首次运行检测**：

```bash
source "$CF_DIR/shared/clipforge-env.sh" 2>/dev/null || CF_DIR="$(git rev-parse --show-toplevel 2>/dev/null)/.claude/commands/clipforge"
cd "$CF_DIR"
python -c "
import sys; sys.path.insert(0,'.')
import os
from engine.lib.data_paths import resolve_workspace_root, get_config, _git_toplevel, USER_CONFIG
ws = resolve_workspace_root()
in_git = _git_toplevel() is not None
has_cfg = USER_CONFIG.exists()
print(f'工作目录: {ws}')
print(f'来源: {"git(项目内自动)" if in_git else ("配置默认" if has_cfg else "cwd兜底⚠")}')
if not in_git and not has_cfg:
    print('⚠ 非 git 目录且无配置默认。建议运行 /clipforge-switch-workspace <项目路径> 设默认，否则视频输出落 cwd。')
"
```

- **git 项目内**：工作目录 = 当前项目根，无需配置，cd 即切换。
- **非 git + 无配置**：提示用户跑 `/clipforge-switch-workspace`（或确认 cwd 是预期工作目录）。
- **非 git + 有配置**：用配置默认。
```

- [ ] **Step 3: 冒烟（项目内应提示 git 自动）**

```bash
cd /d/AI-Agent/video-clipforge/.claude/commands/clipforge
python -c "
import sys; sys.path.insert(0,'.')
from engine.lib.data_paths import resolve_workspace_root, _git_toplevel, USER_CONFIG
print('ws=', resolve_workspace_root())
print('in_git=', _git_toplevel() is not None)
print('has_cfg=', USER_CONFIG.exists())
"
```
Expected: ws=项目根，in_git=True，has_cfg=False（或你测试设的）。

- [ ] **Step 4: Commit（需用户授权）**

```bash
git add .claude/commands/clipforge/stages/stage0-env.md
# 等用户授权后：git commit -m "feat(clipforge): stage0-env 加工作目录检测与首次配置引导"
```

---

## Task 6: 双层验证（遵循 CLAUDE.md 架构演进规范）

**Files:**
- 临时: `workspace/test/decouple/`（隔离，不进生产 YYYY/MM/DD）
- 主 agent 协调 subagent

### 6A. 推演核实（subagent + 主 agent）

- [ ] **Step 1: 派 subagent 全管线推演（技能软链 ~/.claude 模拟用户级）**

派 Explore/general-purpose subagent：
- 软链模拟：`ln -sf <项目>/.claude/commands/clipforge ~/.claude/commands/clipforge`
- 任务：读真实文件，验证每个脚本/命令在「技能在 ~/.claude，workspace 在项目根」假设下：
  - data_paths 四级回退返回项目根（git rev-parse）
  - 6 脚本 import 后 WORKSPACE_ROOT/DATA_DIR 指向项目 workspace
  - 5 命令 source helper 后 CF_DIR 指向 ~/.claude（用户级软链）
  - 每结论附 `file:line`
- 输出：路径断裂清单 + 不一致点

- [ ] **Step 2: 主 agent 交叉验证**

主 agent grep/read 验证 subagent 每条结论，修正过度解读。确认：
- 无脚本残留 `parents[3]`：`grep -rn "parents\[3\]\|parent\.parent\.parent.*video" .claude/commands/clipforge/scripts/`
- 无命令残留 `cd .claude/commands/clipforge`（裸）：`grep -rn "cd \.claude/commands/clipforge" .claude/commands/*.md`（应只剩 source helper 的）

### 6B. 真实重做（端到端，workspace/test/decouple/ 隔离）

- [ ] **Step 3: 准备隔离环境**

```bash
export CLIPFORGE_WORKSPACE=/d/AI-Agent/video-clipforge/workspace/test/decouple
mkdir -p "$CLIPFORGE_WORKSPACE"
ln -sf /d/AI-Agent/video-clipforge/.claude/commands/clipforge "$HOME/.claude/commands/clipforge"
# 验证四级回退第 1 级（env）生效
cd /tmp  # 非 git 非 cwd
python /d/AI-Agent/video-clipforge/.claude/commands/clipforge/engine/../scripts/auto_evolve.py 2>&1 | head -5 || \
python -c "import sys; sys.path.insert(0,'/d/AI-Agent/video-clipforge/.claude/commands/clipforge'); from engine.lib.data_paths import resolve_workspace_root; print(resolve_workspace_root())"
```
Expected: resolve_workspace_root 返回 workspace/test/decouple（env 第 1 级覆盖 git/cwd）。

- [ ] **Step 4: 主 agent 协调 subagent 跑完整 /clipforge 视频管线**

派 general-purpose subagent（bypassPermissions）跑 `/clipforge`：
- 设 `CLIPFORGE_WORKSPACE=workspace/test/decouple`
- 用最简测试内容（如 stage1 测试 fixture，或小段文字）
- 验证：视频生成在 `workspace/test/decouple/2026/06/18/...`（而非生产路径），evolution 数据落 test 目录
- 跑 stage 门禁（stage1/3/4/6/7）全过

- [ ] **Step 5: 验证产物隔离 + 清理**

```bash
# 产物应在 test/decouple，不污染生产
ls /d/AI-Agent/video-clipforge/workspace/test/decouple/2026/06/18/ 2>&1
ls /d/AI-Agent/video-clipforge/workspace/2026/06/18/ | grep -v github-trending  # 生产路径不应有测试视频
# 清理软链
rm -f "$HOME/.claude/commands/clipforge"
unset CLIPFORGE_WORKSPACE
```
Expected: 测试视频在 test/decouple；生产路径无测试残留。

- [ ] **Step 6: 回归现有定时任务（项目级场景，向后兼容）**

```bash
# 验证现有 github-daily-trending 命令在项目级技能下仍工作（CF_DIR=项目 .claude）
cd /d/AI-Agent/video-clipforge
source .claude/commands/clipforge/shared/clipforge-env.sh
echo "CF_DIR=$CF_DIR"  # 应指向项目 .claude
python "$CF_DIR/engine/../scripts/auto_evolve.py" --help >/dev/null 2>&1 && echo "auto_evolve 可执行" || echo "FAIL"
```
Expected: CF_DIR 指向项目 .claude（无 ~/.claude 软链时），脚本可执行——向后兼容确认。

- [ ] **Step 7: 最终 commit + memory（需用户授权）**

```bash
# 等用户授权后：
git add docs/superpowers/specs/ docs/superpowers/plans/
git commit -m "docs(clipforge): 解耦改造 spec + 实施计划（技能用户级 install + 工作目录项目级）"
```
写 memory `feedback-clipforge-decouple-paths`：技能可 install 用户级；data_paths 四级回退（env>git>config>cwd）；命令 source clipforge-env.sh 定位 CF_DIR；cd 即切换工作目录；向后兼容。

---

## Self-Review（计划自审）

**Spec 覆盖**：
- ✅ 四级回退 → Task 1
- ✅ 6 脚本收口 → Task 2
- ✅ 5 命令前缀 → Task 3
- ✅ 配置 + 首次配置 → Task 1(config 函数) + Task 5(stage0-env 引导)
- ✅ 切换 → Task 4（/switch）+ Task 3（cd 即切换）
- ✅ 向后兼容 → Task 6 Step 6 回归
- ✅ 双层验证 → Task 6

**Placeholder 扫描**：无 TBD/TODO；每步含具体代码/命令。

**类型一致**：`WORKSPACE_ROOT` / `PROJECT_ROOT`（别名）/ `CF_DIR`（bash）/ `set_workspace_default` / `resolve_workspace_root` 全计划一致。
