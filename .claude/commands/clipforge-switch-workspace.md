# /clipforge-switch-workspace — 切换 ClipForge 工作目录

切换 ClipForge 的工作目录（视频输出 / evolution / 播放数据落哪里）。写入 `~/.claude/clipforge-config.json` 的 `workspace_default`，**优先级高于 git**——设置后在任何目录（含 git 项目内）跑命令都用此工作目录。

> **三种工作目录形态**：①技能装用户级 + 显式指定工作目录；②技能装项目级 + 显式指定（本命令）；③技能装项目级 + 不设置，默认用当前项目根下的 workspace。data_paths 回退顺序：`env > config(本命令) > git(当前项目) > cwd`，config 优先于 git。

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
print(f'   说明: config 优先于 git，所有场景（含 git 项目内）生效；未设置时才用当前项目下 workspace')
" "\$@"
```

## 参数

- 无参数：交互式（显示当前默认 + 输入新路径）
- `<绝对路径>`：直接设为默认

## 验证

切换后，下次在任何目录（含 git 项目内）跑 `/clipforge` 等命令时，工作目录都用新默认（config 优先于 git）。清空 config 才回退到当前项目下 workspace。
