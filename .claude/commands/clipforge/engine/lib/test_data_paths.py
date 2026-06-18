"""data_paths 四级回退 + 配置读写单测。用 mock 不污染真实环境。"""
import json
import os
import sys
from pathlib import Path
from unittest import mock

# 让 test 能 import engine.lib.data_paths
# test 在 engine/lib/，parents[2] = clipforge/（含 engine 包）
_CLIPFORGE = Path(__file__).resolve().parents[2]
if str(_CLIPFORGE) not in sys.path:
    sys.path.insert(0, str(_CLIPFORGE))

import engine.lib.data_paths as dp
import importlib


def _resolve_with(env=None, git_root=None, config_path=None, cwd=None):
    """用指定环境调 resolve_workspace_root（mock 注入，不污染真实）。"""
    clean_env = {k: v for k, v in os.environ.items() if k != "CLIPFORGE_WORKSPACE"}
    if env is not None:
        clean_env["CLIPFORGE_WORKSPACE"] = env
    with mock.patch.dict(os.environ, clean_env, clear=False):
        with mock.patch.object(dp, "_git_toplevel", return_value=git_root):
            cfg_mock = config_path if config_path is not None else dp.USER_CONFIG
            with mock.patch.object(dp, "USER_CONFIG", cfg_mock):
                if cwd is not None:
                    with mock.patch("pathlib.Path.cwd", return_value=Path(cwd)):
                        return dp.resolve_workspace_root()
                return dp.resolve_workspace_root()


def test_env_var_wins(tmp_path):
    """1 级：CLIPFORGE_WORKSPACE 环境变量优先（即使有 git/config）。"""
    env_dir = tmp_path / "env_ws"
    env_dir.mkdir()
    root = _resolve_with(env=str(env_dir), git_root="/some/git", config_path=None)
    assert root == env_dir.resolve()


def test_git_toplevel_second(tmp_path):
    """2 级：无 env 时 git rev-parse。"""
    git_dir = tmp_path / "git_proj"
    git_dir.mkdir()
    root = _resolve_with(env=None, git_root=str(git_dir), config_path=None)
    assert root == git_dir.resolve()


def test_config_default_third(tmp_path):
    """3 级：无 env 无 git 时用 USER_CONFIG workspace_default。"""
    cfg_dir = tmp_path / "cfg_proj"
    cfg_dir.mkdir()
    cfg_file = tmp_path / "clipforge-config.json"
    cfg_file.write_text(json.dumps({"workspace_default": str(cfg_dir)}), encoding="utf-8")
    root = _resolve_with(env=None, git_root=None, config_path=cfg_file)
    assert root == cfg_dir.resolve()


def test_cwd_fallback(tmp_path):
    """4 级：全无时 cwd 兜底。"""
    root = _resolve_with(env=None, git_root=None, config_path=None, cwd=str(tmp_path))
    assert root == tmp_path.resolve()


def test_get_set_config(tmp_path):
    """配置读写：set_workspace_default 写 USER_CONFIG。"""
    cfg = tmp_path / "clipforge-config.json"
    with mock.patch.object(dp, "USER_CONFIG", cfg):
        resolved = dp.set_workspace_default(str(tmp_path / "proj"))
        assert resolved == (tmp_path / "proj").resolve()
        data = json.loads(cfg.read_text(encoding="utf-8"))
        assert data["workspace_default"].endswith("proj")
        assert "configured_at" in data
        # get_config 读回
        assert dp.get_config()["workspace_default"].endswith("proj")
