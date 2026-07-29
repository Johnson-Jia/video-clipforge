"""门禁引擎 — HARD + SOFT 校验。"""
from __future__ import annotations
import argparse
import html
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from engine.lib.rule_parser import load_skill
from engine.lib.models import (
    GateReport, Violation, Severity, GateType, Rigor, SkillDefinition,
)

# 结构类失败统一修复指引：window.__hf / composition / clip id / data-width / audio data-start
# 这些结构由 s6_assemble_html.py 确定性生成（见 s6_assemble.sh）。
# trace 实证：手写/手改 index.html 是结构门禁反复失败的最常见根因
# （交互模式监督用脚本 → 0 次结构失败；cron 自动模式 SubAgent 倾向手写 → 多轮磨）。
# 失败时强制引导回 creative/ 碎片 + 重跑组装脚本，禁止手补 index.html。
_ASSEMBLE_HINT = (
    " [修复: 此结构由 s6_assemble.sh 生成，禁止手写/手改 index.html；"
    "修 creative/ 对应碎片后重跑 bash scripts/s6_assemble.sh]"
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


def check_cinematic_fields(project_dir: Path, params: dict) -> tuple[bool, str]:
    """软校验 narration_segments.json 的电影级字段（shot_size/camera_move/transition）在白名单。

    软校验：非法值不 fail（cinematic.py 映射函数已默认兜底），仅在 msg 记录警告，供评分/追溯。
    缺文件/解析失败 → 跳过（通过）。
    """
    fp = project_dir / params.get("file", "narration_segments.json")
    if not fp.exists():
        return True, "narration_segments.json 缺失（跳过电影级字段校验）"
    try:
        segs = json.loads(fp.read_text(encoding="utf-8"))
    except Exception:
        return True, "narration_segments.json 解析失败（跳过电影级字段校验）"
    try:
        from scripts.cinematic import SHOT_SIZES, CAMERA_MOVES, TRANSITIONS
    except ImportError:
        return True, "cinematic 模块缺失（跳过）"
    bad = []
    for i, s in enumerate(segs, 1):
        if not isinstance(s, dict):
            continue
        for field, whitelist in (("shot_size", SHOT_SIZES),
                                 ("camera_move", CAMERA_MOVES),
                                 ("transition", TRANSITIONS)):
            v = s.get(field)
            if v is not None and v not in whitelist:
                bad.append(f"S{i}.{field}={v}")
    if bad:
        return True, f"电影级字段非法值（默认兜底）: {', '.join(bad[:5])}"
    return True, "电影级字段白名单通过"


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


def _load_sensitive_keywords(project_dir: Path) -> list[str]:
    """从分类配置 YAML 中读取 sensitive_keywords，合并所有数组返回去重列表。"""
    import yaml
    clipforge_dir = Path(__file__).resolve().parent.parent
    cat_dir = clipforge_dir / "categories"
    keywords: list[str] = []
    for cat_file in cat_dir.glob("*.md"):
        try:
            text = cat_file.read_text(encoding="utf-8")
            start = text.find("<!-- CONFIG-START:")
            end = text.find("<!-- CONFIG-END -->")
            if start == -1 or end == -1:
                continue
            yaml_block = text[start:end]
            yaml_block = re.sub(r'<!--\s*CONFIG-START:[^>]*>', '', yaml_block)
            config = yaml.safe_load(yaml_block)
            if not config:
                continue
            content_cfg = config.get("content", {})
            sk = content_cfg.get("sensitive_keywords", {})
            for key in ("finance", "extreme_words", "hype_numbers", "ai_deepfake"):
                words = sk.get(key, [])
                if isinstance(words, list):
                    keywords.extend(str(w) for w in words)
        except Exception:
            continue
    return list(set(keywords))


def check_no_forbidden_speech(project_dir: Path, params: dict,
                              guardrails: list | None = None) -> tuple[bool, str]:
    base_forbidden = [
        # 营销/绝对化用语（R-G-001）
        "必装", "必备", "神器", "赶紧去", "马上去", "立即下载",
        "全网最好", "第一", "最强", "你一定要", "千万别错过",
        "免费领", "福利", "白嫖", "点赞关注", "一键三连",
        "一定", "绝对", "必然",
        "远超预期", "别人没做的事", "史无前例", "前所未有",
        "吊打", "碾压", "完爆", "秒杀",
        # 违法工具/盗版/盗播（平台合规红线，2026-06-13 抖音违规事故：MasterDnsVPN/iptv-org）
        # 注意：不含"VPN"（合法技术词，避免误伤技术讨论）
        "翻墙", "电视直播源", "直播源", "破解版", "盗版", "盗链",
    ]
    cat_keywords = _load_sensitive_keywords(project_dir)
    forbidden = list(set(base_forbidden + cat_keywords))
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


def check_narration_translation_pattern(project_dir: Path, params: dict) -> tuple[bool, str]:
    """SOFT: 检测旁白中'不是X而是Y'/'而非X而是Y'翻译腔套路句。

    'not X but Y' 是英语直译，违背中文表达习惯（中文宜直接肯定句），
    知识区/科技区滥用成套路，观众审美疲劳。详见 shared/shared-rules.md §1.2。
    """
    pattern = re.compile(r"(不是|而非)[^。！？\n]{0,30}而是")
    check_files = params.get("files", ["narration.txt"])
    found: list[str] = []
    for fname in check_files:
        fp = project_dir / fname
        if not fp.exists():
            continue
        content = fp.read_text(encoding="utf-8", errors="ignore")
        for m in pattern.finditer(content):
            start = max(0, m.start() - 4)
            end = min(len(content), m.end() + 8)
            snippet = content[start:end].replace("\n", " ")
            found.append(f"{fname}: '…{snippet}…'")
    if found:
        return (False, f"发现 {len(found)} 处'不是X而是Y'翻译腔套路句"
                f"（非中文表达习惯，宜用直接肯定句，详见 shared-rules §1.2）: "
                f"{' | '.join(found[:3])}")
    return True, ""


def check_narration_emotion_type_valid(project_dir: Path, params: dict) -> tuple[bool, str]:
    """SOFT: 检查 narration_segments.json 各 segment emotion 必 str 名（6 拍 grab/build/reveal/climax/settle/summon）。

    防 LLM 把 emotion_intensity 数字误填进 emotion（float），致 auto_evolve 取众数 dominant_emotion 非 str 崩。
    auto_evolve L192 已 isinstance(str) 兜底，此 checker 让数据源头干净。
    """
    fpath = project_dir / params.get("file", "narration_segments.json")
    if not fpath.exists():
        return True, ""
    try:
        data = json.loads(fpath.read_text(encoding="utf-8"))
    except Exception:
        return True, ""
    segs = data if isinstance(data, list) else data.get("segments", [])
    bad = []
    for i, s in enumerate(segs):
        if not isinstance(s, dict):
            continue
        emo = s.get("emotion")
        if emo is not None and not isinstance(emo, str):
            bad.append(f"seg{i}: emotion={emo!r} ({type(emo).__name__})")
    if bad:
        return (False, f"narration emotion 必 str 名（grab/build/reveal/climax/settle/summon），发现非 str: {bad[:3]}"
                f"（auto_evolve dominant_emotion 取众数，非 str 致分析崩）")
    return True, ""


def check_no_real_person_name(project_dir: Path, params: dict,
                               guardrails: list | None = None) -> tuple[bool, str]:
    """R-G-008: 检测旁白/文案中的真实人名+头衔组合，防平台隐私审核"""
    import re as _re
    # 检测"姓名+头衔"模式：X教授、X老师、X博士、X院士
    name_title_pattern = _re.compile(
        r'[一-鿿]{1,3}(教授|老师|博士|院士|研究员)'
    )
    check_files = params.get("files", ["narration.txt", "douyin.md", "index.html"])
    found: list[str] = []
    for fname in check_files:
        fp = project_dir / fname
        if not fp.exists():
            continue
        content = fp.read_text(encoding="utf-8", errors="ignore")
        # 去掉 HTML 标签中的 class/id 等技术性内容，只检查可见文字
        if fname.endswith(".html"):
            import re as _re2
            content = _re2.sub(r'<style[^>]*>.*?</style>', '', content, flags=_re2.DOTALL)
            content = _re2.sub(r'<script[^>]*>.*?</script>', '', content, flags=_re2.DOTALL)
            content = _re2.sub(r'<[^>]+>', ' ', content)
        matches = name_title_pattern.findall(content)
        if matches:
            for m in name_title_pattern.finditer(content):
                found.append(f"{fname}: '{m.group()}'")
    if found:
        return False, f"R-G-008: 发现真实人名+头衔（触发平台隐私审核）: {'; '.join(found[:5])}"
    return True, ""


def check_no_school_name(project_dir: Path, params: dict,
                          guardrails: list | None = None) -> tuple[bool, str]:
    """R-G-009: 检测具体学校名/机构名"""
    school_names = [
        "中科大", "中国科学技术大学", "清华大学", "北京大学", "北大",
        "浙江大学", "浙大", "上海交通大学", "上海交大", "复旦大学", "复旦",
        "南京大学", "南大", "中科院", "中国科学院",
    ]
    check_files = params.get("files", ["narration.txt", "douyin.md", "index.html"])
    found: list[str] = []
    for fname in check_files:
        fp = project_dir / fname
        if not fp.exists():
            continue
        content = fp.read_text(encoding="utf-8", errors="ignore")
        # 去掉 HTML 标签
        if fname.endswith(".html"):
            import re as _re
            content = _re.sub(r'<style[^>]*>.*?</style>', '', content, flags=_re.DOTALL)
            content = _re.sub(r'<script[^>]*>.*?</script>', '', content, flags=_re.DOTALL)
            content = _re.sub(r'<[^>]+>', ' ', content)
        for school in school_names:
            if school in content:
                found.append(f"{fname}: '{school}'")
    if found:
        return False, f"R-G-009: 发现具体学校/机构名（触发平台隐私审核）: {'; '.join(found[:5])}"
    return True, ""


def check_no_app_name(project_dir: Path, params: dict,
                      guardrails: list | None = None) -> tuple[bool, str]:
    """R-G-014: 检测具体商业 app/软件名（剪映/CapCut 等）。

    剪映是字节系（抖音母公司）产品，在抖音提它做"替代/对标"会触发封禁
    （前两期事故）。用功能泛化（"视频剪辑工具"）替代具体 app 名。
    """
    app_names = [
        # 视频剪辑类（剪映封禁事故，2026-07）
        "剪映", "CapCut", "必剪", "快剪辑", "快影", "小影",
    ]
    check_files = params.get("files", ["narration.txt", "douyin.md", "index.html"])
    found: list[str] = []
    for fname in check_files:
        fp = project_dir / fname
        if not fp.exists():
            continue
        content = fp.read_text(encoding="utf-8", errors="ignore")
        # 去掉 HTML 标签
        if fname.endswith(".html"):
            import re as _re
            content = _re.sub(r'<style[^>]*>.*?</style>', '', content, flags=_re.DOTALL)
            content = _re.sub(r'<script[^>]*>.*?</script>', '', content, flags=_re.DOTALL)
            content = _re.sub(r'<[^>]+>', ' ', content)
        for app in app_names:
            if app in content:
                found.append(f"{fname}: '{app}'")
    if found:
        return False, f"R-G-014: 发现商业 app/软件名（剪映是字节系产品，提它做替代触发封禁；用功能泛化如'视频剪辑工具'）: {'; '.join(found[:5])}"
    return True, ""


def check_no_meta_instruction(project_dir: Path, params: dict,
                              guardrails: list | None = None) -> tuple[bool, str]:
    """R-G-016: 检测创作元指令/制作术语泄露到旁白。

    "一带而过/快速带过/老朋友/熟面孔/先放一边/信息节制" 是给创作者的决策
    （如 selection_strategy 的"连续霸榜项目快速带过 3-4s"），不是给观众的内容。
    观众听到会感到被敷衍+意识到偷懒；"老朋友/熟面孔"还对新观众指代落空、
    建立观看门槛（频道定位是排行榜快速播报、每天拉新）。用内容化表达替代
    （直接介绍项目，不标"快报/一带而过"）。2026-07-26 github s6 "老朋友一带而过" 事故触发。
    """
    meta_terms = [
        "一带而过", "快速带过", "老朋友", "熟面孔", "先放一边", "信息节制",
    ]
    check_files = params.get("files", ["narration.txt"])
    found: list[str] = []
    for fname in check_files:
        fp = project_dir / fname
        if not fp.exists():
            continue
        content = fp.read_text(encoding="utf-8", errors="ignore")
        # 去掉 HTML 标签（兼容未来扩展到 index.html）
        if fname.endswith(".html"):
            import re as _re
            content = _re.sub(r'<style[^>]*>.*?</style>', '', content, flags=_re.DOTALL)
            content = _re.sub(r'<script[^>]*>.*?</script>', '', content, flags=_re.DOTALL)
            content = _re.sub(r'<[^>]+>', ' ', content)
        for term in meta_terms:
            if term in content:
                found.append(f"{fname}: '{term}'")
    if found:
        return False, f"R-G-016: 创作元指令/制作术语泄露到旁白（一带而过/老朋友/快速带过/熟面孔/先放一边/信息节制是给创作者的决策，不是给观众的内容，改用内容化表达）: {'; '.join(found[:5])}"
    return True, ""


def check_no_competitor_attack(project_dir: Path, params: dict,
                                guardrails: list | None = None) -> tuple[bool, str]:
    """R-G-010: 检测竞品负面对比/拉踩"""
    attack_patterns = [
        "不如", "缺实时", "没有XX", "做不到", "比不上",
        "过时", "落后", "闭源数据不过",
    ]
    # 竞品名称列表（常见开源项目 + 商业产品）
    competitor_names = [
        "LiveTalking", "HeyGen", "D-ID", "Synthesia",
    ]
    check_files = params.get("files", ["narration.txt", "douyin.md", "index.html"])
    found: list[str] = []
    for fname in check_files:
        fp = project_dir / fname
        if not fp.exists():
            continue
        content = fp.read_text(encoding="utf-8", errors="ignore")
        if fname.endswith(".html"):
            import re as _re
            content = _re.sub(r'<style[^>]*>.*?</style>', '', content, flags=_re.DOTALL)
            content = _re.sub(r'<script[^>]*>.*?</script>', '', content, flags=_re.DOTALL)
            content = _re.sub(r'<[^>]+>', ' ', content)
        for comp in competitor_names:
            if comp in content:
                for pattern in attack_patterns:
                    if pattern in content:
                        found.append(f"{fname}: 竞品'{comp}'附近发现负面描述'{pattern}'")
                        break
    if found:
        return False, f"R-G-010: 竞品负面对比（触发'贬低同行'审核）: {'; '.join(found[:5])}"
    return True, ""


def check_no_search_cTA(project_dir: Path, params: dict,
                        guardrails: list | None = None) -> tuple[bool, str]:
    """R-G-013: 禁止'去XX搜索''搜XX'等搜索引导话术。

    短视频内容不应引导观众去外部平台搜索特定关键词，
    这属于推广/导流行为，可能触发平台审核。
    """
    search_cta_patterns = [
        r'去\s*GitHub\s*搜', r'GitHub\s*搜\s*\w',
        r'在\s*GitHub\s*搜', r'GitHub\s*搜索',
        r'搜\s*[“””]?\w+[“””]?\s*就\s*能',
        r'搜索\s*\w+\s*就能',
        r'GitHub\s*搜索\s*[:：]',
        r'搜\s*项目\s*名', r'搜\s*名字\s*就',
        r'去\s*搜\s*\w', r'去\s*GitHub',
        r'感兴趣.*搜',
    ]
    check_files = params.get("files", ["narration.txt", "douyin.md", "index.html"])
    found: list[str] = []
    for fname in check_files:
        fp = project_dir / fname
        if not fp.exists():
            continue
        content = fp.read_text(encoding="utf-8", errors="ignore")
        if fname.endswith(".html"):
            content = re.sub(r'<style[^>]*>.*?</style>', '', content, flags=re.DOTALL)
            content = re.sub(r'<script[^>]*>.*?</script>', '', content, flags=re.DOTALL)
            content = re.sub(r'<[^>]+>', ' ', content)
        for pat in search_cta_patterns:
            m = re.search(pat, content)
            if m:
                found.append(f"{fname}: '{m.group()}'")
    if found:
        return False, f"R-G-013: 搜索引导话术（平台视为导流）: {'; '.join(found[:5])}"
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


def check_design_storyboard_valid(project_dir: Path, params: dict) -> tuple[bool, str]:
    """校验 design.md 包含必需字段且 emotion_curve 为 6 元素数组。"""
    required_keys = params.get("required_keys", ["style", "mood", "color_direction", "storyboard"])
    emotion_curve_length = params.get("emotion_curve_length", 6)

    design_path = project_dir / "design.md"
    if not design_path.exists():
        return False, f"design.md 不存在: {design_path}"

    content = design_path.read_text(encoding="utf-8")

    # 校验 required keys
    missing = [k for k in required_keys if k + ":" not in content and k + " :" not in content]
    if missing:
        return False, f"design.md 缺少必需字段: {', '.join(missing)}"

    # 校验 emotion_curve
    ec_match = re.search(r"emotion_curve:\s*\[([^\]]*)\]", content)
    if not ec_match:
        return False, "design.md 未找到 emotion_curve 数组"

    elements = [e.strip().strip("'\"") for e in ec_match.group(1).split(",") if e.strip()]
    if len(elements) != emotion_curve_length:
        return False, f"emotion_curve 应为 {emotion_curve_length} 元素数组，实际 {len(elements)} 元素: {elements}"

    return True, f"design.md 字段完整，emotion_curve = {elements}"


GATE_CHECKERS = {
    GateType.file_exists: check_file_exists,
    GateType.json_valid: check_json_valid,
    GateType.loudnorm_verified: check_loudnorm_verified,
    GateType.bgm_volume_set: check_bgm_volume_set,
    GateType.no_forbidden_speech: check_no_forbidden_speech,
    GateType.no_url_in_output: check_no_url,
    GateType.no_real_person_name: check_no_real_person_name,
    GateType.no_school_name: check_no_school_name,
    GateType.no_app_name: check_no_app_name,
    GateType.no_meta_instruction: check_no_meta_instruction,
    GateType.no_competitor_attack: check_no_competitor_attack,
    GateType.no_search_cta: check_no_search_cTA,
    GateType.duration_in_range: check_duration_in_range,
    GateType.hook_pattern_verified: None,  # 占位，在下面实现
    GateType.design_storyboard_valid: check_design_storyboard_valid,
}


# hook 模式禁用词列表（数据驱动：疑问/互动模式平均 1,195 播放，最低）
HOOK_FORBIDDEN_STARTS = ("你知道吗", "有没有想过", "猜猜", "你知道", "大家知道")
# hook 高优模式关键词（数据驱动：反直觉/冲突平均 46,596 播放）
HOOK_HIGH_VALUE_KEYWORDS = ("不用", "却能", "居然", "竟然", "竟然能", "只要", "不需要")
# hook 数字锚定关键词 — 默认为空，由分类配置 narration.hook_anchors 提供
_DEFAULT_HOOK_NUMBER_ANCHORS: tuple[str, ...] = ()


def _get_hook_anchors(params: dict) -> tuple[str, ...]:
    """从 params 或 category 配置获取 hook_anchors（桥接 category，参照 attribution.py:22-31）。

    gap 修复：原仅读 params.hook_anchors，但 stage3 yaml 未传 → github 分类下数字锚定恒 False。
    现 fallback 读 CLIPFORGE_CATEGORY 对应 category 的 narration.hook_anchors。
    """
    anchors = params.get("hook_anchors")
    if anchors:
        return tuple(anchors)
    import os
    cat_id = os.environ.get("CLIPFORGE_CATEGORY")
    if cat_id:
        try:
            from engine.lib.category_config import load_category_config, get as _cfg_get
            cfg = load_category_config(cat_id)
            cat_anchors = _cfg_get(cfg, "narration.hook_anchors", [])
            if cat_anchors:
                return tuple(cat_anchors)
        except Exception:
            pass
    return _DEFAULT_HOOK_NUMBER_ANCHORS


def check_hook_pattern_verified(project_dir: Path, params: dict) -> tuple[bool, str]:
    """校验 hook 场景文本是否命中高优模式，是否避开禁用模式。

    数据来源：抖音 58 条视频分析
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

    # 兼容两种格式：顶层数组 或 {"segments": [...]}
    segments = data if isinstance(data, list) else data.get("segments", [])
    if not segments:
        return False, "segments 为空"

    # 兼容两种字段名：text（Stage 3 规范）或 narration_segment（旧格式）
    first_seg = segments[0]
    hook_text = first_seg.get("text", first_seg.get("narration_segment", "")).strip()
    if not hook_text:
        return False, "hook 场景的 narration_segment 为空"

    # 检查禁用模式
    for forbidden in HOOK_FORBIDDEN_STARTS:
        if hook_text.startswith(forbidden) or forbidden in hook_text[:10]:
            return False, f"hook 命中禁用模式 '{forbidden}'（疑问/互动平均 1,195 播放，数据来源：抖音 58 条）"

    # 具象度检查（c5s 根因修复：parse_hook_metrics 与 score 子分共用，避免重复解析）
    # 数据：6月高 c5s hook 均≤15字+具象锚点；7月 0729 38字+元铺垫 c5s 0.32
    from engine.hook_strength import parse_hook_metrics
    m = parse_hook_metrics(hook_text)
    if m["len"] > 20:
        return False, f"hook 字数 {m['len']}>20（前5秒需精简，6月高 c5s 均≤15字）: {hook_text[:30]}"
    if m["has_pileup"]:
        return False, f"hook 含堆叠连接词（多信息稀释钩子）: {hook_text[:30]}"
    if m["has_meta_premise"]:
        return False, f"hook 含元铺垫「方向/今天讲什么」（制作层信息，与 R-G-016 同构）: {hook_text[:30]}"
    if not (m["has_conflict"] or m["has_number"]):
        return False, f"hook 未命中数字或冲突词（c5s 需具象锚点）: {hook_text[:30]}"

    # 命中高优或数字锚定（信息性，具象度已 HARD 拦截不达标）
    is_high_value = any(kw in hook_text for kw in HOOK_HIGH_VALUE_KEYWORDS)
    hook_anchors = _get_hook_anchors(params)
    is_number_anchor = any(kw in hook_text for kw in hook_anchors) if hook_anchors else False

    if is_high_value:
        return True, f"hook 命中反直觉/冲突模式（平均 46,596 播放）: {hook_text[:30]}"
    if is_number_anchor:
        return True, f"hook 命中数字锚定模式（平均 42,783 播放）: {hook_text[:30]}"

    return True, f"hook 通过具象度校验: {hook_text[:30]}"


# 更新 GATE_CHECKERS
GATE_CHECKERS[GateType.hook_pattern_verified] = check_hook_pattern_verified
GATE_CHECKERS[GateType.narration_translation_pattern] = check_narration_translation_pattern
GATE_CHECKERS[GateType.narration_emotion_type_valid] = check_narration_emotion_type_valid


def check_hf_api_present(project_dir: Path, params: dict) -> tuple[bool, str]:
    """检查 index.html 包含 window.__hf 声明。缺 __hf → HyperFrames 渲染超时崩溃（45s）。"""
    fp = project_dir / params.get("file", "index.html")
    if not fp.exists():
        return False, "index.html 缺失"
    content = fp.read_text(encoding="utf-8", errors="ignore")

    # 检查 window.__hf 存在
    if "window.__hf" not in content:
        return False, "index.html 缺少 window.__hf 声明，HyperFrames 渲染会失败（45s 超时）" + _ASSEMBLE_HINT

    # 检查 duration 字段
    dur_match = re.search(r"window\.__hf\s*=\s*\{[^}]*duration\s*:\s*([\d.]+)", content)
    if not dur_match:
        return False, "window.__hf 缺少 duration 字段" + _ASSEMBLE_HINT

    # 检查 seek 函数
    if "seek" not in content.split("window.__hf")[1].split("}")[0]:
        return False, "window.__hf 缺少 seek 函数" + _ASSEMBLE_HINT

    duration = float(dur_match.group(1))
    return True, f"window.__hf 存在, duration={duration}s"


def check_scene_ids_match(project_dir: Path, params: dict) -> tuple[bool, str]:
    """检查 index.html 中每个 .clip 场景都有唯一 id，防止 GSAP 选择器失效。

    clip id 由组装脚本按位置生成（s01, s02, ...），本检查验证：
    1) clip 数量与 narration segments 一致
    2) 每个 clip 都有非空 id
    3) id 唯一（无重复 → 无 GSAP 选择器冲突）
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

    # 提取所有 .clip 元素的 id（按出现顺序）
    clip_ids: list[str] = re.findall(r'<div[^>]*class="clip"[^>]*\bid="([^"]+)"', html_content)
    if not clip_ids:
        clip_ids = re.findall(r'<div[^>]*\bid="([^"]+)"[^>]*class="clip"', html_content)

    # 兼容两种格式：顶层数组 或 {"segments": [...]}
    if isinstance(data, list):
        segments = data
    elif isinstance(data, dict):
        segments = data.get("segments", [])
    else:
        return True, "narration_segments.json 格式未知，跳过场景 ID 检查"
    n = len(segments)

    # 数量检查
    if len(clip_ids) != n:
        return False, f"clip 数量不匹配: HTML {len(clip_ids)} 个 vs narration {n} 段（GSAP 动画将失效）" + _ASSEMBLE_HINT

    # id 存在性检查
    if any(not cid for cid in clip_ids):
        return False, "存在无 id 的 clip（GSAP 动画将失效）" + _ASSEMBLE_HINT

    # 唯一性检查
    seen: set[str] = set()
    dupes: set[str] = set()
    for cid in clip_ids:
        if cid in seen:
            dupes.add(cid)
        seen.add(cid)
    if dupes:
        return False, f"clip id 重复（GSAP 选择器将冲突）: {', '.join(sorted(dupes))}" + _ASSEMBLE_HINT

    return True, f"所有 {n} 个 clip id 唯一且存在 ({clip_ids[0]}..{clip_ids[-1]})"


