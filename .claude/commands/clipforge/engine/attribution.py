"""归因引擎 — 强归因（规则命中分析）+ 弱归因（根因判定 + Delta 产出）+ 播放数据归因。

架构哲学对齐：
- P3（事故复盘）：弱归因产出 Delta，实现「失败 → 归因 → 收紧规则」闭环
- P8（渐进严谨）：证据驱动置信度，而非硬编码常量
- Delta Rule API 完整调用：归因不再只返回 dict，而是直接产出增量规则变更
- 数据驱动归因：从播放数据（播放量、5s 完播率、分享率）反推失败根因
"""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from engine.lib.category_config import load_category_config, get as _cfg_get

# hook 数字锚定关键词 — 由分类配置 narration.hook_anchors 提供
_hook_anchors_cache: tuple[str, ...] | None = None


def _get_hook_anchors() -> tuple[str, ...]:
    global _hook_anchors_cache
    if _hook_anchors_cache is not None:
        return _hook_anchors_cache
    import os
    cat_id = os.environ.get("CLIPFORGE_CATEGORY")
    cfg = load_category_config(cat_id)
    anchors = _cfg_get(cfg, "narration.hook_anchors", [])
    _hook_anchors_cache = tuple(anchors) if anchors else ()
    return _hook_anchors_cache
from engine.lib.rule_parser import load_all_rules, RULES_DIR
from engine.lib.models import Rule, Severity, RuleClass, Platform, PerformanceRecord
from engine.lib.delta import create_delta, save_delta, shadow_validate


def _evidence_confidence(violation: dict, trace: dict | None = None) -> float:
    """证据驱动置信度：基于语义级信号动态计算。

    信号来源（按权重递减）：
    1. trace 中是否存在规则触碰记录（constraint_hits）→ 直接证据
    2. violation 是否匹配已有规则的 detection.keywords → 模式匹配证据
    3. trace gate_report 中 hard_violations 的数量 → 上下文证据
    4. violation 详情中是否包含具体关键词（绕过/跳过/无法）→ 行为证据
    """
    signals = 0.25  # 基础置信度（低起点，证据积累才提升）

    # 信号 1：trace 中有规则触碰记录（最高权重）
    if trace:
        exec_data = trace.get("execution", {})
        steps = exec_data.get("steps", [])
        for step in steps:
            hits = step.get("constraint_hits", [])
            if hits:
                signals += 0.25
                break

        # 信号 3：gate_report 中 hard_violations 数量提供上下文
        gate = trace.get("result", {}).get("gate_report", {})
        violations = gate.get("hard_violations", [])
        if len(violations) >= 1:
            signals += 0.10
        if len(violations) >= 2:
            signals += 0.05

        # path_switches 说明 Agent 曾尝试规避
        switches = exec_data.get("path_switches", [])
        if switches:
            signals += 0.10

    # 信号 2：violation 详情匹配具体行为关键词
    details = violation.get("details", violation.get("rule_pattern", ""))
    behavior_keywords = ["绕过", "跳过", "忽略", "遗漏", "缺失", "失败", "异常"]
    matched_behaviors = sum(1 for kw in behavior_keywords if kw in details)
    if matched_behaviors >= 1:
        signals += 0.10
    if matched_behaviors >= 2:
        signals += 0.05

    return min(signals, 0.95)


def strong_attribution(violation: dict, rules: list[Rule]) -> dict:
    """强归因：检查已有规则是否覆盖此违规。确定性推理，可全自动执行。"""
    violation_pattern = violation.get("details", violation.get("rule_pattern", ""))

    for rule in rules:
        if violation.get("rule_id", "").endswith(rule.id):
            return {
                "layer": "STRONG",
                "root_cause": "rule_hit",
                "matched_rule": rule.id,
                "action": "OPTIMIZE_DETECTION",
                "requires_human_review": False,
                "confidence": 1.0,
            }

        from engine.lib.positive_rewrite import rewrite_rule
        guardrail = rewrite_rule(rule)["guardrail"]
        if guardrail and any(kw in violation_pattern for kw in rule.detection.keywords):
            return {
                "layer": "STRONG",
                "root_cause": "rule_hit",
                "matched_rule": rule.id,
                "action": "STRENGTHEN_RULE",
                "requires_human_review": False,
                "confidence": 1.0,
            }

    return {
        "layer": "STRONG",
        "root_cause": "no_rule_match",
        "matched_rule": None,
        "action": "PASS_TO_WEAK",
        "requires_human_review": False,
    }


