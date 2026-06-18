"""ClipForge inject 测试（项1：STANDARD 注入 red_flags 消除死声明）。

inject.py:285 原「仅 STRICT 注入 red_flags」→ STANDARD 也注入。
用真实 stage3-scenes（STANDARD + 2 red_flags）做集成验证。
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from engine.inject import generate_injection


class TestInjectRedflagsStandard(unittest.TestCase):
    def test_standard_skill_injects_red_flags(self):
        """STANDARD skill 的 guard.red_flags 应被注入（消除死声明）。"""
        injection = generate_injection("stage3-scenes")
        self.assertIn(
            "行为守卫", injection,
            "STANDARD skill 应注入 red_flags 表格（项1：消除死声明）",
        )

    def test_lite_skill_also_injects_red_flags(self):
        """LITE skill 的 red_flags 也注入（认知守卫对所有调度 LLM 普遍生效）。"""
        injection = generate_injection("stage0-env")
        self.assertIn(
            "行为守卫", injection,
            "LITE skill 也应注入 red_flags（red_flags 为 ALL 生效的基础设施）",
        )

    def test_redflags_table_includes_trigger_column(self):
        """red_flags 表格注入 trigger 列（与 lint 三键要求一致，无死字段）。"""
        injection = generate_injection("stage0-env")
        self.assertIn("触发场景", injection)        # 表格第三列 header
        self.assertIn("env_check.sh", injection)    # 第二条 trigger 内容


if __name__ == "__main__":
    unittest.main()
