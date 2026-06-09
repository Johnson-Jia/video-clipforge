"""归因争议追踪 + 熔断器 — 当归因被推翻时追踪并触发熔断。

架构哲学对齐：
- P3（事故复盘）：争议追踪确保归因质量，避免系统性错误产出大量错误 Delta
- P6（渐进严谨）：熔断器在争议率过高时暂停自动归因，强制人工介入
- 熔断阈值：30 天内争议率 > 30% → 全局暂停自动归因
"""
from __future__ import annotations
import argparse
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from engine.lib.delta import load_deltas, DELTAS_DIR
from engine.lib.rule_parser import load_all_rules, RULES_DIR

DISPUTES_FILE = Path(__file__).parent.parent / "deltas" / "disputes.json"
CIRCUIT_BREAKER_WINDOW_DAYS = 30
CIRCUIT_BREAKER_THRESHOLD = 0.30


def record_dispute(
    delta_id: str,
    reason: str,
    overturned: bool,
    disputes_file: Path | None = None,
) -> dict:
    """记录一条争议。追加写入 disputes.json。"""
    disputes_file = disputes_file or DISPUTES_FILE
    disputes_file.parent.mkdir(parents=True, exist_ok=True)

    record = {
        "delta_id": delta_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "reason": reason,
        "overturned": overturned,
    }

    existing: list[dict] = []
    if disputes_file.exists():
        try:
            existing = json.loads(disputes_file.read_text(encoding="utf-8"))
            if not isinstance(existing, list):
                existing = []
        except (json.JSONDecodeError, UnicodeDecodeError):
            existing = []

    existing.append(record)
    disputes_file.write_text(
        json.dumps(existing, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return record


def get_dispute_rate(
    days: int = 30,
    deltas_dir: Path | None = None,
    disputes_file: Path | None = None,
) -> float:
    """计算近 N 天的争议率 = overturned_count / total_deltas_in_period。"""
    disputes_file = disputes_file or DISPUTES_FILE
    deltas_dir = deltas_dir or DELTAS_DIR
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    # 读取争议记录
    disputes: list[dict] = []
    if disputes_file.exists():
        try:
            raw = json.loads(disputes_file.read_text(encoding="utf-8"))
            if isinstance(raw, list):
                disputes = raw
        except (json.JSONDecodeError, UnicodeDecodeError):
            pass

    overturned_count = 0
    for d in disputes:
        if not d.get("overturned"):
            continue
        ts = d.get("timestamp", "")
        try:
            dt = datetime.fromisoformat(ts)
            if dt >= cutoff:
                overturned_count += 1
        except (ValueError, TypeError):
            continue

    # 统计同期 Delta 总数
    deltas = load_deltas(deltas_dir)
    total_in_period = 0
    for delta in deltas:
        dd = delta.get("delta", delta)
        created = dd.get("created_at", "")
        try:
            dt = datetime.fromisoformat(created)
            if dt >= cutoff:
                total_in_period += 1
        except (ValueError, TypeError):
            continue

    return overturned_count / max(total_in_period, 1)


def check_circuit_breaker(
    disputes_file: Path | None = None,
    deltas_dir: Path | None = None,
) -> dict:
    """检查熔断器是否触发。"""
    rate = get_dispute_rate(
        days=CIRCUIT_BREAKER_WINDOW_DAYS,
        deltas_dir=deltas_dir,
        disputes_file=disputes_file,
    )
    return {
        "triggered": rate > CIRCUIT_BREAKER_THRESHOLD,
        "dispute_rate": round(rate, 4),
        "threshold": CIRCUIT_BREAKER_THRESHOLD,
        "window_days": CIRCUIT_BREAKER_WINDOW_DAYS,
    }


def _increment_fp_in_file(rule_id: str, fp: Path) -> bool:
    """在单个 YAML 文件中递增 false_positive_count，保持原格式。"""
    import re
    try:
        text = fp.read_text(encoding="utf-8")
    except Exception:
        return False

    # 用正则找到该规则块中的 false_positive_count 行并递增
    # 匹配: 在包含 id: "rule_id" 的规则块内，找到 false_positive_count: N
    pattern = re.compile(
        r'(- id:\s*["\']?' + re.escape(rule_id) + r'["\']?\s*\n(?:.*\n)*?)'
        r'(false_positive_count:\s*)(\d+)',
        re.MULTILINE,
    )
    match = pattern.search(text)
    if match:
        prefix = match.group(1)
        key = match.group(2)
        count = int(match.group(3)) + 1
        text = text[:match.start(2)] + f"{key}{count}" + text[match.end(3):]
        fp.write_text(text, encoding="utf-8")
        return True

    # 如果规则块中没有 false_positive_count 字段，在 source 行后插入
    rule_block = re.compile(
        r'(- id:\s*["\']?' + re.escape(rule_id) + r'["\']?\s*\n(?:.*\n)*?)'
        r'(    source:\s*[^\n]+)',
        re.MULTILINE,
    )
    match = rule_block.search(text)
    if match:
        insert_after = match.end(2)
        text = text[:insert_after] + f"\n    false_positive_count: 1" + text[insert_after:]
        fp.write_text(text, encoding="utf-8")
        return True

    return False


def increment_false_positive(
    rule_id: str,
    rules_dir: Path | None = None,
) -> bool:
    """递增规则的 false_positive_count 字段并写回 YAML（保持原格式）。"""
    rules_dir = rules_dir or RULES_DIR

    for fp in sorted(rules_dir.glob("*.yaml")):
        if _increment_fp_in_file(rule_id, fp):
            return True

    cat_dir = rules_dir / "categories"
    if cat_dir.exists():
        for fp in sorted(cat_dir.glob("*.yaml")):
            if _increment_fp_in_file(rule_id, fp):
                return True
    return False


def main():
    parser = argparse.ArgumentParser(description="ClipForge 归因争议追踪")
    parser.add_argument("command", choices=["check", "record"])
    parser.add_argument("--delta-id", default=None)
    parser.add_argument("--reason", default="")
    parser.add_argument("--overturned", action="store_true", default=False)
    args = parser.parse_args()

    if args.command == "check":
        result = check_circuit_breaker()
        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif args.command == "record":
        if not args.delta_id:
            print("错误: record 需要指定 --delta-id", file=sys.stderr)
            sys.exit(1)
        result = record_dispute(args.delta_id, args.reason, args.overturned)
        print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
