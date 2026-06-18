"""ClipForge freshness 聚合分析测试（项3：freshness_signal 学习层）。

analyze_freshness_signals 聚合 feedback_results 的 freshness_signal，
产出 exploration 探索-利用校准建议。机制就位，数据驱动生效（<min_samples 空转）。
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from engine.freshness import analyze_freshness_signals


def _fr(signal):
    """构造一条 feedback_result（含 calibration.freshness_signal）。"""
    return {"calibration": {"freshness_signal": {"signal": signal}}}


class TestAnalyzeFreshnessSignals(unittest.TestCase):
    def test_insufficient_data_returns_none(self):
        """<5 样本 → recommendation None（数据不足空转）。"""
        r = analyze_freshness_signals([_fr("FRESH_BUT_LOW_PLAYS")] * 4)
        self.assertIsNone(r["recommendation"])

    def test_fresh_but_low_majority_narrows_explore(self):
        """FRESH_BUT_LOW_PLAYS ≥40% → NARROW_EXPLORE（explore 方向错）。"""
        data = [_fr("FRESH_BUT_LOW_PLAYS")] * 3 + [_fr("ALIGNED")] * 2
        r = analyze_freshness_signals(data)
        self.assertEqual(r["recommendation"], "NARROW_EXPLORE")

    def test_similar_but_high_majority_reviews_weight(self):
        """SIMILAR_BUT_HIGH_PLAYS ≥40% → REVIEW_FRESHNESS_WEIGHT。"""
        data = [_fr("SIMILAR_BUT_HIGH_PLAYS")] * 3 + [_fr("ALIGNED")] * 2
        r = analyze_freshness_signals(data)
        self.assertEqual(r["recommendation"], "REVIEW_FRESHNESS_WEIGHT")

    def test_balanced_no_recommendation(self):
        """正常分布（ALIGNED 主导）→ None。"""
        r = analyze_freshness_signals([_fr("ALIGNED")] * 5)
        self.assertIsNone(r["recommendation"])


if __name__ == "__main__":
    unittest.main()
