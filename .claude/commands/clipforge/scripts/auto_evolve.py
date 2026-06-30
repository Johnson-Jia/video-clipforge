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
from collections import defaultdict, Counter
import os

# Windows 控制台 UTF-8
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# 路径解析
# auto_evolve.py 位于 .claude/commands/clipforge/scripts/
CLIPFORGE_ROOT = Path(__file__).parent.parent          # .claude/commands/clipforge/
sys.path.insert(0, str(CLIPFORGE_ROOT))
from engine.lib.data_paths import WORKSPACE_ROOT as PROJECT_ROOT  # 四级回退(env>git>config>cwd)
WORKSPACE = PROJECT_ROOT / "workspace"

# 为 attribution._classify_hook_type 提供分类上下文（hook_anchors 读 CLIPFORGE_CATEGORY）
# auto_evolve 批量分析的数据均为 github 分类，设默认值不覆盖已显式设置的值
os.environ.setdefault("CLIPFORGE_CATEGORY", "github")

from engine.lib.delta import create_delta, save_delta, shadow_validate, DELTAS_DIR
from engine.lib.rule_parser import load_all_rules, RULES_DIR
from engine.lib.thresholds import load as load_thresholds, save as save_thresholds
from engine.lib.models import Severity
from engine.success_analyzer import (
    auto_extract_from_performance, save_pattern, gate_validate_pattern,
    _platform_success_score, _is_platform_success,
)
# 统一 hook 分类口径：复用 attribution 权威分类器（5类），废弃本地 _classify_hook（4类，口径冲突）
from engine.attribution import _classify_hook_type as _classify_hook
from engine.lib.data_paths import traces_dir as _evolution_traces_dir, pattern_file as _pattern_file, auto_patterns_dir as _auto_patterns_dir
from engine.publish_time import aggregate_publish_time, analyze_publish_time, build_publish_advice
from engine.recency import project_data_weight, weighted_mean


# ── 工具函数 ──────────────────────────────────────────────────────────────────

def _load_safe_traces() -> list[dict]:
    traces_dir = _evolution_traces_dir()
    traces: list[dict] = []
    if not traces_dir.exists():
        return traces
    for f in traces_dir.rglob("trace.json"):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            items = data if isinstance(data, list) else [data]
            for item in items:
                # test 目录隔离：test trace 不进回归样本（与 freshness.py 对齐）
                if "test" in (item.get("project_dir") or "").split("/"):
                    continue
                traces.append(item)
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


def _wmean(items: list[dict], key: str) -> float:
    """加权均值（用 data_weight，缺省 1.0 等权）。近期数据权重高，校准偏向新表现。"""
    return weighted_mean([p.get(key, 0.0) for p in items],
                         [p.get("data_weight", 1.0) for p in items])


# _classify_hook 已迁移至 engine.attribution._classify_hook_type（顶部 import as _classify_hook）
# 统一归因/自进化两套口径，消除 P-hook-action_number 等 pattern 来自旧 4 类口径的冲突


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


# ── 跨平台共识引擎辅助（题材/封面/旁白四维分析）─────────────────────────────

def _percentile_rank(pool: list[float], value: float) -> float:
    """value 在 pool（某平台所有项目 plays）中的分位数 (0-1)。消除平台量级差异。"""
    if not pool:
        return 0.0
    below = sum(1 for v in pool if v < value)
    return round(below / len(pool), 4)


def _project_domain(lang: str, topics: list, desc: str) -> str:
    """单个 GitHub 项目 → 领域分类（题材分类器基础单元）。"""
    lang = (lang or "").lower()
    blob = " ".join(topics or []).lower() + " " + (desc or "").lower()
    if any(k in blob for k in ["ai", "llm", "gpt", "agent", "model", "transformer",
                                "rag", "deep-learning", "machine-learning", "智能"]):
        return "AI/智能体"
    if any(k in blob for k in ["security", "privacy", "crypto", "vuln", "pentest", "安全"]):
        return "安全/隐私"
    if any(k in blob for k in ["react", "vue", "frontend", "ui-component", "css", "tailwind"]) \
            or lang in ("javascript", "typescript"):
        return "前端/Web"
    if lang in ("rust", "go", "c", "c++", "zig"):
        return "系统/底层"
    if any(k in blob for k in ["cli", "tool", "devtool", "productivity", "terminal", "工具"]):
        return "开发工具"
    if any(k in blob for k in ["database", "sql", "etl", "pipeline"]) or "data" in blob:
        return "数据/后端"
    if lang == "python":
        return "Python/通用"
    return "其他"


def _classify_topic(proj_dir: Path) -> str:
    """视频题材分类：读 raw_trending.json，取所有项目领域众数。最大领域占比<50%记为'综合盘点'。"""
    rt = proj_dir / "raw_trending.json"
    if not rt.exists():
        name = proj_dir.name.lower()
        if "weekly" in name:
            return "周榜综合"
        if any(w in name for w in ["deep", "service", "report", "compare"]):
            return "专题深度"
        return "unknown"
    try:
        d = json.loads(rt.read_text("utf-8"))
        projects = d.get("projects", []) if isinstance(d, dict) else (d if isinstance(d, list) else [])
    except Exception:
        return "unknown"
    domains = [_project_domain(p.get("language"), p.get("topics"), p.get("description"))
               for p in projects if isinstance(p, dict)]
    domains = [x for x in domains if x]
    if not domains:
        return "unknown"
    top_domain, top_count = Counter(domains).most_common(1)[0]
    return top_domain if top_count / len(domains) >= 0.5 else "综合盘点"


def _read_narration(proj_dir: Path) -> dict:
    """读 narration_segments.json（兼容 list 旧格式 / dict 新格式）。
    返回 {hook_text, attrs}。attrs 含结构化字段（仅新格式 segment 有 scene_type/emotion 等）。"""
    result = {"hook_text": "", "attrs": None}
    ns_file = proj_dir / "narration_segments.json"
    if ns_file.exists():
        try:
            ns = json.loads(ns_file.read_text("utf-8"))
            segs = ns if isinstance(ns, list) else (ns.get("segments", []) if isinstance(ns, dict) else [])
            if segs and isinstance(segs, list):
                first = segs[0] if isinstance(segs[0], dict) else {}
                result["hook_text"] = (first.get("narration_segment") or first.get("text") or "")[:80]
                has_struct = any(first.get(k) for k in ("scene_type", "emotion", "humor_type", "contrarian_angle"))
                scene_types = [s.get("scene_type") for s in segs if isinstance(s, dict) and s.get("scene_type")]
                # 只收 str 类型 emotion（防历史数据 emotion 误存 float/int 致 dominant_emotion 非 str，
                # 2026-06-30 auto_evolve L594 {emo:12s} 崩溃根因；float/int/None 一律排除 → dominant 必 str）
                emotions = [s.get("emotion") for s in segs if isinstance(s, dict) and isinstance(s.get("emotion"), str)]
                humor = sum(1 for s in segs if isinstance(s, dict) and s.get("humor_type"))
                contrarian = sum(1 for s in segs if isinstance(s, dict) and s.get("contrarian_angle"))
                result["attrs"] = {
                    "n_segments": len(segs),
                    "has_struct": has_struct,
                    "dominant_scene": Counter(scene_types).most_common(1)[0][0] if scene_types else None,
                    "dominant_emotion": Counter(emotions).most_common(1)[0][0] if emotions else None,
                    "humor_density": round(humor / len(segs), 2),
                    "contrarian_density": round(contrarian / len(segs), 2),
                }
        except Exception:
            pass
    if not result["hook_text"]:
        try:
            result["hook_text"] = (proj_dir / "narration.txt").read_text("utf-8").split("\n")[0][:80]
        except Exception:
            pass
    return result


