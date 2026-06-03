"""门禁引擎 — HARD + SOFT 校验。"""
from __future__ import annotations
import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
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


def check_root_attributes_complete(project_dir: Path, params: dict) -> tuple[bool, str]:
    """根组合必须包含 data-width 和 data-height，audio 必须包含 data-start。

    事故记录：2026-05-30 VibeCoding 大赏视频 index.html 根组合缺少 data-width/data-height，
    HyperFrames viewport 设置错误 → 100% 黑帧（174s 全黑，21kbps）。
    cover.html 有尺寸属性正常渲染，A/B 实验确认根因。
    """
    fp = project_dir / params.get("file", "index.html")
    if not fp.exists():
        return False, "index.html 缺失"
    content = fp.read_text(encoding="utf-8", errors="ignore")

    issues: list[str] = []

    # 检查根组合 data-width/data-height
    root_pattern = r'<div[^>]*data-composition-id="main"[^>]*>'
    match = re.search(root_pattern, content)
    if not match:
        return False, '未找到 data-composition-id="main" 的根组合'

    root_tag = match.group(0)
    missing = []
    if 'data-width="' not in root_tag:
        missing.append("data-width")
    if 'data-height="' not in root_tag:
        missing.append("data-height")
    if missing:
        issues.append(f"根组合缺少 {', '.join(missing)} → HyperFrames viewport 错误 → 黑帧")

    # 检查 audio 元素的 data-start
    audio_tags = re.findall(r'<audio[^>]*>', content)
    audio_missing = []
    for i, tag in enumerate(audio_tags, 1):
        if 'data-start="' not in tag:
            audio_missing.append(f"audio#{i}")
    if audio_missing:
        issues.append(f'<audio> 元素缺少 data-start="0": {", ".join(audio_missing)}')

    if issues:
        return False, "; ".join(issues)

    return True, "根组合尺寸属性完整（data-width + data-height + audio data-start）"


def check_output_no_bgm_valid(project_dir: Path, params: dict) -> tuple[bool, str]:
    """检查 output_no_bgm.mp4 不是黑屏。

    事故记录：2026-05-28 ai-training-impact 项目使用 ffmpeg color=c=black 生成
    output_no_bgm.mp4，导致纯黑屏。正确方式是从 output.mp4 取视频轨 + narration.mp3 音频轨。
    """
    bgm_file = project_dir / params.get("bgm_file", "output.mp4")
    no_bgm_file = project_dir / params.get("no_bgm_file", "output_no_bgm.mp4")

    if not bgm_file.exists():
        return False, "output.mp4 缺失，无法验证 no_bgm 版本"
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
GATE_CHECKERS[GateType.root_attributes_complete] = check_root_attributes_complete
GATE_CHECKERS[GateType.output_no_bgm_valid] = check_output_no_bgm_valid


def check_bgm_silence_valid(project_dir: Path, params: dict) -> tuple[bool, str]:
    """检查 BGM 在旁白时长范围内无连续静音段。

    集成 scripts/bgm_silence_check.py 的核心逻辑。
    在旁白覆盖范围内，连续 >= 3 秒静音（< -45 dB）即 FAIL。
    """
    sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
    from bgm_silence_check import analyze_bgm

    bgm_file = project_dir / params.get("bgm_file", "bgm.wav")
    seg_file = project_dir / params.get("segments_file", "segment_durations.json")
    silence_db = params.get("silence_db", -45)
    min_silent_blocks = params.get("min_silent_blocks", 3)

    if not bgm_file.exists():
        return False, f"BGM 文件缺失: {bgm_file.name}"
    if not seg_file.exists():
        return False, f"时长文件缺失: {seg_file.name}"

    try:
        seg_data = json.loads(seg_file.read_text(encoding="utf-8"))
        narration_sec = sum(s.get("actual_duration", 0) for s in seg_data.get("segments", []))
    except Exception as e:
        return False, f"读取时长数据失败: {e}"

    if narration_sec <= 0:
        return False, "旁白总时长为 0，无法检查 BGM 覆盖"

    silent_runs, blocks, coverage, check_range = analyze_bgm(
        str(bgm_file), narration_sec,
        silence_db=silence_db,
        min_silent_blocks=min_silent_blocks,
    )

    if silent_runs:
        runs_desc = ", ".join(f"{s}s~{e}s ({l}s)" for s, e, l in silent_runs[:3])
        return False, f"BGM 存在连续静音段: {runs_desc}（覆盖率 {coverage:.0f}%）"

    if coverage < 80:
        return False, f"BGM 音频覆盖率仅 {coverage:.0f}%（阈值 80%）"

    return True, f"BGM 全程有声: {check_range}s 覆盖率 {coverage:.0f}%"


GATE_CHECKERS[GateType.bgm_silence_valid] = check_bgm_silence_valid


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


def check_bgm_not_exceeds_narration(project_dir: Path, params: dict) -> tuple[bool, str]:
    """检查 bgm.wav 时长不超过旁白时长（防止 A/V 漂移）。

    事故记录：2026-05-31 github-trending 视频 BGM 70.92s 而旁白 69.94s，
    HyperFrames discoveredDuration = max(所有音频轨) = BGM 时长，
    导致视频渲染到 70.93s，旁白在 69.94s 结束后出现 ~1s 纯画面无旁白。

    根因：bgm_pipeline.sh TARGET_DUR = 旁白 + 1s 缓冲，使 BGM 系统性地
    比旁白长。HyperFrames 以最长音频轨为视频时长，BGM > 旁白 → 视频延伸。

    本门禁是独立于 bgm_pipeline.sh 的最后防线。
    允许容差 tolerance（默认 0.15s），处理采样精度误差。
    """
    bgm_file = project_dir / params.get("bgm_file", "bgm.wav")
    seg_file = project_dir / params.get("segments_file", "segment_durations.json")
    narr_file = project_dir / params.get("narration_file", "narration.mp3")
    tolerance = params.get("tolerance", 0.15)

    if not bgm_file.exists():
        return False, "bgm.wav 缺失"

    # 获取旁白总时长
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
            return True, "无法获取旁白时长，跳过 BGM 超时检查"

    if narr_dur == 0:
        return True, "无旁白时长数据，跳过 BGM 超时检查"

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

    excess = bgm_dur - narr_dur
    if excess > tolerance:
        return False, (
            f"A/V 漂移风险: bgm={bgm_dur:.2f}s > 旁白={narr_dur:.2f}s "
            f"(超出 {excess:.2f}s > 容差 {tolerance}s)。"
            f"HyperFrames 会以最长音频轨为准渲染，BGM 超长导致视频尾段无旁白。"
            f"修复: ffmpeg -y -i bgm.wav -t {narr_dur:.2f} -c:a pcm_s16le bgm.wav"
        )

    return True, f"BGM 未超旁白: bgm={bgm_dur:.2f}s <= 旁白={narr_dur:.2f}s + {tolerance}s"


GATE_CHECKERS[GateType.bgm_not_exceeds_narration] = check_bgm_not_exceeds_narration


def check_data_duration_source(project_dir: Path, params: dict) -> tuple[bool, str]:
    """检查 HTML data-duration 值与 segment_durations.json 的一致性。

    事故记录：2026-05-30 ai-agent-business-value 10 分钟视频，
    SubAgent 用 narration_segments.json 的 estimated_duration（偏长 16.9%）
    计算动画断点，导致旁白与画面节奏不同步。本门禁确保 HTML 中
    data-duration 值来自 actual_duration 而非 estimated_duration。

    检查项：
    1. HTML 中每个 .clip/data-duration 值与 segment_durations.json 逐段对比
    2. 差值 > tolerance（默认 0.5s）判定为 HARD 失败
    3. HTML 中禁止出现 estimated_duration 关键词（来自上游的泄露）
    """
    html_file = project_dir / params.get("html_file", "index.html")
    seg_file = project_dir / params.get("segments_file", "segment_durations.json")
    tolerance = params.get("tolerance", 0.5)

    if not html_file.exists():
        return False, "index.html 缺失"
    if not seg_file.exists():
        return False, "segment_durations.json 缺失"

    try:
        seg_data = json.loads(seg_file.read_text(encoding="utf-8"))
        actual_durations = [s.get("actual_duration", 0) for s in seg_data.get("segments", [])]
    except Exception as e:
        return False, f"segment_durations.json 解析失败: {e}"

    html_content = html_file.read_text(encoding="utf-8", errors="ignore")

    # 检测 estimated_duration 泄露
    if "estimated_duration" in html_content:
        return False, "index.html 包含 'estimated_duration' 关键词（应为 actual_duration）"

    # 提取 clip 级别的 data-duration 值（排除 root composition）
    html_durations = []
    for m in re.finditer(r'data-duration=["\']?([\d.]+)', html_content):
        tag_start = html_content.rfind('<', 0, m.start())
        tag_end = html_content.find('>', m.start())
        tag = html_content[tag_start:tag_end] if tag_start >= 0 and tag_end >= 0 else ""
        if 'data-composition-id' not in tag:
            html_durations.append(float(m.group(1)))

    if not html_durations:
        return False, "index.html 未找到 data-duration 属性"

    # 逐段对比
    mismatches: list[str] = []
    for i, hd in enumerate(html_durations):
        if i >= len(actual_durations):
            mismatches.append(f"场景{i+1}: HTML 有 {len(html_durations)} 段但 segment_durations 仅 {len(actual_durations)} 段")
            break
        ad = actual_durations[i]
        diff = abs(hd - ad)
        if diff > tolerance:
            mismatches.append(f"场景{i+1}: HTML={hd:.2f}s vs actual={ad:.2f}s (偏差 {diff:.2f}s)")

    if mismatches:
        return False, f"data-duration 不匹配 actual_duration: {'; '.join(mismatches[:6])}"

    return True, f"HTML data-duration 与 actual_duration 一致 ({len(html_durations)} 场景, 容差 {tolerance}s)"


