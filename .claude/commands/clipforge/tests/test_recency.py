"""数据时效加权 TDD 测试。

auto_evolve 统计给近期数据更高权重，校准偏向新表现（不让远古数据拖累趋势校准）。
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from engine.recency import recency_weight, weighted_mean, project_data_weight  # noqa: E402


class TestRecencyWeight(unittest.TestCase):
    """数据年龄 → 权重（近期高，旧衰减但不归零保留样本）。"""

    def test_within_7_days_full_weight(self):
        self.assertEqual(recency_weight(0), 1.0)
        self.assertEqual(recency_weight(7), 1.0)

    def test_8_to_14_days(self):
        self.assertEqual(recency_weight(8), 0.7)
        self.assertEqual(recency_weight(14), 0.7)

    def test_15_to_30_days(self):
        self.assertEqual(recency_weight(15), 0.4)
        self.assertEqual(recency_weight(30), 0.4)

    def test_over_30_days_minimal(self):
        self.assertEqual(recency_weight(31), 0.1)
        self.assertEqual(recency_weight(100), 0.1)


class TestWeightedMean(unittest.TestCase):
    """加权平均；权重和为 0 时降级简单均值。"""

    def test_equal_weights(self):
        self.assertEqual(weighted_mean([1.0, 2.0], [1.0, 1.0]), 1.5)

    def test_unequal_weights(self):
        self.assertEqual(weighted_mean([1.0, 2.0], [3.0, 1.0]), 1.25)

    def test_zero_weights_fallback_mean(self):
        self.assertEqual(weighted_mean([1.0, 2.0], [0.0, 0.0]), 1.5)

    def test_empty(self):
        self.assertEqual(weighted_mean([], []), 0.0)


class TestProjectDataWeight(unittest.TestCase):
    """从 snapshots 算项目权重（最新 source_date 距今天数）。"""

    def test_recent_data_full_weight(self):
        snapshots = [{"source_date": "2026-06-19"}]
        self.assertEqual(project_data_weight(snapshots, "2026-06-20"), 1.0)  # 1 天

    def test_old_data_decayed(self):
        snapshots = [{"source_date": "2026-06-01"}]
        self.assertEqual(project_data_weight(snapshots, "2026-06-20"), 0.4)  # 19 天

    def test_no_snapshots_full_weight(self):
        self.assertEqual(project_data_weight([], "2026-06-20"), 1.0)

    def test_multiple_snapshots_uses_latest(self):
        snapshots = [{"source_date": "2026-05-01"}, {"source_date": "2026-06-19"}]
        self.assertEqual(project_data_weight(snapshots, "2026-06-20"), 1.0)  # 用最新 06-19


if __name__ == "__main__":
    unittest.main()