def _read_cover_attrs(proj_dir: Path) -> dict:
    """读 cover_params.json → 封面属性（封面维度分析输入）。无文件返回空 dict。"""
    cp_file = proj_dir / "cover_params.json"
    if not cp_file.exists():
        return {}
    try:
        cp = json.loads(cp_file.read_text("utf-8"))
    except Exception:
        return {}
    title = cp.get("title", [])
    styles = [t.get("style") for t in title if isinstance(t, dict) and t.get("style")] if isinstance(title, list) else []
    def _to_float(v):
        try:
            return float(v) if v else 0.0
        except (TypeError, ValueError):
            return 0.0
    # 兼容两种 cover_params.json 格式：旧顶层 accent_warm / 新 colors.accent_warm
    colors = cp.get("colors") or {}
    warm, cool = bool(cp.get("accent_warm") or colors.get("accent_warm")), \
                bool(cp.get("accent_cool") or colors.get("accent_cool"))
    color_bias = "冷暖对比" if (warm and cool) else ("暖色主调" if warm else ("冷色主调" if cool else "未知"))
    glow = _to_float(cp.get("glow_warm_opacity") or colors.get("glow_warm_opacity")) + \
           _to_float(cp.get("glow_cool_opacity") or colors.get("glow_cool_opacity"))
    return {
        "color_bias": color_bias,
        "title_styles": ",".join(sorted(set(styles))) if styles else "none",
        "glow_intensity": "high" if glow > 0.3 else ("medium" if glow > 0.15 else "low"),
        "n_cards": len(cp.get("cards", [])) if isinstance(cp.get("cards"), list) else 0,
        "orientation": cp.get("orientation", ""),
    }


def _read_injected(proj_dir: Path) -> list[str]:
    """读项目 injected_patterns.json → 本次注入的 pattern id 列表（采纳追溯基建）。
    inject.py --project-dir 写入；无文件返回空列表。"""
    fp = proj_dir / "injected_patterns.json"
    if not fp.exists():
        return []
    try:
        data = json.loads(fp.read_text("utf-8"))
        return [p.get("id", "") for p in (data.get("injected_patterns") or []) if p.get("id")]
    except Exception:
        return []


def _read_score_freshness(proj_dir: Path) -> float | None:
    """读项目 score_report.json 的 freshness_score（项3 学习层数据源）。"""
    try:
        sr = json.loads((proj_dir / "score_report.json").read_text("utf-8"))
        return (sr.get("freshness") or {}).get("freshness_score")
    except Exception:
        return None


def _read_bgm_source(proj_dir: Path) -> str | None:
    """读项目 segment_durations.json 的 meta.bgm_source（BGM 文件名）。"""
    try:
        meta = (json.loads((proj_dir / "segment_durations.json").read_text("utf-8"))).get("meta") or {}
        return meta.get("bgm_source")
    except Exception:
        return None


def _classify_bgm_style(bgm_source: str | None) -> str:
    """BGM 文件名→风格（回归归因用，量化'BGM 风格→播放'是否显著）。"""
    if not bgm_source:
        return "unknown"
    name = str(bgm_source).lower()
    for key, style in (
        ("bold-energetic", "energetic"), ("neon-electric", "electronic"),
        ("cinematic", "cinematic"), ("epic-trailer", "epic"),
        ("motivational", "motivational"), ("clean-corporate", "corporate"),
        ("chill-lofi", "lofi"),
    ):
        if key in name:
            return style
    return "other"


def _write_freshness_feedback(analysis: dict) -> None:
    """写 freshness 学习层反馈（供 exploration.decide 读，调 explore/exploit）。B 闭环。"""
    try:
        import yaml
        from engine.lib.data_paths import auto_patterns_dir
        fp = auto_patterns_dir().parent / "freshness_feedback.yaml"
        fp.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "recommendation": analysis.get("recommendation"),
            "fresh_but_low_ratio": analysis.get("fresh_but_low_ratio"),
            "similar_but_high_ratio": analysis.get("similar_but_high_ratio"),
            "sample_size": analysis.get("sample_size"),
        }
        fp.write_text(yaml.dump(payload, allow_unicode=True, default_flow_style=False), encoding="utf-8")
    except Exception as e:
        print(f"[auto_evolve] freshness_feedback 写入失败: {e}", file=sys.stderr)


def _make_delta(operation, source, confidence, target_rule_id=None,
                new_rule_raw=None, modified_fields=None, reason=None,
                rules=None, traces=None, observation_days=3, category=None) -> dict:
    d = create_delta(
        operation=operation, source=source, confidence=confidence,
        target_rule_id=target_rule_id, new_rule_raw=new_rule_raw,
        modified_fields=modified_fields, reason=reason,
        category=category,
    )
    safe_traces = traces or []
    validation = shadow_validate(d, rules or [], safe_traces)
    d["shadow_validation"] = validation
    d["requires_human_review"] = not validation.get("safe", True)
    # auto_evolve 基于大数据统计，设置短观察期
    dd = d.get("delta", d)
    dd["observation_days"] = observation_days
    return d


def _cleanup_old_deltas(target_rule: str, keep_filename: str) -> list[str]:
    """删除同 target_rule 的旧 auto_evolve Delta 文件（保留刚创建的）。"""
    removed = []
    for fp in DELTAS_DIR.glob("D-*.yaml"):
        if fp.name == keep_filename:
            continue
        try:
            import yaml
            data = yaml.safe_load(fp.read_text(encoding="utf-8"))
            dd = data.get("delta", data)
            if dd.get("target_rule") == target_rule and "auto_evolve" in dd.get("source", ""):
                fp.unlink()
                removed.append(fp.name)
        except Exception:
            pass
    return removed


# ── Phase 实现 ────────────────────────────────────────────────────────────────