def check_composition_structure(project_dir: Path, params: dict) -> tuple[bool, str]:
    """检查 index.html 包含 HyperFrames composition 结构。缺 data-composition-id / __timelines 注册 / timeline {paused:true} → 渲染后文字层层覆盖。"""
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

    # GSAP repeat:-1（OOM/probe 根因：infinite repeat 破坏 HF 确定性捕获引擎，HF lint error，2026-07-03 复现）
    if re.search(r'repeat:\s*-1', content):
        issues.append("GSAP repeat:-1（infinite）→ 破坏 HF 确定性捕获，browser probe 可能 OOM。用有限 repeat: Math.floor(duration/cycle)-1，或环境运动改 CSS animation infinite")

    # data-composition-id 与 __timelines["X"] 匹配（OOM 根因：mismatch → probe 等 timeline 注册超时 45s → OOM "Set maximum size exceeded"）
    comp_m = re.search(r'data-composition-id="([^"]+)"', content)
    tl_m = re.search(r'__timelines\[\s*["\']([^"\']+)["\']\s*\]\s*=', content)
    if comp_m and tl_m and comp_m.group(1) != tl_m.group(1):
        issues.append(f'data-composition-id="{comp_m.group(1)}" 与 __timelines["{tl_m.group(1)}"] 不匹配 → browser probe 等 timeline 注册超时 → OOM。两者必须一致（通常 =main）')

    if issues:
        return False, f"composition 结构缺陷: {'; '.join(issues)}" + _ASSEMBLE_HINT

    return True, "composition 结构完整（composition-id + __timelines + paused）"


def check_root_attributes_complete(project_dir: Path, params: dict) -> tuple[bool, str]:
    """根组合必须含 data-width/data-height，audio 必须含 data-start。缺尺寸属性 → HyperFrames viewport 错误 → 全黑帧。"""
    fp = project_dir / params.get("file", "index.html")
    if not fp.exists():
        return False, "index.html 缺失"
    content = fp.read_text(encoding="utf-8", errors="ignore")

    issues: list[str] = []

    # 检查根组合 data-width/data-height
    root_pattern = r'<div[^>]*data-composition-id="main"[^>]*>'
    match = re.search(root_pattern, content)
    if not match:
        return False, '未找到 data-composition-id="main" 的根组合' + _ASSEMBLE_HINT

    root_tag = match.group(0)
    missing = []
    if 'data-width="' not in root_tag:
        missing.append("data-width")
    if 'data-height="' not in root_tag:
        missing.append("data-height")
    if missing:
        issues.append(f"根组合缺少 {', '.join(missing)} → HyperFrames viewport 错误 → 黑帧")
    # 根 data-start="0"（OOM 根因：缺 data-start → HF runtime 无法开始播放 → browser probe 异常 → "Set maximum size exceeded"，2026-07-03 复现确认）
    if 'data-start="' not in root_tag:
        issues.append('根组合缺少 data-start="0" → HF runtime 无法开始播放，browser probe 异常可能 OOM（Set maximum size exceeded）')

    # 检查 audio 元素的 data-start
    audio_tags = re.findall(r'<audio[^>]*>', content)
    audio_missing = []
    for i, tag in enumerate(audio_tags, 1):
        if 'data-start="' not in tag:
            audio_missing.append(f"audio#{i}")
    if audio_missing:
        issues.append(f'<audio> 元素缺少 data-start="0": {", ".join(audio_missing)}')

    if issues:
        return False, "; ".join(issues) + _ASSEMBLE_HINT

    return True, "根组合尺寸属性完整（data-width + data-height + audio data-start）"


