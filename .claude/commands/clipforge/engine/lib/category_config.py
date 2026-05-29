"""分类配置加载器 — 引擎级模块的统一配置源。

从 categories/{id}.md 的 CONFIG-START/END 段解析 YAML 配置，
供 render_stage.py、gate.py、attribution.py 等模块统一调用。
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

CATEGORIES_DIR = Path(__file__).parent.parent.parent / "categories"

_cache: dict[str, dict] = {}


def parse_category_config(category_path: Path) -> dict:
    """从分类 .md 文件提取 CONFIG-START/END 之间的 YAML 配置。"""
    import yaml

    content = category_path.read_text(encoding="utf-8")
    match = re.search(
        r"<!--\s*CONFIG-START[^>]*>\s*\n(.*?)<!--\s*CONFIG-END\s*-->",
        content,
        re.DOTALL,
    )
    if not match:
        return {}
    try:
        return yaml.safe_load(match.group(1)) or {}
    except yaml.YAMLError as e:
        print(f"WARNING: CONFIG YAML 解析失败: {e}", file=sys.stderr)
        return {}


def load_category_config(category_id: str | None) -> dict:
    """加载并缓存分类配置。category_id 为 None 时返回空字典。"""
    if category_id is None:
        return {}
    if category_id not in _cache:
        path = CATEGORIES_DIR / f"{category_id}.md"
        if not path.exists():
            return {}
        _cache[category_id] = parse_category_config(path)
    return _cache[category_id]


def get(config: dict, dotted_key: str, default=None):
    """按点号路径获取嵌套字典值。

    get(cfg, "audio.default_voice", "zh-CN-YunjianNeural")
    等价于 cfg.get("audio", {}).get("default_voice", "zh-CN-YunjianNeural")
    """
    keys = dotted_key.split(".")
    value = config
    for key in keys:
        if isinstance(value, dict) and key in value:
            value = value[key]
        else:
            return default
    return value


def resolve_value(config: dict, dotted_key: str, default: str = "") -> str:
    """获取配置值并转为字符串。列表用空格连接。"""
    value = get(config, dotted_key, default)
    if value is None:
        return ""
    if isinstance(value, list):
        return " ".join(str(v) for v in value)
    if isinstance(value, bool):
        return str(value)
    return str(value)