class AutoEvolve:
    def __init__(self):
        self.rules = load_all_rules(RULES_DIR)
        self.traces = _load_safe_traces()
        self.projects: list[dict] = []
        self.report_lines: list[str] = []
        self.deltas_saved: list[str] = []
        self.patterns_saved: list[str] = []
        self.patterns_revalidated: list[str] = []
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

        # ── Pass 1: 收集每项目原始多平台数据 + 内容属性（题材/封面/旁白）──
        raw_projects: list[dict] = []
        for pf in sorted(WORKSPACE.rglob("performance.json")):
            proj = pf.parent
            if "test" in proj.parts:
                continue  # test 目录隔离，不进回归/训练样本
            try:
                data = json.loads(pf.read_text("utf-8"))
            except Exception:
                continue
            plats = data.get("platforms", {})
            plats = plats if isinstance(plats, dict) else {}
            narr = _read_narration(proj)
            per_plat = {}
            for pname, pdata in plats.items():
                if isinstance(pdata, dict) and (pdata.get("plays") or pdata.get("impressions")):
                    per_plat[pname] = pdata
            _pt = aggregate_publish_time(per_plat)
            raw_projects.append({
                "name": proj.name,
                "per_plat": per_plat,
                "hook_text": narr["hook_text"],
                "hook_type": _classify_hook(narr["hook_text"]),
                "content_mode": _classify_mode(proj),
                "topic": _classify_topic(proj),
                "cover_attrs": _read_cover_attrs(proj),
                "narration_attrs": narr["attrs"],
                "snapshots": data.get("snapshots", []),
                "injected": _read_injected(proj),
                "freshness": _read_score_freshness(proj),
                "bgm_source": (_bgm := _read_bgm_source(proj)),
                "bgm_style": _classify_bgm_style(_bgm),
                "publish_hour": _pt["publish_hour"],
                "publish_weekday": _pt["publish_weekday"],
                "data_weight": project_data_weight(data.get("snapshots", []), date.today().isoformat()),
            })

        # ── 各平台 plays 池（分位数排名，消除平台量级差异）──
        plat_pools: dict[str, list[float]] = defaultdict(list)
        for rp in raw_projects:
            for pname, pdata in rp["per_plat"].items():
                plat_pools[pname].append(float(pdata.get("plays", 0) or 0))

        # ── Pass 2: 跨平台综合分（不绑单一平台）──
        # reach_composite = 各平台 plays 分位均值（题材/封面受众广度信号）
        # quality_composite = 各平台原生 success_score 均值（话术/旁白留存信号）
        for rp in raw_projects:
            reach_pcts, succ_flags = [], []
            c5s_v, comp_v, save_v, share_v, like_v = [], [], [], [], []
            for pname, pdata in rp["per_plat"].items():
                plays = float(pdata.get("plays", 0) or 0)
                reach_pcts.append(_percentile_rank(plat_pools.get(pname, []), plays))
                if _is_platform_success(pdata):
                    succ_flags.append(pname)
                if pdata.get("completion_5s_rate") is not None:
                    c5s_v.append(pdata["completion_5s_rate"])
                comp_val = pdata.get("completion_rate") or pdata.get("avg_play_progress")
                if comp_val is not None:
                    comp_v.append(comp_val)
                for key, bucket in (("save_rate", save_v), ("share_rate", share_v), ("like_rate", like_v)):
                    if pdata.get(key) is not None:
                        bucket.append(pdata[key])
            rp["n_platforms"] = len(rp["per_plat"])
            rp["reach_composite"] = round(statistics.mean(reach_pcts), 4) if reach_pcts else 0.0
            rp["quality_composite"] = round(
                statistics.mean([_platform_success_score(pd) for pd in rp["per_plat"].values()]), 4
            ) if rp["per_plat"] else 0.0
            rp["reach_consensus"] = sum(1 for p in reach_pcts if p >= 0.7)
            rp["quality_consensus"] = len(succ_flags)
            rp["plays"] = rp["reach_composite"]      # 向后兼容：题材/封面信号（0-1）
            rp["c5s"] = rp["quality_composite"]      # 向后兼容：话术/旁白信号（0-1）
            rp["completion"] = round(statistics.mean(comp_v), 4) if comp_v else 0.0
            rp["save_rate"] = round(statistics.mean(save_v), 4) if save_v else 0.0
            rp["share_rate"] = round(statistics.mean(share_v), 4) if share_v else 0.0
            rp["like_rate"] = round(statistics.mean(like_v), 4) if like_v else 0.0

        self.projects = raw_projects

        valid = [p for p in self.projects if p["n_platforms"] > 0]
        self._log(f"  有效项目: {len(valid)}/{len(self.projects)}（多平台综合）")
        consensus_hits = [p for p in valid if p["reach_consensus"] >= 2]
        self._log(f"  跨平台共识爆款(≥2平台前30%): {len(consensus_hits)}")

        # 大盘基线：当前全体有效项目的受众广度均值（相对衰减的基准，phase3.5 复用）
        self.market_avg = round(_wmean(valid, "reach_composite"), 4) if valid else 0.0

        insights: dict = {"valid_count": len(valid), "market_avg_reach": self.market_avg}

        # ── 项3: freshness_signal 学习层（机制就位，数据驱动；<min_samples 空转）──
        # freshness 高=explore(冷门维度)，低=exploit。reach_composite 为受众广度(0-1)。
        # 高freshness+低reach=explore方向错 → analyze 建议收敛 explore 目标维度。
        # 注：只迭代 valid（n_platforms>0，即发布且有播放数据）项目——freshness 需配对
        # 播放数据才有学习意义，未发布项目的 freshness 不纳入（样本量 = 发布项目子集）。
        # outcome 用 reach_composite（跨项目百分位）近似，非 calibrate 的 causes（单项目绝对
        # 阈值）——两层诊断口径有意不同：本层跨项目消除平台量级差异，calibrate 单项目精确。两者
        # 自洽，不互相依赖（本层产 recommendation 喂 exploration，calibrate 产 signal 喂 collect）。
        try:
            from engine.freshness import analyze_freshness_signals
            fr_signals: list[dict] = []
            for p in valid:
                fs = p.get("freshness")
                reach = p.get("reach_composite", 0)
                if fs is None:
                    continue
                if fs >= 0.7 and reach < 0.3:
                    sig = "FRESH_BUT_LOW_PLAYS"
                elif fs < 0.3 and reach >= 0.5:
                    sig = "SIMILAR_BUT_HIGH_PLAYS"
                else:
                    sig = "ALIGNED"
                fr_signals.append({"calibration": {"freshness_signal": {"signal": sig}}})
            fr_analysis = analyze_freshness_signals(fr_signals)
            insights["freshness_analysis"] = fr_analysis
            if fr_analysis.get("recommendation"):
                self._log(f"  ⚠ freshness 学习层建议: {fr_analysis['recommendation']}"
                          f"（fresh_but_low={fr_analysis.get('fresh_but_low_ratio')},"
                          f" similar_but_high={fr_analysis.get('similar_but_high_ratio')},"
                          f" N={fr_analysis.get('sample_size')}）"
                          f" → 已写 freshness_feedback，exploration 将收窄 explore")
                _write_freshness_feedback(fr_analysis)  # B 闭环：写反馈供 exploration.decide 读
            else:
                self._log(f"  freshness 学习层: {fr_analysis.get('note') or '无校准建议'}"
                          f"（N={fr_analysis.get('sample_size')}）")
        except Exception as e:
            self._log(f"  freshness 学习层跳过: {e}")

        # ── 维度1: 题材分析（reach_composite 受众广度信号）──
        topic_groups = defaultdict(list)
        for p in valid:
            topic_groups[p["topic"]].append(p)
        insights["topic_analysis"] = {}
        for tp, items in sorted(topic_groups.items(),
                                key=lambda x: -statistics.mean(p["reach_composite"] for p in x[1])):
            avg_reach = _wmean(items, "reach_composite")
            avg_qual = _wmean(items, "quality_composite")
            insights["topic_analysis"][tp] = {
                "count": len(items),
                "avg_reach": round(avg_reach, 3),
                "avg_quality": round(avg_qual, 3),
            }
            self._log(f"  题材 {tp:14s}: N={len(items):2d}  广度={avg_reach:.2f}  留存={avg_qual:.2f}")

        # ── 维度2: 话术分析（hook 类型 × quality_composite 留存信号）──
        hook_groups = defaultdict(list)
        for p in valid:
            hook_groups[p["hook_type"]].append(p)
        insights["hook_analysis"] = {}
        for ht, items in sorted(hook_groups.items(),
                                key=lambda x: -statistics.mean(p["quality_composite"] for p in x[1])):
            avg_reach = _wmean(items, "reach_composite")
            avg_qual = _wmean(items, "quality_composite")
            insights["hook_analysis"][ht] = {
                "count": len(items),
                "avg_plays": round(avg_reach, 3),   # 向后兼容（reach 0-1 尺度）
                "avg_c5s": round(avg_qual, 3),      # 向后兼容（quality 0-1 尺度）
            }
            self._log(f"  Hook {ht:20s}: N={len(items):2d}  留存={avg_qual:.2f}  广度={avg_reach:.2f}")

        # ── 维度3: 封面分析（color_bias × reach_composite 受众广度）──
        cover_groups = defaultdict(list)
        for p in valid:
            cb = p.get("cover_attrs", {}).get("color_bias", "未知")
            cover_groups[cb].append(p)
        insights["cover_analysis"] = {}
        for cb, items in sorted(cover_groups.items(),
                                key=lambda x: -statistics.mean(p["reach_composite"] for p in x[1])):
            avg_reach = _wmean(items, "reach_composite")
            insights["cover_analysis"][cb] = {
                "count": len(items),
                "avg_reach": round(avg_reach, 3),
            }
            self._log(f"  封面 {cb:10s}: N={len(items):2d}  广度={avg_reach:.2f}")

        # ── 维度3b: 封面子维度（title 含 cool 色段 / 有无 glow，区分度高于 color_bias）──
        # color_bias 在本频道高度统一（42/45 冷暖对比），改用子维度寻找区分度
        for _sub_key, _sub_label in (("title_cool", "标题含cool"), ("glow", "有光晕")):
            _sub_groups: dict[str, list] = defaultdict(list)
            for p in valid:
                _attrs = p.get("cover_attrs") or {}
                if _sub_key == "title_cool":
                    _val = "含cool" if "cool" in (_attrs.get("title_styles") or "") else "不含cool"
                else:
                    _val = "有glow" if _attrs.get("glow_intensity") in ("high", "medium") else "无glow"
                _sub_groups[_val].append(p)
            for _val, _items in sorted(_sub_groups.items(),
                                       key=lambda x: -statistics.mean(p["reach_composite"] for p in x[1])):
                if len(_items) >= 2:
                    _avg = _wmean(_items, "reach_composite")
                    insights["cover_analysis"][f"{_sub_label}_{_val}"] = {"count": len(_items), "avg_reach": round(_avg, 3)}
                    self._log(f"  封面{_sub_label}{_val}: N={len(_items):2d}  广度={_avg:.2f}")

        # ── 维度4: 旁白分析（dominant_emotion × quality_composite 留存信号）──
        narr_groups = defaultdict(list)
        for p in valid:
            attrs = p.get("narration_attrs") or {}
            emo = attrs.get("dominant_emotion") or "无结构"
            narr_groups[emo].append(p)
        insights["narration_analysis"] = {}
        for emo, items in sorted(narr_groups.items(),
                                 key=lambda x: -statistics.mean(p["quality_composite"] for p in x[1])):
            avg_qual = _wmean(items, "quality_composite")
            attrs0 = items[0].get("narration_attrs") or {}
            insights["narration_analysis"][emo] = {
                "count": len(items),
                "avg_quality": round(avg_qual, 3),
                "humor_density": attrs0.get("humor_density", 0),
                "contrarian_density": attrs0.get("contrarian_density", 0),
            }
            self._log(f"  旁白 {emo:12s}: N={len(items):2d}  留存={avg_qual:.2f}")

        # ── 内容模式分析（保留，多平台化）──
        mode_groups = defaultdict(list)
        for p in valid:
            mode_groups[p["content_mode"]].append(p)
        insights["mode_analysis"] = {}
        for mode, items in sorted(mode_groups.items(),
                                  key=lambda x: -statistics.mean(p["reach_composite"] for p in x[1])):
            avg_reach = _wmean(items, "reach_composite")
            avg_qual = _wmean(items, "quality_composite")
            insights["mode_analysis"][mode] = {
                "count": len(items),
                "avg_plays": round(avg_reach, 3),
                "avg_c5s": round(avg_qual, 3),
            }

        # ── 5s 完播分段（按 quality_composite 分段，供 phase4 兼容）──
        c5s_buckets = {">=0.6": [], "0.4-0.6": [], "<0.4": []}
        for p in valid:
            q = p["quality_composite"]
            if q >= 0.6:
                c5s_buckets[">=0.6"].append(p)
            elif q >= 0.4:
                c5s_buckets["0.4-0.6"].append(p)
            else:
                c5s_buckets["<0.4"].append(p)
        insights["c5s_analysis"] = {}
        for bucket, items in c5s_buckets.items():
            if items:
                avg_reach = _wmean(items, "reach_composite")
                insights["c5s_analysis"][bucket] = {"count": len(items), "avg_plays": round(avg_reach, 3)}
                self._log(f"  留存 {bucket:8s}: N={len(items):2d}  广度={avg_reach:.2f}")

        # ── 收藏率分析（多平台 save_rate 均值，供 phase4）──
        high_save = [p for p in valid if p["save_rate"] > 0.03]
        low_save = [p for p in valid if p["save_rate"] < 0.01]
        if high_save and low_save:
            hs_avg = _wmean(high_save, "reach_composite")
            ls_avg = _wmean(low_save, "reach_composite")
            insights["save_ratio"] = hs_avg / max(ls_avg, 0.01)
            self._log(f"  收藏率: 高(>3%)广度={hs_avg:.2f} vs 低(<1%)={ls_avg:.2f} ({hs_avg/max(ls_avg,0.01):.1f}x)")

        # ── 增长分析（保留，供 phase4）──
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
                            "quality": p["quality_composite"],
                        })
                except Exception:
                    pass
        if growth_data:
            growing = [g for g in growth_data if g["daily_growth"] > 100]
            stalled = [g for g in growth_data if g["daily_growth"] < 10]
            if growing and stalled:
                gc = statistics.mean(g["quality"] for g in growing)
                sc = statistics.mean(g["quality"] for g in stalled)
                insights["growth_c5s_gap"] = round(gc - sc, 3)
                self._log(f"  增长组留存={gc:.2f} vs 停滞组={sc:.2f} (差{gc-sc:.2f})")

        # ── 维度5: 发布时段分析（reach_composite 受众广度，运营决策维度）──
        # 关联非因果：只供发布时机参考，不生成内容 pattern/Delta（运营变量≠内容规律）
        pt_analysis = analyze_publish_time(valid)
        if pt_analysis["hour_bucket"] or pt_analysis["weekday"]:
            insights["publish_time_analysis"] = pt_analysis
            for _bucket, _st in pt_analysis["hour_bucket"].items():
                self._log(f"  发布时段 {_bucket:14s}: N={_st['count']:2d}  广度={_st['avg_reach']:.2f}")
            if pt_analysis["best_hour_bucket"]:
                _best = pt_analysis["best_hour_bucket"]
                self._log(f"  ⭐ 最佳发布时段: {_best} "
                          f"(广度={pt_analysis['hour_bucket'][_best]['avg_reach']:.2f}, "
                          f"coverage {pt_analysis['coverage_hour']})")
        else:
            self._log(f"  发布时段分析: {pt_analysis['note']} (coverage {pt_analysis['coverage_hour']})")

        # 生成发布时机建议文件（供 evolve-daily 汇报；运营决策，不进创作 pattern）
        _advice = build_publish_advice(pt_analysis, self.market_avg)
        try:
            _advice_path = WORKSPACE / "evolution" / "publish_timing_advice.json"
            _advice_path.parent.mkdir(parents=True, exist_ok=True)
            _advice_path.write_text(json.dumps({
                **_advice,
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "coverage_note": "基于含时分的发布记录（视频号无时分，4/5 平台覆盖）",
            }, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception as _e:
            self._log(f"  发布时机建议写入失败: {_e}")

        # ── Spearman 相关（共识→广度，质量→广度）──
        if len(valid) >= 10:
            reach = [float(p["reach_composite"]) for p in valid]
            quality = [float(p["quality_composite"]) for p in valid]
            consensus = [float(p["reach_consensus"]) for p in valid]
            insights["spearman_consensus"] = _spearman(consensus, reach)
            insights["spearman_quality"] = _spearman(quality, reach)
            insights["spearman_c5s"] = insights["spearman_quality"]  # 向后兼容
            self._log(f"  Spearman: 共识→广度={_spearman(consensus, reach):.3f}  质量→广度={_spearman(quality, reach):.3f}")

        # ── 回归归因（statsmodels）：控制其他变量后的边际净效应，反哺 pattern 权重 ──
        insights["regression"] = self._regression_attribution(valid)

        return insights

    def _regression_attribution(self, valid: list[dict]) -> dict:
        """statsmodels OLS 回归归因：输出"控制其他变量后的边际净效应"。

        替代 phase2 单变量分组均值的正交假设缺陷——分组均值无法分离
        题材×hook 的交互效应。在数据充足的 github-trending 子集上做带交互项
        回归。缺包时降级（try import 守卫，不报错），返回 available=False。
        """
        try:
            import statsmodels.formula.api as smf
            import pandas as pd
        except ImportError:
            self._log("  回归归因: statsmodels 未安装，跳过（降级为 Spearman）")
            return {"available": False, "reason": "statsmodels not installed"}
        # 子集：github-trending 系（topic 51% 单一无方差，无法跨 topic 回归，只能同质子集内）
        sub = [p for p in valid
               if p.get("content_mode") in ("daily_trending", "weekly")
               or "github" in (p.get("topic") or "").lower()
               or p.get("topic") in ("综合盘点", "周榜综合")]
        if len(sub) < 20:
            self._log(f"  回归归因: 子集样本 {len(sub)} < 20，跳过")
            return {"available": False, "reason": f"sample {len(sub)} < 20"}
        df = pd.DataFrame([{
            "reach": p["reach_composite"],
            "hook_type": p["hook_type"],
            "n_segments": (p.get("narration_attrs") or {}).get("n_segments", 0),
            "humor_density": (p.get("narration_attrs") or {}).get("humor_density", 0),
            "save_rate": p["save_rate"],
            "cover_cool": 1 if "cool" in ((p.get("cover_attrs") or {}).get("title_styles") or "") else 0,
            "bgm_style": p.get("bgm_style") or "unknown",
        } for p in sub])
        try:
            # topic 单一无方差不纳入协变量；cover_cool = 封面标题含 cool 色段（子维度分析强信号）
            model = smf.ols(
                "reach ~ C(hook_type) + n_segments + humor_density + save_rate + cover_cool "
                "+ C(hook_type):save_rate + C(bgm_style)", data=df
            ).fit()
        except Exception as e:
            self._log(f"  回归归因: 拟合失败 {e}")
            return {"available": False, "reason": f"fit failed: {e}"}
        result = {
            "available": True, "n": int(len(df)),
            "r_squared": round(float(model.rsquared), 4),
            "significant_pos": [], "significant_neg": [], "coef": {},
        }
        for k in model.params.index:
            coef = float(model.params[k])
            pv = float(model.pvalues[k])
            result["coef"][k] = {"coef": round(coef, 4), "p": round(pv, 4)}
            if pv < 0.10:  # 探索性阈值；反哺时用更严的 p<0.05 + N>=30
                (result["significant_pos"] if coef > 0 else result["significant_neg"]).append(k)
        self._log(f"  回归归因: N={len(df)} R²={result['r_squared']:.3f} "
                  f"显著正(p<.1)={len(result['significant_pos'])} 显著负={len(result['significant_neg'])}")
        try:
            report_path = WORKSPACE / "sources" / f"regression-{datetime.now(timezone.utc).strftime('%Y%m%d')}.json"
            report_path.parent.mkdir(parents=True, exist_ok=True)
            report_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            pass
        return result

    # ── Phase 3: 模式提炼 ─────────────────────────────────────────────────────

    def phase3_patterns(self, insights: dict) -> list[dict]:
        self._log("\nPhase 3: 模式提炼")

        # 中文维度值 → ASCII slug（文件名安全）
        topic_slug = {
            "AI/智能体": "ai", "安全/隐私": "security", "前端/Web": "frontend",
            "系统/底层": "system", "开发工具": "devtools", "数据/后端": "backend",
            "Python/通用": "python", "综合盘点": "misc", "周榜综合": "weekly",
            "专题深度": "special", "其他": "other", "unknown": "unknown",
        }
        cover_slug = {"冷暖对比": "contrast", "暖色主调": "warm", "冷色主调": "cool", "未知": "unknown"}

        saved: list[str] = []

        def _try_save(pat: dict):
            pat_id = pat["id"]
            if _pattern_file(pat_id).exists():
                return
            if gate_validate_pattern(pat)["valid"]:
                save_pattern(pat)
                saved.append(pat_id)
                self._log(f"  新增 pattern: {pat_id} (weight={pat['as_preference']['weight']})")

        # ── 维度1: 话术 pattern（hook 类型，avg_plays 现为 reach_composite 0-1 尺度）──
        for ht, data in insights.get("hook_analysis", {}).items():
            if data["avg_plays"] >= 0.55 and data["count"] >= 3 and ht not in ("empty", "plain"):
                _try_save({
                    "id": f"P-hook-{ht}",
                    "seed": False, "category": "github", "skill_scope": "stage3-scenes",
                    "description": f"Hook {ht} 模式: {data['count']} 条，留存 {data['avg_c5s']:.2f}，广度 {data['avg_plays']:.2f}",
                    "evidence": {"sample_size": data["count"], "avg_reach": data["avg_plays"],
                                 "avg_quality": data["avg_c5s"], "market_avg_at_birth": self.market_avg,
                                 "confidence": min(0.5 + data["count"] * 0.1, 0.95)},
                    "as_preference": {
                        "text": f"hook 偏好 {ht} 模式（{data['count']} 条多平台样本，留存 {data['avg_c5s']:.2f}，广度 {data['avg_plays']:.2f}）",
                        "weight": "HIGH" if data["avg_plays"] >= 0.65 else "MEDIUM",
                        "source_pattern": f"P-hook-{ht}",
                    },
                })

        # ── 维度2: 题材 pattern（按受众广度排序，reach_composite 信号）──
        for tp, data in sorted(insights.get("topic_analysis", {}).items(),
                               key=lambda x: -x[1]["avg_reach"]):
            if data["avg_reach"] >= 0.55 and data["count"] >= 3 and tp != "unknown":
                slug = topic_slug.get(tp, "other")
                _try_save({
                    "id": f"P-topic-{slug}",
                    "seed": False, "category": "github", "skill_scope": "stage1-content",
                    "description": f"题材「{tp}」受众广: {data['count']} 条，广度 {data['avg_reach']:.2f}，留存 {data['avg_quality']:.2f}",
                    "evidence": {"sample_size": data["count"], "avg_reach": data["avg_reach"],
                                 "avg_quality": data["avg_quality"], "market_avg_at_birth": self.market_avg,
                                 "confidence": min(0.5 + data["count"] * 0.1, 0.95)},
                    "as_preference": {
                        "text": f"选题偏重「{tp}」领域（{data['count']} 条多平台样本，受众广度 {data['avg_reach']:.2f} 高于均值）",
                        "weight": "HIGH" if data["avg_reach"] >= 0.7 else "MEDIUM",
                        "source_pattern": f"P-topic-{slug}",
                    },
                })

        # ── 维度3: 封面 pattern（color_bias × 受众广度）──
        for cb, data in sorted(insights.get("cover_analysis", {}).items(),
                               key=lambda x: -x[1]["avg_reach"]):
            if data["avg_reach"] >= 0.6 and data["count"] >= 3 and cb != "未知":
                slug = cover_slug.get(cb, "other")
                _try_save({
                    "id": f"P-cover-{slug}",
                    "seed": False, "category": "github", "skill_scope": "stage7-delivery",
                    "description": f"封面「{cb}」受众广: {data['count']} 条，广度 {data['avg_reach']:.2f}",
                    "evidence": {"sample_size": data["count"], "avg_reach": data["avg_reach"],
                                 "market_avg_at_birth": self.market_avg,
                                 "confidence": min(0.5 + data["count"] * 0.1, 0.95)},
                    "as_preference": {
                        "text": f"封面配色偏「{cb}」（{data['count']} 条多平台样本，受众广度 {data['avg_reach']:.2f}）",
                        "weight": "HIGH" if data["avg_reach"] >= 0.7 else "MEDIUM",
                        "source_pattern": f"P-cover-{slug}",
                    },
                })

        # ── 维度4: 旁白 pattern（结构化 narration vs 旧格式，留存信号）──
        valid = [p for p in self.projects if p.get("n_platforms", 0) > 0]
        structd = [p for p in valid if (p.get("narration_attrs") or {}).get("has_struct")]
        unstructd = [p for p in valid if p.get("narration_attrs") and not p["narration_attrs"].get("has_struct")]
        if len(structd) >= 3 and len(unstructd) >= 3:
            sq = statistics.mean(p["quality_composite"] for p in structd)
            uq = statistics.mean(p["quality_composite"] for p in unstructd)
            if sq > uq + 0.08:  # 结构化组留存显著更高
                _try_save({
                    "id": "P-narration-structured",
                    "seed": False, "category": "github", "skill_scope": "stage3-scenes",
                    "description": f"结构化 narration（含 scene_type/emotion）留存更高: 结构化 {len(structd)} 条留存 {sq:.2f} vs 旧格式 {len(unstructd)} 条 {uq:.2f}",
                    "evidence": {"sample_size": len(structd) + len(unstructd),
                                 "structured_quality": round(sq, 3), "unstructured_quality": round(uq, 3),
                                 "confidence": min(0.5 + (len(structd) + len(unstructd)) * 0.05, 0.95)},
                    "as_preference": {
                        "text": f"narration_segments.json 必须写结构化字段（scene_type/emotion/humor_type），多平台留存 {sq:.2f} 显著高于旧格式 {uq:.2f}",
                        "weight": "HIGH" if sq - uq >= 0.15 else "MEDIUM",
                        "source_pattern": "P-narration-structured",
                    },
                })

        if not saved:
            self._log("  无新 pattern")
        self.patterns_saved = saved
        return saved

    # ── Phase 3.5: 时效重验（衰减闭环）─────────────────────────────────────────

    def phase3_5_revalidate(self) -> list[str]:
        """重验现有 pattern 当前表现 vs 出生分：下降→降权，连续2次下降→deprecated 移出注入池。
        只处理 seed:false 且有 avg_reach 基准的 auto_evolve pattern；人工 seed pattern 不衰减。"""
        self._log("\nPhase 3.5: 时效重验（衰减闭环）")

        # 逆映射（phase3 的 topic_slug / cover_slug 反向，slug → 中文维度值）
        topic_unslug = {v: k for k, v in {
            "AI/智能体": "ai", "安全/隐私": "security", "前端/Web": "frontend",
            "系统/底层": "system", "开发工具": "devtools", "数据/后端": "backend",
            "Python/通用": "python", "综合盘点": "misc", "周榜综合": "weekly",
            "专题深度": "special", "其他": "other", "unknown": "unknown",
        }.items()}
        cover_unslug = {v: k for k, v in {
            "冷暖对比": "contrast", "暖色主调": "warm", "冷色主调": "cool", "未知": "unknown"
        }.items()}

        DECLINE_RATIO = 0.70   # recent < birth × 0.70 → declining（受众广度显著下滑，口味变了）
        RISING_RATIO = 1.10    # recent > birth × 1.10 → rising
        MIN_SAMPLE = 5         # 覆盖项目集 < 5 不判定（小样本噪声）
        WEIGHT_LADDER = ["LOW", "MEDIUM", "HIGH"]

        patterns_dir = _auto_patterns_dir()
        revalidated: list[str] = []
        import yaml
        for fp in sorted(patterns_dir.glob("P-*.yaml")):
            try:
                data = yaml.safe_load(fp.read_text("utf-8"))
            except Exception:
                continue
            if not data or data.get("seed") is True:        # 决策1：跳过手工 seed pattern（人工经验不被机器淘汰）
                continue
            ev = data.get("evidence") or {}
            birth = ev.get("avg_reach")
            if birth is None:                                # 无 reach 尺度基准（如 seed 的 avg_soft_score），跳过
                continue

            pat_id = data.get("id") or fp.stem
            proj_subset = self._match_pattern_projects(pat_id, topic_unslug, cover_unslug)
            if len(proj_subset) < MIN_SAMPLE:                # 决策6：统计保护
                continue

            recent = round(statistics.mean(p["reach_composite"] for p in proj_subset), 4)

            # 相对大盘衰减（核心修正）：绝对量级 reach 会被大盘涨跌误导——
            # 大盘涨→所有 pattern 误判 rising；大盘跌→误杀好 pattern。
            # 改用超额广度（类基金 alpha）：birth_excess/recent_excess = pattern 相对同期大盘的超出量。
            market_birth = ev.get("market_avg_at_birth")
            if market_birth is None:                         # 旧 pattern 无 birth 大盘基线 → 用当前大盘回填（近似）
                market_birth = self.market_avg
            current_market = self.market_avg
            birth_excess = birth - market_birth
            recent_excess = recent - current_market

            prev_streak = int(ev.get("decline_streak", 0) or 0)
            # 幂等保护：本次超额与上次记录的 recent_excess 相同（数据未更新，纯重跑）→
            # 冻结 trend/streak/weight/status，避免重复执行累积 streak 或持续降权。
            prev_excess = ev.get("recent_excess")
            _same_data = (prev_excess is not None
                          and isinstance(prev_excess, (int, float))
                          and abs(recent_excess - prev_excess) < 1e-6)

            if _same_data:
                trend = ev.get("trend", "stable")
                streak = prev_streak
            else:
                # 趋势判定：birth_excess>0（出生跑赢大盘）用超额比例判定；否则用绝对超额阈值
                if birth_excess > 0.01:
                    decline_cond = recent_excess < birth_excess * DECLINE_RATIO
                    rising_cond = recent_excess > birth_excess * RISING_RATIO
                else:
                    decline_cond = recent_excess < -0.05
                    rising_cond = recent_excess > 0.05
                if decline_cond:
                    trend, streak = "declining", prev_streak + 1
                elif rising_cond:
                    trend, streak = "rising", 0
                else:
                    trend, streak = "stable", 0

            # weight 升降（决策5）：单次 trend 驱动爬梯子一级；rising 需 streak==0（首次回升才升）
            pref = data.get("as_preference") or {}
            w = pref.get("weight", "MEDIUM")
            if w not in WEIGHT_LADDER:
                w = "MEDIUM"
            if not _same_data:                  # 数据未变时冻结 weight（幂等，不重复降权）
                idx = WEIGHT_LADDER.index(w)
                if trend == "declining":
                    w = WEIGHT_LADDER[max(idx - 1, 0)]
                elif trend == "rising" and streak == 0:
                    w = WEIGHT_LADDER[min(idx + 1, len(WEIGHT_LADDER) - 1)]
            pref["weight"] = w

            # status 硬淘汰（决策5）：连续2次 declining → deprecated，inject 过滤移出注入池
            status = "deprecated" if streak >= 2 else "active"

            # 写回时效字段（不动 avg_reach，保 birth 绝对基准不变）
            ev["recent_reach"] = recent
            ev["market_avg_at_birth"] = round(market_birth, 4)   # 持久化回填的 birth 大盘基线
            ev["market_avg_current"] = round(current_market, 4)
            ev["recent_excess"] = round(recent_excess, 4)
            ev["window_end"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            ev["trend"] = trend
            ev["decline_streak"] = streak
            ev["status"] = status
            data["evidence"] = ev
            data["as_preference"] = pref

            if gate_validate_pattern(data).get("valid"):    # 决策4：防御性过 gate（只改 evidence 不改 text，必过）
                save_pattern(data)                          # 直接覆盖写回（绕过 _try_save 的"已存在即跳过"）
                revalidated.append(pat_id)
                self._log(f"  {pat_id}: recent={recent:.2f}(excess{recent_excess:+.2f}) "
                          f"birth={birth:.2f}(excess{birth_excess:+.2f}) market={current_market:.2f} → {trend}, "
                          f"streak={streak}, weight={w}, status={status}")

        if not revalidated:
            self._log("  无可重验 pattern（被 seed 过滤 / 无 birth 基准 / 样本不足）")
        self.patterns_revalidated = revalidated
        return revalidated

    def _match_pattern_projects(self, pat_id: str, topic_unslug: dict, cover_unslug: dict) -> list[dict]:
        """解析 P-{dim}-{slug} id，返回 self.projects 中匹配维度值且 n_platforms>0 的项目子集。
        topic/cover 用逆映射转中文，hook slug 直接是 hook_type 值，narration 暂不支持（返回空）。"""
        valid = [p for p in self.projects if p.get("n_platforms", 0) > 0]
        parts = pat_id.split("-")
        if len(parts) < 3:
            return []
        dim, slug = parts[1], "-".join(parts[2:])
        if dim == "topic":
            cn = topic_unslug.get(slug)
            return [p for p in valid if p.get("topic") == cn] if cn else []
        if dim == "hook":
            return [p for p in valid if p.get("hook_type") == slug]
        if dim == "cover":
            cn = cover_unslug.get(slug)
            return [p for p in valid if (p.get("cover_attrs") or {}).get("color_bias") == cn] if cn else []
        return []  # narration 等特殊布尔模式维度暂不参与衰减

    # ── Phase 4: Delta 生成 ───────────────────────────────────────────────────

    def phase4_deltas(self, insights: dict) -> list[str]:
        self._log("\nPhase 4: Delta 生成")
        saved_ids: list[str] = []
        hook_analysis = insights.get("hook_analysis", {})
        valid_count = insights.get("valid_count", 0)
        # 多平台综合：save_ratio = 高收藏广度/低收藏广度；growth_gap = 增长组留存 - 停滞组留存
        save_ratio = insights.get("save_ratio", 0.0)
        growth_gap = insights.get("growth_c5s_gap", 0.0)

        # avg_plays 现为 reach_composite（0-1 受众广度尺度）
        plain_plays = hook_analysis.get("plain", {}).get("avg_plays", 0.0)
        action_plays = hook_analysis.get("action_number", {}).get("avg_plays", 0.0)
        contrarian_plays = hook_analysis.get("contrarian", {}).get("avg_plays", 0.0)

        # 规则 1: Hook 类型倍率（解耦，不再嵌套规则 2）
        if action_plays > plain_plays * 1.3 and valid_count >= 10:
            ratio = action_plays / max(plain_plays, 0.01)
            d = _make_delta(
                operation="ADDED",
                source="auto_evolve",
                confidence=min(0.7 + valid_count * 0.005, 0.90),
                target_rule_id="R-S3-008",
                new_rule_raw={
                    "id": "R-S3-008",
                    "type": "FORBIDDEN_ACTION",
                    "pattern": "hook 场景第一句不含动作词/数字锚定/反直觉陈述",
                    "positive": f"hook 第一句必须包含至少一个：(a)动作词（杀入/冲上/炸）(b)量化数字 (c)反直觉转折。多平台数据：action hook 受众广度 {action_plays:.2f} 是平铺 {plain_plays:.2f} 的 {ratio:.1f}x",
                    "guardrail": "segments[0].text 前 15 字不包含任何 hook_anchors 关键词或数字",
                    "detection": {"keywords": [], "semantic_check": True},
                    "severity": "HARD",
                    "class": "EXPERIENTIAL",
                    "scope": "SKILL",
                    "skill": "stage3-scenes",
                    "source": f"auto_evolve: N={valid_count}, action={action_plays:.2f} vs plain={plain_plays:.2f} ({ratio:.1f}x, 多平台 reach_composite)",
                },
                reason=f"数据驱动: action_number 广度{action_plays:.2f} vs plain {plain_plays:.2f} ({ratio:.1f}x)",
                rules=self.rules, traces=self.traces,
                category="github",  # R-S3-008 主轨 hook 词（杀入/冲上/炸）分类隔离，goldminer 不注入
            )
            path = save_delta(d, DELTAS_DIR)
            saved_ids.append(path.name)
            self._log(f"  {'自动生效' if not d.get('requires_human_review') else '待审核'}: {path.name}")
            _cleanup_old_deltas("R-S3-008", path.name)

        # 规则 2: 高收藏率（save_ratio 从 insights 读取，多平台受众广度比）
        if save_ratio > 1.5 and valid_count >= 10:
            d = _make_delta(
                operation="ADDED",
                source="auto_evolve",
                confidence=min(0.7 + valid_count * 0.005, 0.85),
                target_rule_id="R-PAT-high-save-rate",
                new_rule_raw={
                    "id": "R-PAT-high-save-rate",
                    "type": "REQUIRED_METHOD",
                    "pattern": "内容缺少'值得收藏'的实用信息",
                    "positive": f"视频中至少 1 个场景必须包含可操作的实用信息。多平台数据：高收藏(>3%)受众广度是低收藏(<1%)的 {save_ratio:.1f}x",
                    "guardrail": "所有场景均为泛泛描述，无具体工具名/数据/步骤",
                    "detection": {"keywords": [], "semantic_check": True},
                    "severity": "SOFT",
                    "class": "EXPERIENTIAL",
                    "scope": "SKILL",
                    "skill": "stage3-scenes",
                    "source": f"auto_evolve: 高/低收藏广度比={save_ratio:.1f}x, 增长留存差={growth_gap:.2f} (多平台综合)",
                },
                reason=f"收藏率广度比={save_ratio:.1f}x，是长尾增长核心指标",
                rules=self.rules, traces=self.traces,
            )
            path = save_delta(d, DELTAS_DIR)
            saved_ids.append(path.name)
            self._log(f"  {'自动生效' if not d.get('requires_human_review') else '待审核'}: {path.name}")
            _cleanup_old_deltas("R-PAT-high-save-rate", path.name)

        if not saved_ids:
            self._log("  无新 Delta（现有规则已充分）")
        self.deltas_saved = saved_ids
        return saved_ids

    # ── Phase 5: 阈值校准 ─────────────────────────────────────────────────────

    def phase5_calibrate(self, insights: dict) -> list[str]:
        self._log("\nPhase 5: 阈值校准")
        changed: list[str] = []

        # 用真实抖音数据校准 douyin 阈值（不从 composite 0-1 尺度，避免污染 gate 用的原始阈值）
        douyin_data: list[dict] = []
        for p in self.projects:
            dy = p.get("per_plat", {}).get("douyin", {})
            if not isinstance(dy, dict):
                continue
            c5s = dy.get("completion_5s_rate")
            plays = dy.get("plays", 0) or 0
            save_rate = dy.get("save_rate")
            if c5s is not None and plays > 0:
                douyin_data.append({
                    "c5s": float(c5s),
                    "plays": float(plays),
                    "save_rate": float(save_rate) if save_rate is not None else 0.0,
                })
        if len(douyin_data) < 10:
            self._log(f"  抖音样本不足 ({len(douyin_data)}/10)，跳过阈值校准")
            return changed

        thresholds = load_thresholds()

        # 校准 5s_completion_low: 找播放量最佳分隔点（最低 0.36，防止过拟合）
        c5s_values = [(p["c5s"], p["plays"]) for p in douyin_data]
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
        save_values = [(p["save_rate"], p["plays"]) for p in douyin_data if p["save_rate"] > 0]
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
            thresholds["calibration"]["sample_size"] = len(douyin_data)
            save_thresholds(thresholds)
        else:
            self._log("  阈值无需更新")

        self.thresholds_changed = changed
        return changed

    def phase6_train_hook(self) -> None:
        """Phase 6: 播放量预测训练钩子（不遗忘——每次跑都 check，≥100 样本自动训练升级）。

        扫 performance.json（拿 proj_dir + 多平台播放），提取 features（freshness/hook/项目数）
        × log_plans → predict.train_if_ready。样本不足返回待训练状态，达标自动训练+持久化。
        """
        self._log("\nPhase 6: 播放量预测训练钩子")
        import math
        from engine.freshness import compute_freshness, _hook_text, _project_set
        from engine.predict import train_if_ready, CONTRARIAN_WORDS, NUMBER_RE
        samples = []
        for pf in sorted(WORKSPACE.rglob("performance.json")):
            proj = pf.parent
            if "test" in proj.parts:
                continue  # test 目录隔离，不进回归/训练样本
            try:
                data = json.loads(pf.read_text("utf-8"))
            except Exception:
                continue
            plats = data.get("platforms", {})
            if not isinstance(plats, dict):
                continue
            plays = 0
            for pdata in plats.values():
                if isinstance(pdata, dict):
                    plays = max(plays, pdata.get("plays", 0) or pdata.get("impressions", 0) or 0)
            if plays <= 0:
                continue
            try:
                fr = compute_freshness(proj, 10)
                hook = _hook_text(proj)
                contra = any(w in hook for w in CONTRARIAN_WORDS)
                num = bool(NUMBER_RE.search(hook))
                pcount = len(_project_set(proj))
                samples.append({
                    "freshness": fr.get("freshness_score", 0.5),
                    "hook_contrarian": int(contra), "hook_number": int(num),
                    "project_count": pcount, "log_plays": math.log10(plays),
                })
            except Exception:
                continue
        result = train_if_ready(samples)
        tag = result.get("version") or result.get("note", "")
        self._log(f"  join 样本={len(samples)} → trained={result.get('trained')} {tag}")

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

        # Phase 3.5（衰减闭环）
        self.phase3_5_revalidate()

        # Phase 4
        self.phase4_deltas(insights)

        # Phase 5
        self.phase5_calibrate(insights)

        # Phase 6（播放量预测训练钩子——不遗忘，数据达标自动升级启发式→训练模型）
        self.phase6_train_hook()

        # 汇总
        self._log("\n" + "=" * 60)
        self._log("汇总")
        self._log("=" * 60)
        self._log(f"  分析项目: {insights.get('valid_count', 0)}")
        self._log(f"  新增 Pattern: {len(self.patterns_saved)}")
        self._log(f"  重验 Pattern: {len(self.patterns_revalidated)}")
        self._log(f"  新增 Delta: {len(self.deltas_saved)}")
        self._log(f"  阈值变更: {len(self.thresholds_changed)}")
        for c in self.thresholds_changed:
            self._log(f"    {c}")

        # 清理过期 Delta（90 天）
        from engine.lib.delta import cleanup_expired_deltas
        expired = cleanup_expired_deltas(max_age_days=90)
        if expired:
            self._log(f"  清理过期 Delta: {len(expired)}")

        return {
            "projects_analyzed": insights.get("valid_count", 0),
            "patterns_created": self.patterns_saved,
            "patterns_revalidated": self.patterns_revalidated,
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