def weak_attribution(
    violation: dict,
    trace: dict | None = None,
    produce_delta: bool = True,
    rules_dir: Path | None = None,
) -> dict:
    """弱归因：根因判定 + Delta 产出。

    证据驱动置信度 + rule_missing 时自动调用 create_delta。
    """
    rules_dir = rules_dir or RULES_DIR
    violation_pattern = violation.get("details", violation.get("rule_pattern", ""))
    confidence = _evidence_confidence(violation, trace)

    if "绕过" in violation_pattern or "跳过" in violation_pattern:
        root = "behavior_violation"
    elif "无法" in violation_pattern or "不支持" in violation_pattern:
        root = "capability_gap"
    else:
        root = "rule_missing"

    action = None
    candidate = None
    delta_path = None

    if root == "rule_missing":
        action = "NEW_RULE"
        # rule_id 可能含 Windows 非法字符（如 gate:xxx），替换为下划线
        safe_rule_id = violation.get("rule_id", "UNK").replace(":", "_").replace("/", "_")
        candidate = {
            "id": f"R-AUTO-{safe_rule_id}",
            "type": "FORBIDDEN_ACTION",
            "pattern": violation_pattern[:200],
            "positive": f"确保{violation_pattern[:80]}的正确处理",
            "severity": "SOFT",
            "class": "EXPERIENTIAL",
            "scope": "SKILL",
        }
        if produce_delta:
            delta = create_delta(
                operation="ADDED",
                source="weak_attribution",
                confidence=confidence,
                target_rule_id=candidate["id"],
                new_rule_raw=candidate,
                reason=f"归因发现规则缺失: {violation_pattern[:100]}",
            )
            # shadow_validate before saving
            rules = load_all_rules(rules_dir)
            traces_dir = Path(rules_dir).parent / "traces"
            traces = []
            if traces_dir.exists():
                for f in traces_dir.rglob("trace.json"):
                    try:
                        data = json.loads(f.read_text(encoding="utf-8"))
                        if isinstance(data, list):
                            traces.extend(data)
                        else:
                            traces.append(data)
                    except (json.JSONDecodeError, UnicodeDecodeError):
                        pass
            validation = shadow_validate(delta, rules, traces)
            if not validation.get("safe", True):
                delta["shadow_validation"] = validation
                delta["requires_human_review"] = True
            delta_path = save_delta(delta)

    elif root == "behavior_violation":
        action = "STRENGTHEN_INJECTION"

    return {
        "layer": "WEAK",
        "root_cause": root,
        "confidence": round(confidence, 3),
        "evidence": [t for t in [violation_pattern] if t],
        "action": action,
        "candidate_rule": candidate,
        "delta_path": str(delta_path) if delta_path else None,
        "requires_human_review": confidence < 0.55,
    }


def analyze_trace(trace_file: Path, rules_dir: Path | None = None) -> dict:
    rules_dir = rules_dir or RULES_DIR
    rules = load_all_rules(rules_dir)

    with open(trace_file, "r", encoding="utf-8") as f:
        content = f.read()
    try:
        traces = json.loads(content)
        if not isinstance(traces, list):
            traces = [traces]
    except json.JSONDecodeError:
        return {"error": f"无法解析 trace 文件: {trace_file}"}

    results: list[dict] = []
    for trace in traces:
        gate = trace.get("result", {}).get("gate_report", {})
        if gate and not gate.get("hard_passed", True):
            for v in gate.get("hard_violations", []):
                strong = strong_attribution(v, rules)
                if strong["root_cause"] == "no_rule_match":
                    weak = weak_attribution(v, trace)
                    results.append({"trace_id": trace.get("id"), "attribution": weak})
                else:
                    results.append({"trace_id": trace.get("id"), "attribution": strong})

    return {"total_traces": len(traces), "attributions": results}


