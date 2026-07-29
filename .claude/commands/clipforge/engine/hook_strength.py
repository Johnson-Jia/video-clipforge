"""hook 具象度指标解析 — 量化 hook 文案前 5 秒抓眼球能力（c5s 根因）。

背景：c5s 6月0.40→7月0.32（-20%），drill-c5s 下钻定位 hook 变长/抽象化/堆叠/元铺垫
（0729 38字「不用装软件...方向挺杂」vs 6月15字「输入砍掉九成」）。freshness（题材轮换）
与 c5s（开头吸引力）正交。

parse_hook_metrics(text) → {len, has_conflict, has_number, has_pileup, has_meta_premise}
gate.check_hook_pattern_verified 复用做 HARD 拦截（字数>20/堆叠/元铺垫/无锚点）。

注：曾设计 compute_hook_strength 连续分值进 overall_score（W=0.15），审查发现与 gate
拦截重叠——gate HARD 拦后剩余 hook 都达标，连续子分区分价值未验证（权重亦无数据支撑），
已砍。gate 确定性拦截是核心，score 不需要 hook_strength 子分。
"""
from __future__ import annotations
import re

# 冲突词（反直觉/强对比/动作，高 c5s 信号，6月验证）— 含 gate.HOOK_HIGH_VALUE_KEYWORDS + 扩展
HOOK_CONFLICT_WORDS = (
    "不用", "却能", "居然", "竟然", "竟然能", "只要", "不需要",  # gate 高优
    "砍", "省", "降", "倍", "首次", "杀入", "冲上", "炸",  # 动作/量化冲突
)
# 数字锚定（阿拉伯/中文/百分比/量级）
_NUMBER_RE = re.compile(r"\d|%|九成|八成|七成|六成|五成|一半|千|万|亿|百")
# 堆叠连接词（多信息稀释钩子，0729「，还有个」类）
HOOK_PILEUP_MARKERS = ("，还有个", ",还有个", "，以及", ",以及", "，同时", ",同时", "，另外", ",另外")
# 元铺垫（告诉观众"今天讲什么/方向如何"的制作层元信息，与 R-G-016 同构；精准短语避免误报）
HOOK_META_PREMISE = ("方向挺杂", "方向挺多", "方向多杂", "几个猛项目", "今天讲", "这期讲", "本期讲")


def parse_hook_metrics(text: str) -> dict:
    """解析 hook 文本，返回具象度指标（gate.check_hook_pattern_verified HARD 拦截用）。"""
    text = (text or "").strip()
    return {
        "len": len(text),
        "has_conflict": any(w in text for w in HOOK_CONFLICT_WORDS),
        "has_number": bool(_NUMBER_RE.search(text)),
        "has_pileup": any(m in text for m in HOOK_PILEUP_MARKERS),
        "has_meta_premise": any(m in text for m in HOOK_META_PREMISE),
    }
