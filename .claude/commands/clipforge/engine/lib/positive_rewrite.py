"""正向重述引擎 — 将负向规则转换为正向表述注入 prompt。"""
from __future__ import annotations
from .models import Rule


def rewrite_rule(rule: Rule) -> dict[str, str]:
    """返回 {positive: 正向表述, guardrail: 校验表述}。
    如果规则已有 positive/guardrail 字段则直接使用，否则从 pattern 生成。"""
    if rule.positive:
        return {"positive": rule.positive, "guardrail": rule.guardrail or rule.pattern}
    positive = _auto_rewrite(rule.pattern, rule.type.value)
    guardrail = rule.pattern
    return {"positive": positive, "guardrail": guardrail}


def _auto_rewrite(pattern: str, rule_type: str) -> str:
    """从 FORBIDDEN_* 模式自动生成正向表述。"""
    if "绝对化" in pattern or "极限用语" in pattern:
        return "所有表述使用限定性语言，如'可能'、'通常'、'在一定程度上'"
    if "URL" in pattern or "网址" in pattern or "链接" in pattern:
        return "只展示项目名称/产品名称，链接放评论区"
    if "播报腔" in pattern or "播报" in pattern or "Yunyang" in pattern:
        return "使用分类配置指定的叙事感音色，保持'我在跟你聊'的自然口吻"
    if "淡入" in pattern:
        return "音频从第一帧立即全音量播放，确保 hook 冲击力"
    if "anim-in" in pattern or "opacity:0" in pattern or "CSS 入场" in pattern:
        return "所有内容元素默认可见（opacity:1），入场动画使用 GSAP .from()"
    if "HTML 实体" in pattern or "&#9733;" in pattern:
        return "使用 Unicode 字符直接输入（★ 而非 &#9733;）"
    if "padding" in pattern and "双重" in pattern:
        return "安全区 padding 只设一层（180px 80px 220px 80px），scene-wrap 或 .phase 二选一"
    if "均分" in pattern or "gap" in pattern:
        return "Phase 断点按旁白话题转换对齐，用字数比例换算时间戳"
    if "预衰减" in pattern or "gain" in pattern or "volume 滤镜" in pattern:
        return "bgm.wav 保持原始音量，混音衰减由 HTML data-volume 控制"
    if "output.mp4" in pattern and "提取" in pattern:
        return "output_no_bgm.mp4 从 narration.mp3 合成，不从 output.mp4 提取音频"
    if "loop" in pattern and "HTML" in pattern:
        return "BGM 循环使用 FFmpeg -stream_loop 扩展 WAV，不依赖 HTML loop 属性"
    if "download" in pattern.lower() or "安装" in pattern or "下载" in pattern:
        return "只描述能力，不说获取路径：说'能做什么'，不说'去哪下载/怎么安装'"
    if "诱导" in pattern or "点赞" in pattern:
        return "正文自然提及，不用命令式引导互动"
    # 兜底：从 FORBIDDEN 模式提取核心意图并正向化，而非原样传递负向规则
    return _fallback_rewrite(pattern)


def _fallback_rewrite(pattern: str) -> str:
    """兜底正向重述：从 FORBIDDEN_* 模式提取核心意图并正向化。

    策略：去掉否定词后，将"禁止X"转为"确保非X"或直接陈述正向行为。
    """
    # 去掉常见否定前缀
    cleaned = pattern
    for neg in ("禁止", "不得", "不能", "不可", "不要", "避免", "拒绝"):
        if cleaned.startswith(neg):
            cleaned = cleaned[len(neg):]
            break

    # 根据核心动作生成正向表述
    if "复制" in cleaned:
        return f"确保内容原创，基于理解重新组织表达"
    if "绕过" in cleaned or "跳过" in cleaned:
        return f"按完整流程执行每一步，不省略任何环节"
    if "虚构" in cleaned or "伪造" in cleaned:
        return f"所有数据来源于真实 API 返回值，不编造任何信息"
    if "绝对化" in cleaned or "极限" in cleaned:
        return f"使用限定性语言表述，保持客观中立的语气"
    if "忽略" in cleaned or "无视" in cleaned:
        return f"逐一检查所有相关约束，确保每条都被遵守"

    # 通用正向化：将禁止内容转为"确保..."
    return f"确保：{cleaned.strip('，。、')}"