# ── 播放数据归因 ──────────────────────────────────────────────────────────────
# 数据来源：2026-05-27 三平台分析
# - 抖音：5s 完播率 ≥44% → 36K 播放，<38% → 3.1K
# - 视频号：分享率 4-5% → 高增长
# - 小红书：收藏 > 1.5x 点赞 → 高价值

_DOUYIN_THRESHOLDS = {
    "5s_completion_low": 0.38,
    "5s_completion_high": 0.44,
    "completion_rate_sweet_low": 0.03,
    "completion_rate_sweet_high": 0.05,
    "plays_low": 3000,
    "plays_high": 10000,
}

_WECHAT_THRESHOLDS = {
    "share_rate_low": 0.02,
    "share_rate_high": 0.04,
}

_XHS_THRESHOLDS = {
    "save_to_like_ratio_high": 1.5,
}

_BILIBILI_THRESHOLDS = {
    "bounce_3s_rate_high": 0.40,
    "interaction_rate_low": 0.02,
}


def _classify_hook_type(hook_text: str) -> str:
    """分类 hook 文本模式。"""
    if not hook_text:
        return "empty"
    for kw in ("你知道吗", "有没有想过", "猜猜", "你知道"):
        if kw in hook_text[:10]:
            return "question_interactive"
    for kw in ("不用", "却能", "居然", "竟然", "不需要"):
        if kw in hook_text:
            return "contrarian_conflict"
    for kw in _get_hook_anchors():
        if kw in hook_text:
            return "number_anchor"
    if any(hook_text.startswith(w) for w in ("这个", "今天", "注意")):
        return "signal_attention"
    return "direct_narrative"


