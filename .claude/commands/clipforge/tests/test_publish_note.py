"""render_publish_note 执行漂移高亮测试。"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from engine.publish_time import render_publish_note


_BASE = {
    "best_hour_bucket": "evening", "confidence": "high",
    "best_avg_reach": 0.565, "market_avg_reach": 0.481, "coverage_hour": "115/119",
}


class TestPublishNoteDrift(unittest.TestCase):
    def test_no_drift_no_highlight(self):
        """recent_drift 无 flag → note 不含漂移高亮。"""
        advice = {**_BASE, "recent_drift": {"enabled": True, "timing": {"drift": False}, "c5s": {"flag": False}}}
        note = render_publish_note(advice)
        self.assertNotIn("执行漂移", note)

    def test_timing_drift_shows_highlight(self):
        advice = {**_BASE, "recent_drift": {"enabled": True, "window": "14d",
                "timing": {"drift": True, "best_slot": "evening", "recent_ratio": 0.0,
                           "baseline_ratio": 0.16, "recent_n": 10,
                           "advice": "近10条 evening 占比 0%（全期16%），建议下个发布窗口调 evening"},
                "c5s": {"flag": False}}}
        note = render_publish_note(advice)
        self.assertIn("执行漂移", note)
        self.assertIn("evening", note)

    def test_c5s_flag_shows_highlight(self):
        advice = {**_BASE, "recent_drift": {"enabled": True,
                "timing": {"drift": False},
                "c5s": {"flag": True, "previous": 0.43, "current": 0.32, "drop": 0.25,
                        "advice": "5s完播退化"}}}
        note = render_publish_note(advice)
        self.assertIn("执行漂移", note)
        self.assertIn("5s完播", note)


if __name__ == "__main__":
    unittest.main()
