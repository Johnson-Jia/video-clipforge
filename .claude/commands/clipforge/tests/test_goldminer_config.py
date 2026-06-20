"""goldminer 分类配置可加载性 + 字段完整性测试。

副轨"创业淘金者"专栏配置（2026-06-20 从技术淘金者转型为失败案例淘金）。
确保 engine 能识别分类，且 CONFIG 段含失败复盘所需的全部字段。
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from engine.lib.category_config import load_category_config


class TestGoldminerConfigLoadable(unittest.TestCase):
    def test_config_loads(self):
        """category_config.py 按 {id}.md 自动加载，goldminer 必须可加载且 CONFIG 非空。"""
        cfg = load_category_config("goldminer")
        self.assertTrue(cfg, "goldminer.md 缺失或 CONFIG 段解析为空")

    def test_frontmatter_id(self):
        """frontmatter 声明分类 id（schema 约定；engine 用文件名路由，不解析 frontmatter）。"""
        path = Path(__file__).parent.parent / "categories" / "goldminer.md"
        frontmatter = path.read_text(encoding="utf-8").split("---")[1]
        self.assertIn('id: "goldminer"', frontmatter)


class TestGoldminerConfigFields(unittest.TestCase):
    """CONFIG 段必填字段（对比式淘金所需）。"""

    def setUp(self):
        self.cfg = load_category_config("goldminer")

    def test_audio_voice(self):
        self.assertIn("audio", self.cfg)
        self.assertEqual(self.cfg["audio"]["default_voice"], "zh-CN-YunjianNeural")

    def test_audio_rate(self):
        """default_rate +15%（失败复盘沉稳语气，比主轨 +25% 慢，防误同步主轨）。"""
        self.assertEqual(self.cfg["audio"]["default_rate"], "+15%")

    def test_narration_word_count(self):
        self.assertEqual(self.cfg["narration"]["word_count_range"], [410, 640])

    def test_narration_hook_anchor(self):
        """开场主锚「开淘」必须进 hook_anchors（供 gate 检测）。"""
        self.assertIn("开淘", self.cfg["narration"].get("hook_anchors", []))

    def test_delivery_cover_badge(self):
        self.assertEqual(self.cfg["delivery"]["cover_badge"], "创业淘金者")

    def test_design_style(self):
        self.assertIn("淘金", self.cfg["design"]["default_style"])


if __name__ == "__main__":
    unittest.main()
