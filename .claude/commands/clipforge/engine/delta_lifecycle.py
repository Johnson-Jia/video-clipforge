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

    dry_run=True 时只列出候选，不实际修改。
    dry_run=False 时将 delta 的规则写入对应的 rules/*.yaml 并标记为 PROMOTED。
    """
    deltas_dir = deltas_dir or DELTAS_DIR
    rules_dir = rules_dir or RULES_DIR
    deltas = load_deltas(deltas_dir)
    candidates = []
    for d in deltas:
        inner = d.get("delta", d)
        if inner.get("confidence", 0) < min_confidence:
            continue
        if inner.get("requires_human_review", True):
            continue
        if inner.get("operation") in ("EXPIRED", "DEPRECATED", "PROMOTED"):
            continue
        candidates.append({
            "id": inner.get("id"),
            "operation": inner.get("operation"),
            "target_rule": inner.get("target_rule"),
            "confidence": inner.get("confidence"),
            "new_rule": inner.get("new_rule"),
        })

    if not dry_run and candidates:
        _apply_promotion(candidates, deltas_dir, rules_dir)

    return candidates


def _apply_promotion(candidates: list[dict], deltas_dir: Path, rules_dir: Path) -> list[str]:
    """将候选 delta 写入规则 YAML 并标记为 PROMOTED。"""
    promoted_ids: list[str] = []

    # 按 target_rule 分组，找到对应的规则 YAML 文件
    for cand in candidates:
        target_rule = cand.get("target_rule", "")
        if not target_rule or not cand.get("new_rule"):
            continue

        # 确定 target rule 所在的 YAML 文件
        # 规则 ID 格式: R-S3-008 → stage3.yaml, R-PAT-* → patterns
        target_file = _resolve_rule_file(target_rule, rules_dir)
        if not target_file:
            continue

        # 读取现有规则
        try:
            with open(target_file, "r", encoding="utf-8") as f:
                content = yaml.safe_load(f) or {}
        except Exception:
            continue

        rules_list = content.get("rules", [])

        # 查找并更新目标规则
        new_rule = cand["new_rule"]
        rule_id = new_rule.get("id", target_rule)

        found = False
        for i, existing in enumerate(rules_list):
            if existing.get("id") == rule_id:
                # 合并：用 new_rule 的字段覆盖
                merged = {**existing, **new_rule}
                rules_list[i] = merged
                found = True
                break

        if not found:
            # 新规则，追加
            rules_list.append(new_rule)

        content["rules"] = rules_list

        # 写回
        with open(target_file, "w", encoding="utf-8") as f:
            yaml.dump(content, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

        # 标记 delta 为 PROMOTED
        for fp in deltas_dir.glob("*.yaml"):
            try:
                data = yaml.safe_load(fp.read_text(encoding="utf-8"))
                dd = data.get("delta", data)
                if dd.get("id") == cand.get("id"):
                    dd["operation"] = "PROMOTED"
                    dd["promoted_at"] = datetime.now().isoformat()
                    fp.write_text(
                        yaml.dump(data, allow_unicode=True, default_flow_style=False),
                        encoding="utf-8",
                    )
                    break
            except Exception:
                continue

        promoted_ids.append(cand.get("id", "?"))

    return promoted_ids


def _resolve_rule_file(rule_id: str, rules_dir: Path) -> Path | None:
    """根据规则 ID 推断所在的规则文件。"""
    if not rule_id.startswith("R-"):
        return None

    # R-S3-008 → stage3.yaml
    # R-S4-001 → stage4.yaml
    # R-PAT-* → 不写入（pattern 由 patterns/ 管理）
    parts = rule_id.split("-")
    if len(parts) >= 3 and parts[1].startswith("S") and parts[1][1:].isdigit():
        stage_num = parts[1][1:]
        candidate = rules_dir / f"stage{stage_num}.yaml"
        if candidate.exists():
            return candidate

    # 全局规则
    candidate = rules_dir / "00-global-safety.yaml"
    if candidate.exists():
        # 检查文件中是否有此规则
        try:
            with open(candidate, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            for r in data.get("rules", []):
                if r.get("id") == rule_id:
                    return candidate
        except Exception:
            pass

    return None


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
