"""电影级剪辑映射测试（流程固化层）：分镜字段 → 渲染映射。"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from scripts.cinematic import (
    camera_move_to_gsap, transition_to_phase, shot_size_to_density,
    SHOT_SIZES, CAMERA_MOVES, TRANSITIONS,
)


class TestCameraMoveToGsap(unittest.TestCase):
    def test_push_scale_up(self):
        r = camera_move_to_gsap("s01", "推", 0, 3)
        self.assertIn("scale:1.1", r)
        self.assertIn("#s01 .layer-content", r)

    def test_pull_scale_down(self):
        r = camera_move_to_gsap("s01", "拉", 0, 3)
        self.assertIn("scale:0.9", r)

    def test_fixed_no_animation(self):
        self.assertEqual(camera_move_to_gsap("s01", "固定", 0, 3), "")

    def test_dutch_angle_static_rotate(self):
        r = camera_move_to_gsap("s01", "荷兰角", 0, 3)
        self.assertIn("tl.set", r)
        self.assertIn("rotation", r)

    def test_invalid_falls_back_default_fixed(self):
        self.assertEqual(camera_move_to_gsap("s01", "乱来", 0, 3), "")

    def test_all_camera_moves_no_error(self):
        for cm in CAMERA_MOVES:
            self.assertIsInstance(camera_move_to_gsap("s01", cm, 0, 3), str)


class TestTransitionToPhase(unittest.TestCase):
    def test_hardcut_instant_set(self):
        r = transition_to_phase("s01", "s02", 5.0, "硬切")
        self.assertTrue(any("tl.set" in x and "opacity:0" in x for x in r))
        self.assertTrue(any("tl.set" in x and "opacity:1" in x for x in r))

    def test_crossfade_has_to_duration(self):
        r = transition_to_phase("s01", "s02", 5.0, "叠化")
        self.assertTrue(any("tl.to" in x and "duration:0.4" in x for x in r))

    def test_fadein_cur_to_opacity(self):
        r = transition_to_phase("s01", "s02", 5.0, "淡入")
        self.assertTrue(any("opacity:1" in x and "duration:0.5" in x for x in r))

    def test_black_via_zero_three_steps(self):
        r = transition_to_phase("s01", "s02", 5.0, "黑场")
        self.assertEqual(len(r), 3)
        self.assertTrue(any("opacity:0" in x for x in r))

    def test_all_transitions_no_error(self):
        for tr in TRANSITIONS:
            self.assertIsInstance(transition_to_phase("s01", "s02", 5.0, tr), list)


class TestShotSizeToDensity(unittest.TestCase):
    def test_closeup_generous(self):
        self.assertEqual(shot_size_to_density("特写"), "generous")
        self.assertEqual(shot_size_to_density("大特写"), "generous")

    def test_wide_compact(self):
        self.assertEqual(shot_size_to_density("远景"), "compact")
        self.assertEqual(shot_size_to_density("大远景"), "compact")

    def test_medium_standard(self):
        self.assertEqual(shot_size_to_density("中景"), "standard")

    def test_invalid_default_standard(self):
        self.assertEqual(shot_size_to_density("乱来"), "standard")


class TestCheckCinematicFields(unittest.TestCase):
    """gate 软校验：非法值不 fail（映射函数默认兜底），仅记录警告。"""
    def test_missing_file_passes(self):
        import tempfile
        from engine.gate import check_cinematic_fields
        with tempfile.TemporaryDirectory() as td:
            ok, msg = check_cinematic_fields(Path(td), {"file": "narration_segments.json"})
            self.assertTrue(ok)

    def test_valid_values_pass(self):
        import tempfile, json
        from engine.gate import check_cinematic_fields
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            (td / "narration_segments.json").write_text(
                json.dumps([{"shot_size": "特写", "camera_move": "推", "transition": "叠化"}]),
                encoding="utf-8")
            ok, msg = check_cinematic_fields(td, {"file": "narration_segments.json"})
            self.assertTrue(ok)
            self.assertIn("通过", msg)

    def test_invalid_values_still_pass_but_warn(self):
        import tempfile, json
        from engine.gate import check_cinematic_fields
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            (td / "narration_segments.json").write_text(
                json.dumps([{"shot_size": "乱来", "camera_move": "乱来", "transition": "乱来"}]),
                encoding="utf-8")
            ok, msg = check_cinematic_fields(td, {"file": "narration_segments.json"})
            self.assertTrue(ok)
            self.assertIn("非法", msg)


if __name__ == "__main__":
    unittest.main()