def performance_attribution(
    performance: dict,
    narration_file: Path | None = None,
    produce_delta: bool = True,
    rules_dir: Path | None = None,
) -> dict:
    """从播放数据反推失败根因。

    Args:
        performance: 播放数据 {platform, plays, completion_rate, completion_5s_rate, ...}
        narration_file: narration_segments.json 路径（可选，用于 hook 文本分析）
        produce_delta: 是否产出 Delta 规则建议

    Returns:
        归因结果，包含 root_cause、evidence、delta_path 等
    """
    rules_dir = rules_dir or RULES_DIR
    platform = performance.get("platform", "")
    causes: list[dict] = []
    evidence: list[str] = []
    delta_path = None

    # ── 抖音归因 ──
    if platform == Platform.DOUYIN.value or platform == "douyin":
        plays = performance.get("plays", 0)
        c5s = performance.get("completion_5s_rate", 0)
        comp = performance.get("completion_rate", 0)

        # 信号 1：5s 完播率低
        if c5s > 0 and c5s < _DOUYIN_THRESHOLDS["5s_completion_low"]:
            causes.append({"cause": "low_5s_completion", "severity": "HIGH",
                           "detail": f"5s 完播率 {c5s:.1%} < {_DOUYIN_THRESHOLDS['5s_completion_low']:.0%}，平均仅 3,102 播放"})
            evidence.append(f"5s 完播率 {c5s:.1%}（阈值 ≥44% 对应 36K 播放）")

        # 信号 2：完播率不在甜蜜区
        if comp > 0 and (comp < _DOUYIN_THRESHOLDS["completion_rate_sweet_low"] or
                         comp > _DOUYIN_THRESHOLDS["completion_rate_sweet_high"] * 2):
            causes.append({"cause": "completion_out_of_sweet_spot", "severity": "MEDIUM",
                           "detail": f"完播率 {comp:.1%}，甜蜜区 3-5%（平均 29,871 播放）"})
            evidence.append(f"完播率 {comp:.1%}（甜蜜区 3-5%）")

        # 信号 3：播放量低
        if 0 < plays < _DOUYIN_THRESHOLDS["plays_low"]:
            causes.append({"cause": "low_plays", "severity": "HIGH",
                           "detail": f"播放量 {plays} < {_DOUYIN_THRESHOLDS['plays_low']}（基线）"})
            evidence.append(f"播放量 {plays}")

    # ── 视频号归因 ──
    elif platform in (Platform.WECHAT_VIDEO.value, "wechat_video"):
        share_rate = performance.get("share_rate", 0)
        if share_rate > 0 and share_rate < _WECHAT_THRESHOLDS["share_rate_low"]:
            causes.append({"cause": "low_share_rate", "severity": "HIGH",
                           "detail": f"分享率 {share_rate:.1%} < {_WECHAT_THRESHOLDS['share_rate_low']:.0%}，视频号增长靠分享驱动"})
            evidence.append(f"分享率 {share_rate:.1%}（阈值 ≥4%）")

    # ── 小红书归因 ──
    elif platform in (Platform.XIAOHONGSHU.value, "xiaohongshu"):
        save_rate = performance.get("save_rate", 0)
        like_rate = performance.get("like_rate", 0)
        if like_rate > 0 and save_rate / like_rate < _XHS_THRESHOLDS["save_to_like_ratio_high"]:
            causes.append({"cause": "low_save_to_like", "severity": "MEDIUM",
                           "detail": f"收藏/点赞比 {save_rate/like_rate:.1f} < {_XHS_THRESHOLDS['save_to_like_ratio_high']}，小红书收藏驱动"})
            evidence.append(f"收藏/点赞比 {save_rate/like_rate:.1f}")

    # ── B站归因 ──
    elif platform in (Platform.BILIBILI.value, "bilibili"):
        bounce_3s = performance.get("bounce_3s_rate", 0)
        interaction = performance.get("interaction_rate", 0)
        plays_b = performance.get("plays", 0)

        if bounce_3s > 0 and bounce_3s > _BILIBILI_THRESHOLDS["bounce_3s_rate_high"]:
            causes.append({"cause": "high_3s_bounce", "severity": "HIGH",
                           "detail": f"3秒跳出率 {bounce_3s:.1%} > {_BILIBILI_THRESHOLDS['bounce_3s_rate_high']:.0%}，B站推荐依赖前期留存"})
            evidence.append(f"3秒跳出率 {bounce_3s:.1%}")

        if interaction > 0 and interaction < _BILIBILI_THRESHOLDS["interaction_rate_low"]:
            causes.append({"cause": "low_interaction", "severity": "MEDIUM",
                           "detail": f"互动率 {interaction:.1%} < {_BILIBILI_THRESHOLDS['interaction_rate_low']:.0%}，B站权重依赖互动指标"})
            evidence.append(f"互动率 {interaction:.1%}")

        if 0 < plays_b < 200:
            causes.append({"cause": "low_plays", "severity": "HIGH",
                           "detail": f"播放量 {plays_b} < 200（B站基线）"})
            evidence.append(f"播放量 {plays_b}")

    # ── Hook 文本分析（如果提供了 narration 文件）──
    hook_type = ""
    if narration_file and narration_file.exists():
        try:
            data = json.loads(narration_file.read_text(encoding="utf-8"))
            segments = data.get("segments", [])
            if segments:
                hook_text = segments[0].get("narration_segment", "")
                hook_type = _classify_hook_type(hook_text)
                if hook_type == "question_interactive":
                    causes.append({"cause": "weak_hook_pattern", "severity": "HIGH",
                                   "detail": f"hook 使用疑问/互动模式（平均 1,195 播放，最低）"})
                    evidence.append(f"hook 模式: {hook_type}, 文本: '{hook_text[:30]}'")
                elif hook_type == "direct_narrative":
                    causes.append({"cause": "generic_hook", "severity": "MEDIUM",
                                   "detail": f"hook 使用直接叙述模式（平均 5,363 播放，基线）"})
                    evidence.append(f"hook 模式: {hook_type}")
        except (json.JSONDecodeError, UnicodeDecodeError):
            pass

    # ── 综合判定 ──
    if not causes:
        return {
            "layer": "PERFORMANCE",
            "root_cause": "no_performance_issue",
            "confidence": 0.0,
            "evidence": [],
            "action": None,
            "causes": [],
            "requires_human_review": False,
        }

    primary = causes[0]
    confidence = min(0.4 + len(causes) * 0.15, 0.90)

    # 产出 Delta（针对可修复的根因）
    action = None
    candidate = None
    if primary["cause"] in ("weak_hook_pattern", "low_5s_completion") and produce_delta:
        action = "STRENGTHEN_RULE"
        candidate = {
            "id": f"R-PERF-{platform}-{primary['cause'][:20]}",
            "type": "FORBIDDEN_ACTION",
            "pattern": primary["detail"],
            "positive": "使用反直觉/冲突模式或数字锚定模式作为 hook（数据来源：抖音 58 条分析）",
            "severity": "HARD",
            "class": "EXPERIENTIAL",
            "scope": "SKILL",
        }
        delta = create_delta(
            operation="ADDED",
            source="performance_attribution",
            confidence=confidence,
            target_rule_id=candidate["id"],
            new_rule_raw=candidate,
            reason=f"播放数据归因: {primary['detail'][:80]}",
        )
        # shadow_validate before saving
        rules = load_all_rules(rules_dir)
        traces_dir = Path(rules_dir).parent / "traces"
        traces = []
        if traces_dir.exists():
            for f in traces_dir.rglob("trace.json"):
                try:
                    data = json.loads(f.read_text(encoding="utf-8"))
                    if isinstance(data, list):
                        traces.extend(data)
                    else:
                        traces.append(data)
                except (json.JSONDecodeError, UnicodeDecodeError):
                    pass
        validation = shadow_validate(delta, rules, traces)
        if not validation.get("safe", True):
            delta["shadow_validation"] = validation
            delta["requires_human_review"] = True
        delta_path = save_delta(delta)

    return {
        "layer": "PERFORMANCE",
        "root_cause": primary["cause"],
        "confidence": round(confidence, 3),
        "evidence": evidence,
        "action": action,
        "causes": causes,
        "hook_type": hook_type,
        "candidate_rule": candidate,
        "delta_path": str(delta_path) if delta_path else None,
        "requires_human_review": confidence < 0.55,
    }


