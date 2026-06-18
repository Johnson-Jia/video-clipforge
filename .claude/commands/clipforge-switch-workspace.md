# /clipforge-switch-workspace — 切换 ClipForge 工作目录

切换 ClipForge 的工作目录（视频输出 / evolution / 播放数据落哪里）。写入 `~/.claude/clipforge-config.json` 的 `workspace_default`，作为「非 git 目录」时的兜底默认。

> **日常无需此命令**：在 git 项目内跑 `/clipforge` 等命令时，工作目录自动用当前项目根（data_paths 四级回退第 2 级 git rev-parse）。本命令仅用于设「非 git 兜底默认」或显式指定。

## 用法

```bash
source "$HOME/.claude/commands/clipforge/shared/clipforge-env.sh" 2>/dev/null || source "$(git rev-parse --show-toplevel 2>/dev/null)/.claude/commands/clipforge/shared/clipforge-env.sh"
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
print(f'   说明: git 项目内跑命令仍用该项目（git 优先）；非 git 目录用此默认')
" "\$@"
```

## 参数

- 无参数：交互式（显示当前默认 + 输入新路径）
- `<绝对路径>`：直接设为默认

## 验证

切换后，下次在**非 git 目录**跑 `/clipforge-feedback` 时，工作目录用新默认；在 git 项目内跑则仍用该项目（git 优先）。