def check_estimation_accuracy(project_dir: Path, params: dict) -> tuple[bool, str]:
    """检查 Stage 3 预估时长与 Stage 4 实测时长的偏差。

    事故记录：2026-05-30 ai-agent-business-value 项目 TTS 使用 +0% 语速
    而非默认 +25%，导致实际时长 508s vs 预估 611s（偏短 16.9%）。
    单段偏差最大 45%。本门禁在 Stage 4 结束后对比两份时长数据，
    发现系统性偏差时发出预警。

    检查项：
    1. 逐段对比 estimated vs actual：单段偏差 > segment_threshold（默认 30%）→ SOFT
    2. 总体偏差 > total_threshold（默认 20%）→ HARD（可能 TTS 配置错误）
    """
    narr_file = project_dir / params.get("narration_file", "narration_segments.json")
    seg_file = project_dir / params.get("segments_file", "segment_durations.json")
    seg_threshold = params.get("segment_threshold", 0.30)
    total_threshold = params.get("total_threshold", 0.20)

    if not narr_file.exists():
        return True, "narration_segments.json 缺失，跳过预估偏差检查"
    if not seg_file.exists():
        return True, "segment_durations.json 缺失，跳过预估偏差检查"

    try:
        narr_data = json.loads(narr_file.read_text(encoding="utf-8"))
        seg_data = json.loads(seg_file.read_text(encoding="utf-8"))
    except Exception:
        return True, "JSON 解析失败，跳过预估偏差检查"

    narr_segs = narr_data if isinstance(narr_data, list) else narr_data.get("segments", [])
    actual_segs = seg_data.get("segments", [])

    if not narr_segs or not actual_segs:
        return True, "段落数据为空，跳过预估偏差检查"

    total_est = 0.0
    total_act = 0.0
    big_deviations: list[str] = []

    for i in range(min(len(narr_segs), len(actual_segs))):
        est = narr_segs[i].get("estimated_duration", 0)
        act = actual_segs[i].get("actual_duration", 0)
        total_est += est
        total_act += act
        if act > 0:
            deviation = abs(est - act) / act
            if deviation > seg_threshold:
                big_deviations.append(
                    f"场景{i+1}: est={est:.1f}s act={act:.1f}s ({deviation:.0%})"
                )

    if total_act == 0:
        return True, "实际总时长为 0，跳过偏差检查"

    total_deviation = abs(total_est - total_act) / total_act

    if total_deviation > total_threshold:
        return False, (
            f"预估/实际总偏差 {total_deviation:.1%} > {total_threshold:.0%} "
            f"(est={total_est:.0f}s act={total_act:.0f}s)，"
            f"可能 TTS 语速配置错误（如用了 +0% 而非 +25%）"
        )

    if big_deviations:
        return True, (
            f"预估总偏差 {total_deviation:.1%} 可接受，"
            f"但 {len(big_deviations)} 段偏差 >{seg_threshold:.0%}: "
            f"{'; '.join(big_deviations[:4])}"
        )

    return True, f"预估偏差正常: 总偏差 {total_deviation:.1%}, 单段偏差均 <{seg_threshold:.0%}"


GATE_CHECKERS[GateType.data_duration_source_valid] = check_data_duration_source
GATE_CHECKERS[GateType.estimation_accuracy_valid] = check_estimation_accuracy


def check_phase_timings_valid(project_dir: Path, params: dict) -> tuple[bool, str]:
    """检查 phase_timings.json 的完整性：phase 时间覆盖完整场景时长，无间隙/重叠。

    事故记录：手工 GSAP 硬编码断点导致旁白与画面不同步（偏差 5-12 秒），
    phase_calibrator.py 自动校准后通过本门禁确保产出完整无遗漏。

    检查项：
    1. phase_timings.json 存在且可解析
    2. 每个 scene 的 phases 覆盖完整 duration（间隙 > max_gap 秒判定为失败）
    3. phase 起止时间无重叠（后一 phase start_offset < 前一 phase end_offset）
    4. 首个 phase start_offset=0，末个 phase end_offset=duration
    """
    pt_file = project_dir / params.get("file", "phase_timings.json")
    max_gap = params.get("max_gap", 0.5)

    if not pt_file.exists():
        return True, "phase_timings.json 不存在（无多 phase 场景或未启用校准，跳过）"

    try:
        pt_data = json.loads(pt_file.read_text(encoding="utf-8"))
    except Exception as e:
        return False, f"phase_timings.json 解析失败: {e}"

    scenes = pt_data.get("scenes", [])
    if not scenes:
        return True, "phase_timings.json 无场景数据，跳过"

    issues: list[str] = []

    for sc in scenes:
        scene_name = sc.get("scene", "?")
        duration = sc.get("duration", 0)
        phases = sc.get("phases", [])

        if not phases:
            continue

        # 首个 phase 应从 0 开始
        if phases[0].get("start_offset", -1) != 0:
            issues.append(f"{scene_name}: 首个 phase start_offset={phases[0].get('start_offset')} (应为 0)")

        # 末个 phase 应覆盖到 duration
        last_end = phases[-1].get("end_offset", 0)
        if duration > 0 and abs(last_end - duration) > max_gap:
            issues.append(f"{scene_name}: 末 phase end_offset={last_end:.2f}s != duration={duration:.2f}s")

        # 逐 phase 检查间隙/重叠
        for i in range(len(phases) - 1):
            cur_end = phases[i].get("end_offset", 0)
            nxt_start = phases[i + 1].get("start_offset", 0)
            gap = nxt_start - cur_end
            if gap > max_gap:
                issues.append(f"{scene_name}: phase {i+1}→{i+2} 间隙 {gap:.2f}s > {max_gap}s")
            elif gap < -0.1:
                issues.append(f"{scene_name}: phase {i+1}→{i+2} 重叠 {-gap:.2f}s")

    if issues:
        return False, f"phase_timings 校验失败: {'; '.join(issues[:6])}"

    return True, f"phase_timings 完整: {len(scenes)} 场景, 间隙 <{max_gap}s"


def check_phase_anchor_coverage(project_dir: Path, params: dict) -> tuple[bool, str]:
    """检查 phase 校准覆盖率：auto-split 场景占比过高时发出 SOFT 警告。

    narration_anchor 是 Stage 3 人工标注的句子索引，phase_calibrator.py
    据此精确定位断点（±50ms）。无 anchor 时回退为按句子数等分（±30%），
    精度大幅下降。本门禁确保 anchor 覆盖率达标。

    检查项：
    1. 统计 anchor_calibrated vs auto_split 场景数
    2. auto_split 占比 > max_auto_ratio（默认 50%）→ SOFT 警告
    """
    pt_file = project_dir / params.get("file", "phase_timings.json")
    max_auto_ratio = params.get("max_auto_ratio", 0.5)

    if not pt_file.exists():
        return True, "phase_timings.json 不存在，跳过 anchor 覆盖检查"

    try:
        pt_data = json.loads(pt_file.read_text(encoding="utf-8"))
    except Exception:
        return True, "phase_timings.json 解析失败，跳过 anchor 覆盖检查"

    stats = pt_data.get("stats", {})
    anchor_count = stats.get("anchor_calibrated", 0)
    auto_count = stats.get("auto_split", 0)
    total = anchor_count + auto_count

    if total == 0:
        return True, "无 phase 校准场景，跳过"

    auto_ratio = auto_count / total

    if auto_count > 0 and auto_ratio > max_auto_ratio:
        return True, (
            f"SOFT: anchor 覆盖率不足: {anchor_count}/{total} 校准, "
            f"{auto_count}/{total} auto-split ({auto_ratio:.0%} > {max_auto_ratio:.0%})。"
            f"建议在 narration_segments.json 的 visual_phases 中添加 narration_anchor"
        )

    if auto_count > 0:
        return True, (
            f"anchor 覆盖率可接受: {anchor_count} 校准 + {auto_count} auto-split "
            f"(auto 比率 {auto_ratio:.0%} <= {max_auto_ratio:.0%})"
        )

    return True, f"全部 {total} 场景均为 anchor 校准（精度 ±50ms）"


