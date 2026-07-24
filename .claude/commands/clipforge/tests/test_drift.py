"""执行漂移诊断纯函数测试（timing drift + c5s trend）。

依据 2026-07-24 下钻：evening 全期 16%/7月 0%（drift）、5s完播 0.43→0.32（flag）。
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from engine.drift import proj_date, within_days, diagnose_timing_drift


def _proj(hour=None):
    """构造一条项目记录（publish_hour int|None）。"""
    return {"publish_hour": hour}


class TestProjDate(unittest.TestCase):
    def test_extracts_from_path(self):
        self.assertEqual(proj_date(Path("D:/ws/2026/07/24/github-trending")), "2026-07-24")

    def test_returns_none_when_no_date(self):
        self.assertIsNone(proj_date(Path("D:/ws/test/foo")))


class TestWithinDays(unittest.TestCase):
    def test_within_window(self):
        from datetime import date
        self.assertTrue(within_days("2026-07-20", date(2026, 7, 24), 14))

    def test_outside_window(self):
        from datetime import date
        self.assertFalse(within_days("2026-06-01", date(2026, 7, 24), 14))

    def test_none_date(self):
        from datetime import date
        self.assertFalse(within_days(None, date(2026, 7, 24), 14))


class TestTimingDrift(unittest.TestCase):
    def test_drift_when_recent_best_slot_drops_to_zero(self):
        """evening 全期 16%、近期 0% → drift=True（本次塌方场景）。"""
        # publish_hour 19-22 = evening（hour_to_bucket 分桶）
        all_p = [_proj(8)] * 10 + [_proj(20)] * 2 + [_proj(13)] * 5   # evening 占 2/17≈12%
        recent = [_proj(8)] * 6 + [_proj(13)] * 4                       # evening 占 0%
        r = diagnose_timing_drift(recent, all_p, "evening")
        self.assertTrue(r["drift"])
        self.assertEqual(r["recent_ratio"], 0.0)
        self.assertGreater(r["baseline_ratio"], 0.0)
        self.assertIsNotNone(r["advice"])

    def test_no_drift_when_stable(self):
        """近期 best_slot 占比与全期接近 → drift=False。"""
        all_p = [_proj(20)] * 5 + [_proj(8)] * 5
        recent = [_proj(20)] * 3 + [_proj(8)] * 2
        r = diagnose_timing_drift(recent, all_p, "evening")
        self.assertFalse(r["drift"])

    def test_no_best_slot(self):
        r = diagnose_timing_drift([_proj(8)], [_proj(8)], None)
        self.assertFalse(r["drift"])


if __name__ == "__main__":
    unittest.main()