def check_output_no_bgm_valid(project_dir: Path, params: dict) -> tuple[bool, str]:
    """检查 output_no_bgm.mp4 不是黑屏。误用 ffmpeg color=c=black 会生成纯黑屏；正确方式是从 output.mp4 取视频轨 + narration.mp3 音频轨。"""
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
    """检查 bgm.wav 时长是否覆盖旁白总时长。BGM < 旁白 → 后半段无背景音乐（bgm_pipeline.sh 未执行）。

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
    HyperFrames discoveredDuration = max(所有音频轨) = BGM 时长（以最长音频轨为视频时长）。
    BGM > 旁白 → 视频延伸，旁白结束后出现纯画面无旁白。
    根因：bgm_pipeline.sh TARGET_DUR = 旁白 + 1s 缓冲，系统性地使 BGM 比旁白长。

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
    data-duration 必须取自 actual_duration（实测），不可用 estimated_duration（预估，可偏 16.9%）→ 误用会导致旁白与画面节奏不同步。

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

    # 提取 clip 级别的 data-duration 值（排除 root composition 和 audio/video 标签）
    html_durations = []
    for m in re.finditer(r'data-duration=["\']?([\d.]+)', html_content):
        tag_start = html_content.rfind('<', 0, m.start())
        tag_end = html_content.find('>', m.start())
        tag = html_content[tag_start:tag_end] if tag_start >= 0 and tag_end >= 0 else ""
        if 'data-composition-id' in tag:
            continue
        if tag.lstrip().startswith('<audio') or tag.lstrip().startswith('<video'):
            continue
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
    TTS 语速或分段估算偏差会导致 actual vs estimated 系统性偏离（单段可达 45%）。本门禁在 Stage 4 结束后对比两份时长数据，发现系统性偏差时预警。

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


# ═══════════════════════════════════════════════════════════════════════
# 描述保真度检测器 — 杜绝从 owner/repo 名杜撰项目描述
# 从 owner/repo 名杜撰项目描述会导致观众搜索找不到项目。
# 本门禁要求 content_ready.txt 内嵌原始英文 description，用子串匹配验证。
# ═══════════════════════════════════════════════════════════════════════


def _parse_content_ready_projects(text: str) -> list[tuple[str, str]]:
    """解析 content_ready.txt 中的显式项目条目行，返回 [(owner/repo, full_line), ...]。

    兼容两种格式：
    - 编号列表：`5. refactoringhq/tolaria | TypeScript | ... | AI 代码重构平台`
    - Markdown 表格：`| 1 | apple/container | Swift | ... |`
    提取每行第一个 `owner/repo` token（排除 URL/文件路径）。
    """
    projects: list[tuple[str, str]] = []
    seen: set[str] = set()
    # 贪心匹配 owner/repo（最长匹配，避免 last30days-skill 被截断）
    repo_re = re.compile(r"(?<![\w/.])([A-Za-z][\w.-]*/[A-Za-z][\w.-]*)")
    for line in text.splitlines():
        stripped = line.lstrip("| ").strip()
        # 仅处理形如"条目"的行：以数字开头，或表格行含 |
        is_entry = bool(re.match(r"^\d+[\.\)、\s]", stripped)) or (
            line.count("|") >= 2 and re.search(r"\| *\d+[\s|]", line)
        )
        if not is_entry:
            continue
        m = repo_re.search(line)
        if not m:
            continue
        repo = m.group(1).strip(".-")
        # 排除明显非 GitHub repo 的（含点号像域名、两部分无字母）
        if "." in repo and not re.search(r"[A-Za-z]", repo.split("/")[-1]):
            continue
        if repo not in seen:
            seen.add(repo)
            projects.append((repo, line))
    return projects


def check_description_fidelity(project_dir: Path, params: dict) -> tuple[bool, str]:
    """交叉校验 content_ready.txt 项目描述与 raw_trending.json 原始描述保真度。

    仅当 raw_trending.json 存在（GitHub 分类）时生效，其他分类优雅跳过。

    设计原理：跨语言语义判断（中译英锚点重叠）无法做成零误报的 HARD 门禁
    ——忠实翻译会把 dossier→档案、methodology→方法论，英文锚点全丢。
    因此采用"原始描述内嵌"机制：content_ready.txt 必须内嵌每个项目的原始
    英文 description，门禁用确定性子串匹配验证（零跨语言歧义）。LLM 被迫
    把真实描述写在中文旁边，从源头杜绝从 owner/repo 名杜撰。

    检查项（任一失败即 HARD）：
    1. **描述锚点存在**：raw_trending.json 中每个被 content_ready.txt 提及的
       项目，其 description（非空时）必须以子串形式出现在 content_ready.txt 中。
    2. **项目存在性**：显式项目条目行中的 owner/repo 必须存在于 raw_trending.json。
    """
    content_fp = project_dir / params.get("content_file", "content_ready.txt")
    raw_fp = project_dir / params.get("raw_file", "raw_trending.json")

    # 非 GitHub 分类（无 raw_trending.json）优雅跳过
    if not raw_fp.exists():
        return True, "raw_trending.json 不存在，跳过描述保真度检查（非数据源分类）"
    if not content_fp.exists():
        return True, "content_ready.txt 不存在，跳过描述保真度检查"

    try:
        raw_data = json.loads(raw_fp.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        return False, f"raw_trending.json 解析失败: {e}"

    raw_projects = raw_data.get("projects", []) if isinstance(raw_data, dict) else raw_data
    if not isinstance(raw_projects, list):
        return True, "raw_trending.json 无 projects 列表，跳过"
    raw_map: dict[str, dict] = {}
    for p in raw_projects:
        if isinstance(p, dict):
            name = p.get("name") or p.get("full_name") or p.get("repo")
            if name:
                raw_map[str(name).strip()] = p

    content_text = content_fp.read_text(encoding="utf-8", errors="ignore")
    # HTML 实体规范化（&amp; → &）：github_trending.py 从 HTML 抓取的 description 含未解码实体，
    # 与 content_ready.txt 中自然写法的 & 语义等价却判失败。统一 unescape 消除编码差异误判。
    content_norm = html.unescape(content_text)
    content_lower = content_norm.lower()
    lines = content_text.splitlines()

    # ── 检查 1：描述锚点存在（子串匹配，零跨语言歧义）──
    missing_anchors: list[str] = []
    anchor_checked = 0
    for repo, p in raw_map.items():
        # 仅校验被 content_ready.txt 提及的项目
        if not any(repo in line for line in lines):
            continue
        raw_desc = (p.get("description") or "").strip()
        if not raw_desc:
            continue  # 原始描述为空，无锚点可比对
        anchor_checked += 1
        # 子串匹配（大小写不敏感，HTML 实体已规范化）。原始英文 description 必须原样出现在文件中。
        if html.unescape(raw_desc).lower() not in content_lower:
            missing_anchors.append(repo)

    # ── 检查 2：项目存在性（显式条目行中的 repo 必须在 raw_map）──
    entries = _parse_content_ready_projects(content_text)
    missing_projects: list[str] = []
    for repo, _line in entries:
        if repo not in raw_map:
            missing_projects.append(repo)

    problems: list[str] = []
    if missing_anchors:
        problems.append(
            f"项目描述锚点缺失（content_ready.txt 未内嵌原始 description）: "
            f"{', '.join(missing_anchors[:6])}"
        )
    if missing_projects:
        problems.append(
            f"显式条目项目不在 raw_trending.json（疑似杜撰）: {', '.join(missing_projects[:6])}"
        )

    if problems:
        return False, "描述保真度不达标: " + " | ".join(problems)
    return True, f"{anchor_checked} 个项目描述锚点合格（原始 description 已内嵌）"


GATE_CHECKERS[GateType.description_fidelity_valid] = check_description_fidelity


def check_phase_timings_valid(project_dir: Path, params: dict) -> tuple[bool, str]:
    """检查 phase_timings.json 的完整性：phase 时间覆盖完整场景时长，无间隙/重叠。
    手工 GSAP 硬编码断点会导致旁白与画面不同步；phase_calibrator.py 自动校准后，本门禁确保产出完整无遗漏。

    检查项：
    1. phase_timings.json 存在且可解析
    2. 每个 scene 的 phases 覆盖完整 duration（间隙 > max_gap 秒判定为失败）
    3. phase 起止时间无重叠（后一 phase start_offset < 前一 phase end_offset）
    4. 首个 phase start_offset=0，末个 phase end_offset=duration
    """
    pt_file = project_dir / params.get("file", "phase_timings.json")
    max_gap = params.get("max_gap", 0.5)

    if not pt_file.exists():
        # Check whether there are multi-phase scenes that require phase timings
        narr_file = project_dir / "narration_segments.json"
        if narr_file.exists():
            try:
                narr_data = json.loads(narr_file.read_text(encoding="utf-8"))
                segs = narr_data if isinstance(narr_data, list) else narr_data.get("segments", [])
                multi_phase_scenes = [
                    s.get("scene", "?") for s in segs
                    if len(s.get("visual_phases", [])) > 1
                ]
                if multi_phase_scenes:
                    return False, (
                        f"phase_timings.json 缺失，但有 {len(multi_phase_scenes)} 个多 phase 场景 "
                        f"({', '.join(multi_phase_scenes[:4])})。"
                        f"骨架 fallback 会用文本比例估算（精度 ±30%），建议运行 phase_calibrator.py 获取精确校准"
                    )
            except Exception:
                pass
        return True, "phase_timings.json 不存在且无多 phase 场景，跳过"

    try:
        pt_data = json.loads(pt_file.read_text(encoding="utf-8"))
    except Exception as e:
        return False, f"phase_timings.json 解析失败: {e}"

    # 兼容旧格式：纯 list → {"scenes": list}
    if isinstance(pt_data, list):
        pt_data = {"scenes": pt_data}

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

    # 兼容旧格式：纯 list → {"scenes": list}
    if isinstance(pt_data, list):
        pt_data = {"scenes": pt_data}

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


def check_phase_visibility_present(project_dir: Path, params: dict) -> tuple[bool, str]:
    """检查多 phase 场景的 Phase 2+ 是否有 GSAP opacity:1 恢复。

    骨架模板将 Phase 2+ 设为 opacity:0，phase_timings.json 或 fallback breakpoints
    应自动恢复可见性。本门禁扫描最终 HTML 确认恢复逻辑存在。
    """
    narr_file = project_dir / params.get("segments_file", "narration_segments.json")
    html_file = project_dir / params.get("html_file", "index.html")
    pt_file = project_dir / "phase_timings.json"

    if not narr_file.exists():
        return True, "narration_segments.json 缺失，跳过 phase visibility 检查"
    if not pt_file.exists():
        return True, "phase_timings.json 缺失，HTML 未使用 phase 分镜模式，跳过"
    if not html_file.exists():
        return True, "index.html 缺失，跳过"

    try:
        narr_data = json.loads(narr_file.read_text(encoding="utf-8"))
    except Exception:
        return True, "narration_segments.json 解析失败，跳过"

    segs = narr_data if isinstance(narr_data, list) else narr_data.get("segments", [])

    # 教程 reveal 模式（§6.16）：单 phase div + 多 region + data-reveal，不切 phase。
    # 此模式下 visual_phases 记录 reveal 步骤（每步一个 region reveal 时间点），不对应 phase-2+ 切换。
    # 判定：任一 segment 标 tutorial_reveal_mode:true，且 HTML 含 data-reveal 属性 → 跳过 phase-2+ 可见性检查
    tutorial_reveal = any(
        (seg.get("tutorial_reveal_mode") in (True, "true", 1, "1"))
        for seg in segs if isinstance(seg, dict)
    )

    html = html_file.read_text(encoding="utf-8", errors="ignore")
    if tutorial_reveal and 'data-reveal="' in html:
        return True, "教程 reveal 模式（§6.16 单 phase + 多 region + data-reveal），跳过 phase-2+ 可见性检查"

    # 提取 HTML 中所有 clip 的真实 id（按出现顺序，适配 s01/s1 等任意格式）
    html_clip_ids: list[str] = re.findall(r'<div[^>]*class="clip"[^>]*\bid="([^"]+)"', html)
    if not html_clip_ids:
        html_clip_ids = re.findall(r'<div[^>]*\bid="([^"]+)"[^>]*class="clip"', html)

    multi_phase = []
    for i, seg in enumerate(segs):
        phases = seg.get("visual_phases", [])
        num = phases if isinstance(phases, int) else len(phases)
        if num > 1:
            scene_name = seg.get("scene", f"segment-{i}")
            # 用 HTML 中的真实 clip id（组装脚本生成），fallback 到 sNN 格式
            real_id = html_clip_ids[i] if i < len(html_clip_ids) else f"s{i+1:02d}"
            multi_phase.append((str(scene_name), real_id, num))

    if not multi_phase:
        return True, "无多 phase 场景，跳过"

    missing: list[str] = []
    # 字符类：匹配 ' " , 空白 ) — 确保选择器 .phase-N 是末尾而非后代前缀
    _term_chars = "['" + '"' + ",\\s)]"
    for scene_name, real_id, num_phases in multi_phase:
        for phase_num in range(2, num_phases + 1):
            # Must target the .phase-N container itself (not children like .phase-N > div)
            pat_to = rf"tl\.(to|set)\([^)]*#{re.escape(real_id)}\s+\.phase-{phase_num}(?={_term_chars})[^)]*\{{[^}}]*opacity\s*:\s*1"
            if not re.search(pat_to, html):
                missing.append(f"{scene_name} .phase-{phase_num}")

    if missing:
        return False, (
            f"R-S6-022: {len(missing)} 个 phase 无可见性恢复: "
            f"{', '.join(missing[:6])}。"
            f"Phase 2+ 在骨架中被设为 opacity:0 但从未恢复 → 空白帧"
        )

    return True, f"所有 {len(multi_phase)} 个多 phase 场景的 phase-2+ 可见性已恢复"


GATE_CHECKERS[GateType.phase_timings_valid] = check_phase_timings_valid
GATE_CHECKERS[GateType.phase_anchor_coverage] = check_phase_anchor_coverage
GATE_CHECKERS[GateType.phase_visibility_present] = check_phase_visibility_present


def check_video_bitrate_valid(project_dir: Path, params: dict) -> tuple[bool, str]:
    """检查渲染后的视频码率是否正常，防止黑屏视频通过。
    CSS class 切换可见性（非 GSAP timeline）会使所有场景 opacity:0 → 黑屏视频（1080x1920 正常应 > 500 kbps）。

    检测策略：
    1. 用 ffprobe 获取视频码率
    2. 低于 min_bitrate_kbps（默认 500 kbps）判定为黑屏/异常
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
    min_kbps = params.get("min_bitrate_kbps", 500)

    if bitrate_kbps < min_kbps:
        return False, (
            f"视频码率异常: {bitrate_kbps:.0f} kbps < {min_kbps} kbps（疑似黑屏）。"
            f"分辨率 {width}x{height}, 时长 {duration:.1f}s。"
            f"常见原因：index.html 使用 CSS class 切换可见性而非 GSAP timeline"
        )

    return True, f"视频码率正常: {bitrate_kbps:.0f} kbps ({width}x{height}, {duration:.1f}s)"


