"""ClipForge engine lint 扩展测试（方案乙：声明-生效一致性）。

覆盖三个新检查：
- lint_numbering: 主章节编号「§1 起」规范
- lint_rigor_redflags: red_flags 死声明（rigor≠STRICT 不注入）
- lint_safety_protection: apply_delta SAFETY 保护完备性
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from engine.lint import lint_numbering, lint_rigor_redflags, lint_safety_protection
from engine.lib.models import (
    SkillDefinition, SkillMeta, SkillIntent, SkillBoundary,
    SkillGate, SkillTrace, Rigor,
    Rule, RuleType, RuleClass, Severity,
)


class TestLintNumbering(unittest.TestCase):
    """主章节编号规范：§1 起、连续递增、禁多位小数、禁字母后缀。"""

    def test_flags_section_zero_start(self):
        """## 0. 起号违反「§1 起」规范。"""
        md = "# ClipForge\n\n## 0. 角色\n\n正文\n\n## 1. 双轨\n"
        violations = lint_numbering(md)
        self.assertTrue(len(violations) > 0, "从 0 起号应被检测")
        self.assertTrue(
            any("0" in v for v in violations),
            f"违规应指向 0 起号，实际: {violations}",
        )

    def test_passes_when_starting_from_one(self):
        """从 ## 1. 起号、连续递增 = 合规，无违规。"""
        md = "# T\n\n## 1. A\n\n## 2. B\n\n## 3. C\n"
        self.assertEqual(lint_numbering(md), [])


class TestLintRigorRedflags(unittest.TestCase):
    """red_flags 声明-生效一致性：inject.py:285 仅 STRICT 注入 red_flags。"""

    def _make_skill(self, rigor, red_flags=None):
        return SkillDefinition(
            meta=SkillMeta(id=f"skill.test-{rigor.value}", rigor=rigor),
            intent=SkillIntent(objective="测试"),
            boundary=SkillBoundary(),
            gate=SkillGate(),
            trace=SkillTrace(),
            guard_red_flags=red_flags or [],
        )

    def test_warns_redflags_missing_reality(self):
        """red_flags 缺 reality/trigger 键 → 报声明不完整（inject ALL 注入后，检查转向声明质量）。"""
        skill = self._make_skill(Rigor.STANDARD, [{"thought": "x"}])
        warnings = lint_rigor_redflags({"test": skill})
        self.assertTrue(len(warnings) > 0, "缺键的 red_flags 应报声明不完整")

    def test_no_warning_when_redflags_complete(self):
        """red_flags 含 thought+reality+trigger → 不报。"""
        skill = self._make_skill(Rigor.STANDARD,
                                 [{"thought": "x", "reality": "y", "trigger": "z"}])
        self.assertEqual(lint_rigor_redflags({"test": skill}), [])


class TestLintSafetyProtection(unittest.TestCase):
    """SAFETY 保护完备性：apply_delta 对 SAFETY 规则的 MODIFIED/REMOVED/DEPRECATED 必须保护。

    通过依赖注入 apply_func 测 lint 探测逻辑本身（不耦合真实 delta.py 当前状态）。
    """

    def test_reports_when_modified_leaks_safety(self):
        """apply 对 SAFETY 规则的 MODIFIED 不保护 → 应报 MODIFIED。"""
        def leaky(rules, delta):
            rs = list(rules)
            d = delta.get("delta", delta)
            if d.get("operation") == "MODIFIED":
                for r in rs:
                    for f, v in d.get("modified_fields", {}).items():
                        if hasattr(r, f):
                            setattr(r, f, v)
            return rs
        warnings = lint_safety_protection(apply_func=leaky)
        self.assertTrue(
            any("MODIFIED" in w for w in warnings),
            f"应报 MODIFIED 未保护，实际: {warnings}",
        )

    def test_no_warning_when_fully_protected(self):
        """apply 对所有 op 都不动 SAFETY 规则 → 无警告。"""
        def safe(rules, delta):
            return list(rules)
        self.assertEqual(lint_safety_protection(apply_func=safe), [])


if __name__ == "__main__":
    unittest.main()
