"""loot-drop.io 详情页解析 TDD 测试。

parse_failure_detail 从 SSR HTML 提取失败案例完整字段：
公司名/融资/overview/6维分析/重建点子/相关失败。
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from scripts.lootdrop_parser import parse_failure_detail  # noqa: E402

FIXTURE = Path(__file__).parent / "testdata" / "lootdrop_plenty.html"


def _load():
    return FIXTURE.read_text(encoding="utf-8")


class TestParseFailureDetail(unittest.TestCase):
    def setUp(self):
        self.r = parse_failure_detail(
            _load(), url="https://www.loot-drop.io/startup/2563-plenty-unlimited")

    def test_name_from_title(self):
        self.assertEqual(self.r["name"], "Plenty Unlimited")

    def test_funding_extracted(self):
        self.assertIn("944", self.r["funding"])  # $944M

    def test_overview_present(self):
        self.assertIn("vertical farming", self.r["overview"].lower())

    def test_failure_analysis_section(self):
        self.assertIn("unit economics", self.r["failure_analysis"].lower())

    def test_failure_analysis_full_not_summary(self):
        """data-full-text 全文（非 card-text 摘要，防回退）。Plenty 全文 > 500 字。"""
        self.assertGreater(len(self.r["failure_analysis"]), 500)

    def test_startup_learnings_section(self):
        self.assertIn("unit economics", self.r["startup_learnings"].lower())

    def test_pivot_concept_nonempty(self):
        # 重建点子是淘金核心，必须提取到实质内容
        self.assertGreater(len(self.r["pivot_concept"]), 50)

    def test_related_names_and_urls(self):
        names = [r["name"] for r in self.r["related"]]
        self.assertIn("K-Scale Labs", names)
        self.assertTrue(self.r["related"][0]["url"].startswith("/startup/"))

    def test_url_preserved(self):
        self.assertIn("plenty-unlimited", self.r["url"])


class TestInferRegion(unittest.TestCase):
    """地区推断（中国公司筛选依赖）。"""

    def test_china_keyword(self):
        from scripts.lootdrop_parser import infer_region
        self.assertEqual(infer_region("China's largest K-12 platform, based in Beijing"), "中国")

    def test_usa_keyword(self):
        from scripts.lootdrop_parser import infer_region
        self.assertEqual(infer_region("based in San Francisco, Walmart partnership"), "美国")

    def test_unknown(self):
        from scripts.lootdrop_parser import infer_region
        self.assertEqual(infer_region("a vertical farming company"), "其他")


if __name__ == "__main__":
    unittest.main()
