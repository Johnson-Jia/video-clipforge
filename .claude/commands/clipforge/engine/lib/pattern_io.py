"""Pattern 读写单源。

背景（2026-08-16 审计 P0）：auto_evolve 把时效状态写入 evidence.status（嵌套层），
而 exploration.py 曾只读顶层 status —— 写读层级不对齐导致已判 deprecated 的 pattern
仍被 exploration 选为 exploit/explore 目标 force 注入生产。

约定：所有 pattern 状态的**读方**（inject / exploration / dashboard / 未来的写方）
一律经本模块取值，禁止各自手写 `data.get("status")`。写入方（auto_evolve）维持
evidence.status 不变，本模块双兜底兼容两种层级。

seed pattern（人工经验，seed: true）无时效概念：mtime 老化豁免（见 is_seed）。
"""

from __future__ import annotations

from pathlib import Path


def load_pattern(fp: Path) -> dict | None:
    """读单个 pattern yaml，空/坏文件返回 None。"""
    try:
        import yaml
        data = yaml.safe_load(fp.read_text("utf-8"))
    except Exception:
        return None
    return data if isinstance(data, dict) and data else None


def pattern_status(data: dict) -> str | None:
    """时效状态唯一取值口：顶层 status 优先，evidence.status 兜底（auto_evolve 写入层）。"""
    if not isinstance(data, dict):
        return None
    top = data.get("status")
    if isinstance(top, str) and top:
        return top
    ev = data.get("evidence")
    if isinstance(ev, dict):
        nested = ev.get("status")
        if isinstance(nested, str) and nested:
            return nested
    return None


def is_deprecated(data: dict) -> bool:
    """已硬淘汰（连续 declining）：任何消费方不得再注入/推荐。"""
    return pattern_status(data) == "deprecated"


def is_seed(data: dict) -> bool:
    """人工经验 pattern：不参与探索-利用、不受 mtime 老化（经 inject 常规注入）。"""
    return isinstance(data, dict) and data.get("seed") is True
