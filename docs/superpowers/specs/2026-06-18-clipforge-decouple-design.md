# ClipForge 技能解耦改造设计

> 日期：2026-06-18
> 状态：设计审批中
> 目标：技能可 install 到用户级 `~/.claude/`，工作目录保持项目级，首次可配置，支持切换

## 1. 背景与问题

ClipForge 当前假设技能在**项目级** `.claude/commands/clipforge/`：

- 6+ 脚本用 `SCRIPT_DIR.parents[3]` / `CLIPFORGE_ROOT.parent.parent.parent` 定位项目根：
  - `scripts/auto_evolve.py`、`collect_performance.py`、`fetch_bilibili.py`、`backfill_cover.py`、`backfill_injected.py`、`bgm_history.py`
- 5 命令文档 `cd .claude/commands/clipforge`（项目根相对）：clipforge-feedback / evolve-daily / github-daily-trending / github-weekly-trending / clipforge-category-setup
- `engine/lib/data_paths.py` 的 `PROJECT_ROOT = CLIPFORGE_ROOT.parent.parent.parent`（line 19）

install 到用户级 `~/.claude/` 后：

- `PROJECT_ROOT` 算成 `~/.claude`（错）→ `workspace = ~/.claude/workspace`（数据错位）
- 命令 `cd .claude/commands/clipforge` 失败（项目根无此目录，技能在 `~/.claude/`）
- 视频输出 / evolution / 播放数据全写错位置

## 2. 目标

1. 技能可 install 到用户级 `~/.claude/`（脱离项目 `.claude/`）
2. 工作目录（workspace / 视频输出 / evolution / 播放数据）保持项目级（用户当前项目）
3. 首次运行可配置工作目录
4. 支持切换工作目录
5. 向后兼容（现有项目级用户零感知、零迁移）

## 3. 设计

### 3.1 核心：data_paths.py 四级回退

`engine/lib/data_paths.py` 改 `PROJECT_ROOT` 为四级回退定位（弃 `parents[3]`）：

```python
import os, json, subprocess
from pathlib import Path

CLIPFORGE_ROOT = Path(__file__).resolve().parents[2]           # 技能目录（用户级/项目级自适应）
USER_CONFIG = Path.home() / ".claude" / "clipforge-config.json"

def resolve_workspace_root() -> Path:
    # 1. 环境变量 CLIPFORGE_WORKSPACE（临时覆盖，测试/CI）
    env = os.environ.get("CLIPFORGE_WORKSPACE")
    if env and Path(env).exists():
        return Path(env).resolve()
    # 2. git rev-parse --show-toplevel（项目内自动，cd 即切换）
    try:
        root = subprocess.check_output(
            ["git", "rev-parse", "--show-toplevel"],
            stderr=subprocess.DEVNULL,
        ).strip().decode()
        if root:
            return Path(root)
    except Exception:
        pass
    # 3. 用户配置默认（非 git 兜底）
    if USER_CONFIG.exists():
        ws = json.loads(USER_CONFIG.read_text(encoding="utf-8")).get("workspace_default")
        if ws and Path(ws).exists():
            return Path(ws).resolve()
    # 4. cwd
    return Path.cwd()

WORKSPACE_ROOT = resolve_workspace_root()
PROJECT_ROOT = WORKSPACE_ROOT                                    # 别名，脚本兼容
EVOLUTION_ROOT = WORKSPACE_ROOT / "workspace" / "evolution"
VIDEO_DATA_DIR = WORKSPACE_ROOT / "workspace" / "sources" / "视频数据"
BILI_COOKIE = VIDEO_DATA_DIR / ".bili-cookie"
```

收口扩展（data_paths 原来只收口 evolution 层，新增 sources/播放数据/cookie）。

配置读写函数：

```python
def get_config() -> dict:
    return json.loads(USER_CONFIG.read_text(encoding="utf-8")) if USER_CONFIG.exists() else {}

def set_workspace_default(path: str) -> None:
    cfg = get_config()
    cfg["workspace_default"] = str(Path(path).resolve())
    cfg["configured_at"] = datetime.now().isoformat()
    USER_CONFIG.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
```

### 3.2 脚本收口

6+ 脚本弃各自 `parents[3]`，统一 `from engine.lib.data_paths import ...`：

