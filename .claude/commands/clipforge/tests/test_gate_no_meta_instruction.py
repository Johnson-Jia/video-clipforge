"""R-G-016 创作元指令/制作术语泄露 gate 测试（确定性硬拦截）。

照抄 test_cinematic.py:79-110 模式（tempfile + 内联写文件 + 调 check 函数断言）。
覆盖：合规通过 / 边界（文件缺失·空文件）不误报 / 6 词各一违规 / 今日真实事故文案端到端拦截。
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from engine.gate import check_no_meta_instruction


class TestCheckNoMetaInstruction(unittest.TestCase):
    """R-G-016: narration 含制作术语 → HARD 失败；干净/缺失 → 通过。"""

    def _assert_blocked(self, text: str, expected_term: str):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            (td / "narration.txt").write_text(text, encoding="utf-8")
            ok, msg = check_no_meta_instruction(td, {"files": ["narration.txt"]})
            self.assertFalse(ok, f"应拦截含'{expected_term}'的文案")
            self.assertIn("R-G-016", msg)
            self.assertIn(expected_term, msg)

    def test_clean_narration_passes(self):
        """内容化表达（无制作术语）→ 通过。"""
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            (td / "narration.txt").write_text(
                "断网也能群聊，居然做到了。还有两个上榜的——buzz 单日涨两千四，"
                "今天的榜首；Pumpkin 用 Rust 重写游戏服务器，自建不卡。",
                encoding="utf-8")
            ok, msg = check_no_meta_instruction(td, {"files": ["narration.txt"]})
            self.assertTrue(ok)

    def test_missing_file_passes(self):
        """文件不存在 → 通过（不误报，参照 check_no_app_name 边界）。"""
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            ok, msg = check_no_meta_instruction(Path(td), {"files": ["narration.txt"]})
            self.assertTrue(ok)

    def test_empty_file_passes(self):
        """空 narration → 通过。"""
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            (td / "narration.txt").write_text("", encoding="utf-8")
            ok, msg = check_no_meta_instruction(td, {"files": ["narration.txt"]})
            self.assertTrue(ok)

    def test_term_yidaierguo_blocked(self):
        self._assert_blocked("老朋友一带而过——buzz 居榜首", "一带而过")

    def test_term_kuaisudaianguo_blocked(self):
        self._assert_blocked("这两个快速带过，buzz 和 Pumpkin。", "快速带过")

    def test_term_laopengyou_blocked(self):
        self._assert_blocked("老朋友 buzz 又上榜了。", "老朋友")

    def test_term_shumiankong_blocked(self):
        self._assert_blocked("熟面孔 pumpkin 还在榜。", "熟面孔")

    def test_term_xianfangyibian_blocked(self):
        self._assert_blocked("OAuth 先放一边，信息过载。", "先放一边")

    def test_term_xinxijiezhi_blocked(self):
        self._assert_blocked("信息节制，只讲一条路。", "信息节制")

    def test_today_real_narration_blocked(self):
        """2026-07-26 github 真实事故文案：必须同时拦截'老朋友'+'一带而过'。"""
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            (td / "narration.txt").write_text(
                "老朋友一带而过——buzz 单日两千四百星居榜首，Pumpkin 自建游戏服又涨星。"
                "这几个不靠云端的工具，你最想试哪个？",
                encoding="utf-8")
            ok, msg = check_no_meta_instruction(td, {"files": ["narration.txt"]})
            self.assertFalse(ok)
            self.assertIn("R-G-016", msg)
            self.assertIn("老朋友", msg)
            self.assertIn("一带而过", msg)


if __name__ == "__main__":
    unittest.main()
