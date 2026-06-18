"""ClipForge exploration 测试（B 修复：freshness feedback 调 explore/exploit）。

freshness 学习层 recommendation 真正闭环到 exploration action——
NARROW_EXPLORE（近期高freshness低播放）→ 调低 ε，收窄冷门探索。
"""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from engine.exploration import decide


class TestFreshnessFeedback(unittest.TestCase):
    def setUp(self):
        self.empty_patterns = Path(tempfile.mkdtemp())  # 无 P-*.yaml，candidates=[]，聚焦测 ε

    def test_narrow_explore_reduces_epsilon(self):
        """NARROW_EXPLOVE feedback → effective epsilon 调低（收窄冷门探索）。"""
        r = decide("proj", "2026-06-18", patterns_dir=self.empty_patterns,
                   freshness_feedback={"recommendation": "NARROW_EXPLORE"})
        self.assertLess(r["epsilon"], 0.15)
        self.assertAlmostEqual(r["epsilon"], 0.075)

    def test_no_feedback_default_epsilon(self):
        """无 feedback → epsilon 默认 0.15。"""
        r = decide("proj", "2026-06-18", patterns_dir=self.empty_patterns,
                   freshness_feedback=None)
        self.assertEqual(r["epsilon"], 0.15)

    def test_other_recommendation_no_change(self):
        """非 NARROW_EXPLORE（如 REVIEW_FRESHNESS_WEIGHT）→ epsilon 不变（不影响探索比例）。"""
        r = decide("proj", "2026-06-18", patterns_dir=self.empty_patterns,
                   freshness_feedback={"recommendation": "REVIEW_FRESHNESS_WEIGHT"})
        self.assertEqual(r["epsilon"], 0.15)


if __name__ == "__main__":
    unittest.main()
