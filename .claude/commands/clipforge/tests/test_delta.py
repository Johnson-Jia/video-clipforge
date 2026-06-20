"""ClipForge delta.py 测试（方案乙配套：SAFETY 保护纵深补全）。

§5.3 承诺「SAFETY 规则不可被 Delta 移除」。REMOVED/DEPRECATED 已保护，
本测试锁定 MODIFIED 分支也必须保护 SAFETY 规则（防御纵深补全）。
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from engine.lib.delta import apply_delta_to_rules
from engine.lib.models import Rule, RuleType, RuleClass, Severity, Detection


def _safety_rule() -> Rule:
    return Rule(
        id="R-TEST-SAFETY", type=RuleType.FORBIDDEN_ACTION,
        pattern="p", positive="p", guardrail="p",
        detection=Detection(), severity=Severity.HARD, rule_class=RuleClass.SAFETY,
    )


class TestApplyDeltaSafetyProtection(unittest.TestCase):
    def test_modified_does_not_touch_safety_rule(self):
        """MODIFIED 操作不得修改 SAFETY 规则的字段（severity/pattern）。"""
        rule = _safety_rule()
        delta = {"delta": {"operation": "MODIFIED", "target_rule": "R-TEST-SAFETY",
                           "modified_fields": {"severity": "SOFT", "pattern": "leaked"}}}
        result = apply_delta_to_rules([rule], delta)
        found = [r for r in result if r.id == "R-TEST-SAFETY"]
        self.assertTrue(found, "SAFETY 规则不应被删除")
        self.assertEqual(found[0].severity, Severity.HARD, "SAFETY severity 不应被降级")
        self.assertEqual(found[0].pattern, "p", "SAFETY pattern 不应被改")


class TestDeltaCategory(unittest.TestCase):
    """delta category 隔离（缺口3）：分类专属 delta 不注入其他分类。

    R-S3-008（主轨 github 数据归纳，含'杀入/冲上/炸'）标 category=github 后，
    inject --category goldminer 应过滤掉它，goldminer 不再收主轨 hook 词。
    通用 delta（无 category）仍注入所有分类。
    """

    def test_create_delta_with_category(self):
        """create_delta 支持 category，写入 delta.category（分类专属 delta）。"""
        from engine.lib.delta import create_delta
        d = create_delta("ADDED", "test", 0.9, target_rule_id="R-X",
                         new_rule_raw={"id": "R-X", "type": "FORBIDDEN_ACTION",
                                       "pattern": "p", "positive": "p", "guardrail": "p"},
                         category="github")
        self.assertEqual(d["delta"]["category"], "github")

    def test_create_delta_no_category_is_generic(self):
        """无 category → 不写字段（通用 delta，所有分类注入）。"""
        from engine.lib.delta import create_delta
        d = create_delta("ADDED", "test", 0.9, target_rule_id="R-X",
                         new_rule_raw={"id": "R-X", "type": "FORBIDDEN_ACTION",
                                       "pattern": "p", "positive": "p", "guardrail": "p"})
        self.assertNotIn("category", d["delta"])

    def test_filter_keeps_matching_and_generic(self):
        """filter_deltas_by_category：保留 category 匹配 + 通用(None)。"""
        from engine.lib.delta import filter_deltas_by_category, create_delta
        github_d = create_delta("ADDED", "t", 0.9, target_rule_id="R-G",
            new_rule_raw={"id": "R-G", "type": "FORBIDDEN_ACTION", "pattern": "p", "positive": "p", "guardrail": "p"},
            category="github")
        generic_d = create_delta("ADDED", "t", 0.9, target_rule_id="R-X",
            new_rule_raw={"id": "R-X", "type": "FORBIDDEN_ACTION", "pattern": "p", "positive": "p", "guardrail": "p"})
        # goldminer 视角：generic 保留，github 过滤掉
        filtered = filter_deltas_by_category([github_d, generic_d], "goldminer")
        targets = [d["delta"]["target_rule"] for d in filtered]
        self.assertIn("R-X", targets)
        self.assertNotIn("R-G", targets)
        # github 视角：两个都保留（匹配 + 通用）
        self.assertEqual(len(filter_deltas_by_category([github_d, generic_d], "github")), 2)


class TestLoadDeltasStructureGuard(unittest.TestCase):
    """load_deltas 结构守卫（B7）：跳过非 delta 格式文件（feedback report 等）。"""

    def test_skips_non_delta_files(self):
        """load_deltas 只加载有 delta: 顶层键的文件，跳过 feedback report 等非 delta。"""
        import tempfile
        from engine.lib.delta import load_deltas
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            # 真 delta
            (td / "D-real.yaml").write_text(
                "delta:\n  id: D-real\n  operation: ADDED\n  target_rule: R-X\n",
                encoding="utf-8")
            # 非 delta（feedback report 格式，无 delta 键）
            (td / "feedback-20260605.yaml").write_text(
                "meta:\n  analysis_date: x\ncalibration_summary:\n  verdict: OVERESTIMATED\n",
                encoding="utf-8")
            deltas = load_deltas(td)
            ids = [d["delta"]["id"] for d in deltas]
            self.assertIn("D-real", ids)
            self.assertEqual(len(deltas), 1)  # feedback 被跳过，只 1 个真 delta


if __name__ == "__main__":
    unittest.main()
