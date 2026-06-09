"""ClipForge 自进化引擎 — 数据驱动的全自动规则优化。

人工操作：将各平台导出数据放入 workspace/sources/视频数据/YYYY-MM-DD/
然后运行: python scripts/auto_evolve.py

一切自动完成：
  Phase 1: 数据采集 + 匹配（调用 collect_performance.py）
  Phase 2: 批量分析（跨项目统计 + 相关性计算）
  Phase 3: 模式提炼（高分案例 → patterns/*.yaml）
  Phase 4: Delta 生成（数据洞察 → deltas/*.yaml，安全规则自动生效）
  Phase 5: 阈值校准（更新 thresholds.yaml）
"""
from __future__ import annotations
import sys
import io
import json
import statistics
import subprocess
from pathlib import Path
from datetime import datetime, timezone, date
from collections import defaultdict

# Windows 控制台 UTF-8
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# 路径解析
# auto_evolve.py 位于 .claude/commands/clipforge/scripts/
CLIPFORGE_ROOT = Path(__file__).parent.parent          # .claude/commands/clipforge/
PROJECT_ROOT = CLIPFORGE_ROOT.parent.parent.parent      # video-clipforge/
WORKSPACE = PROJECT_ROOT / "workspace"
sys.path.insert(0, str(CLIPFORGE_ROOT))

from engine.lib.delta import create_delta, save_delta, shadow_validate, DELTAS_DIR
from engine.lib.rule_parser import load_all_rules, RULES_DIR
from engine.lib.thresholds import load as load_thresholds, save as save_thresholds
from engine.lib.models import Severity
from engine.success_analyzer import auto_extract_from_performance, save_pattern, gate_validate_pattern


# ── 工具函数 ──────────────────────────────────────────────────────────────────

def _load_safe_traces() -> list[dict]:
    traces_dir = RULES_DIR.parent / "traces"
    traces: list[dict] = []
    if not traces_dir.exists():
        return traces
    for f in traces_dir.rglob("trace.json"):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            items = data if isinstance(data, list) else [data]
            traces.extend(items)
        except Exception:
            pass
    return [t for t in traces
            if t.get("result") and t.get("result", {}).get("gate_report") is not None]


def _spearman(x: list[float], y: list[float]) -> float:
    n = len(x)
    if n < 5:
        return 0.0
    sorted_x = sorted(range(n), key=lambda i: x[i])
    sorted_y = sorted(range(n), key=lambda i: y[i])
    rx = {sorted_x[i]: i for i in range(n)}
    ry = {sorted_y[i]: i for i in range(n)}
    d_sq = sum((rx[i] - ry[i]) ** 2 for i in range(n))
    return 1 - 6 * d_sq / (n * (n * n - 1))


def _classify_hook(text: str) -> str:
    if not text:
        return "empty"
    ht = text[:60]
    if any(w in ht for w in ["居然", "但", "不用", "也能", "反直觉", "砍掉", "翻车", "实测"]):
        return "contrarian"
    if any(w in ht for w in ["杀入", "冲上", "炸", "猛"]):
        return "action_number"
    if any(c.isdigit() for c in ht[:25]) and any(w in ht for w in ["涨", "最高", "项目", "千星"]):
        return "number_anchor"
    return "plain"


def _classify_mode(proj_dir: Path) -> str:
    name = proj_dir.name.lower()
    if "trending" in name and "weekly" not in name:
        return "daily_trending"
    if "weekly" in name:
        return "weekly"
    if any(w in name for w in ["deep", "service", "report", "compare", "value"]):
        return "special_topic"
    ns_file = proj_dir / "narration_segments.json"
    if ns_file.exists():
        try:
            ns = json.loads(ns_file.read_text("utf-8"))
            if isinstance(ns, list):
                if len(ns) <= 5:
                    return "short"
                if len(ns) <= 8:
                    return "standard"
                return "long"
        except Exception:
            pass
    return "unknown"


