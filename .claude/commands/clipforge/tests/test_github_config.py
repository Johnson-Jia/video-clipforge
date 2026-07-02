"""github 分类配置测试。

重点验证 bgm_style 选曲指引存在（2026-07-02 新增，纠正 LLM 偏向电子激昂）。
组件 A 为正文软引导（非 CONFIG 字段），用文档完整性测试。
"""
import unittest
from pathlib import Path

GITHUB_CFG = Path(__file__).parent.parent / "categories" / "github.md"


class TestGithubBgmStyle(unittest.TestCase):
    def setUp(self):
        self.content = GITHUB_CFG.read_text(encoding="utf-8")

    def test_bgm_style_section_exists(self):
        """audio 段含 ### bgm_style 子节。"""
        self.assertIn("### bgm_style", self.content)

    def test_preferred_styles_present(self):
        """✅ 首选低调分类必须列出（clean-corporate/warm-editorial/monochrome）。"""
        for tag in ["clean-corporate", "warm-editorial", "monochrome"]:
            self.assertIn(tag, self.content, f"github.md 缺少首选 BGM 分类 {tag}")

    def test_avoided_styles_present(self):
        """⛔ 避开激昂分类必须列出（bold-energetic/epic-trailer/epic-uplifting）。"""
        for tag in ["bold-energetic", "epic-trailer", "epic-uplifting"]:
            self.assertIn(tag, self.content, f"github.md 缺少避开 BGM 分类 {tag}")

    def test_neon_electric_restricted(self):
        """neon-electric 标注节制使用（⚠️，不连续两期）。"""
        self.assertIn("neon-electric", self.content)


if __name__ == "__main__":
    unittest.main()