def check_html_no_css_visibility(project_dir: Path, params: dict) -> tuple[bool, str]:
    """检查 index.html 禁止使用 CSS class 切换场景可见性（HyperFrames 不执行 CSS class 切换）。
    HyperFrames 通过 GSAP timeline seek 驱动，不添加/移除 CSS class；用 CSS class 切换可见性 → 所有场景永远 opacity:0 → 黑屏。

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
        return False, f"R-S6-011: {'; '.join(issues)}。正确方式：GSAP timeline .set()/.fromTo() 控制场景可见性"

    return True, "未检测到 CSS class 可见性切换模式"


GATE_CHECKERS[GateType.video_bitrate_valid] = check_video_bitrate_valid
GATE_CHECKERS[GateType.html_no_css_visibility] = check_html_no_css_visibility


# ═══════════════════════════════════════════════════════════════════════
# HTML 内容级检测器 — R-R-008 / R-R-009 / R-R-010
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
    """分类 bg 层中的视觉元素类型。

    优先读组件声明（data-bg-types，由 s6_assemble_html 从 @ComponentMeta visual_types 注入），
    无声明时用正则识别。声明优先避免分类器正则追不上组件库实际 CSS 写法（2026-06-23 事故）。
    """
    decl = re.search(r'data-bg-types="([^"]+)"', bg_chunk)
    if decl:
        return {t.strip() for t in decl.group(1).split(",") if t.strip()}
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
    # 粒子：发光小圆点（box-shadow:0 0 Npx 是粒子典型发光，区别于 filter:blur 的 glow 光晕）。
    # 组件库大量用 <div border-radius:50% + box-shadow:0 0 Npx> 做粒子，旧分类器不认导致
    # diamond_lattice 等丰富组件被误判为 glow+grid 三件套（2026-06-23 事故）
    if re.search(r'box-shadow\s*:\s*0(?:px)?\s+0(?:px)?\s+\d{1,2}px', bg_chunk):
        types.add("particles")
    # 几何节点：clip-path 菱形/多边形/圆形装饰前景（旧分类器完全不识别）
    if re.search(r'clip-path\s*:\s*(?:polygon|circle|ellipse|inset)', bg_chunk):
        types.add("geometry")
    # 流光条带：横向/纵向 linear-gradient 条带（两端 transparent 的光带，非 conic 的 beams 补充）
    if re.search(r'linear-gradient\([^)]{0,30}transparent[^)]{0,80}transparent[^)]{0,30}\)', bg_chunk) \
       and not re.search(r'linear-gradient[^;]{0,60}1px', bg_chunk):
        types.add("beams")
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
        if re.search(r'(?:^|;)\s*opacity\s*:\s*0(?:\.0+)?\s*(?:;|$|")', s):
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
    """R-R-009: bg 层必须 ≥2 种视觉元素类型，禁止 glow+grid 三件套。"""
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
        return False, f"R-R-009: {'; '.join(violations[:6])}"
    return True, f"{len(scenes)} 场景 bg 视觉多样性合格"


def check_adjacent_bg_diversity(project_dir: Path, params: dict) -> tuple[bool, str]:
    """R-R-010: 相邻场景 bg 必须有可区分的视觉差异。"""
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
            f"R-R-010: {len(violations)} 对相邻同质 "
            f"({unique_styles} 种风格/{len(scenes)} 场景, 需≥{min_styles}); "
            f"{'; '.join(violations[:4])}"
        )
    if unique_styles < min_styles:
        return False, f"R-R-010: 风格组不足 ({unique_styles}/{min_styles})"
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
        # 检查 fx 元素数量（至少 3 个子 div）
        fx_child_divs = len(re.findall(r'<div\b', fx)) - 1  # 减去 layer-fx 自身
        if fx_child_divs < 3:
            violations.append(f"{sid}(仅{fx_child_divs}元素,需≥3)")
            continue
        # 检查特效类型多样性（≥2 个不同 fx-* class，防 3 个同类光晕凑数）
        fx_classes = set()
        for cls_str in re.findall(r'class="([^"]+)"', fx):
            for c in cls_str.split():
                if c.startswith('fx-') and c not in ('fx-glow', 'fx-line', 'fx-dot'):
                    fx_classes.add(c)
        if len(fx_classes) < 2:
            violations.append(f"{sid}(仅{len(fx_classes)}种fx类型,需≥2)")
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


def check_bg_component_source(project_dir: Path, params: dict) -> tuple[bool, str]:
    """R-R-021: bg 层必须使用组件库中的 bg 组件（标记+内容指纹双重验证）。"""
    fp = project_dir / params.get("file", "index.html")
    if not fp.exists():
        return False, "index.html 缺失"
    html = fp.read_text(encoding="utf-8", errors="ignore")
    scenes = _split_into_scenes(html)
    if not scenes:
        return True, "无场景可检查"

    _bg_dir = Path(__file__).resolve().parent.parent / "components" / "bg"
    no_marker = []
    missing_comp = []
    fake_marker = []

    for sid, scene_html in scenes:
        bg = _extract_layer_chunk(scene_html, "layer-bg")
        if not bg.strip():
            continue  # 空 bg 由其他规则检查

        # --- 标记检查 ---
        marker = re.search(r'<!--\s*bg-component:\s*(\S+)\s*-->', bg)
        if not marker:
            no_marker.append(sid)
            continue

        comp_name = marker.group(1)
        comp_path = _bg_dir / f"{comp_name}.html"

        # --- 组件文件存在性 ---
        if not comp_path.exists():
            missing_comp.append(f"{sid}({comp_name})")
            continue

        # --- 内容指纹验证 ---
        # 组件 @keyframes 名称集合 vs layer-bg animation 引用集合
        comp_content = comp_path.read_text(encoding="utf-8", errors="ignore")
        comp_kf = set(re.findall(r'@keyframes\s+([\w-]+)', comp_content))
        bg_anim_names = set()
        for m in re.finditer(r'animation\s*:\s*([\w-]+)', bg):
            bg_anim_names.add(m.group(1))
        used_kf = comp_kf & bg_anim_names

        if comp_kf and not used_kf:
            # 组件有动画但 layer-bg 未引用任何组件 keyframe → 假标记
            fake_marker.append(f"{sid}({comp_name}):0/{len(comp_kf)} keyframes引用")
        elif not comp_kf:
            # 静态组件：检查 div 数量（真组件 DOM 通常 ≥3 个 div）
            bg_divs = len(re.findall(r'<div\b', bg))
            if bg_divs < 3:
                fake_marker.append(f"{sid}({comp_name}):仅{bg_divs}个div(静态组件)")

    issues = []
    if no_marker:
        issues.append(f"{len(no_marker)}个无标记({','.join(no_marker[:4])})")
    if missing_comp:
        issues.append(f"{len(missing_comp)}个组件不存在({','.join(missing_comp[:4])})")
    if fake_marker:
        issues.append(f"{len(fake_marker)}个假标记({','.join(fake_marker[:4])})")

    if issues:
        return False, "R-R-021: " + "; ".join(issues)
    return True, f"{len(scenes)} 场景 bg 组件来源+内容合格"


GATE_CHECKERS[GateType.bg_component_source] = check_bg_component_source


def check_fx_animation_present(project_dir: Path, params: dict) -> tuple[bool, str]:
    """R-R-013: fx 层元素必须有 GSAP 动画目标。根因：原无规则要求 fx 有 GSAP 动画，门禁只检查"非空" → fx 全是静态 div。"""
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

        # 使用正则搜索 GSAP 动画调用
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

        if not has_fx_animation:
            violations.append(sid)

    if violations:
        return False, f"R-R-013: {len(violations)} 个场景 fx 层无 GSAP 动画 ({', '.join(violations[:6])})"
    return True, f"{len(scenes)} 场景 fx 动画合格"


def check_safezone_rendered(project_dir: Path, params: dict) -> tuple[bool, str]:
    """渲染后内容必须在安全区内(竖屏 y∈[180,1700] / 横屏 y∈[60,1860])。
    优先读 visual_qa_report.json(s6_visual_qa.py 产出);不存在则自抽帧(解耦,门禁不依赖 QA 是否跑过)。

    skip(output.mp4 缺失)是有意设计:本门禁在渲染前(组合结构检查阶段,output 不存在)和渲染后两次触发,渲染前必须 skip 不阻塞;这与 video_bitrate 等 sibling 门禁(仅渲染后触发,output 缺失即 fail)不同。
    """
    import sys, shutil
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from lib.visual_qa import extract_scene_frames, analyze_frame, check_safezone

    output_mp4 = project_dir / "output.mp4"
    if not output_mp4.exists():
        return (True, "skip(output.mp4 不存在,渲染前检查)")  # 仅在 output 存在时生效

    orientation = "portrait"
    design = project_dir / "design.md"
    if design.exists():
        if re.search(r"^orientation:\s*landscape", design.read_text(encoding="utf-8"), re.M):
            orientation = "landscape"

    scenes = None
    report_path = project_dir / "visual_qa_report.json"
    if report_path.exists():
        try:
            scenes = json.loads(report_path.read_text(encoding="utf-8")).get("scenes")
        except (json.JSONDecodeError, ValueError, OSError):
            scenes = None  # malformed → fallback to self-extract
    if scenes is None:
        seg_path = project_dir / "segment_durations.json"
        if not seg_path.exists():
            return (True, "skip(无 segment_durations.json,无法定位场景时间点)")
        segs = json.loads(seg_path.read_text(encoding="utf-8")).get("segments", [])
        t = 0.0
        time_points = []
        for s in segs:
            dur = s.get("actual_duration", 0)
            time_points.append({"scene": s.get("scene", "s"), "t": t + dur / 2})
            t += dur
        out_dir = project_dir / ".qa_frames_gate"
        try:
            frames = extract_scene_frames(str(output_mp4), time_points, str(out_dir))
            scenes = []
            for f in frames:
                cy = analyze_frame(f["path"])["content_y"]
                scenes.append({"id": f["scene"], "content_y": cy})
        finally:
            shutil.rmtree(out_dir, ignore_errors=True)

    for sc in scenes:
        res = check_safezone(sc.get("content_y"), orientation)
        if not res["ok"]:
            return (False, f"{sc.get('id')}: 内容溢出安全区 {res['overflow']} "
                    f"(content_y={sc.get('content_y')}, bounds={res['bounds']})")
    return (True, f"全部 {len(scenes)} 场景内容在安全区内")


GATE_CHECKERS[GateType.fx_animation_present] = check_fx_animation_present
GATE_CHECKERS[GateType.safezone_rendered] = check_safezone_rendered


def check_portrait_typography(project_dir: Path, params: dict) -> tuple[bool, str]:
    """R-R-015/R-R-016: 竖屏排版门禁 — 检查字号最低标准 + 禁用 section-tag 小徽章。根因：原无字号门禁，字号体系未区分竖屏/横屏 → 正文过小，手机端不可读。"""
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
        min_body = 38
        min_annotation = 32

    violations = []

    # 1. 检查 section-tag 小徽章（R-R-016）
    # 兼容单引号和双引号的 class 属性
    section_tag_pattern = r'''class=['"][^'"]*section-tag[^'"]*['"]'''
    section_tags = re.findall(section_tag_pattern, html)
    if section_tags:
        violations.append(f"R-R-016: 发现 {len(section_tags)} 个 section-tag 小徽章（禁止作为场景标题）")

    # 2. 检查字号最低标准（R-R-015）
    # 地板值 = min_annotation：content 层任何可见文字不得低于此值。
    # 正文和标注的区分交给 LLM 创意，门禁只执行绝对地板。
    min_readable = min_annotation  # 32px(竖屏) / 24px(横屏)
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


def _collect_top_level_divs(html: str, start: int = 0, limit: int | None = None) -> list[str]:
    """收集 html 中深度为 1（顶层）的所有完整 div 块。

    用 <div / </div> 深度栈匹配，处理任意嵌套。limit 提前终止。
    - start 指向某个 <div 开标签 + limit=1 → 返回该 div 的完整闭合块（用于取容器）
    - 对"剥掉外层后的 inner"调用、不限 limit → 得到其全部直接子 div
    依赖规整 HTML（LLM 渲染产物无 <div> 碎片注释），SOFT 门禁容许极小概率误读。
    """
    blocks: list[str] = []
    n = len(html)
    i = start
    depth = 0
    cur_start: int | None = None
    while i < n:
        open_idx = html.find("<div", i)
        close_idx = html.find("</div>", i)
        if open_idx == -1 and close_idx == -1:
            break
        if open_idx != -1 and (close_idx == -1 or open_idx < close_idx):
            if depth == 0:
                cur_start = open_idx
            depth += 1
            gt = html.find(">", open_idx)
            if gt == -1:
                break
            i = gt + 1
        else:
            depth -= 1
            close_end = close_idx + len("</div>")
            if depth == 0 and cur_start is not None:
                blocks.append(html[cur_start:close_end])
                cur_start = None
                if limit is not None and len(blocks) >= limit:
                    return blocks
            i = close_end
    return blocks


def _strip_outer_div(block: str) -> str:
    """剥掉 div 块最外层开/闭标签，返回内部 HTML。"""
    m = re.match(r'<div\b[^>]*>', block)
    if not m:
        return block
    inner_start = m.end()
    end = block.rfind("</div>")
    return block[inner_start:end] if end != -1 else block[inner_start:]


def _row_has_width_constraint(child_block: str, equal_width_classes: list[str]) -> bool:
    """判断子 div 是否有等宽约束（有则豁免，不算裸行）。

    等宽 = 命中等宽组件类（width:100%+max-width） 或 内联 width/max-width。
    负向回顾 (?<![\\w-]) 排除 min-width / border-width 等带前缀词。
    """
    open_m = re.match(r'<div\b[^>]*>', child_block)
    if not open_m:
        return False
    open_tag = open_m.group(0)
    cls_m = re.search(r'class\s*=\s*["\']([^"\']*)', open_tag)
    if cls_m:
        cls_str = cls_m.group(1)
        for eq in equal_width_classes:
            if re.search(rf'\b{re.escape(eq)}\b', cls_str):
                return True
    if re.search(r'(?<![\w-])(?:width|max-width)\s*:', open_tag):
        return True
    return False


def check_list_alignment_valid(project_dir: Path, params: dict) -> tuple[bool, str]:
    """列表对齐门禁（SOFT）— 多行裸 div 列表容器必须 align-items:flex-start。

    只有"存在列表"时才校验对齐：检测 flex-direction:column + align-items:center 容器，
    若直接子是 ≥2 个无等宽约束的裸 div 行（shrink-to-fit、宽度依赖内容），则图标/序号/emoji
    无法落在同一垂直线 → 参差错落。等宽行项（width:100%+max-width 或等宽组件类）等宽，
    center 与 flex-start 视觉一致，豁免；<2 个直接子 div 不算列表，不校验。
    根因：LLM 写居中容器顺手 align-items:center，裸行宽度不一 → 标记符号无法垂直成列。
    """
    fp = project_dir / params.get("file", "index.html")
    if not fp.exists():
        return False, "index.html 缺失"
    html = fp.read_text(encoding="utf-8", errors="ignore")

    equal_width_classes = params.get("equal_width_classes", [
        "dim-card", "caution-row", "compare-row", "stat-card", "feature-card",
        "info-card", "data-card", "metric-row", "step-card", "tag-row",
        "card-row", "benefit-row", "point-row",
    ])

    violations: list[str] = []
    for sid, scene_html in _split_into_scenes(html):
        content = _extract_layer_chunk(scene_html, "layer-content")
        if not content.strip():
            continue
        for m in re.finditer(r'<div\b[^>]*>', content):
            tag = m.group(0)
            # 排除 .phase 自身（合法的居中锚点）
            if re.search(r'class\s*=\s*["\'][^"\']*\bphase\b', tag):
                continue
            if not re.search(r'flex-direction\s*:\s*column', tag):
                continue
            if not re.search(r'align-items\s*:\s*center', tag):
                continue
            # 取容器完整块（limit=1：扫到自身闭合即止）
            top = _collect_top_level_divs(content, m.start(), limit=1)
            if not top:
                continue
            children = _collect_top_level_divs(_strip_outer_div(top[0]))
            if len(children) < 2:
                continue  # 不是列表，不校验对齐
            bare_rows = [c for c in children if not _row_has_width_constraint(c, equal_width_classes)]
            if len(bare_rows) >= 2:
                violations.append(
                    f"{sid}({len(bare_rows)}个裸行列表 align-items:center → 标记符号错落，建议改 flex-start)"
                )

    if violations:
        return False, "列表对齐: " + "; ".join(violations[:6])
    return True, "列表对齐合格（无 center 裸行列表错落）"


GATE_CHECKERS[GateType.list_alignment_valid] = check_list_alignment_valid


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


def check_bgm_pipeline_verified(project_dir: Path, params: dict) -> tuple[bool, str]:
    """验证 BGM 音量由 bgm_pipeline.sh 校准，而非手动硬编码。

    bgm_pipeline.sh 完成后写入 .bgm_pipeline_marker.json 标记文件。
    如果 segment_durations.json 含 bgm_volume 但无标记文件 → SubAgent 跳过管线 → FAIL。

    交叉验证标记中的 bgm_volume 与 segment_durations.json 中的一致，防止伪造。
    """
    marker_file = project_dir / ".bgm_pipeline_marker.json"
    sd_file = project_dir / params.get("sd_file", "segment_durations.json")
    bgm_file = project_dir / "bgm.wav"

    # bgm.wav 不存在时不阻塞（可能还没到音频阶段）
    if not bgm_file.exists():
        return True, "bgm.wav 尚未生成，跳过管线验证"

    # segment_durations.json 不存在时也不阻塞
    if not sd_file.exists():
        return True, "segment_durations.json 尚未生成，跳过管线验证"

    # 读取 bgm_volume
    try:
        sd_data = json.loads(sd_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return True, "segment_durations.json 解析失败，跳过管线验证"

    bgm_volume = sd_data.get("meta", {}).get("bgm_volume")
    if bgm_volume is None:
        # bgm_volume 尚未写入，可能管线还没执行到这一步
        return True, "meta.bgm_volume 尚未写入，跳过管线验证"

    # 标记文件缺失 → 跳过了 bgm_pipeline.sh
    if not marker_file.exists():
        return False, (
            f"meta.bgm_volume={bgm_volume} 存在但无 .bgm_pipeline_marker.json — "
            f"未使用 bgm_pipeline.sh 校准 BGM 音量（HARD）。"
            f"修复: bash .claude/commands/clipforge/scripts/bgm_pipeline.sh"
        )

    # 验证标记文件内容
    try:
        marker = json.loads(marker_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        return False, f".bgm_pipeline_marker.json 解析失败: {e}"

    if marker.get("script") != "bgm_pipeline.sh":
        return False, f"标记文件 script 字段异常: {marker.get('script')}"

    # 交叉验证 bgm_volume 一致
    marker_vol = marker.get("bgm_volume")
    if marker_vol is not None:
        try:
            vol_diff = abs(float(marker_vol) - float(bgm_volume))
            if vol_diff > 0.02:
                return False, (
                    f"标记文件 bgm_volume={marker_vol} 与 segment_durations.json "
                    f"bgm_volume={bgm_volume} 不一致（偏差 {vol_diff:.2f}）— "
                    f"标记可能伪造或文件被覆盖"
                )
        except (ValueError, TypeError):
            return False, f"bgm_volume 格式异常: marker={marker_vol}, sd={bgm_volume}"

    # 验证 bgm_duration 合理
    marker_dur = marker.get("bgm_duration", 0)
    try:
        if float(marker_dur) <= 0:
            return False, "标记文件 bgm_duration ≤ 0"
    except (ValueError, TypeError):
        return False, f"标记文件 bgm_duration 格式异常: {marker_dur}"

    return True, f"BGM 由 bgm_pipeline.sh 校准（volume={bgm_volume}, mode={marker.get('mode', 'N/A')}）"


GATE_CHECKERS[GateType.bgm_pipeline_verified] = check_bgm_pipeline_verified


def check_bgm_volume_provenance(project_dir: Path, params: dict) -> tuple[bool, str]:
    """检查 bgm_volume 来源合规性（bgm_pipeline.sh 执行证明）。

    bgm_pipeline.sh 首次运行时:
    1. 创建 bgm_orig.wav 作为原始备份
    2. 调用 bgm_gap_check.py 公式计算 volume
    3. 写入 segment_durations.json

    检查策略（三选一通过）：
    A. bgm_orig.wav 存在 = 管线执行过（最强证据）
    B. segment_durations.json 含 meta.bgm_volume_source = "formula" 标记
    C. 都不满足 → 拒绝（疑似手动硬编码）
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

    # 策略 B: 来源标记（formula=当前公式，bgm_pipeline/bgm_gap_check.py=历史合法来源）
    source = data.get("meta", {}).get("bgm_volume_source", "")
    if source in ("formula", "bgm_pipeline", "bgm_gap_check.py"):
        return True, f"meta.bgm_volume_source = {source} → 校准已执行"

    # 策略 C: 无溯源标记 → 拒绝
    vol = data.get("meta", {}).get("bgm_volume", 0)
    return False, (
        f"R-S4-005: bgm_volume={vol} 无溯源标记（bgm_volume_source 缺失），"
        f"bgm_orig.wav 也不存在。"
        f"修复: bash .claude/commands/clipforge/scripts/bgm_pipeline.sh"
    )


GATE_CHECKERS[GateType.narration_sample_rate_valid] = check_narration_sample_rate
GATE_CHECKERS[GateType.bgm_volume_provenance_valid] = check_bgm_volume_provenance


