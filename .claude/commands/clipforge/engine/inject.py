"""注入生成器 — 生成约束 prompt 段（正向重述 + 经验模式 + Guard Red Flags）。

根据 Skill 的 rigor 级别控制注入内容：
- LITE: 仅 HARD 规则
- STANDARD: 全量规则 + 经验模式
- STRICT: 全量 + Red Flags + spirit_vs_letter 声明
"""
from __future__ import annotations
import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from engine.lib.rule_parser import load_skill, load_rules_by_scope, RULES_DIR, SKILLS_DIR
from engine.lib.models import Severity, Rigor, Rule, RuleClass
from engine.lib.positive_rewrite import rewrite_rule
from engine.lib.delta import load_deltas, apply_delta_to_rules


def merge_rules(rules: list[Rule]) -> list[Rule]:
    """按 ID 去重，SAFETY 规则不可覆盖，EXPERIENTIAL 后声明的优先。"""
    seen: dict[str, Rule] = {}
    for r in rules:
        if r.id in seen:
            existing = seen[r.id]
            if existing.rule_class == RuleClass.SAFETY:
                continue
        seen[r.id] = r
    return list(seen.values())


def _gate_anchor(rule: Rule) -> str:
    """从 source 字段提取 gate checker 名（如 check_portrait_typography）。

    rules 的 source 若标注 'engine/gate.py check_xxx'，则该规则有机器 gate 拦截。
    返回 checker 名；无则返回空串（规则靠自觉，无机器拦截）。
    这让 LLM 推理时能区分「违反即被机器拦截」与「靠自觉的硬约束」。
    """
    m = re.search(r'\bcheck_\w+', rule.source or '')
    return m.group() if m else ''


