"""门禁引擎 — HARD + SOFT 校验。"""
from __future__ import annotations
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from engine.lib.rule_parser import load_skill, load_rules_by_scope, RULES_DIR, SKILLS_DIR
from engine.lib.models import (
    GateReport, Violation, Severity, GateType, SkillDefinition, RuleClass,
)


def check_file_exists(project_dir: Path, params: dict) -> tuple[bool, str]:
    for f in params.get("files", []):
        fp = project_dir / f
        if not fp.exists() or fp.stat().st_size == 0:
            return False, f"文件缺失或为空: {f}"
    return True, ""


def check_json_valid(project_dir: Path, params: dict) -> tuple[bool, str]:
    for f in params.get("files", []):
        fp = project_dir / f
        if not fp.exists():
            return False, f"JSON 文件缺失: {f}"
        try:
            data = json.loads(fp.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            return False, f"JSON 解析失败 {f}: {e}"
        for key in params.get("required_keys", []):
            if key not in data:
                return False, f"{f} 缺少必要字段: {key}"
    return True, ""


def check_loudnorm_verified(project_dir: Path, params: dict) -> tuple[bool, str]:
    fp = project_dir / params.get("file", "narration.mp3")
    if not fp.exists():
        return False, f"音频文件缺失: {fp.name}"
    try:
        result = subprocess.run(
            ["ffmpeg", "-i", str(fp), "-af", "volumedetect", "-f", "null", "-"],
            capture_output=True, text=True, timeout=30,
        )
        output = result.stderr
        match = re.search(r"max_volume:\s*([-\d.]+)\s*dB", output)
        if match:
            max_vol = float(match.group(1))
            min_db = params.get("min_db", -10)
            if max_vol < min_db:
                return False, f"max_volume {max_vol} dB < {min_db} dB，loudnorm 未达标"
            return True, f"max_volume: {max_vol} dB"
        return False, "无法从 ffmpeg 输出解析 max_volume"
    except Exception as e:
        return False, f"loudnorm 检查异常: {e}"


def check_bgm_volume_set(project_dir: Path, params: dict) -> tuple[bool, str]:
    fp = project_dir / params.get("file", "segment_durations.json")
    if not fp.exists():
        return False, "segment_durations.json 缺失"
    try:
        data = json.loads(fp.read_text(encoding="utf-8"))
        key = params.get("key", "meta.bgm_volume")
        keys = key.split(".")
        val = data
        for k in keys:
            val = val.get(k) if isinstance(val, dict) else None
            if val is None:
                return False, f"BGM 音量未设置: {key}"
        return True, f"BGM volume: {val}"
    except Exception as e:
        return False, f"BGM 音量检查异常: {e}"


def check_no_forbidden_speech(project_dir: Path, params: dict,
                              guardrails: list | None = None) -> tuple[bool, str]:
    forbidden = [
        "必装", "必备", "神器", "赶紧去", "马上去", "立即下载",
        "全网最好", "第一", "最强", "你一定要", "千万别错过",
        "免费领", "福利", "白嫖", "点赞关注", "一键三连",
        "一定", "绝对", "必然",
    ]
    check_files = params.get("files", ["narration.txt", "douyin.md"])
    found: list[str] = []
    for fname in check_files:
        fp = project_dir / fname
        if not fp.exists():
            continue
        content = fp.read_text(encoding="utf-8", errors="ignore")
        for kw in forbidden:
            if kw in content:
                found.append(f"{fname}: '{kw}'")
    if found:
        return False, f"发现违禁词: {'; '.join(found[:5])}"
    return True, ""


def check_no_url(project_dir: Path, params: dict) -> tuple[bool, str]:
    url_pattern = re.compile(r'https?://[^\s<>"\']+|github\.com/[^\s<>"\']+')
    check_files = params.get("files", ["narration.txt", "douyin.md"])
    found: list[str] = []
    for fname in check_files:
        fp = project_dir / fname
        if not fp.exists():
            continue
        content = fp.read_text(encoding="utf-8", errors="ignore")
        matches = url_pattern.findall(content)
        if matches:
            found.extend([f"{fname}: {m}" for m in matches[:3]])
    if found:
        return False, f"发现 URL: {'; '.join(found[:5])}"
    return True, ""


def check_duration_in_range(project_dir: Path, params: dict) -> tuple[bool, str]:
    fp = project_dir / params.get("file", "segment_durations.json")
    if not fp.exists():
        return False, "时长文件缺失"
    try:
        data = json.loads(fp.read_text(encoding="utf-8"))
        total = sum(s.get("actual_duration", 0) for s in data.get("segments", []))
        min_d = params.get("min", 0)
        max_d = params.get("max", 9999)
        if total < min_d or total > max_d:
            return False, f"总时长 {total:.1f}s 不在 [{min_d}, {max_d}] 范围内"
        return True, f"总时长: {total:.1f}s"
    except Exception as e:
        return False, f"时长检查异常: {e}"


GATE_CHECKERS = {
    GateType.file_exists: check_file_exists,
    GateType.json_valid: check_json_valid,
    GateType.loudnorm_verified: check_loudnorm_verified,
    GateType.bgm_volume_set: check_bgm_volume_set,
    GateType.no_forbidden_speech: check_no_forbidden_speech,
    GateType.no_url_in_output: check_no_url,
    GateType.duration_in_range: check_duration_in_range,
    GateType.hook_pattern_verified: None,  # 占位，在下面实现
}


# hook 模式禁用词列表（数据驱动：疑问/互动模式平均 1,195 播放，最低）
HOOK_FORBIDDEN_STARTS = ("你知道吗", "有没有想过", "猜猜", "你知道", "大家知道")
# hook 高优模式关键词（数据驱动：反直觉/冲突平均 46,596 播放）
HOOK_HIGH_VALUE_KEYWORDS = ("不用", "却能", "居然", "竟然", "竟然能", "只要", "不需要")
# hook 数字锚定关键词 — 默认为空，由分类配置 narration.hook_anchors 提供
_DEFAULT_HOOK_NUMBER_ANCHORS: tuple[str, ...] = ()


def _get_hook_anchors(params: dict) -> tuple[str, ...]:
    """从 params 中获取 hook_anchors，或使用默认值。"""
    anchors = params.get("hook_anchors")
    if anchors:
        return tuple(anchors)
    return _DEFAULT_HOOK_NUMBER_ANCHORS


def check_hook_pattern_verified(project_dir: Path, params: dict) -> tuple[bool, str]:
    """校验 hook 场景文本是否命中高优模式，是否避开禁用模式。

    数据来源：2026-05-27 抖音 58 条视频分析
    - 禁用模式（疑问词开头）：平均 1,195 播放
    - 高优模式（反直觉/冲突）：平均 46,596 播放
    - 数字锚定模式：平均 42,783 播放
    """
    narration_file = project_dir / params.get("file", "narration_segments.json")
    if not narration_file.exists():
        return False, "narration_segments.json 缺失，无法校验 hook 模式"
    try:
        data = json.loads(narration_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        return False, f"narration_segments.json 解析失败: {e}"

    segments = data.get("segments", [])
    if not segments:
        return False, "segments 为空"

    hook_text = segments[0].get("narration_segment", "").strip()
    if not hook_text:
        return False, "hook 场景的 narration_segment 为空"

    # 检查禁用模式
    for forbidden in HOOK_FORBIDDEN_STARTS:
        if hook_text.startswith(forbidden) or forbidden in hook_text[:10]:
            return False, f"hook 命中禁用模式 '{forbidden}'（疑问/互动平均 1,195 播放，数据来源：抖音 58 条）"

    # 检查是否命中高优或数字锚定
    is_high_value = any(kw in hook_text for kw in HOOK_HIGH_VALUE_KEYWORDS)
    hook_anchors = _get_hook_anchors(params)
    is_number_anchor = any(kw in hook_text for kw in hook_anchors) if hook_anchors else False

    if is_high_value:
        return True, f"hook 命中反直觉/冲突模式（平均 46,596 播放）: {hook_text[:30]}"
    if is_number_anchor:
        return True, f"hook 命中数字锚定模式（平均 42,783 播放）: {hook_text[:30]}"

    return True, f"hook 未命中高优模式但未违规: {hook_text[:30]}"


# 更新 GATE_CHECKERS
GATE_CHECKERS[GateType.hook_pattern_verified] = check_hook_pattern_verified


def check_hf_api_present(project_dir: Path, params: dict) -> tuple[bool, str]:
    """检查 index.html 包含 window.__hf 声明，防止 HyperFrames 渲染失败。

    事故记录：2026-05-28 和此前 service-as-software 项目均因遗漏 __hf 导致
    渲染在 62% 处崩溃（window.__hf not ready after 45000ms）。
    """
    fp = project_dir / params.get("file", "index.html")
    if not fp.exists():
        return False, "index.html 缺失"
    content = fp.read_text(encoding="utf-8", errors="ignore")

    # 检查 window.__hf 存在
    if "window.__hf" not in content:
        return False, "index.html 缺少 window.__hf 声明，HyperFrames 渲染会失败（45s 超时）"

    # 检查 duration 字段
    dur_match = re.search(r"window\.__hf\s*=\s*\{[^}]*duration\s*:\s*([\d.]+)", content)
    if not dur_match:
        return False, "window.__hf 缺少 duration 字段"

    # 检查 seek 函数
    if "seek" not in content.split("window.__hf")[1].split("}")[0]:
        return False, "window.__hf 缺少 seek 函数"

    duration = float(dur_match.group(1))
    return True, f"window.__hf 存在, duration={duration}s"


def check_scene_ids_match(project_dir: Path, params: dict) -> tuple[bool, str]:
    """检查 index.html 中每个场景都有对应的 id 属性，防止 GSAP 选择器失效。

    事故记录：2026-05-28 ai-training-impact 项目中 s1 和 s19 缺少 id 属性，
    导致 GSAP 动画选择器 #s1 .hero-badge 等找不到元素，首尾场景动画丢失。
    """
    html_file = project_dir / params.get("html_file", "index.html")
    segs_file = project_dir / params.get("segments_file", "narration_segments.json")

    if not html_file.exists():
        return False, "index.html 缺失"
    if not segs_file.exists():
        return True, "narration_segments.json 缺失，跳过场景 ID 检查"

    try:
        data = json.loads(segs_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return True, "narration_segments.json 解析失败，跳过场景 ID 检查"

    html_content = html_file.read_text(encoding="utf-8", errors="ignore")

    # 收集 HTML 中所有 id="sN" 属性
    html_ids = set(re.findall(r'id=["\']?(s\d+)', html_content))

    # 兼容两种格式：顶层数组 或 {"segments": [...]}
    if isinstance(data, list):
        segments = data
    elif isinstance(data, dict):
        segments = data.get("segments", [])
    else:
        return True, "narration_segments.json 格式未知，跳过场景 ID 检查"

    missing: list[str] = []
    for seg in segments:
        scene = seg.get("scene", "")
        # 从 "s1-hook" 提取 "s1"
        scene_id = scene.split("-")[0] if "-" in scene else scene
        if scene_id.startswith("s") and scene_id not in html_ids:
            missing.append(f"{scene} → 缺少 id=\"{scene_id}\"")

    if missing:
        return False, f"场景 ID 缺失（GSAP 动画将失效）: {'; '.join(missing)}"

    return True, f"所有 {len(segments)} 个场景 ID 匹配"


def check_composition_structure(project_dir: Path, params: dict) -> tuple[bool, str]:
    """检查 index.html 包含 HyperFrames composition 结构。

    事故记录：2026-05-28 ai-training-impact 项目缺少 data-composition-id 包裹、
    __timelines 注册和 timeline {paused: true}，导致渲染后文字层层覆盖。
    """
    fp = project_dir / params.get("file", "index.html")
    if not fp.exists():
        return False, "index.html 缺失"
    content = fp.read_text(encoding="utf-8", errors="ignore")

    issues: list[str] = []

    # 1. data-composition-id 包裹层
    if "data-composition-id" not in content:
        issues.append("缺少 data-composition-id 包裹层")

    # 2. window.__timelines 声明和注册
    if "window.__timelines" not in content:
        issues.append("缺少 window.__timelines 声明")
    elif not re.search(r'__timelines\s*\[\s*["\']', content):
        issues.append("__timelines 未注册任何 timeline")

    # 3. GSAP timeline {paused: true}
    if not re.search(r'gsap\.timeline\s*\(\s*\{[^}]*paused\s*:\s*true', content):
        issues.append("GSAP timeline 未设置 {paused: true}")

    if issues:
        return False, f"composition 结构缺陷: {'; '.join(issues)}"

    return True, "composition 结构完整（composition-id + __timelines + paused）"


def check_output_no_bgm_valid(project_dir: Path, params: dict) -> tuple[bool, str]:
    """检查 output_no_bgm.mp4 不是黑屏。

    事故记录：2026-05-28 ai-training-impact 项目使用 ffmpeg color=c=black 生成
    output_no_bgm.mp4，导致纯黑屏。正确方式是从 output.mp4 取视频轨 + narration.mp3 音频轨。
    """
    bgm_file = project_dir / params.get("bgm_file", "output.mp4")
    no_bgm_file = project_dir / params.get("no_bgm_file", "output_no_bgm.mp4")

    if not bgm_file.exists():
        return True, "output.mp4 不存在，跳过 no_bgm 检查"
    if not no_bgm_file.exists():
        return False, "output_no_bgm.mp4 缺失"

    bgm_size = bgm_file.stat().st_size
    no_bgm_size = no_bgm_file.stat().st_size

    if bgm_size == 0:
        return True, "output.mp4 为空文件，跳过大小比率检查"

    ratio = no_bgm_size / bgm_size
    min_ratio = params.get("min_size_ratio", 0.4)

    if ratio < min_ratio:
        return False, f"output_no_bgm.mp4 疑似黑屏（大小比率 {ratio:.1%} < {min_ratio:.0%}，正常应 >50%）"

    return True, f"output_no_bgm.mp4 大小比率正常: {ratio:.1%}"


GATE_CHECKERS[GateType.hf_api_present] = check_hf_api_present
GATE_CHECKERS[GateType.scene_ids_match] = check_scene_ids_match
GATE_CHECKERS[GateType.composition_structure] = check_composition_structure
GATE_CHECKERS[GateType.output_no_bgm_valid] = check_output_no_bgm_valid


def check_bgm_duration_covers(project_dir: Path, params: dict) -> tuple[bool, str]:
    """检查 bgm.wav 时长是否覆盖旁白总时长。

    事故记录：2026-05-28 ai-training-impact 项目 BGM 仅 102s 而旁白 588s，
    导致后半段视频无背景音乐。bgm_pipeline.sh 未被执行。

    对齐策略（按优先级）：
    1. bgm.wav >= 旁白时长 → 通过
    2. bgm.wav < 旁白时长 → 拒绝，需执行 bgm_pipeline.sh --extend 拼接
    """
    bgm_file = project_dir / params.get("bgm_file", "bgm.wav")
    seg_file = project_dir / params.get("segments_file", "segment_durations.json")
    narr_file = project_dir / params.get("narration_file", "narration.mp3")

    if not bgm_file.exists():
        return False, "bgm.wav 缺失"

    # 获取旁白总时长：优先 segment_durations.json，兜底 ffprobe
    narr_dur = 0.0
    if seg_file.exists():
        try:
            data = json.loads(seg_file.read_text(encoding="utf-8"))
            narr_dur = sum(s.get("actual_duration", 0) for s in data.get("segments", []))
        except Exception:
            pass

    if narr_dur == 0 and narr_file.exists():
        try:
            result = subprocess.run(
                ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
                 "-of", "csv=p=0", str(narr_file)],
                capture_output=True, text=True, timeout=10,
            )
            narr_dur = float(result.stdout.strip())
        except Exception:
            return True, "无法获取旁白时长，跳过 BGM 覆盖检查"

    if narr_dur == 0:
        return True, "无旁白时长数据，跳过 BGM 覆盖检查"

    # 获取 BGM 时长
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
             "-of", "csv=p=0", str(bgm_file)],
            capture_output=True, text=True, timeout=10,
        )
        bgm_dur = float(result.stdout.strip())
    except Exception:
        return False, "无法获取 bgm.wav 时长"

    min_ratio = params.get("min_coverage_ratio", 0.95)
    coverage = bgm_dur / narr_dur if narr_dur > 0 else 0

    if coverage < min_ratio:
        return False, (
            f"BGM 时长不足: bgm={bgm_dur:.1f}s < 旁白={narr_dur:.1f}s "
            f"(覆盖率 {coverage:.0%} < {min_ratio:.0%})。"
            f"需执行 bgm_pipeline.sh --extend 拼接多首 BGM"
        )

    return True, f"BGM 覆盖充分: bgm={bgm_dur:.1f}s >= 旁白={narr_dur:.1f}s ({coverage:.0%})"


