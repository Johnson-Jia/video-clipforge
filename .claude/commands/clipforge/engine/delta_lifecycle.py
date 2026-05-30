"""Delta 生命周期管理 — promote / expire / review。

Delta 从"软生效"（inject.py 运行时加载）到"硬生效"（修改规则源文件）
需要人工审核。本工具提供：
- promote: 将高置信度 delta 合并到规则 YAML（"毕业"）
- expire: 标记超过 N 天未 promote 的低置信度 delta 为 EXPIRED
- review: 列出所有 requires_human_review 的 delta 供人工审核
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).parent.parent))
from engine.lib.delta import load_deltas, DELTAS_DIR
from engine.lib.rule_parser import load_all_rules, RULES_DIR

MAX_AGE_DAYS = 30
PROMOTE_MIN_CONFIDENCE = 0.85
PROMOTE_MIN_SHADOW_PASSES = 2


def review_pending(deltas_dir: Path | None = None) -> list[dict]:
    """列出所有 requires_human_review 的 delta。"""
    deltas = load_deltas(deltas_dir)
    pending = []
    for d in deltas:
        inner = d.get("delta", d)
        if inner.get("requires_human_review", False):
            pending.append({
                "id": inner.get("id", "?"),
                "operation": inner.get("operation", "?"),
                "target_rule": inner.get("target_rule", "?"),
                "source": inner.get("source", "?"),
                "confidence": inner.get("confidence", 0),
                "file": str(d.get("_file", "?")),
            })
    return pending


def expire_stale(
    max_age_days: int = MAX_AGE_DAYS,
    deltas_dir: Path | None = None,
    dry_run: bool = True,
) -> list[str]:
    """标记超过 N 天未 promote 的低置信度 delta 为 EXPIRED。"""
    deltas_dir = deltas_dir or DELTAS_DIR
    if not deltas_dir.exists():
        return []

    expired = []
    for fp in sorted(deltas_dir.glob("*.yaml")):
        data = yaml.safe_load(fp.read_text(encoding="utf-8"))
        inner = data.get("delta", data)
        if inner.get("operation") == "EXPIRED":
            continue
        if inner.get("confidence", 0) >= 0.70:
            continue

        mtime = datetime.fromtimestamp(fp.stat().st_mtime)
        if (datetime.now() - mtime).days > max_age_days:
            inner["operation"] = "EXPIRED"
            inner["expired_reason"] = f"超过 {max_age_days} 天未 promote 且置信度 < 0.70"
            if not dry_run:
                fp.write_text(
                    yaml.dump(data, allow_unicode=True, default_flow_style=False),
                    encoding="utf-8",
                )
            expired.append(fp.name)

    return expired


def promote_ready(
    min_confidence: float = PROMOTE_MIN_CONFIDENCE,
    deltas_dir: Path | None = None,
    rules_dir: Path | None = None,
    dry_run: bool = True,
) -> list[dict]:
    """列出满足 promote 条件的 delta（高置信度 + 无需人工审核）。

    Promote 会直接修改规则 YAML 文件，是高风险操作。
    dry_run=True 时只列出候选，不实际修改。
    """
    deltas = load_deltas(deltas_dir)
    candidates = []
    for d in deltas:
        inner = d.get("delta", d)
        if inner.get("confidence", 0) < min_confidence:
            continue
        if inner.get("requires_human_review", True):
            continue
        if inner.get("operation") in ("EXPIRED", "DEPRECATED"):
            continue
        candidates.append({
            "id": inner.get("id"),
            "operation": inner.get("operation"),
            "target_rule": inner.get("target_rule"),
            "confidence": inner.get("confidence"),
        })

    return candidates


def main():
    parser = argparse.ArgumentParser(description="Delta 生命周期管理")
    parser.add_argument("action", choices=["review", "expire", "promote"])
    parser.add_argument("--apply", action="store_true", help="实际执行（默认 dry-run）")
    parser.add_argument("--max-age-days", type=int, default=MAX_AGE_DAYS)
    parser.add_argument("--min-confidence", type=float, default=PROMOTE_MIN_CONFIDENCE)
    args = parser.parse_args()

    if args.action == "review":
        pending = review_pending()
        if not pending:
            print("无待审核 Delta")
        else:
            print(json.dumps(pending, ensure_ascii=False, indent=2))

    elif args.action == "expire":
        expired = expire_stale(
            max_age_days=args.max_age_days,
            dry_run=not args.apply,
        )
        mode = "DRY-RUN" if not args.apply else "APPLIED"
        print(f"[{mode}] 过期 Delta: {len(expired)}")
        for e in expired:
            print(f"  - {e}")

    elif args.action == "promote":
        candidates = promote_ready(min_confidence=args.min_confidence)
        if not candidates:
            print("无满足条件的 Delta 可 promote")
        else:
            mode = "DRY-RUN" if not args.apply else "APPLIED"
            print(f"[{mode}] 可 promote Delta: {len(candidates)}")
            print(json.dumps(candidates, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