def check_bgm_volume_table_valid(project_dir: Path, params: dict) -> tuple[bool, str]:
    """验证 bgm_volume 是否由公式正确计算。

    用 bgm_gap_check.py 的 calc_volume 函数，以存储的 bgm_mean_db 和 bgm_max_db
    重新计算预期 volume，与实际 bgm_volume 对比。
    """
    import math
    import sys
    scripts_dir = Path(__file__).parent.parent / "scripts"
    sys.path.insert(0, str(scripts_dir))
    from bgm_gap_check import calc_volume, NARR_MEAN_REF

    sd_file = project_dir / params.get("file", "segment_durations.json")
    if not sd_file.exists():
        return False, "segment_durations.json 缺失"

    try:
        data = json.loads(sd_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        return False, f"segment_durations.json 解析失败: {e}"

    meta = data.get("meta", {})
    bgm_mean = meta.get("bgm_mean_db")
    bgm_max = meta.get("bgm_max_db")
    bgm_volume = meta.get("bgm_volume")

    if bgm_mean is None:
        return False, (
            "meta.bgm_mean_db 缺失 — bgm_gap_check.py 未写入溯源数据。"
            "修复: python scripts/bgm_gap_check.py <mean> <max> <narr_max>"
        )

    if bgm_volume is None:
        return False, "meta.bgm_volume 缺失"

    if bgm_max is None:
        return False, (
            "meta.bgm_max_db 缺失 — bgm_gap_check.py 未写入峰值数据。"
            "修复: python scripts/bgm_gap_check.py <mean> <max> <narr_max>"
        )

    # 优先使用存储的 narr_max（精确还原计算），兜底 params 或默认值
    narr_max = meta.get("bgm_narr_max_db") or params.get("narr_max", -1.5)
    # 还原 bgm_gap_check.py 使用的分档基准：优先 LRA（pipeline 主路径写入 bgm_lra），
    # 否则回退 spread（兼容兜底）。不传 lra 时 calc_volume 会用 spread 分档，
    # 导致 LRA-balanced (peak_gap=11) 与 spread-beat-heavy (peak_gap=15) 偏差。
    lra = meta.get("bgm_lra")
    expected, reason, _ = calc_volume(bgm_mean, bgm_max, NARR_MEAN_REF, narr_max, lra=lra)

    # 允许 ±0.02 容差（round 精度）
    tolerance = params.get("tolerance", 0.02)
    diff = abs(bgm_volume - expected)

    if diff <= tolerance:
        eff_mean = bgm_mean + 20 * math.log10(bgm_volume) if bgm_volume > 0 else -120
        gap = NARR_MEAN_REF - eff_mean
        return True, (
            f"bgm_volume={bgm_volume} 公式验证通过 "
            f"(mean={bgm_mean:.1f} dB, gap={gap:.1f} dB, 方式={reason})"
        )

    return False, (
        f"bgm_volume={bgm_volume} 公式不匹配: "
        f"mean={bgm_mean:.1f} dB → 公式值={expected}, 实际={bgm_volume}, "
        f"偏差={diff:.2f} > 容差={tolerance}。"
        f"修复: python scripts/bgm_gap_check.py {bgm_mean} {bgm_max} {narr_max}"
    )


GATE_CHECKERS[GateType.bgm_volume_table_valid] = check_bgm_volume_table_valid


def _parse_douyin_platform_sections(content: str) -> dict[str, list[str]]:
    """将 douyin.md 按 ## 平台名 拆分为 {平台名: [行列表]}。

    每个 section 从 ## 平台名 开始到下一个 ## 或文档结尾。
    """
    sections: dict[str, list[str]] = {}
    current_name = None
    current_lines: list[str] = []

    for line in content.split("\n"):
        heading_match = re.match(r"^##\s+(.+)$", line)
        if heading_match:
            if current_name is not None:
                sections[current_name] = current_lines
            current_name = heading_match.group(1).strip()
            current_lines = []
        elif current_name is not None:
            current_lines.append(line)

    if current_name is not None:
        sections[current_name] = current_lines

    return sections


def _count_title_chars(line: str) -> int:
    """计算标题行的中文字符数（去掉标签和空白）。"""
    # 去掉标签部分
    text = re.sub(r'#\S+', '', line).strip()
    # 统计字符数（中文=1字，英文单词/数字=0.5字近似，直接按 len 统计视觉宽度）
    # 简化：直接用 len(text) 作为字数（中文为主的场景足够准确）
    return len(text.replace(" ", ""))


def _extract_tags(line: str) -> list[str]:
    """从一行文本中提取所有 #标签。"""
    return re.findall(r'#(\S+)', line)


def check_douyin_platforms_complete(project_dir: Path, params: dict) -> tuple[bool, str]:
    """检查 douyin.md 四平台文案质量 + 评论区自评。

    stage7-delivery.md §7.4 + cron-template.md SubAgent-4 段要求:
    1. 四平台文案必填：## 抖音、## B站、## 视频号、## 小红书
    2. 每个平台有标题 + 正文 + 标签（结构完整）
    3. 标题字数上限：抖音≤30 / B站≤80 / 视频号≤16 / 小红书≤20
    4. 标签数 ≥5 / 平台
    5. 抖音标题必须包含 ≥2 个数字（数字锚定）
    6. 视频号必须包含分享引导（"转发""分享"）
    7. 小红书必须包含收藏引导（"收藏"）
    8. 评论区自评必填，包含 owner/repo 路径
    9. 禁止搜索引导（"GitHub搜索:"）
    10. 禁止 URL/链接
    """
    douyin_file = project_dir / params.get("file", "douyin.md")
    if not douyin_file.exists():
        return False, "douyin.md 缺失"

    content = douyin_file.read_text(encoding="utf-8", errors="ignore")
    issues: list[str] = []

    # ── 0. 全局搜索引导检查（HARD — 会导致限流） ──
    search_patterns = [
        r'GitHub\s*搜索\s*[:：]',
        r'感兴趣.*搜',
        r'搜\s*项目\s*名',
    ]
    for pat in search_patterns:
        m = re.search(pat, content)
        if m:
            issues.append(f"R-G-013: 搜索引导 '{m.group()}' 会导致平台限流，改为只列项目名和 owner/repo 路径")
            break  # 只报一次

    # ── 1. 全局 URL 检查 ──
    url_match = re.search(r'https?://\S+', content)
    if url_match:
        issues.append(f"R-G-014: douyin.md 包含 URL '{url_match.group()[:60]}'，平台视为导流，删除所有链接")

    # ── 2. 四平台完整性检查 ──
    required_platforms = params.get("platforms", ["抖音", "B站", "视频号", "小红书"])
    sections = _parse_douyin_platform_sections(content)

    missing_platforms = [p for p in required_platforms if p not in sections]
    if missing_platforms:
        issues.append(f"缺少平台文案: {', '.join(missing_platforms)}（需 ## {'、'.join(required_platforms)}）")

    # ── 3. 各平台质量检查 ──
    platform_limits = {
        "抖音": {"title_max": 30, "min_numbers": 2},
        "B站": {"title_max": 80},
        "视频号": {"title_max": 16, "require_share": True},
        "小红书": {"title_max": 20, "require_collect": True},
    }
    min_tags = params.get("min_tags", 5)

    for platform_name, limit in platform_limits.items():
        if platform_name not in sections:
            continue  # 缺失已在步骤 2 报告

        lines = sections[platform_name]
        # 找到非空行（标题 + 正文 + 标签）
        non_empty = [l.strip() for l in lines if l.strip()]
        if not non_empty:
            issues.append(f"{platform_name}：文案为空")
            continue

        title_line = non_empty[0]
        title_char_count = _count_title_chars(title_line)
        title_max = limit["title_max"]

        # 3a. 标题字数检查
        if title_char_count > title_max:
            issues.append(
                f"{platform_name}标题 {title_char_count} 字，超过上限 {title_max} 字: "
                f"'{title_line[:40]}...'"
            )

        # 3b. 标签数量检查（扫描整个平台段落）
        all_tags: list[str] = []
        for l in lines:
            all_tags.extend(_extract_tags(l))
        if len(all_tags) < min_tags:
            issues.append(f"{platform_name}标签只有 {len(all_tags)} 个，要求 ≥{min_tags} 个")

        # 3c. 抖音数字锚定
        if "min_numbers" in limit:
            numbers = re.findall(r'\d+', title_line)
            if len(numbers) < limit["min_numbers"]:
                issues.append(
                    f"抖音标题数字锚定不足：只有 {len(numbers)} 个数字（{numbers or '无'}），"
                    f"要求 ≥{limit['min_numbers']} 个"
                )

        # 3d. 视频号分享引导
        if limit.get("require_share"):
            platform_text = "\n".join(lines)
            if not re.search(r"转发|分享|发给", platform_text):
                issues.append(f"视频号文案缺少分享引导（需包含'转发给做开发的朋友'等）")

        # 3e. 小红书收藏引导
        if limit.get("require_collect"):
            platform_text = "\n".join(lines)
            if not re.search(r"收藏|存下来|先存|备用", platform_text):
                issues.append(f"小红书文案缺少收藏引导（需包含'收藏备用''值得存下来'等）")

        # 3f. 正文完整性（标题 + 正文 + 标签三件套，stage7-delivery.md L218）
        # 正文 = 标题之后、去掉纯 #标签 行后的实质内容；只有标题+标签无正文则拦
        body_lines = [l for l in non_empty[1:] if re.sub(r'#\S+', '', l).strip()]
        if len(body_lines) < 1:
            issues.append(f"{platform_name}只有标题和标签，缺少正文（须标题+正文+标签三件套）")

    # ── 4. 评论区自评段 ──
    has_comment_section = (
        "## 评论区自评" in content or
        "评论区自评" in content
    )
    if not has_comment_section:
        issues.append("缺少评论区自评（需 ## 评论区自评 段落）")
    else:
        # 4a. 检查项目介绍格式（owner/repo 路径）—— 仅 github 项目盘点视频
        # 非 github 视频（商业分析/intro 等，无 raw_trending.json）评论区是数据来源
        # 说明，没有 github 项目，owner/repo 检查会误判，故仅 github 视频检查
        if (project_dir / "raw_trending.json").exists():
            has_path_format = bool(re.search(r'[\w\-\.]+/[\w\-\.]+', content))
            if not has_path_format:
                issues.append("评论区缺少 owner/repo 路径（如 'apple/container'）")

    if issues:
        return False, f"R-S7-006: {'; '.join(issues)}"

    return True, f" douyin.md 四平台文案质量检查通过（标题字数/标签数/平台引导/评论区完整）"


GATE_CHECKERS[GateType.douyin_platforms_complete] = check_douyin_platforms_complete


def check_cover_layers_present(project_dir: Path, params: dict) -> tuple[bool, str]:
    """检查 cover.html 包含 7 层封面模板结构。封面须遵循 7 层模板（不可用浏览器截图替代）；R-S7-002 原 semantic_check 自动化不可靠，改结构化 HTML 检测。

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
            f"封面禁止引用外部脚本（动画库会导致白屏截图），"
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
                f"封面禁止 JavaScript 动画代码（fromTo opacity:0 等会导致白屏），"
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

    # ── 结构性检查（模板完整性，不只是 class 名） ──
    structure_errors: list[str] = []

    # 脚本生成标记（优先检测）
    is_script_generated = "generated by generate_cover.py" in content

    if not is_script_generated:
        # 非脚本生成时，检测模板关键结构
        if not re.search(r'class="[^"]*cover[^"]*"', content):
            structure_errors.append("缺少 .cover 根容器（非脚本生成时必须）")
        if not re.search(r':root\s*\{', content):
            structure_errors.append("缺少 :root CSS 变量声明（禁止硬编码色值）")
        if not re.search(r'data-composition-id', content):
            structure_errors.append("缺少 data-composition-id（HyperFrames 渲染必需）")
        if not re.search(r'family=Inter', content):
            structure_errors.append("缺少 Inter 字体引入（应为 Inter + JetBrains Mono）")
        if not re.search(r'JetBrains', content):
            structure_errors.append("缺少 JetBrains Mono 字体引入")
        if not re.search(r'blur\(200px\)', content):
            structure_errors.append("光晕缺少 blur(200px)（应为 filter:blur(200px)）")
        # 检测是否使用了正确的 2x 画布尺寸
        has_2160 = "2160" in content
        has_3840 = "3840" in content
        if not (has_2160 and has_3840):
            structure_errors.append("画布尺寸非 2160x3840（竖屏应为 2x 超采样）")

    if structure_errors:
        return False, (
            f"封面结构性违规 ({len(structure_errors)} 项): "
            f"{'; '.join(structure_errors)}。"
            f"建议使用 scripts/generate_cover.py 生成封面"
        )

    return True, f"封面结构完整{'（脚本生成）' if is_script_generated else '（手工模板）'}"


GATE_CHECKERS[GateType.cover_layers_present] = check_cover_layers_present


def check_font_consistency(project_dir: Path, params: dict) -> tuple[bool, str]:
    """检查 design.md 声明的字体是否在 index.html 中正确加载（SOFT）。

    读取 creative/fonts.json（s6_prepare_creative.py 生成），提取 title/body/data 三层
    family，检查 index.html 的 Google Fonts <link> href 是否包含对应 family 参数
    （family 名空格 → +）。缺失即视为断链：渲染时降级为系统 fallback 字体，
    视觉偏离 design.md 的字体气质设计。

    SOFT 级别（警告，不阻塞）：仅在 family 已声明但未被任何方式加载时警告。
    系统字体（PingFang/Microsoft YaHei 等）无需 Google Fonts 加载，跳过。
    """
    fonts_path = project_dir / "creative" / "fonts.json"
    index_path = project_dir / params.get("file", "index.html")

    if not fonts_path.exists():
        return True, "无 creative/fonts.json（旧项目或未跑 prepare），跳过字体一致性检查"
    if not index_path.exists():
        return True, "无 index.html，跳过字体一致性检查"

    try:
        fonts = json.loads(fonts_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return True, "creative/fonts.json 解析失败，跳过字体一致性检查"

    content = index_path.read_text(encoding="utf-8")

    # 合并所有 Google Fonts <link> href（单 <link> 多 family 或多 <link> 均覆盖）
    hrefs = " ".join(
        re.findall(r'<link[^>]+href="([^"]*fonts\.googleapis\.com[^"]*)"', content)
    )

    # 系统字体无需 Google Fonts 加载（fallback 链兜底，不报警告）
    SYSTEM_FONTS = {
        "PingFang SC", "Microsoft YaHei", "sans-serif", "monospace",
        "serif", "SimHei", "SimSun", "Heiti SC",
    }

    missing: list[str] = []
    for layer in ("title", "body", "data"):
        fam = fonts.get(layer, {}).get("family", "")
        if not fam or fam in SYSTEM_FONTS:
            continue
        google_form = fam.replace(" ", "+")
        # Google Fonts URL 形式：family=Ma+Shan+Zheng 或 family=Noto+Sans+SC:wght@...
        # 用 "family=" 前缀锚定，避免子串误匹配（如 "Mono" 命中 "JetBrains Mono"）
        loaded = f"family={google_form}" in hrefs
        if not loaded:
            # 再查内联 font-family 声明（非 Google Fonts 的自定义加载方式）
            loaded = bool(
                re.search(rf'font-family\s*:\s*["\']?{re.escape(fam)}', content)
            )
        if not loaded:
            missing.append(f"{layer}={fam}")

    if missing:
        return False, (
            f"SOFT: index.html 未加载 design.md 声明的字体 [{', '.join(missing)}]。"
            f"渲染时降级为系统 fallback，视觉偏离字体气质设计。"
            f"检查 s6_assemble_html.py 的 GOOGLE_FONT_MAP 是否包含该字体"
        )
    return True, "字体一致性 OK：design.md 声明的字体均已通过 Google Fonts 加载"


GATE_CHECKERS[GateType.font_consistency] = check_font_consistency


def check_final_duration_close_to_output(project_dir: Path, params: dict) -> tuple[bool, str]:
    """检查 final.mp4 时长与 output.mp4 时长差异不超过容差。
    绕过 assemble_final.sh 自行拼接封面（如把 cover.png 渲成数秒封面视频拼到前面），
    会使封面无音频轨 → 旁白从 PTS=0 播放但视觉延后 → 全程 A/V 不同步。
    assemble_final.sh 正确行为：1 帧封面（~0.033s），几乎不影响时长。
    本门禁是独立于 assemble_final.sh 的最后防线。
    """
    final_file = project_dir / params.get("final_file", "final.mp4")
    output_file = project_dir / params.get("output_file", "output.mp4")
    tolerance = params.get("tolerance", 0.1)

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


def check_assemble_final_verified(project_dir: Path, params: dict) -> tuple[bool, str]:
    """验证 final.mp4 由 assemble_final.sh 生成，而非手写 ffmpeg 拼接。

    assemble_final.sh 完成后会写入 .assemble_marker.json 标记文件。
    如果 final.mp4 存在但无标记文件 → SubAgent 绕过脚本自行拼接 → FAIL。

    同时验证标记文件中的时长与实际文件一致，防止伪造标记。
    """
    marker_file = project_dir / ".assemble_marker.json"
    final_file = project_dir / "final.mp4"
    final_nobgm_file = project_dir / "final_no_bgm.mp4"

    # final.mp4 不存在时不阻塞（可能还没到 delivery 阶段）
    if not final_file.exists():
        return True, "final.mp4 尚未生成，跳过脚本调用验证"

    # 标记文件缺失 → 绕过了 assemble_final.sh
    if not marker_file.exists():
        return False, (
            "final.mp4 存在但无 .assemble_marker.json 标记文件 — "
            "未使用 assemble_final.sh 生成 final.mp4（HARD）。"
            "修复: bash .claude/commands/clipforge/scripts/assemble_final.sh <项目目录>"
        )

    # 验证标记文件内容完整性
    try:
        marker = json.loads(marker_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        return False, f".assemble_marker.json 解析失败: {e}"

    required_keys = {"script", "source_duration", "final_duration", "cover_frames"}
    missing = required_keys - set(marker.keys())
    if missing:
        return False, f".assemble_marker.json 缺少字段: {missing}"

    # 验证标记中的脚本名
    if marker.get("script") != "assemble_final.sh":
        return False, f"标记文件 script 字段异常: {marker.get('script')}"

    # 验证封面帧数
    cover_frames = marker.get("cover_frames", 0)
    if cover_frames != 1:
        return False, f"封面帧数异常: {cover_frames}（应为 1）"

    # 交叉验证：标记中的时长 vs 实际 ffprobe 时长
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

    actual_final_dur = _get_duration(final_file)
    if actual_final_dur is not None:
        marker_dur = marker.get("final_duration", 0)
        # 允许 0.5s 容差（mastering loudnorm 可能微调时长）
        if abs(actual_final_dur - marker_dur) > 0.5:
            return False, (
                f"标记文件时长 ({marker_dur:.2f}s) 与实际 final.mp4 时长 "
                f"({actual_final_dur:.2f}s) 不一致 — 标记可能伪造或文件被覆盖"
            )

    # 验证 final_no_bgm.mp4 也存在（assemble_final.sh 同时产出两个文件）
    if not final_nobgm_file.exists():
        return False, "final_no_bgm.mp4 缺失 — assemble_final.sh 应同时产出双版本"

    # 验证 no_bgm 音频来源是 narration.mp3（非 output.mp4 音频轨）
    no_bgm_source = marker.get("no_bgm_audio_source", "")
    if no_bgm_source != "narration.mp3":
        return False, (
            f"no_bgm 音频来源异常: {no_bgm_source}（应为 narration.mp3）"
        )

    issues = []
    if not marker.get("timestamp"):
        issues.append("缺少 timestamp")
    if issues:
        return False, f".assemble_marker.json 不完整: {issues}"

    return True, "final.mp4 由 assemble_final.sh 生成（标记验证通过，no_bgm 音频来源: narration.mp3）"


GATE_CHECKERS[GateType.assemble_final_verified] = check_assemble_final_verified


def check_grad_text_shorthand(project_dir: Path, params: dict) -> tuple[bool, str]:
    """检查 .grad-text 元素是否使用了 background: 简写（导致 background-clip:text 失效）。
    background: 简写（含 linear-gradient）会重置 background-clip 回 border-box → background-clip:text 失效 → 渐变填满元素 + color:transparent 隐藏文字 → 只见色块不见字。须用 background-image: 显式声明。

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


def check_gradient_text_no_dark_shadow(project_dir: Path, params: dict) -> tuple[bool, str]:
    """R-S6-023: background-clip:text 渐变文字禁止搭配黑色 text-shadow。

    黑色 text-shadow (rgba(0,0,0,...)) 叠加在透明填充的渐变文字上
    产生黑色光晕压低文字亮度。纯色文字受同样阴影反而增加层次感，不受影响。
    """
    fp = project_dir / params.get("file", "index.html")
    if not fp.exists():
        return False, "index.html 缺失"
    content = fp.read_text(encoding="utf-8", errors="ignore")

    # Step A: 提取渐变文字类名集合
    gradient_classes: set[str] = set()

    # A1: 从 <style> 中的 CSS 规则块提取
    # 匹配 selector { ... background-clip: text ... } 或 -webkit-text-fill-color: transparent
    css_rule_pattern = re.compile(
        r'([^{}]+)\{([^}]*)\}',
        re.DOTALL,
    )
    for m in css_rule_pattern.finditer(content):
        selector = m.group(1).strip()
        body = m.group(2)
        has_gradient_text = (
            re.search(r'background-clip\s*:\s*text', body) or
            re.search(r'-webkit-text-fill-color\s*:\s*transparent', body)
        )
        if has_gradient_text:
            for cls in re.findall(r'\.([a-zA-Z_][\w-]*)', selector):
                gradient_classes.add(cls)

    # A2: 从 inline style 提取
    inline_pattern = re.compile(
        r'<(\w+)[^>]*class=["\']([^"\']*)["\'][^>]*style=["\']([^"\']*)["\'][^>]*>',
        re.DOTALL,
    )
    inline_pattern_rev = re.compile(
        r'<(\w+)[^>]*style=["\']([^"\']*)["\'][^>]*class=["\']([^"\']*)["\'][^>]*>',
        re.DOTALL,
    )
    for pattern in (inline_pattern, inline_pattern_rev):
        for m in pattern.finditer(content):
            if pattern == inline_pattern:
                style_val = m.group(3)
                class_val = m.group(2)
            else:
                style_val = m.group(2)
                class_val = m.group(3)
            if re.search(r'background-clip\s*:\s*text', style_val):
                for cls in re.findall(r'([a-zA-Z_][\w-]*)', class_val):
                    gradient_classes.add(cls)

    if not gradient_classes:
        return True, "未发现渐变文字（无 background-clip:text），跳过"

    # Step B: 检测黑色 text-shadow 冲突
    dark_shadow_pattern = re.compile(
        r'text-shadow\s*:[^;]*rgba\(\s*0\s*,\s*0\s*,\s*0',
    )
    # 收集含黑色 text-shadow 的类名（用于多 class 组合检测）
    shadow_classes: set[str] = set()
    violations: list[str] = []

    # B1: CSS 规则块中的黑色 text-shadow → 提取类名
    for m in css_rule_pattern.finditer(content):
        selector = m.group(1).strip()
        body = m.group(2)
        if dark_shadow_pattern.search(body):
            rule_shadow_classes = set(re.findall(r'\.([a-zA-Z_][\w-]*)', selector))
            shadow_classes.update(rule_shadow_classes)
            # 同一规则内交叉检测
            overlap = rule_shadow_classes & gradient_classes
            if overlap:
                violations.append(
                    f"CSS规则 '{selector.strip()[:60]}' 黑色 text-shadow 命中渐变类: {', '.join(sorted(overlap))}"
                )

    # B1.5: 多 class 组合检测 — DOM 元素同时携带渐变类 + 阴影类
    # 先收集"覆盖规则"：组合选择器中含渐变类+阴影类但不带黑色 text-shadow
    override_selectors: list[set[str]] = []
    for m in css_rule_pattern.finditer(content):
        selector = m.group(1).strip()
        body = m.group(2)
        sel_classes = set(re.findall(r'\.([a-zA-Z_][\w-]*)', selector))
        if not sel_classes:
            continue
        has_grad = bool(sel_classes & gradient_classes)
        has_shadow_cls = bool(sel_classes & shadow_classes)
        if has_grad and has_shadow_cls and not dark_shadow_pattern.search(body):
            # 组合选择器覆盖了黑色 shadow
            override_selectors.append(sel_classes)

    if shadow_classes and gradient_classes:
        element_class_pattern = re.compile(
            r'<(\w+)[^>]*class=["\']([^"\']*)["\'][^>]*>',
        )
        for em in element_class_pattern.finditer(content):
            el_classes = set(em.group(2).split())
            has_grad = bool(el_classes & gradient_classes)
            has_shadow = bool(el_classes & shadow_classes)
            if has_grad and has_shadow:
                # 检查是否有覆盖规则匹配此元素（覆盖规则的所有 class 都在元素上）
                covered = any(
                    ov <= el_classes for ov in override_selectors
                )
                if not covered:
                    grad_on_el = el_classes & gradient_classes
                    shadow_on_el = el_classes & shadow_classes
                    violations.append(
                        f"DOM 元素 class='{em.group(2)[:50]}' 同时携带渐变类 "
                        f"({','.join(sorted(grad_on_el))}) + 阴影类 ({','.join(sorted(shadow_on_el))})"
                    )

    # B2: inline style 中同时含渐变 + 黑色 text-shadow
    for pattern in (inline_pattern, inline_pattern_rev):
        for m in pattern.finditer(content):
            if pattern == inline_pattern:
                style_val = m.group(3)
                class_val = m.group(2)
            else:
                style_val = m.group(2)
                class_val = m.group(3)
            has_gradient = bool(re.search(r'background-clip\s*:\s*text', style_val))
            has_dark_shadow = bool(dark_shadow_pattern.search(style_val))
            if has_gradient and has_dark_shadow:
                violations.append(
                    f"inline style 同时含渐变+黑色shadow (class='{class_val[:30]}')"
                )

    if violations:
        return False, (
            f"R-S6-023: {len(violations)} 处渐变文字搭配黑色 text-shadow "
            f"（应使用同色系发光）。违规: {'; '.join(violations[:5])}"
        )

    return True, f"渐变文字 ({len(gradient_classes)} 个类) 无黑色 text-shadow 冲突"


GATE_CHECKERS[GateType.gradient_text_no_dark_shadow] = check_gradient_text_no_dark_shadow


# ═══════════════════════════════════════════════════════════════════════
# DOM 结构 + GSAP 模式 + CSS 全局选择器检测器 — R-S6-025/026/027
# ═══════════════════════════════════════════════════════════════════════

def check_no_scene_wrap(project_dir: Path, params: dict) -> tuple[bool, str]:
    """检查 .clip 和三层之间没有中间包裹层。

    事故：06/08 周榜视频 .clip > .scene-wrap > .layer-bg/fx/content，
    HyperFrames 期望 .clip > .layer-bg/fx/content 直系结构。
    """
    fp = project_dir / params.get("file", "index.html")
    if not fp.exists():
        return False, "index.html 缺失"
    content = fp.read_text(encoding="utf-8", errors="ignore")

    issues: list[str] = []

    # 找 .clip 内部到 .layer-bg 之间的标签
    clip_blocks = re.findall(
        r'class="[^"]*clip[^"]*"[^>]*>(.*?)class="[^"]*layer-bg[^"]*"',
        content, re.DOTALL
    )
    for block in clip_blocks:
        inner_tags = re.findall(r'<div[^>]*>', block)
        for tag in inner_tags:
            class_match = re.search(r'class="([^"]*)"', tag)
            if class_match:
                classes = class_match.group(1)
                issues.append(f".clip 和 .layer-bg 之间存在中间层: class=\"{classes}\"")

    if issues:
        return False, (f"R-S6-025: DOM 三层直系铁律违反 — {issues[0]}。"
                       f".clip 必须直接包含 .layer-bg/.layer-fx/.layer-content")

    return True, "DOM 层级正确（.clip 直系三层）"


def check_gsap_pattern(project_dir: Path, params: dict) -> tuple[bool, str]:
    """检查 GSAP 初始化模式符合 HyperFrames 要求。

    事故：06/08 周榜视频使用 DOMContentLoaded 包裹 + __timelines 循环 seek，
    导致 HyperFrames seek 时内容不可见。
    """
    fp = project_dir / params.get("file", "index.html")
    if not fp.exists():
        return False, "index.html 缺失"
    content = fp.read_text(encoding="utf-8", errors="ignore")

    issues: list[str] = []

    # 1. 禁止 DOMContentLoaded 包裹 GSAP
    if re.search(r'DOMContentLoaded.*gsap\.timeline', content, re.DOTALL):
        issues.append("GSAP 代码被 DOMContentLoaded 包裹")

    # 2. 禁止 fromTo
    if re.search(r'\.fromTo\s*\(', content):
        issues.append("使用 tl.fromTo()（应使用 tl.from() 或 tl.to()）")

    # 3. 禁止内容元素 from/to 中包含 opacity:0（非 opacity:0.3 等 fx 用法）
    opacity_in_from = re.findall(
        r'\.(?:from|to)\s*\([^)]*opacity\s*:\s*0(?:\.0+)?(?!\.?\d)[^)]*\)',
        content
    )
    if opacity_in_from:
        issues.append(f"tl.from()/tl.to() 中包含 opacity:0（共 {len(opacity_in_from)} 处）")

    # 4. 禁止 __timelines 循环 seek
    if re.search(r'for\s*\(\s*var\s+\w+\s+in\s+window\.__timelines', content):
        issues.append("__timelines 循环 seek（应使用 tl.time(t, false)）")

    if issues:
        return False, f"R-S6-026: GSAP 模式违反 — {'; '.join(issues)}"

    return True, "GSAP 初始化模式正确"


def check_no_global_text_shadow(project_dir: Path, params: dict) -> tuple[bool, str]:
    """检查 CSS 中没有全局通配选择器设置 text-shadow。

    事故：06/08 周榜视频 .safe-pad *{text-shadow:0 2px 12px rgba(0,0,0,0.5)}
    导致渐变文字整体偏暗。
    """
    fp = project_dir / params.get("file", "index.html")
    if not fp.exists():
        return False, "index.html 缺失"
    content = fp.read_text(encoding="utf-8", errors="ignore")

    issues: list[str] = []

    # 检测 .xxx * { ... text-shadow ... } 或 * { ... text-shadow ... }
    global_shadow = re.findall(
        r'(?:\*|\.?\w+\s*\*)\s*\{[^}]*(text-shadow\s*:)[^}]*\}',
        content
    )
    if global_shadow:
        issues.append(f"全局通配选择器包含 text-shadow（{len(global_shadow)} 处）")

    # 检测全局通配设置 opacity/filter
    global_opacity = re.findall(
        r'(?:\*|\.?\w+\s*\*)\s*\{[^}]*(opacity\s*:|filter\s*:)[^}]*\}',
        content
    )
    if global_opacity:
        issues.append(f"全局通配选择器包含 opacity/filter（{len(global_opacity)} 处）")

    if issues:
        return False, (f"R-S6-027: {'; '.join(issues)}。"
                       f"text-shadow/opacity/filter 应设在具体元素上，禁止通配")

    return True, "未检测到全局通配视觉属性"


GATE_CHECKERS[GateType.no_scene_wrap] = check_no_scene_wrap
GATE_CHECKERS[GateType.gsap_pattern] = check_gsap_pattern
GATE_CHECKERS[GateType.no_global_text_shadow] = check_no_global_text_shadow


def check_pre_render_deps(project_dir: Path, params: dict) -> tuple[bool, str]:
    """渲染前依赖检查 — 调用 scripts/pre_render_check.py 验证所有引用文件存在。"""
    script = Path(__file__).parent.parent / "scripts" / "pre_render_check.py"
    if not script.exists():
        return False, f"pre_render_check.py 不存在: {script}"
    import subprocess
    result = subprocess.run(
        [sys.executable, str(script), str(project_dir)],
        capture_output=True, timeout=30,
    )
    stdout = result.stdout.decode('utf-8', errors='replace') if result.stdout else ''
    stderr = result.stderr.decode('utf-8', errors='replace') if result.stderr else ''
    output = (stdout + stderr).strip()
    if result.returncode == 0:
        return True, output
    return False, output


GATE_CHECKERS[GateType.pre_render_deps] = check_pre_render_deps


def check_html_structure_valid(project_dir: Path, params: dict) -> tuple[bool, str]:
    """HTML 结构完整性检查 — clip/fx 数量匹配、layer-content height。

    注意：安全区 padding 检查已移至 check_safe_area_bounds 门禁（类名无关）。
    """
    html_file = project_dir / params.get("file", "index.html")
    if not html_file.exists():
        return False, f"{html_file.name} 不存在"
    content = html_file.read_text(encoding="utf-8", errors="ignore")
    failures = []

    # clip 数量与 layer-fx 数量匹配（只数 HTML class 属性，排除 CSS 定义）
    clip_count = content.count('class="clip"')
    fx_count = content.count('class="layer-fx"')
    if clip_count != fx_count:
        failures.append(f"clip({clip_count}) 与 layer-fx({fx_count}) 数量不匹配")

    # 单元素 fx 层检测（<div class="layer-fx"> 只含一个子 div）
    import re
    single_fx = re.findall(
        r'class="layer-fx">\s*<div[^>]*></div>\s*</div>', content
    )
    if single_fx:
        failures.append(f"{len(single_fx)} 个 layer-fx 仅含单元素（需≥3个特效元素）")

    # .layer-content 有 padding 永远是违规（它不是 padding 载体）
    lc_has_pad = bool(re.search(
        r'\.layer-content[^}]*padding', content
    ))
    if lc_has_pad:
        failures.append(".layer-content 含 padding（padding 应在 .phase 或 .scene-wrap 上，不是 layer-content）")

    # layer-content 必须有 height
    lc_css = re.search(r'\.layer-content\s*\{([^}]*)\}', content)
    if lc_css and 'height' not in lc_css.group(1):
        failures.append(".layer-content 缺少 height 声明（Phase 内容会塌陷到顶部）")

    if failures:
        return False, "; ".join(failures)
    return True, f"HTML 结构检查通过（{clip_count} scenes）"


# ---------------------------------------------------------------------------
# safe_area_bounds: 类名无关的逐场景 padding 累加下限检测
# ---------------------------------------------------------------------------

def _parse_box_value(raw: str):
    """解析 CSS padding/margin 值为 4-tuple (top, right, bottom, left)。
    支持 1-4 值简写和独立属性。
    """
    raw = raw.strip()
    if not raw or 'calc(' in raw or 'var(' in raw:
        return None
    values = re.findall(r'([\d.]+)\s*(?:px)?', raw)
    if not values:
        return None
    nums = [float(v) for v in values]
    if len(nums) == 1:
        return (nums[0], nums[0], nums[0], nums[0])
    elif len(nums) == 2:
        return (nums[0], nums[1], nums[0], nums[1])
    elif len(nums) == 3:
        return (nums[0], nums[1], nums[2], nums[1])
    else:
        return (nums[0], nums[1], nums[2], nums[3])


def _is_decorative(t, r, b, l):
    """全维度 <50px → 装饰性（tag/badge），不参与安全区累加。"""
    return all(v < 50 for v in (t, r, b, l))


def _extract_padding_rules(content: str):
    """从 HTML 中提取所有 padding 声明。

    返回 list of (scene_scope, base_selector, (t,r,b,l), raw_value)
    - scene_scope: "scene-2" 或 "all"
    - base_selector: ".content-inner", ".phase" 等
    """
    rules = []

    # --- 从 <style> 块提取 ---
    for style_block in re.findall(r'<style[^>]*>(.*?)</style>', content, re.DOTALL):
        for rule_match in re.finditer(r'([^\{]+)\{([^}]+)\}', style_block):
            selector_raw = rule_match.group(1).strip()
            body = rule_match.group(2)

            # 跳过重置
            if selector_raw.startswith('*'):
                continue

            # 跳过背景/特效层
            if any(x in selector_raw for x in ('layer-bg', 'layer-fx', '.bg-', '.fx-')):
                continue

            # 提取 padding
            pad_match = re.search(r'(?:^|;)\s*padding\s*:\s*([^;]+)', body)
            if not pad_match:
                # 检查独立属性
                pt = re.search(r'padding-top\s*:\s*([^;]+)', body)
                pr = re.search(r'padding-right\s*:\s*([^;]+)', body)
                pb = re.search(r'padding-bottom\s*:\s*([^;]+)', body)
                pl = re.search(r'padding-left\s*:\s*([^;]+)', body)
                if pt or pr or pb or pl:
                    # 分别解析各方向
                    def _sv(m):
                        return float(re.findall(r'([\d.]+)', m.group(1))[0]) if m else 0.0
                    pad_tuple = (_sv(pt), _sv(pr), _sv(pb), _sv(pl))
                    if all(v == 0 for v in pad_tuple):
                        continue
                else:
                    continue
            else:
                pad_tuple = _parse_box_value(pad_match.group(1))
                if pad_tuple is None or all(v == 0 for v in pad_tuple):
                    continue

            # 解析选择器：提取 scene scope 和 base selector
            # 场景特定: #scene-2 .content-inner → scope="scene-2", base=".content-inner"
            # 通用: .phase → scope="all", base=".phase"
            scene_match = re.match(r'#(scene-\d+)\s+(.*)', selector_raw)
            if scene_match:
                scene_scope = scene_match.group(1)
                base_sel = scene_match.group(2).strip()
            else:
                scene_scope = "all"
                base_sel = selector_raw

            raw_val = pad_match.group(1).strip() if pad_match else "individual"
            rules.append((scene_scope, base_sel, pad_tuple, raw_val))

    # --- 从 inline style 提取 ---
    # 找到每个 inline style 所属的 scene
    for inline_match in re.finditer(
        r'<div[^>]*(?:id="(scene-\d+)"|class="[^"]*clip[^"]*")[^>]*>.*?'
        r'(?:<div[^>]*?)?style="[^"]*padding\s*:\s*([^";]+)[^"]*"',
        content, re.DOTALL
    ):
        pass  # inline 解析太复杂，下面用更简单的方式

    # 更简单的 inline 解析：逐个找 style 含 padding 的标签，向上找 scene
    lines = content.split('\n')
    current_scene = "all"
    for i, line in enumerate(lines):
        # 追踪当前 scene
        scene_open = re.search(r'id="(scene-\d+)"', line)
        if scene_open:
            current_scene = scene_open.group(1)
        # 检测 scene 关闭（新 clip 开始或文件结束）
        if re.search(r'class="clip"', line) and not scene_open:
            current_scene = "all"

        # 提取 inline padding
        inline_pad = re.search(r'style="[^"]*padding\s*:\s*([^";]+)', line)
        if inline_pad:
            pad_tuple = _parse_box_value(inline_pad.group(1))
            if pad_tuple and not all(v == 0 for v in pad_tuple):
                rules.append((current_scene, "(inline)", pad_tuple, inline_pad.group(1).strip()))

    return rules


def check_safe_area_bounds(project_dir: Path, params: dict) -> tuple[bool, str]:
    """安全区下限检测 — 逐场景 padding 累加 + 下限校验。

    核心逻辑：每个场景的内容区域距画布边缘的 padding 累加和
    不得低于标准值（竖屏 180/90/220/90，横屏 60/120/60/120）。
    """
    html_file = project_dir / params.get("file", "index.html")
    if not html_file.exists():
        return False, f"{html_file.name} 不存在"
    content = html_file.read_text(encoding="utf-8", errors="ignore")
    failures = []

    # --- Step A: 方向检测 ---
    w_match = re.search(r'data-width=["\']?(\d+)', content)
    h_match = re.search(r'data-height=["\']?(\d+)', content)
    if w_match and h_match:
        is_portrait = int(h_match.group(1)) > int(w_match.group(1))
    else:
        is_portrait = True

    if is_portrait:
        MIN_PAD = {"top": 180, "right": 90, "bottom": 220, "left": 90}
        STD_LABEL = "180px 90px 220px 90px"
        ORIENT = "竖屏"
    else:
        MIN_PAD = {"top": 60, "right": 120, "bottom": 60, "left": 120}
        STD_LABEL = "60px 120px 60px 120px"
        ORIENT = "横屏"

    # --- Step B: 提取所有场景 ID ---
    scene_ids = re.findall(r'id="(scene-\d+)"', content)
    if not scene_ids:
        # 可能是旧格式 clip，用 data-clip-id
        scene_ids = re.findall(r'data-clip-id="(scene-\d+)"', content)
    if not scene_ids:
        # 无场景划分，整页作为一个场景检查
        scene_ids = ["__whole__"]

    # --- Step C: 提取所有 padding 规则 ---
    all_rules = _extract_padding_rules(content)

    # --- Step D: 逐场景累加校验 ---
    for scene_id in scene_ids:
        # 按 base_selector 去重：场景特定 > 通用
        scene_rules = {}  # base_selector → (pad_tuple, raw_val)
        for scope, base_sel, pad_tuple, raw_val in all_rules:
            if scope != "all" and scope != scene_id:
                continue
            if base_sel in scene_rules and scope == "all":
                continue  # 有场景特定规则，丢弃通用（CSS 优先级）
            scene_rules[base_sel] = (pad_tuple, raw_val)

        # 过滤装饰性，累加
        non_deco = {}
        for sel, (pad, raw) in scene_rules.items():
            if not _is_decorative(*pad):
                non_deco[sel] = (pad, raw)

        sum_t = sum(p[0] for p, _ in non_deco.values())
        sum_r = sum(p[1] for p, _ in non_deco.values())
        sum_b = sum(p[2] for p, _ in non_deco.values())
        sum_l = sum(p[3] for p, _ in non_deco.values())

        def _dim_label(d, val, minimum):
            return f"{d}={val}px < {minimum}px" if val < minimum else None

        shortfalls = []
        for dim, val, mn in [("top", sum_t, MIN_PAD["top"]),
                              ("right", sum_r, MIN_PAD["right"]),
                              ("bottom", sum_b, MIN_PAD["bottom"]),
                              ("left", sum_l, MIN_PAD["left"])]:
            if val < mn:
                shortfalls.append(f"{dim}={val}<{mn}")

        scene_label = f"#{scene_id}" if scene_id != "__whole__" else "全局"

        if shortfalls:
            carriers = "; ".join(f"{s}={r}" for s, (_, r) in non_deco.items()) or "无"
            failures.append(
                f"{scene_label} padding 不足 [{', '.join(shortfalls)}] "
                f"(标准 {STD_LABEL}, carriers: [{carriers}])"
            )

    # --- Step E: 全画幅容器无 padding 检测 ---
    # 只捕获完全没有 padding 的容器（主检查已覆盖"有 padding 但不足"的情况）
    for style_block in re.findall(r'<style[^>]*>(.*?)</style>', content, re.DOTALL):
        for rule_match in re.finditer(r'([^\{]+)\{([^}]+)\}', style_block):
            selector = rule_match.group(1).strip()
            body = rule_match.group(2)
            if selector.startswith('*'):
                continue
            has_inset_0 = bool(re.search(r'inset\s*:\s*0', body))
            has_full = (bool(re.search(r'top\s*:\s*0', body)) and
                        bool(re.search(r'left\s*:\s*0', body)) and
                        bool(re.search(r'width\s*:\s*100%', body)))
            if not (has_inset_0 or has_full):
                continue
            is_content = bool(re.search(r'flex|justify-content|align-items', body))
            if not is_content:
                continue
            pad_m = re.search(r'padding\s*:\s*([^;]+)', body)
            if pad_m:
                pad_t = _parse_box_value(pad_m.group(1))
                # 有 padding 且任一主要维度(top/bottom) ≥ 50px → 主检查会处理，不重复报告
                if pad_t and (pad_t[0] >= 50 or pad_t[2] >= 50):
                    continue
            failures.append(
                f"全画幅内容容器无 padding ({selector}): "
                f"inset:0 + flex 但无安全区 padding（内容贴边缘）"
            )

    # --- Step F: 危险 margin 检测（内容容器 margin >50px） ---
    for style_block in re.findall(r'<style[^>]*>(.*?)</style>', content, re.DOTALL):
        for rule_match in re.finditer(r'([^\{]+)\{([^}]+)\}', style_block):
            selector = rule_match.group(1).strip()
            body = rule_match.group(2)
            if selector.startswith('*') or selector.startswith('#'):
                continue
            if any(x in selector for x in ('layer-bg', 'layer-fx')):
                continue
            margin_m = re.search(r'margin\s*:\s*([^;]+)', body)
            if not margin_m:
                continue
            m_tuple = _parse_box_value(margin_m.group(1))
            if m_tuple is None:
                continue
            # 排除居中模式 margin: 0 auto
            raw_m = margin_m.group(1).strip().replace(' ', '')
            if '0auto' in raw_m:
                continue
            if any(v > 50 for v in m_tuple):
                failures.append(
                    f"危险 margin ({selector}): {margin_m.group(1).strip()} "
                    f"— 单维度 >50px 可能将内容推出安全区"
                )

    # --- Step G: 绝对定位越界检测 ---
    abs_pattern = re.compile(
        r'([^\{\}]+)\{[^}]*(?:position\s*:\s*absolute)'
        r'[^}]*(?:top|bottom|left|right)\s*:\s*([\d.]+)\s*px'
        r'[^}]*\}',
        re.DOTALL
    )
    for abs_match in abs_pattern.finditer(content):
        selector = abs_match.group(1).strip()
        if selector.startswith('*'):
            continue
        # 伪元素（::before/::after）相对宿主元素定位，非画布绝对坐标，且恒为装饰 — 跳过
        if '::' in selector:
            continue
        if any(x in selector for x in ('layer-bg', 'layer-fx', 'bg-grad', 'grid',
                                         'particle', 'dot', 'line', 'shape',
                                         'prism', 'ring', 'band')):
            continue
        body = abs_match.group(0)
        for pos_m in re.finditer(r'(top|bottom|left|right)\s*:\s*([\d.]+)\s*px', body):
            prop = pos_m.group(1)
            val = float(pos_m.group(2))
            if prop == "top" and val > 0 and val < MIN_PAD["top"]:
                failures.append(
                    f"绝对定位越界 ({selector}): {prop}={val}px < "
                    f"安全区 top 下限 {MIN_PAD['top']}px"
                )
            if prop == "bottom" and val > 0 and val < MIN_PAD["bottom"]:
                failures.append(
                    f"绝对定位越界 ({selector}): {prop}={val}px < "
                    f"安全区 bottom 下限 {MIN_PAD['bottom']}px"
                )
            if prop == "left" and val > 0 and val < MIN_PAD["left"]:
                failures.append(
                    f"绝对定位越界 ({selector}): {prop}={val}px < "
                    f"安全区 left 下限 {MIN_PAD['left']}px"
                )
            if prop == "right" and val > 0 and val < MIN_PAD["right"]:
                failures.append(
                    f"绝对定位越界 ({selector}): {prop}={val}px < "
                    f"安全区 right 下限 {MIN_PAD['right']}px"
                )

    if failures:
        return False, "; ".join(failures)
    return True, f"安全区检查通过 ({ORIENT}, 标准 {STD_LABEL})"


def check_visual_phases_completeness(project_dir: Path, params: dict) -> tuple[bool, str]:
    """视觉分镜完整性 — 长场景必须有足够的 visual_phases。"""
    dur_file = project_dir / params.get("segments_file", "segment_durations.json")
    narr_file = project_dir / params.get("narration_file", "narration_segments.json")
    pt_file = project_dir / "phase_timings.json"
    if not dur_file.exists() or not narr_file.exists():
        return True, "分镜文件缺失，跳过"
    if not pt_file.exists():
        return True, "phase_timings.json 缺失，HTML 未使用 phase 分镜模式，跳过"
    try:
        dur_segs = json.loads(dur_file.read_text(encoding="utf-8"))["segments"]
        narr_raw = json.loads(narr_file.read_text(encoding="utf-8"))
        narr_segs = narr_raw["segments"] if isinstance(narr_raw, dict) else narr_raw
    except Exception:
        return True, "分镜文件解析失败，跳过"

    failures = []
    for seg, narr in zip(dur_segs, narr_segs):
        d = seg.get("actual_duration") or seg.get("duration") or 0
        if not d:
            continue
        vp = narr.get("visual_phases", [])
        vp_count = len(vp) if isinstance(vp, list) else 0
        scene_name = narr.get("scene", "?")
        if d > 15 and vp_count < 2:
            failures.append(f"{scene_name} ({d:.1f}s) 需要 >= 2 visual_phases，当前 {vp_count}")
        elif d > 25 and vp_count < 3:
            failures.append(f"{scene_name} ({d:.1f}s) 建议 >= 3 visual_phases，当前 {vp_count}")

    if failures:
        return False, "; ".join(failures)
    return True, "视觉分镜完整性检查通过"


def check_output_media_valid(project_dir: Path, params: dict) -> tuple[bool, str]:
    """输出视频/音频检查 — 编码格式、分辨率、时长合理性。"""
    import subprocess
    failures = []
    files = params.get("files", ["output.mp4", "output_no_bgm.mp4"])

    for fname in files:
        fpath = project_dir / fname
        if not fpath.exists() or fpath.stat().st_size == 0:
            failures.append(f"{fname} 不存在或为空")
            continue

        streams = subprocess.run(
            ["ffprobe", "-v", "quiet", "-show_streams", str(fpath)],
            capture_output=True, text=True, timeout=15,
        ).stdout

        if "codec_name=h264" not in streams:
            failures.append(f"{fname} 无视频轨（非 h264）")
        if "codec_name=aac" not in streams:
            failures.append(f"{fname} 无音频轨（非 aac）")

        # 分辨率
        w = subprocess.run(
            ["ffprobe", "-v", "quiet", "-show_entries", "stream=width",
             "-of", "csv=p=0", "-select_streams", "v:0", str(fpath)],
            capture_output=True, text=True, timeout=10,
        ).stdout.strip()
        h = subprocess.run(
            ["ffprobe", "-v", "quiet", "-show_entries", "stream=height",
             "-of", "csv=p=0", "-select_streams", "v:0", str(fpath)],
            capture_output=True, text=True, timeout=10,
        ).stdout.strip()
        if w and h:
            valid = (w == "1080" and h == "1920") or (w == "1920" and h == "1080")
            if not valid:
                failures.append(f"{fname} 分辨率异常 {w}x{h}")

        # 时长 > 5s（取整数部分比较，与旧 bash ${DUR%.*} 行为一致）
        dur = subprocess.run(
            ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
             "-of", "csv=p=0", str(fpath)],
            capture_output=True, text=True, timeout=10,
        ).stdout.strip()
        if dur:
            try:
                if int(float(dur)) <= 5:
                    failures.append(f"{fname} 时长过短 ({dur}s)")
            except ValueError:
                pass

    # final.mp4 / final_no_bgm.mp4 采样率必须为 48000
    for fname in ["final.mp4", "final_no_bgm.mp4"]:
        fpath = project_dir / fname
        if fpath.exists():
            sr = subprocess.run(
                ["ffprobe", "-v", "quiet", "-select_streams", "a",
                 "-show_entries", "stream=sample_rate", "-of", "csv=p=0", str(fpath)],
                capture_output=True, text=True, timeout=10,
            ).stdout.strip()
            if sr != "48000":
                failures.append(f"{fname} 采样率={sr or '未知'}，应为 48000")

    if failures:
        return False, "; ".join(failures)
    return True, f"输出视频检查通过（{len(files)} 个文件）"