| 脚本 | 原 | 改 |
|------|-----|-----|
| auto_evolve.py | `PROJECT_ROOT = CLIPFORGE_ROOT.parent.parent.parent` | `from engine.lib.data_paths import WORKSPACE_ROOT as PROJECT_ROOT` |
| collect_performance.py | 同 | 同 |
| fetch_bilibili.py | `WORKSPACE_ROOT = SCRIPT_DIR.parents[3]` | `from engine.lib.data_paths import VIDEO_DATA_DIR as DATA_DIR` |
| backfill_cover.py / backfill_injected.py | 同 | 同 |
| bgm_history.py | `CLIPFORGE_DIR = os.path.join(SCRIPT_DIR, "..")` | `from engine.lib.data_paths import CLIPFORGE_ROOT as CLIPFORGE_DIR` |

### 3.3 命令文档：技能目录探测前缀

5 命令文档弃 `cd .claude/commands/clipforge`（项目根相对，install 用户级断），改 3 行探测前缀（用户级优先，项目级兜底）：

```bash
# 定位技能目录（用户级优先，项目级兜底）
CF_DIR=""
[ -d "$HOME/.claude/commands/clipforge" ] && CF_DIR="$HOME/.claude/commands/clipforge"
[ -z "$CF_DIR" ] && CF_DIR="$(git rev-parse --show-toplevel 2>/dev/null)/.claude/commands/clipforge"
python "$CF_DIR/scripts/auto_evolve.py"
```

### 3.4 配置 + 首次 + 切换

- **配置文件**：`~/.claude/clipforge-config.json`
  ```json
  {"workspace_default": "/abs/path/to/project", "configured_at": "2026-06-18T..."}
  ```
- **首次配置**：`stage0-env` 检测「非 git 目录 + 无 USER_CONFIG」→ 引导用户设默认（在 git 项目内跑则 git 自动，无需配置）
- **切换**：
  - 日常 `cd` 到别的项目 → git rev-parse 自动切换（零命令，最优雅）
  - `/clipforge-switch-workspace <path>` → 改 `workspace_default`（非 git 兜底）+ 立即生效

### 3.5 新命令：/clipforge-switch-workspace

```bash
# .claude/commands/clipforge-switch-workspace.md
# 用途：切换 ClipForge 工作目录（写 ~/.claude/clipforge-config.json workspace_default）
# 无参数 → 交互式（列最近项目 + 输入）
# 有参数 → 直接设
```

## 4. 迁移与向后兼容

- **现有项目级用户**：`git rev-parse` 返回同项目根 → workspace 路径完全不变，零迁移、零感知
- **USER_CONFIG 不存在**：走 git/cwd，行为同今天
- **现有 workspace 数据**：不动（git rev-parse 定位同位置）
- **PROJECT_ROOT 别名**：保留，脚本最小改动

## 5. 验证（遵循 CLAUDE.md「架构演进验证规范」双层）

### 5.1 推演核实（subagent + 主 agent 两层）

- subagent 全管线推演：技能软链到 `~/.claude/commands/clipforge` 模拟用户级 install，读真实文件 + 每结论附 `file:line`，找路径断裂 / 不一致
- 主 agent 交叉验证：grep/read 验证每条脚本/命令路径假设，修正过度解读

### 5.2 真实重做（端到端）

- 隔离目录 `workspace/test/decouple/`（不进 `YYYY/MM/DD` 生产路径）
- 技能软链 `~/.claude/commands/clipforge` → 项目技能目录（模拟用户级 install）
- 设 `CLIPFORGE_WORKSPACE=workspace/test/decouple`（四级回退第 1 级，避免污染生产）
- 跑完整 `/clipforge` 视频管线，验证 workspace 落 test 目录、视频正常生成
- 主 agent 协调多 subagent（一个推演/审查 + 一个执行真实视频制作）

## 6. 非目标（YAGNI）

- 不做 CLI 包发布（`pip install clipforge`）—— 方案 A 已满足，过重
- 不做多 workspace 并行管理 —— 单一当前（git 自动 + 配置兜底）够用
- 不做 workspace 注册表 / history —— USER_CONFIG 只存当前默认

## 7. 影响范围

| 改动类型 | 文件 |
|---------|------|
| 核心 | `engine/lib/data_paths.py`（PROJECT_ROOT 四级回退 + 收口扩展 + 配置函数） |
| 脚本（6） | auto_evolve / collect_performance / fetch_bilibili / backfill_cover / backfill_injected / bgm_history |
| 命令文档（5） | clipforge-feedback / evolve-daily / github-daily-trending / github-weekly-trending / clipforge-category-setup |
| 新增 | `clipforge-switch-workspace.md` 命令 + stage0-env 首次配置引导 |
