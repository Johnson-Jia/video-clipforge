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


if __name__ == "__main__":
    unittest.main()