def check_bgm_isolation_valid(project_dir: Path, params: dict) -> tuple[bool, str]:
    """BGM 隔离性校验 — output.mp4 vs output_no_bgm.mp4 音量差 >= 2dB。"""
    import subprocess
    with_file = project_dir / params.get("with_bgm", "output.mp4")
    without_file = project_dir / params.get("without_bgm", "output_no_bgm.mp4")

    if not with_file.exists() or not without_file.exists():
        return False, "BGM 隔离校验：输出文件缺失"

    def _mean_vol(fpath):
        r = subprocess.run(
            ["ffmpeg", "-i", str(fpath), "-af", "volumedetect", "-f", "null", "-"],
            capture_output=True, text=True, timeout=30,
        )
        m = re.search(r'mean_volume:\s*([-\d.]+)', r.stderr)
        return float(m.group(1)) if m else None

    vol_with = _mean_vol(with_file)
    vol_without = _mean_vol(without_file)

    if vol_with is None or vol_without is None:
        return False, "BGM volumedetect 数据缺失"

    diff = vol_with - vol_without
    # diff < 0: no_bgm 比 with_bgm 更响 → BGM 音量极低，混音后总音量微降 → 正确行为
    # diff >= 0 但 < 2: BGM 可能在 no_bgm 中残留 → 需警告但降级为 soft
    if diff >= 0 and diff < 2.0:
        return False, (
            f"no_bgm 文件 BGM 未消除（差值仅 {diff:.1f} dB，需 >= 2dB）。"
            f"with_bgm={vol_with:.1f}dB, no_bgm={vol_without:.1f}dB"
        )

    return True, f"BGM 隔离校验通过（差值 {diff:.1f} dB）"