def _make_delta(operation, source, confidence, target_rule_id=None,
                new_rule_raw=None, modified_fields=None, reason=None,
                rules=None, traces=None) -> dict:
    d = create_delta(
        operation=operation, source=source, confidence=confidence,
        target_rule_id=target_rule_id, new_rule_raw=new_rule_raw,
        modified_fields=modified_fields, reason=reason,
    )
    safe_traces = traces or []
    validation = shadow_validate(d, rules or [], safe_traces)
    d["shadow_validation"] = validation
    d["requires_human_review"] = not validation.get("safe", True)
    return d


# ── Phase 实现 ────────────────────────────────────────────────────────────────

class AutoEvolve:
    def __init__(self):
        self.rules = load_all_rules(RULES_DIR)
        self.traces = _load_safe_traces()
        self.projects: list[dict] = []
        self.report_lines: list[str] = []
        self.deltas_saved: list[str] = []
        self.patterns_saved: list[str] = []
        self.thresholds_changed: list[str] = []

    def _log(self, msg: str):
        self.report_lines.append(msg)
        print(msg)

    # ── Phase 1: 数据采集 ─────────────────────────────────────────────────────

    def phase1_collect(self) -> str:
        self._log("Phase 1: 数据采集 + 匹配")
        script = Path(__file__).parent / "collect_performance.py"
        result = subprocess.run(
            [sys.executable, str(script), "--scan", "--backfill"],
            capture_output=True, text=True, encoding="utf-8",
            cwd=str(PROJECT_ROOT),
        )
        output = result.stdout or result.stderr
        # 提取匹配摘要行
        for line in output.split("\n"):
            if "matched" in line.lower() or "匹配" in line:
                self._log(f"  {line.strip()}")
        return output

    # ── Phase 2: 批量分析 ─────────────────────────────────────────────────────

    def phase2_analyze(self) -> dict:
        self._log("\nPhase 2: 批量分析")

        for pf in sorted(WORKSPACE.rglob("performance.json")):
            proj = pf.parent
            try:
                data = json.loads(pf.read_text("utf-8"))
            except Exception:
                continue
            plats = data.get("platforms", {})
            douyin = plats.get("douyin", {}) if isinstance(plats, dict) else {}

            hook_text = ""
            for src in [
                lambda: json.loads((proj / "narration_segments.json").read_text("utf-8"))[0].get("text", ""),
                lambda: (proj / "narration.txt").read_text("utf-8").split("\n")[0],
            ]:
                try:
                    hook_text = src()
                    if hook_text:
                        break
                except Exception:
                    continue

            self.projects.append({
                "name": proj.name,
                "plays": douyin.get("plays", 0) or 0,
                "c5s": douyin.get("completion_5s_rate", 0) or 0,
                "completion": douyin.get("completion_rate", 0) or 0,
                "save_rate": douyin.get("save_rate", 0) or 0,
                "share_rate": douyin.get("share_rate", 0) or 0,
                "like_rate": douyin.get("like_rate", 0) or 0,
                "hook_type": _classify_hook(hook_text),
                "hook_text": hook_text[:80],
                "content_mode": _classify_mode(proj),
                "snapshots": sorted(
                    [s for s in data.get("snapshots", [])
                     if s.get("platform") == "douyin" and s.get("plays")],
                    key=lambda s: s.get("source_date", ""),
                ),
            })

        valid = [p for p in self.projects if p["plays"] > 0]
        self._log(f"  有效项目: {len(valid)}/{len(self.projects)}")

        insights: dict = {"valid_count": len(valid)}

        # Hook 类型分析
        hook_groups = defaultdict(list)
        for p in valid:
            hook_groups[p["hook_type"]].append(p)
        insights["hook_analysis"] = {}
        for ht, items in sorted(hook_groups.items(),
                                key=lambda x: -statistics.mean(p["plays"] for p in x[1])):
            avg_plays = statistics.mean(p["plays"] for p in items)
            avg_c5s = statistics.mean(p["c5s"] for p in items)
            insights["hook_analysis"][ht] = {
                "count": len(items),
                "avg_plays": avg_plays,
                "avg_c5s": avg_c5s,
            }
            self._log(f"  Hook {ht:20s}: N={len(items):2d}  均播放={avg_plays:>10,.0f}  5s={avg_c5s:.1%}")

        # 内容模式分析
        mode_groups = defaultdict(list)
        for p in valid:
            mode_groups[p["content_mode"]].append(p)
        insights["mode_analysis"] = {}
        for mode, items in sorted(mode_groups.items(),
                                  key=lambda x: -statistics.mean(p["plays"] for p in x[1])):
            avg_plays = statistics.mean(p["plays"] for p in items)
            avg_c5s = statistics.mean(p["c5s"] for p in items)
            insights["mode_analysis"][mode] = {
                "count": len(items),
                "avg_plays": avg_plays,
                "avg_c5s": avg_c5s,
            }

        # 5s 完播率分段
        c5s_buckets = {">=44%": [], "38-44%": [], "<38%": []}
        for p in valid:
            if p["c5s"] >= 0.44:
                c5s_buckets[">=44%"].append(p)
            elif p["c5s"] >= 0.38:
                c5s_buckets["38-44%"].append(p)
            else:
                c5s_buckets["<38%"].append(p)
        insights["c5s_analysis"] = {}
        for bucket, items in c5s_buckets.items():
            if items:
                avg_plays = statistics.mean(p["plays"] for p in items)
                insights["c5s_analysis"][bucket] = {"count": len(items), "avg_plays": avg_plays}
                self._log(f"  5s完播 {bucket:8s}: N={len(items):2d}  均播放={avg_plays:>10,.0f}")

        # 收藏率分析
        high_save = [p for p in valid if p["save_rate"] > 0.03]
        low_save = [p for p in valid if p["save_rate"] < 0.01]
        if high_save and low_save:
            hs_avg = statistics.mean(p["plays"] for p in high_save)
            ls_avg = statistics.mean(p["plays"] for p in low_save)
            insights["save_ratio"] = hs_avg / max(ls_avg, 1)
            self._log(f"  收藏率: 高(>3%)均播放={hs_avg:,.0f} vs 低(<1%)={ls_avg:,.0f} ({hs_avg/max(ls_avg,1):.1f}x)")

        # 增长分析
        growth_data = []
        for p in valid:
            if len(p["snapshots"]) >= 2:
                first, last = p["snapshots"][0], p["snapshots"][-1]
                fp, lp = first.get("plays", 0), last.get("plays", 0)
                d1, d2 = first.get("source_date", ""), last.get("source_date", "")
                try:
                    days = (date.fromisoformat(d2) - date.fromisoformat(d1)).days
                    if fp > 0 and days > 0:
                        growth_data.append({
                            "daily_growth": (lp - fp) / days,
                            "c5s": p["c5s"],
                            "save_rate": p["save_rate"],
                        })
                except Exception:
                    pass

        if growth_data:
            growing = [g for g in growth_data if g["daily_growth"] > 100]
            stalled = [g for g in growth_data if g["daily_growth"] < 10]
            if growing and stalled:
                gc = statistics.mean(g["c5s"] for g in growing)
                sc = statistics.mean(g["c5s"] for g in stalled)
                insights["growth_c5s_gap"] = gc - sc
                self._log(f"  增长组5s={gc:.1%} vs 停滞组={sc:.1%} (差{gc-sc:.1%})")

        # Spearman 相关
        if len(valid) >= 10:
            plays = [float(p["plays"]) for p in valid]
            c5s = [float(p["c5s"]) for p in valid]
            saves = [float(p["save_rate"]) for p in valid]
            insights["spearman_c5s"] = _spearman(c5s, plays)
            insights["spearman_save"] = _spearman(saves, plays)
            self._log(f"  Spearman: c5s→播放={_spearman(c5s, plays):.3f}  收藏→播放={_spearman(saves, plays):.3f}")

        return insights

    # ── Phase 3: 模式提炼 ─────────────────────────────────────────────────────

    def phase3_patterns(self, insights: dict) -> list[dict]:
        self._log("\nPhase 3: 模式提炼")

        # 构造 success_analyzer 需要的输入
        perf_data = []
        for p in self.projects:
            if p["plays"] > 0:
                perf_data.append({
                    "platform": "douyin",
                    "plays": p["plays"],
                    "completion_5s_rate": p["c5s"],
                    "completion_rate": p["completion"],
                    "hook_type": p["hook_type"],
                    "title": p["name"],
                })

        # 调用已有的自动提取逻辑
        new_patterns = auto_extract_from_performance(perf_data, min_samples=3)

        saved = []
        for pat in new_patterns:
            check = gate_validate_pattern(pat)
            if check["valid"]:
                path = save_pattern(pat)
                saved.append(pat["id"])
                self._log(f"  新增 pattern: {pat['id']} (weight={pat['as_preference']['weight']})")

        # 从批量分析补充高分 hook 模式
        hook_analysis = insights.get("hook_analysis", {})
        for ht, data in hook_analysis.items():
            if data["avg_plays"] > 20000 and data["count"] >= 3 and ht not in ("empty", "plain"):
                pat_id = f"P-hook-{ht}"
                existing = (CLIPFORGE_ROOT / "patterns" / f"{pat_id}.yaml").exists()
                if not existing:
                    pat = {
                        "id": pat_id,
                        "seed": False,
                        "category": "github",
                        "skill_scope": "stage3-scenes",
                        "description": f"Hook {ht} 模式: {data['count']} 条视频，均播放 {data['avg_plays']:.0f}",
                        "evidence": {
                            "sample_size": data["count"],
                            "avg_plays": round(data["avg_plays"]),
                            "avg_c5s": round(data["avg_c5s"], 3),
                            "confidence": min(0.5 + data["count"] * 0.1, 0.95),
                        },
                        "as_preference": {
                            "text": f"hook 使用 {ht} 模式（{data['count']} 条，均播放 {data['avg_plays']:.0f}，5s {data['avg_c5s']:.1%}）",
                            "weight": "HIGH" if data["avg_plays"] > 30000 else "MEDIUM",
                            "source_pattern": pat_id,
                        },
                    }
                    check = gate_validate_pattern(pat)
                    if check["valid"]:
                        save_pattern(pat)
                        saved.append(pat_id)
                        self._log(f"  新增 pattern: {pat_id}")

        if not saved:
            self._log("  无新 pattern")
        self.patterns_saved = saved
        return saved

    # ── Phase 4: Delta 生成 ───────────────────────────────────────────────────

    def phase4_deltas(self, insights: dict) -> list[str]:
        self._log("\nPhase 4: Delta 生成")
        saved_ids: list[str] = []
        hook_analysis = insights.get("hook_analysis", {})
        c5s_analysis = insights.get("c5s_analysis", {})
        valid_count = insights.get("valid_count", 0)

        # 规则 1: Hook 类型倍率检查 — 如果 plain > contrarian 或 plain > action_number
        # 说明现有规则不够强，生成/加强 Delta
        plain_plays = hook_analysis.get("plain", {}).get("avg_plays", 0)
        action_plays = hook_analysis.get("action_number", {}).get("avg_plays", 0)
        contrarian_plays = hook_analysis.get("contrarian", {}).get("avg_plays", 0)

        if action_plays > plain_plays * 2 and valid_count >= 10:
            ratio = action_plays / max(plain_plays, 1)
            d = _make_delta(
                operation="ADDED",
                source="auto_evolve",
                confidence=min(0.7 + valid_count * 0.005, 0.90),
                target_rule_id="R-S3-008",
                new_rule_raw={
                    "id": "R-S3-008",
                    "type": "FORBIDDEN_ACTION",
                    "pattern": "hook 场景第一句不含动作词/数字锚定/反直觉陈述",
                    "positive": f"hook 第一句必须包含至少一个：(a)动作词（杀入/冲上/炸）(b)量化数字 (c)反直觉转折。动作hook均播放{action_plays:.0f}是平铺{plain_plays:.0f}的{ratio:.1f}x",
                    "guardrail": "segments[0].text 前 15 字不包含任何 hook_anchors 关键词或数字",
                    "detection": {"keywords": [], "semantic_check": True},
                    "severity": "HARD",
                    "class": "EXPERIENTIAL",
                    "scope": "SKILL",
                    "skill": "stage3-scenes",
                    "source": f"auto_evolve: N={valid_count}, action={action_plays:.0f} vs plain={plain_plays:.0f} ({ratio:.1f}x)",
                },
                reason=f"数据驱动: action_number 均播放{action_plays:.0f} vs plain {plain_plays:.0f} ({ratio:.1f}x)",
                rules=self.rules, traces=self.traces,
            )
            path = save_delta(d, DELTAS_DIR)
            saved_ids.append(path.name)
            self._log(f"  {'自动生效' if not d.get('requires_human_review') else '待审核'}: {path.name}")

        # 规则 2: 收藏率与增长关联
        save_ratio = insights.get("save_ratio", 0)
        growth_gap = insights.get("growth_c5s_gap", 0)
        if save_ratio > 3 and valid_count >= 10:
            d = _make_delta(
                operation="ADDED",
                source="auto_evolve",
                confidence=min(0.7 + valid_count * 0.005, 0.85),
                target_rule_id="R-PAT-high-save-rate",
                new_rule_raw={
                    "id": "R-PAT-high-save-rate",
                    "type": "REQUIRED_METHOD",
                    "pattern": "内容缺少'值得收藏'的实用信息",
                    "positive": f"视频中至少 1 个场景必须包含可操作的实用信息。高收藏(>3%)均播放是低收藏(<1%)的{save_ratio:.1f}x",
                    "guardrail": "所有场景均为泛泛描述，无具体工具名/数据/步骤",
                    "detection": {"keywords": [], "semantic_check": True},
                    "severity": "SOFT",
                    "class": "EXPERIENTIAL",
                    "scope": "SKILL",
                    "skill": "stage3-scenes",
                    "source": f"auto_evolve: 高收藏/低收藏播放比={save_ratio:.1f}x, 增长5s差={growth_gap:.1%}",
                },
                reason=f"收藏率倍率={save_ratio:.1f}x，是长尾增长核心指标",
                rules=self.rules, traces=self.traces,
            )
            path = save_delta(d, DELTAS_DIR)
            saved_ids.append(path.name)
            self._log(f"  {'自动生效' if not d.get('requires_human_review') else '待审核'}: {path.name}")

        if not saved_ids:
            self._log("  无新 Delta（现有规则已充分）")
        self.deltas_saved = saved_ids
        return saved_ids

    # ── Phase 5: 阈值校准 ─────────────────────────────────────────────────────

    def phase5_calibrate(self, insights: dict) -> list[str]:
        self._log("\nPhase 5: 阈值校准")
        changed: list[str] = []

        valid = [p for p in self.projects if p["plays"] > 0]
        if len(valid) < 10:
            self._log("  样本不足 (<10)，跳过阈值校准")
            return changed

        thresholds = load_thresholds()

        # 校准 5s_completion_low: 找播放量最佳分隔点（最低 0.36，防止过拟合）
        c5s_values = [(p["c5s"], p["plays"]) for p in valid if p["c5s"] > 0]
        if len(c5s_values) >= 15:
            best_t, best_ratio = 0.38, 1.0
            for t_candidate in [i / 100 for i in range(36, 52)]:
                high = [plays for c5s, plays in c5s_values if c5s >= t_candidate]
                low = [plays for c5s, plays in c5s_values if c5s < t_candidate]
                if len(high) >= 5 and len(low) >= 5:
                    ratio = statistics.mean(high) / max(statistics.mean(low), 1)
                    if ratio > best_ratio:
                        best_ratio = ratio
                        best_t = round(t_candidate, 2)

            old_t = thresholds["douyin"]["5s_completion_low"]
            # 约束：新阈值不能比旧值低超过 0.02（防止过拟合）
            if best_t != old_t and best_ratio > 2.0 and best_t >= old_t - 0.02:
                thresholds["douyin"]["5s_completion_low"] = best_t
                changed.append(f"5s_completion_low: {old_t} → {best_t} (分隔比={best_ratio:.1f}x)")
                self._log(f"  5s_completion_low: {old_t} → {best_t} (分隔比={best_ratio:.1f}x)")

        # 校准 save_rate_high: 找增长速度最佳分隔点
        save_values = [(p["save_rate"], p["plays"]) for p in valid if p["save_rate"] > 0]
        if len(save_values) >= 15:
            best_st, best_sr = 0.02, 1.0
            for t_candidate in [i / 1000 for i in range(10, 50)]:
                high = [plays for sr, plays in save_values if sr >= t_candidate]
                low = [plays for sr, plays in save_values if sr < t_candidate]
                if len(high) >= 5 and len(low) >= 5:
                    ratio = statistics.mean(high) / max(statistics.mean(low), 1)
                    if ratio > best_sr:
                        best_sr = ratio
                        best_st = round(t_candidate, 3)

            old_st = thresholds["douyin"].get("save_rate_high", 0)
            if best_sr > 2.0:
                thresholds["douyin"]["save_rate_high"] = best_st
                if best_st != old_st:
                    changed.append(f"save_rate_high: {old_st} → {best_st} (分隔比={best_sr:.1f}x)")
                    self._log(f"  save_rate_high: {old_st} → {best_st} (分隔比={best_sr:.1f}x)")

        # 同步 success 阈值
        if thresholds["douyin"]["5s_completion_low"] != thresholds["success"]["douyin"]["medium"]:
            thresholds["success"]["douyin"]["medium"] = thresholds["douyin"]["5s_completion_low"]
            changed.append("success.douyin.medium 同步更新")

        if changed:
            thresholds["calibration"]["last_updated"] = datetime.now(timezone.utc).isoformat()
            thresholds["calibration"]["sample_size"] = len(valid)
            save_thresholds(thresholds)
        else:
            self._log("  阈值无需更新")

        self.thresholds_changed = changed
        return changed

    # ── 主入口 ────────────────────────────────────────────────────────────────

    def run(self):
        self._log("=" * 60)
        self._log(f"ClipForge 自进化报告 — {datetime.now(timezone.utc).strftime('%Y-%m-%d')}")
        self._log("=" * 60)

        # Phase 1
        self.phase1_collect()

        # Phase 2
        insights = self.phase2_analyze()

        # Phase 3
        self.phase3_patterns(insights)

        # Phase 4
        self.phase4_deltas(insights)

        # Phase 5
        self.phase5_calibrate(insights)

        # 汇总
        self._log("\n" + "=" * 60)
        self._log("汇总")
        self._log("=" * 60)
        self._log(f"  分析项目: {insights.get('valid_count', 0)}")
        self._log(f"  新增 Pattern: {len(self.patterns_saved)}")
        self._log(f"  新增 Delta: {len(self.deltas_saved)}")
        self._log(f"  阈值变更: {len(self.thresholds_changed)}")
        for c in self.thresholds_changed:
            self._log(f"    {c}")

        return {
            "projects_analyzed": insights.get("valid_count", 0),
            "patterns_created": self.patterns_saved,
            "deltas_created": self.deltas_saved,
            "thresholds_changed": self.thresholds_changed,
        }


def main():
    evolver = AutoEvolve()
    result = evolver.run()

    # 保存报告
    report_dir = WORKSPACE / "sources"
    report_dir.mkdir(parents=True, exist_ok=True)
    report_file = report_dir / f"evolution-report-{datetime.now(timezone.utc).strftime('%Y%m%d')}.json"
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"\n报告已保存: {report_file.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
