"""bgm_gap_check 音量校准测试。

重点验证 LRA 分档 mean_gap 值（2026-07-02：beat-heavy 9→10，电子类更让位旁白）。
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from scripts.bgm_gap_check import classify_tier, calc_volume, LRA_TIERS  # noqa: E402


class TestLRATiers(unittest.TestCase):
    def test_beat_heavy_mean_gap_is_10(self):
        """beat-heavy 档 mean_gap=10（2026-07-02 由 9 调整）。电子/合成波高频主观吵，
        mean_gap 与 flat 档看齐加大，让 BGM 均值距旁白 10dB（原 9）。"""
        tier, basis = classify_tier(lra=5.0)
        self.assertEqual(tier["name"], "beat-heavy")
        self.assertEqual(tier["mean_gap"], 10)

    def test_dynamic_unchanged(self):
        """dynamic 档（交响/电影）不动，仍 mean_gap=9。"""
        tier, _ = classify_tier(lra=8.0)
        self.assertEqual(tier["name"], "dynamic")
        self.assertEqual(tier["mean_gap"], 9)

    def test_flat_and_balanced_unchanged(self):
        """flat/balanced 档不受影响。"""
        flat, _ = classify_tier(lra=1.5)
        self.assertEqual(flat["mean_gap"], 11)
        bal, _ = classify_tier(lra=3.0)
        self.assertEqual(bal["mean_gap"], 15)


class TestCalcVolumeBeatHeavy(unittest.TestCase):
    def test_beat_heavy_tier_info_carries_gap_10(self):
        """LRA=5 的电子类 BGM，calc_volume 返回 tier_info.mean_gap=10。"""
        vol, reason, tier = calc_volume(
            bgm_mean=-18.0, bgm_max=-2.0, narr_mean=-17.0, narr_max=-1.5, lra=5.0
        )
        self.assertEqual(tier["name"], "beat-heavy")
        self.assertEqual(tier["mean_gap"], 10)
        self.assertGreater(vol, 0)


class TestSpreadFallbackConsistency(unittest.TestCase):
    def test_beat_heavy_spread_fallback_gap_10(self):
        """兼容兜底路径（LRA 未传）beat-heavy 也 mean_gap=10，与 LRA 档一致。"""
        tier, basis = classify_tier(lra=None, peak_spread=15.0)
        self.assertEqual(tier["name"], "beat-heavy")
        self.assertEqual(basis, "spread")
        self.assertEqual(tier["mean_gap"], 10)


if __name__ == "__main__":
    unittest.main()