def check_narration_audio_embedded(project_dir: Path, params: dict) -> tuple[bool, str]:
    """旁白音频嵌入检查 — index.html 必须包含 narration.mp3 的 <audio> 元素。

    HyperFrames 通过 HTML 内嵌 <audio> 元素混音。缺少旁白 <audio> 会导致渲染出的视频没有旁白声音。
    """
    html_file = project_dir / params.get("file", "index.html")
    if not html_file.exists():
        return False, f"HTML 文件不存在: {html_file}"

    content = html_file.read_text(encoding="utf-8")

    # 检查是否有 narration.mp3 的 <audio> 元素
    narration_audio = re.search(
        r'<audio[^>]*src=["\']narration\.mp3["\']', content
    )
    if not narration_audio:
        # 也检查 data-src 属性
        narration_audio = re.search(
            r'<audio[^>]*data-src=["\']narration\.mp3["\']', content
        )

    if not narration_audio:
        return False, (
            "index.html 缺少旁白 <audio> 元素。"
            "必须添加: <audio data-track-index=\"1\" data-volume=\"1\" "
            "data-start=\"0\" src=\"narration.mp3\" preload=\"auto\"></audio>"
        )

    return True, "旁白音频嵌入检查通过"


def check_delayed_animation_init(project_dir: Path, params: dict) -> tuple[bool, str]:
    """延迟入场动画初始化检查 — 时间偏移 > 2s 的 .from()/.to() 必须有对应 .set()，
    且 .set() 的偏移量必须足以将元素完全推出画布。

    HyperFrames 通过 GSAP timeline seek 驱动帧渲染。当 .from() 的时间偏移 > 0 时，
    seek 到动画触发前的帧时，元素保持 DOM 原位（可见）。必须在 timeline 开始处用
    .set() 初始化离屏状态，且偏移量必须 ≥ 画布尺寸（完全隐藏）。
    """
    html_file = project_dir / params.get("file", "index.html")
    if not html_file.exists():
        return False, f"HTML 文件不存在: {html_file}"

    content = html_file.read_text(encoding="utf-8")

    # 检测方向（竖屏/横屏）
    root_w = re.search(r'data-width=["\'](\d+)["\']', content)
    root_h = re.search(r'data-height=["\'](\d+)["\']', content)
    if root_w and root_h:
        w, h = int(root_w.group(1)), int(root_h.group(1))
        is_portrait = h > w
    else:
        is_portrait = True  # 默认竖屏

    # 偏移量硬标准
    MIN_X = 1080 if is_portrait else 1920
    MIN_Y = 1920 if is_portrait else 1080
    orient_label = "竖屏" if is_portrait else "横屏"

    failures = []
    delay_threshold = 2.0  # 只检查明显延迟入场的元素

    for script_match in re.finditer(r'<script[^>]*>(.*?)</script>', content, re.DOTALL):
        script = script_match.group(1)

        tl_assignments = list(re.finditer(
            r'(\w+)\s*=\s*gsap\.timeline\([^)]*\)\s*',
            script
        ))

        for i, assign in enumerate(tl_assignments):
            tl_name = assign.group(1)
            start_pos = assign.end()
            end_pos = tl_assignments[i + 1].start() if i + 1 < len(tl_assignments) else len(script)
            block = script[start_pos:end_pos]

            # 找所有 .from() 调用，提取选择器、属性和时间偏移
            from_pattern = re.compile(
                r'\.from\(\s*[\'"]([^\'"]+)[\'"]\s*,\s*\{([^}]*)\}\s*,\s*([\'"][^\'"]*[\'"]|[\d.]+)\s*\)',
                re.DOTALL
            )

            # 找所有 .to() 调用，提取选择器、属性和时间偏移
            to_pattern = re.compile(
                r'\.to\(\s*[\'"]([^\'"]+)[\'"]\s*,\s*\{([^}]*)\}\s*,\s*([\'"][^\'"]*[\'"]|[\d.]+)\s*\)',
                re.DOTALL
            )

            # 找所有 .set() 调用，提取选择器和 { ... } 属性值
            set_detail_pattern = re.compile(
                r'\.set\(\s*[\'"]([^\'"]+)[\'"]\s*,\s*\{([^}]*)\}',
                re.DOTALL
            )
            # selector → { 属性字典 }
            set_details = {}
            assign_line_start = script.rfind('\n', 0, assign.start()) + 1
            assign_to_block = script[assign_line_start:start_pos]
            for region in [assign_to_block, block]:
                for sm in set_detail_pattern.finditer(region):
                    sel = sm.group(1).strip()
                    props_str = sm.group(2)
                    props = {}
                    for pm in re.finditer(r'(\w[\w-]*)\s*:\s*([^,}]+)', props_str):
                        key = pm.group(1).strip()
                        val = pm.group(2).strip()
                        try:
                            props[key] = float(val)
                        except ValueError:
                            props[key] = val
                    set_details[sel] = props

            set_selectors = set(set_details.keys())

            # 检查 .from() 和 .to() 中延迟 > 2s 的调用
            for pattern, method_name in [(from_pattern, "from"), (to_pattern, "to")]:
                for m in pattern.finditer(block):
                    selector = m.group(1).strip()
                    anim_props = m.group(2)  # 动画属性字符串
                    time_arg = m.group(3).strip().strip("'\"")

                    try:
                        time_offset = float(time_arg)
                    except (ValueError, TypeError):
                        continue

                    if time_offset <= delay_threshold:
                        continue

                    # 判断是否为滑动/抽屉特效（动画本身含 x/y/translate 属性）
                    is_slide_effect = bool(re.search(
                        r'\b([xy]|translate[XY])\s*:', anim_props))

                    if not is_slide_effect:
                        continue  # 非滑动特效（scale/opacity/fade 等），跳过偏移量检查

                    # 查找匹配的 .set()（分两轮：先精确，再部分匹配）
                    matched_set_sel = None
                    matched_set_props = None
                    # 第一轮：精确匹配
                    for s, props in set_details.items():
                        if s == selector:
                            matched_set_sel = s
                            matched_set_props = props
                            break
                    # 第二轮：ID 交集部分匹配（仅当精确匹配失败时）
                    if matched_set_sel is None:
                        # 部分匹配：要求 .set() 选择器的最后一级 ID 与 .to() 选择器一致
                        # 且 .set() 层级 ≤ .to() 层级（子元素不能覆盖父元素）
                        # 例如 .set('#card-2') 匹配 .to('#scene-2 #card-2')（同一元素，更短）
                        # 但 .set('#card-2 .proj-stars') 不匹配 .to('#card-2')（子元素，更长）
                        sel_id_list = re.findall(r'#[\w-]+', selector)
                        sel_last_id = sel_id_list[-1] if sel_id_list else None
                        sel_segments = len(selector.split())
                        if sel_last_id:
                            for s, props in set_details.items():
                                set_id_list = re.findall(r'#[\w-]+', s)
                                set_last_id = set_id_list[-1] if set_id_list else None
                                set_segments = len(s.split())
                                if (set_last_id and set_last_id == sel_last_id
                                        and set_segments <= sel_segments):
                                    matched_set_sel = s
                                    matched_set_props = props
                                    break

                    if matched_set_sel is None:
                        failures.append(
                            f"{tl_name}: .{method_name}('{selector}', {{...}}, {time_offset}s) "
                            f"偏移 > {delay_threshold}s 但无对应 .set() 初始化离屏状态。"
                            f"应添加: {tl_name}.set('{selector}', {{ x: {MIN_X} }})"
                        )
                        continue

                    # .set() 存在，检查偏移量是否足够
                    props = matched_set_props or {}
                    # 检查是否有 scale:0 或 opacity:0（视为完全隐藏，跳过偏移量检查）
                    if _is_fully_hidden_by_scale_or_opacity(props):
                        continue

                    # 后代选择器豁免：如果父元素已有足够偏移，后代只需微调动画
                    if _is_covered_by_parent(matched_set_sel, set_details, MIN_X, MIN_Y):
                        continue

                    # 检查位移偏移量
                    max_offset = 0
                    offset_axis = ""
                    for key, val in props.items():
                        if key in ('x', 'translateX') and isinstance(val, (int, float)):
                            if abs(val) > max_offset:
                                max_offset = abs(val)
                                offset_axis = f"{key}:{val}"
                        if key in ('y', 'translateY') and isinstance(val, (int, float)):
                            if abs(val) > max_offset:
                                max_offset = abs(val)
                                offset_axis = f"{key}:{val}"

                    if max_offset > 0:
                        # 判断是水平还是垂直偏移
                        is_x_axis = any(k in props for k in ('x', 'translateX'))
                        threshold = MIN_X if is_x_axis else MIN_Y
                        if max_offset < threshold:
                            failures.append(
                                f"{tl_name}: .set('{matched_set_sel}', {{{offset_axis}}}) "
                                f"偏移量 {max_offset}px < {orient_label}最低标准 {threshold}px "
                                f"— 元素未完全推出画布，会半露。"
                                f"应设为 ≥ {threshold}"
                            )

    if failures:
        return False, "; ".join(failures)
    return True, "延迟入场动画初始化检查通过"


