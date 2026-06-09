"""Threshold reader — 从 YAML 读取性能阈值（自进化真相源）。"""
from __future__ import annotations
import yaml
from pathlib import Path
from datetime import datetime, timezone

THRESHOLDS_FILE = Path(__file__).parent / "thresholds.yaml"


def load() -> dict:
    with open(THRESHOLDS_FILE, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def save(data: dict) -> None:
    with open(THRESHOLDS_FILE, "w", encoding="utf-8") as f:
        yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)


def get_douyin() -> dict:
    return load().get("douyin", {})


def get_platform_success() -> dict:
    return load().get("success", {})


def update_calibration(sample_size: int, **kwargs) -> None:
    data = load()
    cal = data.setdefault("calibration", {})
    cal["last_updated"] = datetime.now(timezone.utc).isoformat()
    cal["sample_size"] = sample_size
    cal.update(kwargs)
    save(data)