GATE_CHECKERS[GateType.phase_timings_valid] = check_phase_timings_valid
GATE_CHECKERS[GateType.phase_anchor_coverage] = check_phase_anchor_coverage


def check_video_bitrate_valid(project_dir: Path, params: dict) -> tuple[bool, str]:
    """检查渲染后的视频码率是否正常，防止黑屏视频通过。

    事故记录：2026-05-30 github-trending 项目 HyperFrames 渲染输出 17 kbps 黑屏视频，
    因 index.html 使用 CSS class 切换可见性而非 GSAP timeline，所有场景 opacity:0。
    1080x1920 正常视频应 > 100 kbps。

    检测策略：
    1. 用 ffprobe 获取视频码率
    2. 低于 min_bitrate_kbps（默认 80 kbps）判定为黑屏/异常
    """
    video_file = project_dir / params.get("file", "output.mp4")
    if not video_file.exists():
        return False, f"视频文件缺失: {params.get('file', 'output.mp4')}"

    try:
        result = subprocess.run(
            ["ffprobe", "-v", "quiet", "-show_entries",
             "format=bit_rate,duration,size:stream=codec_name,width,height",
             "-of", "json", str(video_file)],
            capture_output=True, text=True, timeout=15,
        )
        probe = json.loads(result.stdout)
    except Exception as e:
        return False, f"ffprobe 执行失败: {e}"

    streams = probe.get("streams", [])
    video_stream = next((s for s in streams if s.get("codec_name") in ("h264", "h265", "vp9")), None)
    if not video_stream:
        return False, "未找到视频流"

    width = int(video_stream.get("width", 0))
    height = int(video_stream.get("height", 0))

    # 从 format 获取码率
    fmt = probe.get("format", {})
    bit_rate_str = fmt.get("bit_rate", "0")
    try:
        bit_rate = int(bit_rate_str)
    except (ValueError, TypeError):
        bit_rate = 0

    duration_str = fmt.get("duration", "0")
    try:
        duration = float(duration_str)
    except (ValueError, TypeError):
        duration = 0

    # 如果 format 层没有 bit_rate，用文件大小/时长估算
    if bit_rate == 0 and duration > 0:
        file_size = video_file.stat().st_size
        bit_rate = int((file_size * 8) / duration)

    bitrate_kbps = bit_rate / 1000 if bit_rate else 0
    min_kbps = params.get("min_bitrate_kbps", 80)

    if bitrate_kbps < min_kbps:
        return False, (
            f"视频码率异常: {bitrate_kbps:.0f} kbps < {min_kbps} kbps（疑似黑屏）。"
            f"分辨率 {width}x{height}, 时长 {duration:.1f}s。"
            f"常见原因：index.html 使用 CSS class 切换可见性而非 GSAP timeline"
        )

    return True, f"视频码率正常: {bitrate_kbps:.0f} kbps ({width}x{height}, {duration:.1f}s)"


def check_html_no_css_visibility(project_dir: Path, params: dict) -> tuple[bool, str]:
    """检查 index.html 禁止使用 CSS class 切换场景可见性（HyperFrames 不执行 CSS class 切换）。

    事故记录：2026-05-30 github-trending 项目 index.html 使用:
      .scene-wrap{opacity:0;visibility:hidden}
      .scene-wrap.active{opacity:1;visibility:visible}
    HyperFrames 通过 GSAP timeline seek 驱动，不会添加/移除 CSS class，
    导致所有场景永远 opacity:0 → 黑屏。

    禁止模式：
    1. CSS 中设置 scene-wrap/scene 的 opacity:0 + visibility:hidden，依赖 .active class 切换
    2. 任何 CSS class 切换可见性的模式（.xxx.active / .xxx.show / .xxx.visible）
    """
    fp = project_dir / params.get("file", "index.html")
    if not fp.exists():
        return False, "index.html 缺失"

    content = fp.read_text(encoding="utf-8", errors="ignore")
    issues: list[str] = []

    # 检测 CSS 中 scene 相关选择器设置 opacity:0
    # 匹配 .scene-wrap{...opacity:0...visibility:hidden} 模式
    css_blocks = re.findall(
        r'\.scene[_-]?wrap\s*\{([^}]+)\}', content, re.IGNORECASE
    )
    for block in css_blocks:
        has_opacity_zero = re.search(r'opacity\s*:\s*0(?:\.0+)?\s*(?:;|})', block)
        has_visibility_hidden = re.search(r'visibility\s*:\s*hidden', block)
        if has_opacity_zero and has_visibility_hidden:
            issues.append("scene-wrap 同时设置 opacity:0 + visibility:hidden（HyperFrames 不执行 CSS class 切换）")

    # 检测 .xxx.active / .xxx.show / .xxx.visible 可见性切换模式
    active_patterns = re.findall(
        r'\.\w+\.(?:active|show|visible)\s*\{[^}]*opacity\s*:\s*1', content
    )
    if active_patterns:
        issues.append(f"发现 CSS class 切换可见性模式（{len(active_patterns)} 处），HyperFrames 通过 GSAP seek 驱动，不会切换 class")

    if issues:
        return False, f"R-S6-013: {'; '.join(issues)}。正确方式：GSAP timeline .set()/.fromTo() 控制场景可见性"

    return True, "未检测到 CSS class 可见性切换模式"


GATE_CHECKERS[GateType.video_bitrate_valid] = check_video_bitrate_valid
GATE_CHECKERS[GateType.html_no_css_visibility] = check_html_no_css_visibility


# ═══════════════════════════════════════════════════════════════════════
# HTML 内容级检测器 — R-R-008 / R-R-011 / R-R-012
# ═══════════════════════════════════════════════════════════════════════

def _split_into_scenes(html: str) -> list[tuple[str, str]]:
    """按 id="sN" 切割 HTML，返回 [(scene_id, scene_html), ...]。"""
    markers = [(m.group(1), m.start()) for m in re.finditer(r'\bid="(s\d+)"', html)]
    if not markers:
        return []
    scenes = []
    for i, (sid, start) in enumerate(markers):
        end = markers[i + 1][1] if i + 1 < len(markers) else len(html)
        scenes.append((sid, html[start:end]))
    return scenes


def _extract_layer_chunk(scene_html: str, layer_class: str) -> str:
    """提取 layer-bg / layer-fx 到下一个兄弟 layer 之间的 HTML 片段。"""
    start_match = re.search(rf'class="[^"]*{layer_class}[^"]*"', scene_html)
    if not start_match:
        return ""
    pos = start_match.start()
    rest = scene_html[start_match.end():]
    # 查找下一个兄弟 layer（bg→fx→content 顺序）
    suffix = layer_class.split("-")[-1]
    next_layer = re.search(rf'class="[^"]*layer-(?!{suffix})[^"]*"', rest)
    if next_layer:
        return scene_html[pos:start_match.end() + next_layer.start()]
    return scene_html[pos:]