def calibrate_machine_scoring(
    score_report: dict,
    performance: dict,
    human_scores: dict | None = None,
    narration_file: Path | None = None,
    produce_delta: bool = True,
) -> dict:
    """对比机器预测 vs 实际表现，产出校准信号。

    Args:
        score_report: score_report.json 的内容（machine_scoring 段）
        performance: 播放数据 {platform, plays, completion_5s_rate, ...}
        human_scores: 人类评分 {hook, density, visual, audio, overall, weakest_link}
        narration_file: narration_segments.json 路径（可选）
        produce_delta: 是否产出校准 Delta

    Returns:
        校准结果 {verdict, diagnosis, action, delta_path}
    """
    machine_score = score_report.get("overall_soft_score", 0.5)

    # 机器预测分类
    if machine_score >= 0.8:
        prediction = "HIGH"
    elif machine_score >= 0.5:
        prediction = "MEDIUM"
    else:
        prediction = "LOW"

    # 实际表现分类（复用 performance_attribution 的逻辑）
    perf_result = performance_attribution(performance, narration_file, produce_delta=False)
    perf_causes = perf_result.get("causes", [])

    has_high_cause = any(c.get("severity") == "HIGH" for c in perf_causes)
    has_any_cause = len(perf_causes) > 0

    if has_high_cause:
        outcome = "LOW"
    elif has_any_cause:
        outcome = "MEDIUM"
    else:
        outcome = "HIGH"

    # 人类评分交叉验证
    human_signal = ""
    weakest_stage = ""
    if human_scores:
        overall_human = human_scores.get("overall", 3)
        weakest = human_scores.get("weakest_link", "")
        if overall_human <= 2:
            outcome = "LOW"
            human_signal = f"人类整体评分 {overall_human}/5"
        elif overall_human == 3:
            if outcome == "HIGH":
                outcome = "MEDIUM"
            human_signal = f"人类整体评分 {overall_human}/5"

        # 从最薄弱环节映射到 stage
        weakest_map = {
            "hook": "stage3-scenes",
            "文案": "stage3-scenes",
            "配音": "stage4-audio",
            "画面": "stage6-production",
            "节奏": "stage3-scenes",
        }
        weakest_stage = weakest_map.get(weakest, "")

    # 判定校准方向
    prediction_rank = {"HIGH": 3, "MEDIUM": 2, "LOW": 1}
    diff = prediction_rank.get(prediction, 2) - prediction_rank.get(outcome, 2)

    if diff > 0:
        verdict = "OVERESTIMATED"
    elif diff < 0:
        verdict = "UNDERESTIMATED"
    else:
        verdict = "CONSISTENT"

    # 诊断
    diagnosis_parts = []
    diagnosis_parts.append(f"机器预测 {prediction}（score={machine_score:.2f}），实际 {outcome}")
    if human_signal:
        diagnosis_parts.append(human_signal)
    if weakest_stage:
        diagnosis_parts.append(f"最薄弱环节: {human_scores.get('weakest_link', '')} → {weakest_stage}")

    # 找偏差最大的 stage
    phases = score_report.get("phases", {})
    stage_diagnosis = ""
    if verdict != "CONSISTENT" and phases:
        min_stage = min(phases.items(), key=lambda x: x[1].get("soft_score", 1.0))
        stage_diagnosis = f"最低 stage: {min_stage[0]}（soft_score={min_stage[1].get('soft_score', 1.0):.2f}）"

    diagnosis = "；".join(diagnosis_parts)
    if stage_diagnosis:
        diagnosis += "；" + stage_diagnosis

    # 校准动作
    action = None
    delta_path = None
    if verdict == "OVERESTIMATED" and produce_delta:
        # 机器高估 → 收紧规则
        target = weakest_stage or "gate_checker"
        action = {
            "type": "STRENGTHEN_RULE",
            "target": target,
            "detail": f"机器高估（{prediction}→{outcome}），需收紧 {target} 的 gate 阈值/权重",
        }
        delta = create_delta(
            operation="ADDED",
            source="calibrate_machine_scoring",
            confidence=0.70,
            target_rule_id=f"R-CAL-{target}",
            new_rule_raw={
                "id": f"R-CAL-{target}",
                "type": "FORBIDDEN_LOGIC",
                "pattern": f"{target} 的 gate checker 评分偏高，需校准阈值",
                "positive": f"校准 {target} 的 gate checker 阈值，使其更准确反映实际表现",
                "severity": "SOFT",
                "class": "EXPERIENTIAL",
                "scope": "SKILL",
            },
            reason=f"机器评分校准: {diagnosis[:100]}",
        )
        delta["requires_human_review"] = True
        delta_path = str(save_delta(delta))

    elif verdict == "UNDERESTIMATED" and produce_delta:
        # 机器低估 → 放松过严规则（仅 EXPERIENTIAL）
        target = weakest_stage or "gate_checker"
        action = {
            "type": "DEPRECATED",
            "target": target,
            "detail": f"机器低估（{prediction}→{outcome}），{target} 可能过严",
        }

    return {
        "machine_prediction": prediction,
        "actual_outcome": outcome,
        "verdict": verdict,
        "diagnosis": diagnosis,
        "action": action,
        "delta_path": delta_path,
        "requires_human_review": verdict != "CONSISTENT",
    }


def main():
    parser = argparse.ArgumentParser(description="ClipForge 归因引擎")
    parser.add_argument("--trace-file", required=True)
    parser.add_argument("--rules-dir", default=None)
    parser.add_argument("--no-delta", action="store_true", help="不产出 Delta 文件")
    args = parser.parse_args()

    result = analyze_trace(
        Path(args.trace_file),
        Path(args.rules_dir) if args.rules_dir else None,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