def load_patterns_meta(category: str | None = None, skill_name: str | None = None,
                       patterns_dir: Path | None = None, force_ids: set[str] | None = None) -> list[dict]:
    """返回注入 pattern 的元数据列表，供 generate_injection 落盘 injected_patterns.json（采纳追溯基建）。

    过滤逻辑与 load_patterns 完全一致（老化/category/skill_scope/status），但返回
    [{id, kind, weight, skill_scope, text}]：kind=pref|fewshot，便于追溯本次注入了哪些 pattern。
    """
    from datetime import datetime, timedelta

    MAX_AGE_DAYS = 90
    from engine.lib.data_paths import all_pattern_files
    files = all_pattern_files() if patterns_dir is None else sorted(patterns_dir.glob("*.yaml"))
    metas: list[dict] = []
    for fp in files:
        import yaml
        mtime = datetime.fromtimestamp(fp.stat().st_mtime)
        if (datetime.now() - mtime).days > MAX_AGE_DAYS:
            continue
        with open(fp, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        if not data:
            continue
        if category and data.get("category") != category and data.get("category") is not None:
            continue
        pid = data.get("id") or fp.stem
        _parts = pid.split("-", 2)
        _dim = _parts[1] if (len(_parts) >= 3 and _parts[0] == "P"
                             and _parts[1] in ("topic", "hook", "cover", "narration")) else None
        scope_raw = data.get("skill_scope")
        # skill_scope 过滤；force_ids（exploration explore 模式）绕过 skill_scope，但不绕过 deprecated/老化
        if skill_name and scope_raw and pid not in (force_ids or set()):
            scopes = [s.strip() for s in str(scope_raw).split(",") if s.strip()]
            if skill_name not in scopes:
                continue
        if (data.get("status") or (data.get("evidence") or {}).get("status")) == "deprecated":
            continue
        if "as_preference" in data:
            pref = data["as_preference"]
            metas.append({"id": pid, "kind": "pref", "weight": pref.get("weight", "MEDIUM"),
                          "skill_scope": scope_raw or "", "dim": _dim, "text": pref.get("text", "")})
        if "as_fewshot" in data:
            metas.append({"id": pid, "kind": "fewshot", "weight": "", "skill_scope": scope_raw or "",
                          "dim": _dim, "text": data["as_fewshot"].get("example_output", "")[:200]})
    return [m for m in metas if m.get("text")]


def load_patterns(category: str | None = None, skill_name: str | None = None,
                  patterns_dir: Path | None = None) -> list[str]:
    """注入 pattern 文本列表（向后兼容：返回纯文本，丢弃元数据）。"""
    return [m["text"] for m in load_patterns_meta(category, skill_name, patterns_dir)]


def _load_dimension_weights() -> dict:
    """读 dimension_weights.yaml（topic/hook/cover/narration 维度权重）。缺文件返回全 1.0。

    供 generate_injection 计算 effective_rank = pattern_weight_rank × dim_weight，
    让维度权重 + pattern weight 真正影响注入排序/标注（而非仅追溯记录）。
    """
    from engine.lib.data_paths import dimension_weights_file
    fp = dimension_weights_file()
    default = {"topic": 1.0, "hook": 1.0, "cover": 1.0, "narration": 1.0}
    if not fp.exists():
        return default
    try:
        import yaml
        d = yaml.safe_load(fp.read_text("utf-8")) or {}
        return {k: float(d.get(k, 1.0)) for k in default}
    except Exception:
        return default


def generate_injection(
    skill_name: str,
    category: str | None = None,
    rules_dir: Path | None = None,
    skills_dir: Path | None = None,
    patterns_dir: Path | None = None,
    project_dir: Path | None = None,
) -> str:
    rules_dir = rules_dir or RULES_DIR
    skills_dir = skills_dir or SKILLS_DIR

    # 读 exploration directive（探索-利用策略 + explore force 注入依据）
    directive = None
    if project_dir is not None:
        try:
            import yaml as _yaml
            df = Path(project_dir) / "exploration_directive.yaml"
            if df.exists():
                directive = _yaml.safe_load(df.read_text("utf-8")) or {}
        except Exception:
            directive = None
    force_ids: set[str] = set()
    if directive and directive.get("mode") == "explore":
        force_ids = {p.get("id") for p in (directive.get("target_patterns") or []) if p.get("id")}

    skill = load_skill(skill_name, skills_dir)
    rules = load_rules_by_scope(skill_name if skill else None, category, rules_dir)

    if skill:
        skill_rules: list = []
        for ref in skill.boundary.rule_refs:
            if isinstance(ref, str) and ref.endswith("*"):
                prefix = ref.rstrip("*")
                skill_rules.extend([r for r in rules if r.id.startswith(prefix)])
            elif isinstance(ref, str):
                skill_rules.extend([r for r in rules if r.id == ref])
            elif isinstance(ref, dict) and "ref" in ref:
                rref = ref["ref"]
                if rref.endswith("*"):
                    prefix = rref.rstrip("*")
                    skill_rules.extend([r for r in rules if r.id.startswith(prefix)])
                else:
                    skill_rules.extend([r for r in rules if r.id == rref])
        rules = merge_rules(skill_rules)

    # 应用高置信度 Delta（无需人工审核 + 观察期已过）
    DEFAULT_OBSERVATION_DAYS = 7
    _applied_deltas: list[str] = []
    from datetime import datetime as _dt, timezone as _tz
    try:
        deltas = load_deltas()
        auto_deltas = []
        for d in deltas:
            dd = d.get("delta", d)
            if dd.get("confidence", 0) < 0.70:
                continue
            # requires_human_review 可能在外层（attribution 写法）或内层（手动设置）
            needs_review = d.get("requires_human_review", dd.get("requires_human_review", True))
            if needs_review:
                continue
            # 观察期：从 Delta 元数据读取，默认 7 天
            obs_days = dd.get("observation_days", DEFAULT_OBSERVATION_DAYS)
            created = dd.get("created_at", "")
            if created:
                try:
                    created_dt = _dt.fromisoformat(created)
                    age_days = (_dt.now(_tz.utc) - created_dt).days
                    if age_days < obs_days:
                        continue
                except (ValueError, TypeError):
                    continue  # 日期解析失败 → 不自动应用
            auto_deltas.append(d)

        # 去重：同 target_rule 只保留 created_at 最新的
        _by_target: dict[str, dict] = {}
        for d in auto_deltas:
            dd = d.get("delta", d)
            target = dd.get("target_rule", "")
            created = dd.get("created_at", "")
            if target in _by_target:
                if created > _by_target[target]["created_at"]:
                    # 新的更新，替换旧的
                    auto_deltas.remove(_by_target[target]["ref"])
                    _by_target[target] = {"created_at": created, "ref": d}
            else:
                _by_target[target] = {"created_at": created, "ref": d}

        for delta in auto_deltas:
            dd = delta.get("delta", delta)
            rules = apply_delta_to_rules(rules, delta)
            _applied_deltas.append(dd.get("id", "unknown"))
    except Exception:
        pass

    rigor = skill.rigor_level if skill else Rigor.STANDARD

    hard_rules = [r for r in rules if r.severity == Severity.HARD]
    soft_rules = [r for r in rules if r.severity == Severity.SOFT]

    lines: list[str] = []

    # Intent（所有严谨度都注入）
    if skill:
        lines.append(f"## 目标\n{skill.intent.objective}\n")
        if skill.intent.criteria:
            lines.append("## 成功标准")
            for c in skill.intent.criteria:
                lines.append(f"- {c}")
            lines.append("")

    # HARD 规则（所有严谨度都注入）
    lines.append("## 行为准则（必须遵守）")
    for r in hard_rules:
        rw = rewrite_rule(r)
        gate = _gate_anchor(r)
        anchor = f" · 机器拦截: {gate}" if gate else ""
        guard = f"（自检: {rw['guardrail']}）" if rw.get('guardrail') else ""
        lines.append(f"- **[HARD{anchor}]** {rw['positive']} {guard}")
    lines.append("")

    # SOFT 规则（STANDARD 和 STRICT 注入）
    if rigor in (Rigor.STANDARD, Rigor.STRICT) and soft_rules:
        lines.append("## 参考偏好（建议遵守）")
        for r in soft_rules:
            rw = rewrite_rule(r)
            gate = _gate_anchor(r)
            anchor = f" · 机器检查: {gate}" if gate else ""
            guard = f"（自检: {rw['guardrail']}）" if rw.get('guardrail') else ""
            lines.append(f"- [SOFT{anchor}] {rw['positive']} {guard}")
        lines.append("")

    # Skill 声明的偏好（STANDARD 和 STRICT 注入）
    if rigor in (Rigor.STANDARD, Rigor.STRICT) and skill and skill.boundary.preferences:
        lines.append("## 偏好引导（来自 Skill 声明和历史经验）")
        for pref in skill.boundary.preferences:
            lines.append(f"- [{pref.weight}] {pref.text}")
        lines.append("")

    # 经验模式（STANDARD 和 STRICT 注入）
    pattern_metas: list[dict] = []
    if rigor in (Rigor.STANDARD, Rigor.STRICT):
        pattern_metas = load_patterns_meta(category, skill_name=skill_name,
                                           patterns_dir=patterns_dir, force_ids=force_ids)
        # 探索-利用策略引导（软引导，LLM 自由发挥区）
        if directive:
            dmode = directive.get("mode", "exploit")
            dtargs = [p.get("id", "") for p in (directive.get("target_patterns") or [])]
            if dmode == "explore":
                lines.append("## 本次制作策略：探索（主动采集冷门维度数据）")
                lines.append(f"本次刻意探索低数据维度：{', '.join(dtargs)}。选题/钩子/封面优先尝试这些维度，")
                lines.append("即使历史上非最优——目的是为自进化采集真实表现数据，拓宽经验池。\n")
            else:
                lines.append("## 本次制作策略：利用（采用当前最强经验组合）")
                lines.append(f"优先采用高权重经验：{', '.join(dtargs)}。\n")
        if pattern_metas:
            # 按维度权重 × pattern weight 的 effective_rank 排序 + 优先级标注（让 weight 真正生效）
            _dim_w = _load_dimension_weights()
            _WR = {"HIGH": 3, "MEDIUM": 2, "LOW": 1}
            def _eff(m):
                dw = _dim_w.get(m.get("dim"), 1.0) if m.get("dim") else 1.0
                return _WR.get(m.get("weight", "MEDIUM"), 2) * dw
            lines.append("## 成功经验（来自历史高分案例，供参考）")
            for m in sorted(pattern_metas, key=_eff, reverse=True):
                eff = _eff(m)
                prefix = "[优先采用] " if eff >= 3 else ("[次要参考] " if eff <= 1.5 else "")
                lines.append(f"- {prefix}{m['text']}")
            lines.append("")

    # Guard Red Flags（ALL 注入——认知守卫对所有调度 LLM 普遍生效，无死声明）
    # 注：全量注入是密度代价（如 stage6 17 条守卫占 inject prompt ~21%），但每条 red_flags
    # 都有独占认知价值（gate 事后拦截无法替代的"事前反合理化"），收益 > token 成本，非冗余。
    if skill and skill.guard_red_flags:
        lines.append("## 行为守卫（当以下念头出现时，立即 STOP）")
        lines.append("| 当你产生这个念头 | 现实是 | 触发场景 |")
        lines.append("|---|---|---|")
        for rf in skill.guard_red_flags:
            lines.append(f"| {rf.get('thought', '')} | {rf.get('reality', '')} | {rf.get('trigger', '')} |")
        lines.append("任何 Red Flag 触发 → 暂停当前行为，回到约束检查。\n")

    # spirit_vs_letter LETTER 声明（STANDARD+ 注入，协议域核心约束）
    # SPIRIT 声明保留在 STRICT（生成域引导，非强制）
    if rigor in (Rigor.STANDARD, Rigor.STRICT) and skill and skill.spirit_vs_letter:
        letter_entries = [sl for sl in skill.spirit_vs_letter if sl.mode.value == "LETTER"]
        if letter_entries:
            lines.append("## 流程约束（必须按字面精确遵守）")
            for sl in letter_entries:
                lines.append(f"- 规则 {sl.rule_ref}: **按字面精确匹配** — {sl.intent}")
            lines.append("")

    # spirit_vs_letter SPIRIT 声明（仅 STRICT 注入）
    if rigor == Rigor.STRICT and skill and skill.spirit_vs_letter:
        spirit_entries = [sl for sl in skill.spirit_vs_letter if sl.mode.value == "SPIRIT"]
        if spirit_entries:
            lines.append("## 内容引导（按意图灵活解释）")
            for sl in spirit_entries:
                lines.append(f"- 规则 {sl.rule_ref}: 按意图解释 — {sl.intent}")
            lines.append("")

    # 应用日志：gate.py / trace 系统可追踪哪些 Delta 实际参与
    if _applied_deltas:
        lines.append(f"<!-- INJECT_META: applied_deltas={_applied_deltas} -->")

    # 采纳追溯基建：落盘本次注入的 pattern 元数据。
    # 语义=注入候选集（确定性），非 LLM 采纳确认——采纳判定交给回归对比"注入组 vs 未注入组"表现。
    if project_dir is not None:
        try:
            from datetime import datetime as _dt2, timezone as _tz2
            proj = Path(project_dir)
            proj.mkdir(parents=True, exist_ok=True)
            meta_payload = {
                "source": "realtime",  # 实时注入（区别于 backfill 推导的历史视频）
                "skill": skill_name, "category": category,
                "generated_at": _dt2.now(_tz2.utc).isoformat(),
                "injected_patterns": [
                    {"id": m["id"], "kind": m["kind"], "weight": m.get("weight", ""),
                     "skill_scope": m.get("skill_scope", "")} for m in pattern_metas
                ],
                "applied_deltas": _applied_deltas,
            }
            (proj / "injected_patterns.json").write_text(
                json.dumps(meta_payload, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            pass

    # 新鲜度预警（防同质化，P0-3）—— 引导 LLM 主动避开近期重复
    if project_dir is not None:
        try:
            from engine.freshness import recent_context
            ctx = recent_context(project_dir)
            fr = ctx.get("freshness") or {}
            if fr.get("compared_with", 0) > 0:
                sec = ["## 新鲜度预警（防同质化 — 主动差异化）"]
                sec.append(
                    f"- 与近 {fr['compared_with']} 期相似度：hook {fr.get('hook_sim',0):.0%}"
                    f" / 项目集 {fr.get('project_jaccard',0):.0%}"
                    f" / 叙事模板 {fr.get('template_sim',0):.0%}"
                    f"（主导：{fr.get('most_similar_dim','none')}）"
                )
                rh = ctx.get("recent_hooks") or []
                if rh:
                    sec.append("- 近期已用 hook（避开相似句式/数字锚点）：")
                    for h in rh[:5]:
                        sec.append(f"  · {h}")
                tp = ctx.get("top_projects") or []
                if tp:
                    sec.append(f"- 近期高频项目（避免重复展开，可一带而过）：{', '.join(tp[:6])}")
                sec.append("- 本次选题/钩子请主动差异化：换题材角度、换数字锚点、换叙事结构")
                lines.append("\n".join(sec))
                lines.append("")
        except Exception:
            pass

    return "\n".join(lines)


def main():
    # 防 Windows GBK：inject 输出含中文（red_flags/规则正向重述），强制 UTF-8 供 cron SubAgent 正确读取
    # 放 main 内（非模块顶层）——避免 import inject 时副作用改调用方 stdout
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass
    parser = argparse.ArgumentParser(description="ClipForge 注入生成器")
    parser.add_argument("--skill", required=True)
    parser.add_argument("--category", default=None)
    parser.add_argument("--rules-dir", default=None)
    parser.add_argument("--skills-dir", default=None)
    parser.add_argument("--patterns-dir", default=None)
    parser.add_argument("--project-dir", default=None, help="项目目录：写入 injected_patterns.json（采纳追溯）")
    parser.add_argument("--format", choices=["text", "json"], default="text")
    args = parser.parse_args()

    injection = generate_injection(
        args.skill, args.category,
        Path(args.rules_dir) if args.rules_dir else None,
        Path(args.skills_dir) if args.skills_dir else None,
        Path(args.patterns_dir) if args.patterns_dir else None,
        Path(args.project_dir) if args.project_dir else None,
    )
    if args.format == "json":
        print(json.dumps({"injection": injection}, ensure_ascii=False, indent=2))
    else:
        print(injection)


if __name__ == "__main__":
    main()