def _classify_bg_element_types(bg_chunk: str) -> set[str]:
    """分类 bg 层中的视觉元素类型。"""
    types = set()
    if re.search(r'(?<!repeating-)(?:linear|radial)-gradient\s*\(', bg_chunk):
        types.add("gradient")
    if "feTurbulence" in bg_chunk:
        types.add("noise")
    if "repeating-radial-gradient" in bg_chunk:
        types.add("contour")
    if "conic-gradient" in bg_chunk:
        types.add("beams")
    if re.search(r'background-size\s*:\s*\d+px', bg_chunk) and \
       re.search(r'linear-gradient[^;]{0,60}1px[^;]{0,30}transparent', bg_chunk):
        types.add("grid")
    if re.search(r'radial-gradient[^)]{0,200}transparent[^)]{0,200}rgba\(0,\s*0,\s*0', bg_chunk):
        types.add("vignette")
    if re.search(r'filter\s*:\s*blur\(\d+px\)', bg_chunk):
        types.add("glow")
    if re.search(r'ripple|wave', bg_chunk, re.IGNORECASE):
        types.add("wave")
    if re.search(r'scanLine|scan_line|scan-grid', bg_chunk, re.IGNORECASE):
        types.add("scan")
    if re.search(r'background-image\s*:[^;]{0,40}radial-gradient[^;]{0,80}circle[^;]{0,40}\d+px[^;]{0,30}\d+px',
                 bg_chunk):
        types.add("dots")
    return types


def _has_visible_content(chunk: str) -> bool:
    """检查 HTML 片段是否包含可见元素（排除空/注释/opacity:0/display:none）。"""
    cleaned = re.sub(r'<!--.*?-->', '', chunk, flags=re.DOTALL).strip()
    if not cleaned:
        return False
    if not re.search(r'<(?:div|canvas|svg|img|video)\b', cleaned):
        return False
    style = re.search(r'style="([^"]*)"', cleaned)
    if style:
        s = style.group(1)
        if re.search(r'(?:^|;)\s*opacity\s*:\s*0(?:\.0+)?\s*(?:;|$|"|)', s):
            return False
        if re.search(r'display\s*:\s*none', s):
            return False
    return True


def _bg_style_fingerprint(bg_chunk: str) -> str:
    """生成 bg 层的风格指纹（元素类型 + 主色），用于相邻场景对比。"""
    types = ",".join(sorted(_classify_bg_element_types(bg_chunk)))
    colors = sorted(set(re.findall(r'#[0-9a-fA-F]{6}\b', bg_chunk)))
    return f"{types}|{'|'.join(colors)}"


def check_bg_visual_diversity(project_dir: Path, params: dict) -> tuple[bool, str]:
    """R-R-011: bg 层必须 ≥2 种视觉元素类型，禁止 glow+grid 三件套。"""
    fp = project_dir / params.get("file", "index.html")
    if not fp.exists():
        return False, "index.html 缺失"
    html = fp.read_text(encoding="utf-8", errors="ignore")
    scenes = _split_into_scenes(html)
    if not scenes:
        return True, "无场景可检查"
    violations = []
    for sid, scene_html in scenes:
        bg = _extract_layer_chunk(scene_html, "layer-bg")
        if not bg.strip():
            continue
        types = _classify_bg_element_types(bg)
        # 禁止模式：仅 glow+grid 三件套
        if types and types <= {"gradient", "glow", "grid"}:
            violations.append(f"{sid}: glow+grid 三件套 ({', '.join(sorted(types))})")
        elif len(types) < 2:
            violations.append(f"{sid}: 类型不足 ({', '.join(sorted(types)) or '空'})")
    if violations:
        return False, f"R-R-011: {'; '.join(violations[:6])}"
    return True, f"{len(scenes)} 场景 bg 视觉多样性合格"