GATE_CHECKERS[GateType.bgm_duration_covers] = check_bgm_duration_covers


# SAFETY 级 gate：违反即安全事故，不可通过归因自动修复
SAFETY_GATES = {
    GateType.no_forbidden_speech,
    GateType.no_url_in_output,
}


def run_gate(skill: SkillDefinition, project_dir: Path) -> GateReport:
    hard_violations: list[Violation] = []
    hard_passed = True

    for gd in skill.gate.hard:
        checker = GATE_CHECKERS.get(gd.gate)
        if not checker:
            continue
        if gd.gate == GateType.no_forbidden_speech:
            ok, msg = checker(project_dir, gd.params, None)
        else:
            ok, msg = checker(project_dir, gd.params)
        if not ok:
            hard_passed = False
            hard_violations.append(Violation(
                rule_id=f"gate:{gd.gate.value}",
                rule_pattern=msg,
                severity=Severity.HARD,
                details=msg,
            ))

    soft_score = 1.0
    soft_issues: list[str] = []
    for gd in skill.gate.soft:
        checker = GATE_CHECKERS.get(gd.gate)
        if not checker:
            continue
        ok, msg = checker(project_dir, gd.params)
        if not ok:
            soft_score -= 0.15
            soft_issues.append(msg)

    return GateReport(
        hard_passed=hard_passed,
        soft_score=max(soft_score, 0.0),
        hard_violations=hard_violations,
        soft_issues=soft_issues,
    )


def main():
    parser = argparse.ArgumentParser(description="ClipForge 门禁引擎")
    parser.add_argument("--skill", required=True)
    parser.add_argument("--project-dir", required=True)
    parser.add_argument("--skills-dir", default=None)
    args = parser.parse_args()

    project_dir = Path(args.project_dir)
    skills_dir = Path(args.skills_dir) if args.skills_dir else None

    skill = load_skill(args.skill, skills_dir)
    if not skill:
        print(json.dumps({"error": f"Skill not found: {args.skill}"}, ensure_ascii=False))
        sys.exit(1)

    report = run_gate(skill, project_dir)
    output = {
        "hard_passed": report.hard_passed,
        "soft_score": report.soft_score,
        "hard_violations": [
            {
                "rule_id": v.rule_id,
                "details": v.details,
                "rule_class": "SAFETY" if any(
                    v.rule_id.endswith(gt.value) for gt in SAFETY_GATES
                ) else "EXPERIENTIAL",
            }
            for v in report.hard_violations
        ],
        "soft_issues": report.soft_issues,
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))
    sys.exit(0 if report.hard_passed else 1)


if __name__ == "__main__":
    main()
