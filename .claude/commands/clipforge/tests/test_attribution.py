"""ClipForge attribution 测试（方案甲：freshness 平行诊断）。

calibrate_machine_scoring 增加 freshness 维度独立诊断信号，
不影响既有 verdict/Delta 逻辑（零回归）——freshness 进评分(gate.py)却不进校准(attribution)
的断裂，通过独立信号通路补上。
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from engine.attribution import calibrate_machine_scoring, strong_attribution
from engine.lib.models import Rule, RuleType


class TestCalibrateFreshnessSignal(unittest.TestCase):
    def test_fresh_but_low_plays(self):
        """高新鲜度 + 实际表现低 → FRESH_BUT_LOW_PLAYS（新鲜度未转化为播放）。"""
        score_report = {"overall_soft_score": 0.9, "freshness": {"freshness_score": 0.8}}
        result = calibrate_machine_scoring(
            score_report, {}, human_scores={"overall": 2}, produce_delta=False)
        self.assertEqual(result["freshness_signal"]["signal"], "FRESH_BUT_LOW_PLAYS")

    def test_similar_but_high_plays(self):
        """低新鲜度（高度同质化）+ 实际表现高 → SIMILAR_BUT_HIGH_PLAYS。"""
        score_report = {"overall_soft_score": 0.5, "freshness": {"freshness_score": 0.2}}
        result = calibrate_machine_scoring(score_report, {}, produce_delta=False)
        self.assertEqual(result["freshness_signal"]["signal"], "SIMILAR_BUT_HIGH_PLAYS")

    def test_no_freshness_data(self):
        """score_report 无 freshness → NO_DATA。"""
        result = calibrate_machine_scoring({"overall_soft_score": 0.5}, {}, produce_delta=False)
        self.assertEqual(result["freshness_signal"]["signal"], "NO_DATA")


class TestStrongAttributionRobustness(unittest.TestCase):
    def test_skips_none_rule(self):
        """strong_attribution 对含 None 的 rules 不抛（防御 load_all_rules 异常元素，gate closed-loop NoneType bug）。"""
        good = Rule(id="R-G-001", type=RuleType.FORBIDDEN_ACTION,
                    pattern="p", positive="p", guardrail="p")
        result = strong_attribution({"rule_id": "R-G-001", "details": ""}, [None, good])
        self.assertEqual(result["root_cause"], "rule_hit")

    def test_id_match_with_none_detection(self):
        """detection=None 但 ID 匹配 → rule_hit（ID 归因优先于 keyword，等价原始逻辑）。"""
        bad = Rule(id="R-BAD", type=RuleType.FORBIDDEN_ACTION,
                   pattern="p", positive="p", guardrail="p")
        bad.detection = None  # 模拟 detection 缺失（parse_rule 异常）
        result = strong_attribution({"rule_id": "R-BAD", "details": ""}, [bad])
        self.assertEqual(result["root_cause"], "rule_hit")


if __name__ == "__main__":
    unittest.main()