def check_adjacent_bg_diversity(project_dir: Path, params: dict) -> tuple[bool, str]:
    """R-R-012: 相邻场景 bg 必须有可区分的视觉差异。"""
    fp = project_dir / params.get("file", "index.html")
    if not fp.exists():
        return False, "index.html 缺失"
    html = fp.read_text(encoding="utf-8", errors="ignore")
    scenes = _split_into_scenes(html)
    if len(scenes) < 2:
        return True, "场景数不足，跳过相邻检查"
    fps = []
    for sid, scene_html in scenes:
        bg = _extract_layer_chunk(scene_html, "layer-bg")
        fps.append((sid, _bg_style_fingerprint(bg) if bg.strip() else ""))
    violations = []
    for i in range(len(fps) - 1):
        if fps[i][1] and fps[i][1] == fps[i + 1][1]:
            violations.append(f"{fps[i][0]}↔{fps[i+1][0]}")
    unique_styles = len(set(fp for _, fp in fps if fp))
    min_styles = max(len(scenes) // 5, 3)
    if violations:
        return False, (
            f"R-R-012: {len(violations)} 对相邻同质 "
            f"({unique_styles} 种风格/{len(scenes)} 场景, 需≥{min_styles}); "
            f"{'; '.join(violations[:4])}"
        )
    if unique_styles < min_styles:
        return False, f"R-R-012: 风格组不足 ({unique_styles}/{min_styles})"
    return True, f"相邻 bg 可区分 ({unique_styles} 种风格/{len(scenes)} 场景)"


def check_fx_layer_not_empty(project_dir: Path, params: dict) -> tuple[bool, str]:
    """R-R-008: fx 层禁止为空或仅含不可见元素。含 opacity 下限和元素数量检查。"""
    fp = project_dir / params.get("file", "index.html")
    if not fp.exists():
        return False, "index.html 缺失"
    html = fp.read_text(encoding="utf-8", errors="ignore")
    scenes = _split_into_scenes(html)
    if not scenes:
        return True, "无场景可检查"
    violations = []
    for sid, scene_html in scenes:
        fx = _extract_layer_chunk(scene_html, "layer-fx")
        if not fx.strip():
            continue
        if not _has_visible_content(fx):
            violations.append(f"{sid}(空)")
            continue
        # 检查 fx 元素数量（至少 3 个子 div，覆盖至少 2 种不同特效类型）
        fx_child_divs = len(re.findall(r'<div\b', fx)) - 1  # 减去 layer-fx 自身
        if fx_child_divs < 3:
            violations.append(f"{sid}(仅{fx_child_divs}元素,需≥3)")
            continue
        # 检查是否存在全局低 opacity（所有 fx 元素 opacity < 0.10）
        opacity_vals = re.findall(r'opacity:\s*([0-9.]+)', fx)
        if opacity_vals and all(float(v) < 0.10 for v in opacity_vals):
            violations.append(f"{sid}(opacity过低)")
    if violations:
        return False, f"R-R-008: {len(violations)} 个场景 fx 不合格 ({', '.join(violations[:6])})"
    return True, f"{len(scenes)} 场景 fx 层合格"


GATE_CHECKERS[GateType.bg_visual_diversity] = check_bg_visual_diversity
GATE_CHECKERS[GateType.adjacent_bg_diversity] = check_adjacent_bg_diversity
GATE_CHECKERS[GateType.fx_layer_not_empty] = check_fx_layer_not_empty


def check_fx_animation_present(project_dir: Path, params: dict) -> tuple[bool, str]:
    """R-R-013: fx 层元素必须有 GSAP 动画目标。

    事故记录：2026-05-30 VibeCoding 大赏视频 20/22 场景 fx 无动画，全是静态 div。
    根因：无规则要求 fx 有 GSAP 动画，门禁只检查"非空"。
    """
    fp = project_dir / params.get("file", "index.html")
    if not fp.exists():
        return False, "index.html 缺失"
    html = fp.read_text(encoding="utf-8", errors="ignore")
    scenes = _split_into_scenes(html)
    if not scenes:
        return True, "无场景可检查"

    violations = []
    for sid, scene_html in scenes:
        fx = _extract_layer_chunk(scene_html, "layer-fx")
        if not fx.strip():
            continue  # 空 fx 由 R-R-008 检查

        # 检查 fx 层中是否有子元素
        fx_children = re.findall(r'<div\b[^>]*>', fx)
        if len(fx_children) <= 1:  # 只有 layer-fx 自身
            continue

        # 在整个 HTML 中查找该场景的 GSAP timeline 代码
        # 提取该场景相关的 GSAP 动画调用
        scene_timeline = _extract_scene_timeline(html, sid) if '_extract_scene_timeline' in dir() else ""

        # 如果没有专门的提取函数，用正则在全文搜索
        if not scene_timeline:
            # 查找 window.__timelines 或 <script> 中包含该场景 id 的 GSAP 调用
            # 匹配 tl.to/tl.from/tl.fromTo 中包含 #sN 的选择器
            gsap_pattern = rf'tl\.\w+\(\s*["\'][^"\']*{re.escape(sid)}[^"\']*["\']'
            gsap_calls = re.findall(gsap_pattern, html)

            # 也匹配 .layer-fx 直接选择器
            fx_gsap_pattern = rf'tl\.\w+\(\s*["\'][^"\']*layer-fx[^"\']*["\']'
            fx_gsap_calls = re.findall(fx_gsap_pattern, html)

            # 匹配场景内常见 fx 元素类的 GSAP 调用
            fx_class_pattern = rf'tl\.\w+\(\s*["\'][^"\']*{re.escape(sid)}\s+\.(?:orb|ray|particle|streak|ring|pulse|glow|beam|wave|scan|border|drop|char|line)[^"\']*["\']'
            fx_class_calls = re.findall(fx_class_pattern, html)

            has_fx_animation = bool(gsap_calls) or bool(fx_gsap_calls) or bool(fx_class_calls)
        else:
            has_fx_animation = bool(scene_timeline)

        if not has_fx_animation:
            violations.append(sid)

    if violations:
        return False, f"R-R-013: {len(violations)} 个场景 fx 层无 GSAP 动画 ({', '.join(violations[:6])})"
    return True, f"{len(scenes)} 场景 fx 动画合格"


GATE_CHECKERS[GateType.fx_animation_present] = check_fx_animation_present


def check_portrait_typography(project_dir: Path, params: dict) -> tuple[bool, str]:
    """R-R-015/R-R-016: 竖屏排版门禁 — 检查字号最低标准 + 禁用 section-tag 小徽章。

    事故记录：2026-05-30 VibeCoding 大赏视频正文 18-28px，手机端完全不可读。
    根因：无字号门禁，导演工具包字号体系未区分竖屏/横屏。
    """
    fp = project_dir / params.get("file", "index.html")
    if not fp.exists():
        return False, "index.html 缺失"
    html = fp.read_text(encoding="utf-8", errors="ignore")

    # 检测画布方向
    width_match = re.search(r'data-width="(\d+)"', html)
    height_match = re.search(r'data-height="(\d+)"', html)
    is_portrait = True  # 默认竖屏
    if width_match and height_match:
        w, h = int(width_match.group(1)), int(height_match.group(1))
        is_portrait = h > w

    if not is_portrait:
        # 横屏字号底线（1920×1080 在手机横屏播放时缩放比 ~2.67x）
        min_title = 56
        min_body = 32
        min_annotation = 24
    else:
        min_title = 64
        min_body = 36
        min_annotation = 28

    violations = []

    # 1. 检查 section-tag 小徽章（R-R-016）
    # 兼容单引号和双引号的 class 属性
    section_tag_pattern = r'''class=['"][^'"]*section-tag[^'"]*['"]'''
    section_tags = re.findall(section_tag_pattern, html)
    if section_tags:
        violations.append(f"R-R-016: 发现 {len(section_tags)} 个 section-tag 小徽章（禁止作为场景标题）")

    # 2. 检查字号最低标准（R-R-015）
    # 使用 min_body 作为全局最低阈值：content 层主要都是可读文字，
    # 正文（36px）是可读性底线，标注（28px）允许少量辅助信息例外。
    # 因此以 min_body 为门禁阈值，确保正文可读性被强制执行。
    min_readable = min_body  # 36px(竖屏) / 32px(横屏)
    scenes = _split_into_scenes(html)
    small_text_violations = []
    for sid, scene_html in scenes:
        content = _extract_layer_chunk(scene_html, "layer-content")
        if not content.strip():
            continue
        content_sizes = [int(s) for s in re.findall(r'font-size\s*:\s*(\d+)px', content)]
        if not content_sizes:
            continue
        visible_sizes = [s for s in content_sizes if s >= 10]
        if visible_sizes:
            min_visible = min(visible_sizes)
            if min_visible < min_readable:
                small_text_violations.append(f"{sid}(最小{min_visible}px<{min_readable}px)")

    if small_text_violations:
        violations.append(
            f"R-R-015: {len(small_text_violations)} 个场景文字过小 "
            f"({'竖屏' if is_portrait else '横屏'}最低{min_readable}px): "
            f"{', '.join(small_text_violations[:6])}"
        )

    if violations:
        return False, "; ".join(violations)
    return True, f"{'竖屏' if is_portrait else '横屏'}排版合格（标题≥{min_title}px, 正文≥{min_body}px, 标注≥{min_annotation}px）"


GATE_CHECKERS[GateType.portrait_typography_valid] = check_portrait_typography


def check_orientation_consistency(project_dir: Path, params: dict) -> tuple[bool, str]:
    """R-S6-020: design.md 方向与 HTML 画布尺寸一致性校验。"""
    design_md = project_dir / "design.md"
    if not design_md.exists():
        return True, "design.md 不存在，跳过方向校验"

    content = design_md.read_text(encoding="utf-8", errors="ignore")
    orient_match = re.search(r'orientation:\s*(portrait|landscape)', content)
    if not orient_match:
        return True, "design.md 无 orientation 字段，跳过方向校验"
    declared = orient_match.group(1)

    fp = project_dir / params.get("file", "index.html")
    if not fp.exists():
        return True, "index.html 不存在，跳过方向校验"
    html = fp.read_text(encoding="utf-8", errors="ignore")

    w_match = re.search(r'data-width="(\d+)"', html)
    h_match = re.search(r'data-height="(\d+)"', html)
    if not w_match or not h_match:
        return False, "R-S6-020: HTML 根组合缺少 data-width/data-height，无法验证方向"

    w, h = int(w_match.group(1)), int(h_match.group(1))
    actual = "portrait" if h > w else "landscape"

    if declared != actual:
        return False, f"R-S6-020: 方向不一致 — design.md={declared}, HTML={actual}({w}×{h})"
    return True, f"方向一致: {declared}({w}×{h})"


GATE_CHECKERS[GateType.orientation_consistency] = check_orientation_consistency


def check_narration_sample_rate(project_dir: Path, params: dict) -> tuple[bool, str]:
    """检查 narration.mp3 采样率，确保 loudnorm.sh 已执行。

    edge-tts 原始输出 = 24000 Hz（固定）
    loudnorm.sh 输出 = 48000 Hz（固定）

    采样率 24000 Hz = loudnorm 未执行的铁证。
    """
    fp = project_dir / params.get("file", "narration.mp3")
    if not fp.exists():
        return False, "narration.mp3 缺失"

    try:
        result = subprocess.run(
            ["ffprobe", "-v", "quiet", "-show_entries",
             "stream=sample_rate", "-of", "csv=p=0", str(fp)],
            capture_output=True, text=True, timeout=10,
        )
        sample_rate = int(result.stdout.strip())
    except (ValueError, subprocess.TimeoutExpired) as e:
        return False, f"无法获取 narration.mp3 采样率: {e}"

    forbidden_rates = params.get("forbidden_rates", [24000])
    expected_min = params.get("expected_min", 44100)

    if sample_rate in forbidden_rates:
        return False, (
            f"R-S4-004: narration.mp3 采样率 {sample_rate} Hz = raw edge-tts 输出，"
            f"loudnorm.sh 未执行。预期 >= {expected_min} Hz。"
            f"修复: bash .claude/commands/clipforge/scripts/loudnorm.sh narration.mp3"
        )

    return True, f"narration.mp3 采样率: {sample_rate} Hz (loudnorm 已执行)"


def check_bgm_volume_provenance(project_dir: Path, params: dict) -> tuple[bool, str]:
    """检查 bgm_volume 来源合规性（bgm_pipeline.sh 执行证明）。

    bgm_pipeline.sh 首次运行时:
    1. 创建 bgm_orig.wav 作为原始备份
    2. 调用 bgm_gap_check.py 查表自动确定 volume
    3. 写入 segment_durations.json

    事故记录：2026-06-01 三个项目全部硬编码 bgm_volume=0.35，bgm_pipeline.sh
    从未执行，导致 BGM 普遍过响盖过旁白。

    检查策略（三选一通过）：
    A. bgm_orig.wav 存在 = 管线执行过（最强证据）
    B. segment_durations.json 含 meta.bgm_volume_source = "bgm_pipeline" 标记
    C. 都不满足 → 检查是否命中硬编码值黑名单
    """
    # 策略 A: bgm_orig.wav 存在性
    bgm_orig = project_dir / "bgm_orig.wav"
    if bgm_orig.exists():
        return True, "bgm_orig.wav 存在 → bgm_pipeline.sh 已执行"

    sd_file = project_dir / params.get("file", "segment_durations.json")
    if not sd_file.exists():
        return False, "segment_durations.json 缺失，无法验证 bgm_volume 来源"

    try:
        data = json.loads(sd_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        return False, f"segment_durations.json 解析失败: {e}"

    # 策略 B: 来源标记
    source = data.get("meta", {}).get("bgm_volume_source", "")
    if source == "bgm_pipeline":
        return True, "meta.bgm_volume_source = bgm_pipeline → 管线校准"

    # 策略 C: 无溯源标记 → 拒绝
    vol = data.get("meta", {}).get("bgm_volume", 0)
    return False, (
        f"R-S4-005: bgm_volume={vol} 无溯源标记（bgm_volume_source 缺失），"
        f"bgm_orig.wav 也不存在。"
        f"修复: bash .claude/commands/clipforge/scripts/bgm_pipeline.sh"
    )


GATE_CHECKERS[GateType.narration_sample_rate_valid] = check_narration_sample_rate
GATE_CHECKERS[GateType.bgm_volume_provenance_valid] = check_bgm_volume_provenance


# ── 响度表定义（与 bgm_gap_check.py 保持同步） ──
_VOLUME_TABLE = [
    (-4,   0.07),   # 极端响
    (-6,   0.09),   # 非常响
    (-8,   0.11),   # 很响
    (-10,  0.13),   # 响
    (-12,  0.14),   # 偏响
    (-14,  0.18),   # 中等
    (-16,  0.22),   # 标准
    (-18,  0.34),   # 偏安静
    (-20,  0.40),   # 安静
    (-22,  0.45),   # 很安静
    (-24,  0.48),   # 极安静
    (-27,  0.50),   # 接近极限
]


def _lookup_volume(mean_db: float) -> float | None:
    for threshold, vol in _VOLUME_TABLE:
        if mean_db > threshold:
            return vol
    return None


def check_bgm_volume_table_valid(project_dir: Path, params: dict) -> tuple[bool, str]:
    """验证 bgm_volume 是否与响度表匹配。

    前提：bgm_gap_check.py 已将 bgm_mean_db 和 bgm_volume 写入 segment_durations.json。
    门禁反查表验证：用存储的 bgm_mean_db 查表，对比实际 bgm_volume。

    这确保了即使 cleanup 删除了 bgm_orig.wav，仍可验证音量来源的合理性。
    """
    import math

    sd_file = project_dir / params.get("file", "segment_durations.json")
    if not sd_file.exists():
        return False, "segment_durations.json 缺失"

    try:
        data = json.loads(sd_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        return False, f"segment_durations.json 解析失败: {e}"

    meta = data.get("meta", {})
    bgm_mean = meta.get("bgm_mean_db")
    bgm_volume = meta.get("bgm_volume")
    note = meta.get("bgm_volume_table_note", "")

    if bgm_mean is None:
        return False, (
            "meta.bgm_mean_db 缺失 — bgm_gap_check.py 未写入溯源数据。"
            "修复: bash .claude/commands/clipforge/scripts/bgm_pipeline.sh"
        )

    if bgm_volume is None:
        return False, "meta.bgm_volume 缺失"

    # 查表获取预期 volume
    expected = _lookup_volume(bgm_mean)
    if expected is None:
        return False, (
            f"BGM mean_volume={bgm_mean:.1f} dB 超出响度表范围（< -27 dB），"
            f"建议更换更响的 BGM 素材"
        )

    # 允许 ±0.03 容差（bgm_gap_check.py 可能因间距修正调整了查表值）
    tolerance = params.get("tolerance", 0.03)
    diff = abs(bgm_volume - expected)

    if diff <= tolerance:
        return True, (
            f"bgm_volume={bgm_volume} 与响度表匹配 "
            f"(mean={bgm_mean:.1f} dB → 表值={expected}, 档位=\"{note}\", 偏差={diff:.2f})"
        )

    # 偏差较大，检查是否因均值/峰值间距修正导致
    adjusted = meta.get("bgm_volume_adjusted", False)
    if adjusted and bgm_volume < expected:
        # 间距修正确认降低音量是合理的
        return True, (
            f"bgm_volume={bgm_volume} 经间距修正（表值={expected}）"
            f"(mean={bgm_mean:.1f} dB, \"{note}\", 修正后降低)"
        )

    return False, (
        f"bgm_volume={bgm_volume} 与响度表不匹配: "
        f"mean={bgm_mean:.1f} dB → 表值={expected}, 实际={bgm_volume}, "
        f"偏差={diff:.2f} > 容差={tolerance}。"
        f"修复: bash .claude/commands/clipforge/scripts/bgm_pipeline.sh"
    )


GATE_CHECKERS[GateType.bgm_volume_table_valid] = check_bgm_volume_table_valid


def check_douyin_platforms_complete(project_dir: Path, params: dict) -> tuple[bool, str]:
    """检查 douyin.md 包含三平台文案 + 评论区自评。

    stage7-delivery.md §7.5 明确要求:
    1. 三平台文案必填：## 抖音、## 视频号、## 小红书
    2. 评论区自评必填：## 评论区自评（或 --- 分隔线后的自评段）
    3. 评论区必须包含两种项目介绍格式：
       a) 搜索方式："GitHub搜索: 项目名"
       b) 完整路径："owner/repo" 格式

    事故记录：2026-05-31 github-trending 视频只生成了基础交付信息，
    缺少三平台文案和评论区自评。根因：stage7-delivery.md 有文本指令
    但无结构化门禁强制执行，LLM 不自觉遵守就漏掉了。
    """
    douyin_file = project_dir / params.get("file", "douyin.md")
    if not douyin_file.exists():
        return False, "douyin.md 缺失"

    content = douyin_file.read_text(encoding="utf-8", errors="ignore")
    issues: list[str] = []

    # 1. 检查三平台文案
    required_platforms = params.get("platforms", ["抖音", "视频号", "小红书"])
    missing_platforms = []
    for p in required_platforms:
        if f"## {p}" not in content:
            missing_platforms.append(p)
    if missing_platforms:
        issues.append(f"缺少平台文案: {', '.join(missing_platforms)}（需 ## 抖音、## 视频号、## 小红书）")

    # 2. 检查评论区自评段
    has_comment_section = (
        "## 评论区自评" in content or
        "评论区自评" in content
    )
    if not has_comment_section:
        issues.append("缺少评论区自评（需 ## 评论区自评 段落）")
    else:
        # 3. 检查两种项目介绍格式
        # 格式a: 搜索方式 — "GitHub搜索:" 或 "GitHub 搜索:"
        has_search_format = bool(re.search(r'GitHub\s*搜索\s*[:：]', content))
        # 格式b: 完整路径 — "owner/repo" 形式（字母/数字/连字符/下划线/点）
        has_path_format = bool(re.search(r'[\w\-\.]+/[\w\-\.]+', content))

        format_missing = []
        if not has_search_format:
            format_missing.append("搜索方式（如 'GitHub搜索: RuView'）")
        if not has_path_format:
            format_missing.append("完整路径（如 'openpli/ruview'）")
        if format_missing:
            issues.append(f"评论区缺少项目介绍格式: {', '.join(format_missing)}")

    if issues:
        return False, f"R-S7-006: {'; '.join(issues)}"

    return True, f"douyin.md 三平台文案 + 评论区自评（搜索+路径）完整"


GATE_CHECKERS[GateType.douyin_platforms_complete] = check_douyin_platforms_complete


def check_cover_layers_present(project_dir: Path, params: dict) -> tuple[bool, str]:
    """检查 cover.html 包含 7 层封面模板结构。

    事故记录：2026-05-30 github-trending 项目封面用浏览器截图生成，未遵循 7 层模板。
    R-S7-002 原使用 semantic_check 在自动化场景不可靠，改为结构化 HTML 检测。

    检测的 7 层：
    1. 日期层：中文日期格式（含"年"字）或 class="date"
    2. 场景标签：class 含 scene-label 或"热门"/"TRENDING" 等
    3. 胶囊徽章：class 含 badge，且为圆角样式
    4. 主标题：class 含 main-title 或 title，且含大号字体
    5. 渐变分隔线：class 含 divider 或 gradient+line/separator
    6. 数据说明：class 含 subtitle/data/sub
    7. 数据卡片：class 含 card，且有数字+标签结构
    """
    cover_file = project_dir / params.get("file", "cover.html")
    if not cover_file.exists():
        return False, "cover.html 缺失，无法检查封面结构"

    content = cover_file.read_text(encoding="utf-8", errors="ignore")
    if not content.strip():
        return False, "cover.html 为空文件"

    # 门禁 0: 封面禁止 JavaScript 动画（白屏根因）
    external_scripts = re.findall(r'<script[^>]*\bsrc\s*=\s*["\']([^"\']+)["\']', content)
    if external_scripts:
        return False, (
            f"R-S7-003: 封面禁止引用外部脚本（动画库会导致白屏截图），"
            f"发现: {', '.join(external_scripts[:3])}"
        )
    script_blocks = re.findall(r'<script[^>]*>(.*?)</script>', content, re.DOTALL)
    for block in script_blocks:
        stripped = block.strip()
        if not stripped:
            continue
        hf_compat = re.sub(r'window\.__hf\s*=\s*\{[^}]*\}\s*;?\s*', '', stripped)
        hf_compat = re.sub(r'window\.__timelines\s*=\s*\{[^}]*\}\s*;?\s*', '', hf_compat)
        hf_compat = re.sub(r'window\.__timelines\s*=\s*window\.__timelines\s*\|\|\s*\{\}\s*;?\s*', '', hf_compat)
        hf_compat = re.sub(r'[\s;{}]+', '', hf_compat)
        if hf_compat:
            return False, (
                f"R-S7-003: 封面禁止 JavaScript 动画代码（fromTo opacity:0 等会导致白屏），"
                f"发现非法内容: {hf_compat[:60]}"
            )

    missing: list[str] = []

    # 第1层：中文日期（"年"字或 class="date"）
    has_date = bool(re.search(r'class="[^"]*date[^"]*"', content)) or "年" in content
    if not has_date:
        missing.append("第1层:中文日期（需 class='date' 或包含'年'字）")

    # 第2层：场景标签（class 含 scene-label / label / tag）
    has_scene_label = bool(re.search(r'class="[^"]*(?:scene[-_]?label|tag)[^"]*"', content))
    if not has_scene_label:
        missing.append("第2层:场景标签（需 class='scene-label'）")

    # 第3层：胶囊徽章（class 含 badge）
    has_badge = bool(re.search(r'class="[^"]*badge[^"]*"', content))
    if not has_badge:
        missing.append("第3层:胶囊徽章（需 class='badge'）")

    # 第4层：主标题（class 含 main-title / title / heading）
    has_title = bool(re.search(r'class="[^"]*(?:main[-_]?title|title|heading)[^"]*"', content))
    if not has_title:
        missing.append("第4层:主标题（需 class='main-title'）")

    # 第5层：渐变分隔线（class 含 divider / separator，或 linear-gradient 横条）
    has_divider = bool(re.search(r'class="[^"]*(?:divider|separator|line)[^"]*"', content))
    if not has_divider:
        missing.append("第5层:渐变分隔线（需 class='divider'）")

    # 第6层：数据说明（class 含 subtitle / data-sub / description）
    has_subtitle = bool(re.search(
        r'class="[^"]*(?:sub(?:title)?|data[-_]?sub|description)[^"]*"', content))
    if not has_subtitle:
        missing.append("第6层:数据说明（需 class='data-subtitle' 或类似）")

    # 第7层：数据卡片（class 含 card）
    has_cards = bool(re.search(r'class="[^"]*card[^"]*"', content))
    if not has_cards:
        missing.append("第7层:数据卡片（需 class='card'）")

    if missing:
        return False, (
            f"R-S7-002: 封面缺少 {len(missing)} 层: {'; '.join(missing)}。"
            f"参考 stage7-delivery.md §7.1 的 7 层模板"
        )

    return True, "封面 7 层结构完整"


GATE_CHECKERS[GateType.cover_layers_present] = check_cover_layers_present


def check_final_duration_close_to_output(project_dir: Path, params: dict) -> tuple[bool, str]:
    """检查 final.mp4 时长与 output.mp4 时长差异不超过容差。

    事故记录：2026-05-31 github-trending 视频交付 SubAgent 绕过 assemble_final.sh，
    自行用 ffmpeg 将 cover.png 渲染为 3 秒封面视频再拼接到 output.mp4 前面。
    封面无音频轨 → 旁白从 PTS=0 播放 → 视觉内容在 ~3s 才开始 →
    每个场景切换处旁白都比画面提前 ~3 秒，全程 A/V 不同步。

    assemble_final.sh 正确行为：1 帧封面（~0.033s），几乎不影响时长。
    本门禁是独立于 assemble_final.sh 的最后防线。
    """
    final_file = project_dir / params.get("final_file", "final.mp4")
    output_file = project_dir / params.get("output_file", "output.mp4")
    tolerance = params.get("tolerance", 0.2)

    if not final_file.exists():
        return True, "final.mp4 尚未生成，跳过时长比对"
    if not output_file.exists():
        return True, "output.mp4 缺失，跳过时长比对"

    def _get_duration(f: Path) -> float | None:
        try:
            result = subprocess.run(
                ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
                 "-of", "csv=p=0", str(f)],
                capture_output=True, text=True, timeout=10,
            )
            return float(result.stdout.strip())
        except Exception:
            return None

    final_dur = _get_duration(final_file)
    output_dur = _get_duration(output_file)

    if final_dur is None:
        return False, "无法获取 final.mp4 时长"
    if output_dur is None:
        return True, "无法获取 output.mp4 时长，跳过比对"

    diff = final_dur - output_dur
    if diff > tolerance:
        return False, (
            f"封面膨胀 A/V 脱节: final={final_dur:.2f}s vs output={output_dur:.2f}s "
            f"(差 {diff:.2f}s > 容差 {tolerance}s)。"
            f"封面视频占用了 {diff:.1f}s 无音频画面，导致旁白全程领先。"
            f"修复: 使用 assemble_final.sh 重新拼接（1帧封面≈0.033s）"
        )

    return True, f"final.mp4 时长正常: 差值 {diff:.3f}s <= {tolerance}s"


GATE_CHECKERS[GateType.final_duration_close_to_output] = check_final_duration_close_to_output


def check_grad_text_shorthand(project_dir: Path, params: dict) -> tuple[bool, str]:
    """检查 .grad-text 元素是否使用了 background: 简写（导致 background-clip:text 失效）。

    事故记录：2026-06-02 github-trending 视频全部 8 个 .grad-text 元素使用
    background:linear-gradient(...) 简写，CSS background 简写会重置
    background-clip 回 border-box，导致 background-clip:text 失效，
    结果是渐变填满整个元素背景色块，color:transparent 又隐藏文字——只看到色块看不到字。

    检测逻辑：
    1. 扫描 index.html 中所有 class 含 grad-text 的标签
    2. 检查内联 style 是否包含 background:（排除 background-image: 等安全子属性）
    3. 匹配到 → HARD 违规

    正确写法：background-image:linear-gradient(...)
    错误写法：background:linear-gradient(...)
    """
    fp = project_dir / params.get("file", "index.html")
    if not fp.exists():
        return False, "index.html 缺失"
    content = fp.read_text(encoding="utf-8", errors="ignore")

    violations: list[str] = []

    # 匹配含 grad-text class 的标签，捕获 style 属性值
    tag_pattern = re.compile(
        r'<(\w+)\s+[^>]*class=["\'][^"\']*grad-text[^"\']*["\'][^>]*style=["\']([^"\']*)["\'][^>]*>',
        re.IGNORECASE | re.DOTALL,
    )
    tag_pattern_rev = re.compile(
        r'<(\w+)\s+[^>]*style=["\']([^"\']*)["\'][^>]*class=["\'][^"\']*grad-text[^"\']*["\'][^>]*>',
        re.IGNORECASE | re.DOTALL,
    )

    seen: set[str] = set()
    for pattern in (tag_pattern, tag_pattern_rev):
        for m in pattern.finditer(content):
            tag_name = m.group(1)
            style_val = m.group(2)

            # background: 简写会重置 background-clip，排除安全子属性
            shorthand_match = re.search(
                r'(?<!-)\bbackground\s*:\s*(?!image|color|size|position|repeat|origin|attachment)',
                style_val,
            )
            if shorthand_match:
                start = shorthand_match.start()
                snippet = style_val[start:start + 60]
                key = f"{tag_name}:{snippet[:30]}"
                if key not in seen:
                    seen.add(key)
                    violations.append(f"<{tag_name}> style=\"...{snippet}...\"")

    if violations:
        return False, (
            f"R-S6-021: {len(violations)} 个 .grad-text 元素使用了 background: 简写，"
            f"导致 background-clip:text 失效。"
            f"正确写法: background-image:linear-gradient(...)。"
            f"违规: {'; '.join(violations[:5])}"
        )

    return True, ".grad-text 元素均使用 background-image:（非简写）"


GATE_CHECKERS[GateType.grad_text_shorthand_valid] = check_grad_text_shorthand


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


def generate_score_report(project_dir: Path, skills_dir: Path | None = None) -> dict:
    """运行全阶段门禁并聚合为 score_report.json（基础设施：纯记录，无反馈逻辑）。

    返回值含 _gate_details（完整 violations 详情），仅供内部闭环使用，不写入 JSON。
    """
    stages = ["stage1-content", "stage3-scenes", "stage4-audio", "stage6-production", "stage7-delivery"]
    phases = {}
    gate_details = {}  # 保留完整 GateReport 信息，供 trace + attribution 使用
    for stage_id in stages:
        try:
            sk = load_skill(stage_id, skills_dir)
            if not sk:
                continue
            r = run_gate(sk, project_dir)
            phases[stage_id] = {
                "hard_passed": r.hard_passed,
                "soft_score": r.soft_score,
            }
            gate_details[stage_id] = {
                "hard_violations": [
                    {"rule_id": v.rule_id, "details": v.details}
                    for v in r.hard_violations
                ],
                "soft_issues": r.soft_issues,
            }
        except Exception:
            phases[stage_id] = {"hard_passed": False, "soft_score": 0.0, "error": "gate check failed"}

    score_report = {
        "project": str(project_dir),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "phases": phases,
        "overall_soft_score": (
            sum(p["soft_score"] for p in phases.values()) / len(phases) if phases else 0
        ),
        "hard_passed_all": all(p.get("hard_passed", False) for p in phases.values()),
        "total_stages": len(phases),
        "stages_passed": sum(1 for p in phases.values() if p.get("hard_passed")),
    }

    report_path = project_dir / "score_report.json"
    report_path.write_text(
        json.dumps(score_report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    # ⚠ 顺序不可交换：_gate_details 在 write_text 之后赋值，确保不污染 score_report.json
    score_report["_gate_details"] = gate_details
    return score_report


def _run_single_skill(args) -> None:
    """单阶段门禁模式：gate.py --skill X --project-dir Y"""
    project_dir = Path(args.project_dir)
    skills_dir = Path(args.skills_dir) if args.skills_dir else None

    skill = load_skill(args.skill, skills_dir)
    if not skill:
        print(json.dumps({"error": f"Skill not found: {args.skill}"}, ensure_ascii=False))
        sys.exit(1)

    report = run_gate(skill, project_dir)

    # ── Auto-trace: 基础设施层，非反馈逻辑 ──
    trace_path = None
    try:
        from engine.trace import record_trace
        trace_result = "pass" if report.hard_passed else "fail"
        gate_dict = {
            "hard_passed": report.hard_passed,
            "soft_score": report.soft_score,
            "hard_violations": [
                {"rule_id": v.rule_id, "details": v.details}
                for v in report.hard_violations
            ],
            "soft_issues": report.soft_issues,
        }
        trace_path = record_trace(
            skill_id=args.skill,
            project_dir=str(project_dir),
            result=trace_result,
            gate_report=gate_dict,
        )
    except Exception:
        pass

    # ── Auto attribution: HARD 失败时自动强归因（反馈层）──
    attribution_results = []
    if not report.hard_passed:
        try:
            from engine.attribution import strong_attribution
            from engine.lib.rule_parser import load_all_rules
            all_rules = load_all_rules()
            for v in report.hard_violations:
                attr = strong_attribution(
                    {"rule_id": v.rule_id, "details": v.details},
                    rules=all_rules,
                )
                if attr.get("matched_rule"):
                    attribution_results.append(attr)
        except Exception:
            pass

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
    if trace_path:
        output["trace"] = str(trace_path)
    if attribution_results:
        output["attribution"] = attribution_results
    print(json.dumps(output, ensure_ascii=False, indent=2))
    sys.exit(0 if report.hard_passed else 1)


def _activate_closed_loop(report: dict, project_dir: Path) -> None:
    """评分闭环：trace 记录 + attribution 归因。

    从 generate_score_report 的完整结果中提取数据，
    无需重新运行 gate（复用已有结果）。

    闭环链路：
    1. 为每个 stage 记录 trace（pass/fail + gate_report）
    2. HARD 失败的 stage → strong_attribution（确定性规则匹配）
    3. strong_attribution 无匹配 → weak_attribution（根因推断 + Delta 产出）

    幂等策略：同一天同一 stage 的 trace 采用覆盖模式（允许修复后重新评分）。
    全程 try/except 包裹，闭环失败不影响主流程。
    """
    gate_details = report.get("_gate_details", {})
    phases = report.get("phases", {})

    try:
        from engine.trace import record_trace, TRACES_DIR
        from engine.attribution import strong_attribution, weak_attribution
        from engine.lib.rule_parser import load_all_rules
        all_rules = load_all_rules()
    except Exception as e:
        print(f"[closed-loop] 初始化失败: {e}", file=sys.stderr)
        return

    # ── 幂等性：移除今天的旧 trace（覆盖模式，允许修复后重新评分）──
    project_traces_dir = TRACES_DIR / project_dir.name
    trace_file = project_traces_dir / "trace.json"
    today_prefix = datetime.now(timezone.utc).strftime("%Y%m%d")
    if trace_file.exists():
        try:
            existing = json.loads(trace_file.read_text(encoding="utf-8"))
            # 只保留非今天的 trace
            kept = [t for t in existing if not t.get("id", "").startswith(f"T-{today_prefix}")]
            if len(kept) != len(existing):
                trace_file.write_text(
                    json.dumps(kept, ensure_ascii=False, indent=2), encoding="utf-8"
                )
        except (json.JSONDecodeError, UnicodeDecodeError):
            pass

    for stage_id, phase_data in phases.items():
        detail = gate_details.get(stage_id, {})

        # ── Step 1: 记录 trace ──
        gate_dict = {
            "hard_passed": phase_data.get("hard_passed", False),
            "soft_score": phase_data.get("soft_score", 0.0),
            "hard_violations": detail.get("hard_violations", []),
            "soft_issues": detail.get("soft_issues", []),
        }
        try:
            trace_result = "pass" if phase_data.get("hard_passed") else "fail"
            record_trace(
                skill_id=stage_id,
                project_dir=str(project_dir),
                result=trace_result,
                gate_report=gate_dict,
            )
        except Exception as e:
            print(f"[closed-loop] trace 记录失败 ({stage_id}): {e}", file=sys.stderr)
            continue

        # ── Step 2: HARD 失败时触发归因 ──
        if not phase_data.get("hard_passed"):
            violations = detail.get("hard_violations", [])
            # 构造合成 trace 提升弱归因置信度
            synthetic_trace = {
                "execution": {"steps": [], "path_switches": []},
                "result": {"gate_report": gate_dict},
            }
            for v in violations:
                try:
                    attr = strong_attribution(v, all_rules)
                    if attr.get("root_cause") == "no_rule_match":
                        weak_attribution(v, trace=synthetic_trace, produce_delta=True)
                except Exception as e:
                    print(f"[closed-loop] 归因失败 ({v.get('rule_id','?')}): {e}", file=sys.stderr)


def _generate_report(args) -> None:
    """独立评分模式：gate.py --generate-report --project-dir Y

    无条件运行全阶段门禁并产出 score_report.json。
    在 delivery 后、cleanup 前由管线调用。
    与 stage7 是否通过无关 — 失败的项目更需要评分记录。
    """
    project_dir = Path(args.project_dir)
    skills_dir = Path(args.skills_dir) if args.skills_dir else None

    try:
        report = generate_score_report(project_dir, skills_dir)

        # 激活 trace + attribution 闭环（副作用层，不阻塞主流程）
        _activate_closed_loop(report, project_dir)

        output = {
            "generated": True,
            "project": str(project_dir),
            "overall_soft_score": report["overall_soft_score"],
            "hard_passed_all": report["hard_passed_all"],
            "stages_passed": f"{report['stages_passed']}/{report['total_stages']}",
        }
        print(json.dumps(output, ensure_ascii=False, indent=2))
    except Exception as e:
        print(json.dumps({"generated": False, "error": str(e)}, ensure_ascii=False, indent=2))
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="ClipForge 门禁引擎")
    parser.add_argument("--skill", default=None, help="单阶段门禁检查")
    parser.add_argument("--project-dir", required=True)
    parser.add_argument("--skills-dir", default=None)
    parser.add_argument("--generate-report", action="store_true",
                        help="生成全阶段 score_report.json（delivery 后、cleanup 前调用）")
    args = parser.parse_args()

    # 独立评分模式：无条件运行全阶段门禁，产出 score_report.json
    if args.generate_report:
        _generate_report(args)
        return

    # 单阶段门禁模式（向后兼容）
    if not args.skill:
        parser.error("--skill is required when not using --generate-report")
    _run_single_skill(args)


if __name__ == "__main__":
    main()