def _is_fully_hidden_by_scale_or_opacity(props: dict) -> bool:
    """检查 .set() 属性中是否有 scale:0 或 opacity:0（完全隐藏元素）。"""
    for key, val in props.items():
        if key == 'scale' and isinstance(val, (int, float)) and val == 0:
            return True
        if key == 'opacity' and isinstance(val, (int, float)) and val == 0:
            return True
    return False


def _is_covered_by_parent(selector: str, set_details: dict, min_x: int, min_y: int) -> bool:
    """后代选择器豁免：检查父元素是否已有足够偏移完全隐藏。
    例如 #scene-2 #card-2 .proj-desc 的父 #scene-2 #card-2 已有 x:1100 → 子 y:20 是微调，豁免。
    使用选择器前缀匹配（非 ID 交集）确保只有真正的 DOM 祖先才被认可。
    """
    # 只对后代选择器（含空格）生效
    if ' ' not in selector:
        return False

    # 遍历所有 .set() 选择器，用前缀匹配找真正的祖先
    for ps, pp in set_details.items():
        # ps 必须是 selector 的严格前缀（ps + 空格 = selector 的前缀）
        if not selector.startswith(ps + ' '):
            continue
        # ps 是祖先选择器，检查其偏移是否足够
        if _is_fully_hidden_by_scale_or_opacity(pp):
            return True
        for k, v in pp.items():
            if k in ('x', 'translateX') and isinstance(v, (int, float)) and abs(v) >= min_x:
                return True
            if k in ('y', 'translateY') and isinstance(v, (int, float)) and abs(v) >= min_y:
                return True

    return False


GATE_CHECKERS[GateType.html_structure_valid] = check_html_structure_valid
GATE_CHECKERS[GateType.output_media_valid] = check_output_media_valid
GATE_CHECKERS[GateType.bgm_isolation_valid] = check_bgm_isolation_valid
GATE_CHECKERS[GateType.visual_phases_completeness] = check_visual_phases_completeness
GATE_CHECKERS[GateType.safe_area_bounds] = check_safe_area_bounds
GATE_CHECKERS[GateType.narration_audio_embedded] = check_narration_audio_embedded
GATE_CHECKERS[GateType.delayed_animation_init] = check_delayed_animation_init


# SAFETY 级 gate：违反即安全事故，不可通过归因自动修复
SAFETY_GATES = {
    GateType.no_forbidden_speech,
    GateType.no_url_in_output,
    GateType.no_real_person_name,
    GateType.no_school_name,
    GateType.no_app_name,
    GateType.no_competitor_attack,
    GateType.no_search_cta,
}


def run_gate(skill: SkillDefinition, project_dir: Path) -> GateReport:
    hard_violations: list[Violation] = []
    hard_passed = True
    rigor = skill.rigor_level

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

    # Rigor 调制（架构 §6.0）：
    # - LITE: 仅 HARD gates，跳过 SOFT
    # - STANDARD / STRICT: HARD + SOFT gates
    soft_score = 1.0
    soft_issues: list[str] = []
    if rigor != Rigor.LITE:
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
    stages = ["stage0.5-topic-plan", "stage1-content", "stage3-scenes", "stage4-audio", "stage6-production", "stage7-delivery"]
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

    # 合规度（原 overall）：各 stage soft_score 均值
    compliance = (
        sum(p["soft_score"] for p in phases.values()) / len(phases) if phases else 0
    )

    # 新鲜度（P0：与近 N 期历史的相似度取反，阻止同质化顶峰）
    freshness = None
    try:
        from engine.freshness import compute_freshness
        freshness = compute_freshness(project_dir)
    except Exception as e:
        print(f"[score] freshness 计算失败: {e}", file=sys.stderr)

    # 播放量潜力预测（P2：启发式低权，待 auto_evolve 训练验证后调高）
    predicted = None
    try:
        from engine.predict import predict_plays_score
        predicted = predict_plays_score(project_dir)
    except Exception as e:
        print(f"[score] predicted_plays 计算失败: {e}", file=sys.stderr)

    # 多维加权总分：overall = w1·合规 + w2·新鲜度 + w3·播放潜力
    # 注：曾试加 hook_strength 子分，审查发现与 gate 拦截重叠（已砍，gate 拦截是核心）
    W_COMPLIANCE = 0.6
    W_FRESHNESS = 0.3
    W_PREDICTED = 0.1
    overall = W_COMPLIANCE * compliance
    if freshness and "freshness_score" in freshness:
        overall += W_FRESHNESS * freshness["freshness_score"]
    if predicted and "predicted_plays_score" in predicted:
        overall += W_PREDICTED * predicted["predicted_plays_score"]
    overall = round(overall, 3)

    score_report = {
        "project": str(project_dir),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "phases": phases,
        "overall_soft_score": round(compliance, 3),    # 向后兼容：纯合规度
        "overall_score": overall,                       # 多维加权总分（P0+P2）
        "freshness": freshness,                         # 新鲜度分项（P0+）
        "predicted_plays": predicted,                   # 播放量潜力预测分项（P2+）
        "scoring_weights": {"compliance": W_COMPLIANCE, "freshness": W_FRESHNESS, "predicted": W_PREDICTED},
        "hard_passed_all": all(p.get("hard_passed", False) for p in phases.values()),
        "total_stages": len(phases),
        "stages_passed": sum(1 for p in phases.values() if p.get("hard_passed")),
    }

    # cinematic 字段合规（软校验，记录到 score_report 供评分/追溯）
    # check_cinematic_fields 总 passed=True（软），msg 记录字段白名单合规情况（"通过" / "非法值默认兜底"）
    try:
        ns_ok, ns_msg = check_cinematic_fields(project_dir, {"file": "narration_segments.json"})
        score_report["cinematic_compliance"] = {"passed": ns_ok, "msg": ns_msg}
    except Exception:
        pass

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
            rigor=skill.rigor_level.value,
        )
    except Exception as e:
        print(f"[gate] trace 记录失败（不影响门禁）: {e}", file=sys.stderr)

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
        except Exception as e:
            print(f"[gate] 自动归因失败（不影响门禁，HARD 判定已生效）: {e}", file=sys.stderr)

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
        from engine.trace import record_trace, TRACES_DIR, _resolve_trace_dir
        from engine.attribution import strong_attribution, weak_attribution
        from engine.lib.rule_parser import load_all_rules, load_skill
        all_rules = load_all_rules()
    except Exception as e:
        print(f"[closed-loop] 初始化失败: {e}", file=sys.stderr)
        return

    # ── 幂等性：移除今天的旧 trace（覆盖模式，允许修复后重新评分）──
    project_traces_dir = _resolve_trace_dir(str(project_dir), TRACES_DIR)
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
            # 加载 skill 以获取 rigor_level
            rigor_val = None
            try:
                sk = load_skill(stage_id)
                if sk:
                    rigor_val = sk.rigor_level.value
            except Exception:
                pass
            record_trace(
                skill_id=stage_id,
                project_dir=str(project_dir),
                result=trace_result,
                gate_report=gate_dict,
                rigor=rigor_val,
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

            # False positive detection: 同阶段历史 trace 中违规但本次通过 → 误杀
            from engine.dispute_tracker import increment_false_positive
            try:
                project_traces_file = _resolve_trace_dir(str(project_dir), TRACES_DIR) / "trace.json"
                if project_traces_file.exists():
                    prev_traces = json.loads(project_traces_file.read_text(encoding="utf-8"))
                    if isinstance(prev_traces, list):
                        # 筛选同 stage 的历史 trace（排除本次刚写入的）
                        same_stage = [
                            pt for pt in prev_traces
                            if pt.get("skill_id") == stage_id
                        ]
                        if len(same_stage) >= 2:
                            prev_trace = same_stage[-2]  # 同阶段上一条 trace
                            prev_violation_ids = set()
                            prev_gate = (prev_trace.get("result") or {}).get("gate_report") or {}
                            for v in prev_gate.get("hard_violations", []):
                                prev_violation_ids.add(v.get("rule_id", ""))
                            current_violation_ids = set(v.get("rule_id", "") for v in detail.get("hard_violations", []))
                            # 同阶段上次违规但本次不再违规 → 可能是误杀
                            resolved = prev_violation_ids - current_violation_ids
                            for rid in resolved:
                                try:
                                    increment_false_positive(rid.replace("gate:", ""))
                                except Exception:
                                    pass
            except Exception:
                pass  # false positive detection 是辅助功能，不阻塞主流程


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

        fr = report.get("freshness") or {}
        pr = report.get("predicted_plays") or {}
        output = {
            "generated": True,
            "project": str(project_dir),
            "overall_soft_score": report["overall_soft_score"],
            "overall_score": report.get("overall_score"),
            "freshness_score": fr.get("freshness_score"),
            "predicted_plays_score": pr.get("predicted_plays_score"),
            "freshness_detail": {k: fr.get(k) for k in ("hook_sim", "project_jaccard", "template_sim", "most_similar_dim")},
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
