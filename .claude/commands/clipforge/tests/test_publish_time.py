"""发布时间段分析 TDD 测试。

覆盖两类改动：
1. engine.publish_time 纯函数（小时提取 / 5 桶分桶 / 星期推导 / 多平台聚合）
2. collect_performance parse_*_date 保留时分（修复 regex 主动丢弃时分的 bug）

设计原则：纯逻辑全部放 engine/publish_time.py（易测，engine 是包）；
parse_*_date 留在 collect_performance（调用处所在），改 regex 保时分。
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from engine.publish_time import (  # noqa: E402
    extract_hour,
    hour_to_bucket,
    weekday_of,
    aggregate_publish_time,
    analyze_publish_time,
    build_publish_advice,
    render_publish_note,
)
from scripts.collect_performance import (  # noqa: E402
    parse_bilibili_date,
    parse_xhs_date,
    parse_toutiao_date,
)


class TestParseDatesKeepTime(unittest.TestCase):
    """parse_*_date 必须保留时分（修复 regex 主动丢弃时分的 bug）。

    向后兼容铁律：结果 [:10] 仍为 'YYYY-MM-DD'——collect 的匹配/路径逻辑
    (collect_performance.py:668/686/724) 依赖 published_at[:10] 取日期。
    """

    def test_bilibili_keeps_hhmm(self):
        self.assertEqual(parse_bilibili_date("2026年05月29日 12:40:34"), "2026-05-29 12:40")

    def test_bilibili_no_time_falls_back_to_date(self):
        self.assertEqual(parse_bilibili_date("2026年05月29日"), "2026-05-29")

    def test_bilibili_backcompat_date_prefix(self):
        self.assertEqual(parse_bilibili_date("2026年05月29日 12:40:34")[:10], "2026-05-29")

    def test_xhs_keeps_hhmm(self):
        self.assertEqual(parse_xhs_date("2026年05月19日15时39分28秒"), "2026-05-19 15:39")

    def test_xhs_no_time_falls_back_to_date(self):
        self.assertEqual(parse_xhs_date("2026年05月19日"), "2026-05-19")

    def test_toutiao_keeps_hhmm(self):
        self.assertEqual(parse_toutiao_date("2026-06-10 12:34"), "2026-06-10 12:34")

    def test_toutiao_no_time_falls_back_to_date(self):
        self.assertEqual(parse_toutiao_date("2026/6/10"), "2026-06-10")


class TestHourToBucket(unittest.TestCase):
    """小时 → 时段桶（5 桶，对齐短视频流量曲线）。"""

    def test_early_morning_6_to_10(self):
        self.assertEqual(hour_to_bucket(6), "early_morning")
        self.assertEqual(hour_to_bucket(10), "early_morning")

    def test_midday_11_to_14(self):
        self.assertEqual(hour_to_bucket(11), "midday")
        self.assertEqual(hour_to_bucket(14), "midday")

    def test_afternoon_15_to_18(self):
        self.assertEqual(hour_to_bucket(15), "afternoon")
        self.assertEqual(hour_to_bucket(18), "afternoon")

    def test_evening_19_to_23(self):
        """黄金时段。"""
        self.assertEqual(hour_to_bucket(19), "evening")
        self.assertEqual(hour_to_bucket(23), "evening")

    def test_late_night_0_to_5(self):
        self.assertEqual(hour_to_bucket(0), "late_night")
        self.assertEqual(hour_to_bucket(5), "late_night")


class TestExtractHour(unittest.TestCase):
    """从 published_at 提取小时；无时分返回 None。"""

    def test_with_hhmm(self):
        self.assertEqual(extract_hour("2026-05-29 12:40"), 12)

    def test_with_hhmmss(self):
        self.assertEqual(extract_hour("2026-05-29 12:40:34"), 12)

    def test_date_only_returns_none(self):
        self.assertIsNone(extract_hour("2026-05-29"))

    def test_none_input(self):
        self.assertIsNone(extract_hour(None))


class TestWeekdayOf(unittest.TestCase):
    """从 published_at 推星期（中文）；只有日期也能用（视频号覆盖）。"""

    def test_known_friday(self):
        # 2026-05-29 是周五
        self.assertEqual(weekday_of("2026-05-29 12:40"), "周五")

    def test_date_only(self):
        self.assertEqual(weekday_of("2026-05-29"), "周五")

    def test_none_returns_unknown(self):
        self.assertEqual(weekday_of(None), "未知")


class TestAggregatePublishTime(unittest.TestCase):
    """多平台聚合：取首发放时间（最早 published_at）；无时分的平台不参与小时。"""

    def test_earliest_across_platforms(self):
        plats = {
            "douyin": {"published_at": "2026-05-29 20:30"},
            "bilibili": {"published_at": "2026-05-29 12:40"},
        }
        agg = aggregate_publish_time(plats)
        self.assertEqual(agg["publish_hour"], 12)

    def test_skips_platform_without_time(self):
        plats = {
            "wechat_video": {"published_at": "2026-05-29"},  # 无时分
            "douyin": {"published_at": "2026-05-29 20:30"},
        }
        agg = aggregate_publish_time(plats)
        self.assertEqual(agg["publish_hour"], 20)

    def test_all_missing_time_hour_none(self):
        plats = {"wechat_video": {"published_at": "2026-05-29"}}
        agg = aggregate_publish_time(plats)
        self.assertIsNone(agg["publish_hour"])

    def test_weekday_available_even_without_time(self):
        plats = {"wechat_video": {"published_at": "2026-05-29"}}
        agg = aggregate_publish_time(plats)
        self.assertEqual(agg["publish_weekday"], "周五")


class TestAnalyzePublishTime(unittest.TestCase):
    """发布时段 + 星期维度分析（reach_composite 受众广度信号）。"""

    def test_hour_bucket_aggregation_n_ge_3(self):
        """同桶 ≥3 条才报告；evening(19-23) 三条平均。"""
        projects = [
            {"publish_hour": 20, "publish_weekday": "周五", "reach_composite": 0.8},
            {"publish_hour": 21, "publish_weekday": "周五", "reach_composite": 0.6},
            {"publish_hour": 19, "publish_weekday": "周六", "reach_composite": 0.7},
            {"publish_hour": 8, "publish_weekday": "周一", "reach_composite": 0.3},
            {"publish_hour": None, "publish_weekday": "周二", "reach_composite": 0.5},
        ]
        result = analyze_publish_time(projects)
        self.assertEqual(result["hour_bucket"]["evening"]["count"], 3)
        self.assertAlmostEqual(result["hour_bucket"]["evening"]["avg_reach"], 0.7, places=2)
        # early_morning 仅 1 条 <3，不报告
        self.assertNotIn("early_morning", result["hour_bucket"])
        self.assertEqual(result["best_hour_bucket"], "evening")
        # 4/5 含小时（排除 None）
        self.assertEqual(result["coverage_hour"], "4/5")

    def test_skip_bucket_with_less_than_3(self):
        """N<3 桶省略（避免幸存者偏差）。"""
        projects = [{"publish_hour": 20, "publish_weekday": "周五", "reach_composite": 0.8}]
        result = analyze_publish_time(projects)
        self.assertEqual(result["hour_bucket"], {})
        self.assertIsNone(result["best_hour_bucket"])

    def test_weekday_works_without_hour(self):
        """无小时也能算星期（视频号覆盖）。"""
        projects = [
            {"publish_hour": None, "publish_weekday": "周六", "reach_composite": 0.7},
            {"publish_hour": None, "publish_weekday": "周六", "reach_composite": 0.6},
            {"publish_hour": None, "publish_weekday": "周六", "reach_composite": 0.8},
        ]
        result = analyze_publish_time(projects)
        self.assertEqual(result["weekday"]["周六"]["count"], 3)
        self.assertEqual(result["hour_bucket"], {})


class TestBuildPublishAdvice(unittest.TestCase):
    """发布时机建议（advice.json 内容生成）。"""

    def test_high_confidence_above_market_enough_samples(self):
        analysis = {
            "best_hour_bucket": "evening",
            "hour_bucket": {"evening": {"count": 6, "avg_reach": 0.7}},
            "coverage_hour": "10/12",
        }
        advice = build_publish_advice(analysis, market_avg=0.5)
        self.assertEqual(advice["best_hour_bucket"], "evening")
        self.assertEqual(advice["confidence"], "high")

    def test_medium_confidence_above_market_min_samples(self):
        analysis = {
            "best_hour_bucket": "evening",
            "hour_bucket": {"evening": {"count": 4, "avg_reach": 0.7}},
            "coverage_hour": "8/12",
        }
        advice = build_publish_advice(analysis, market_avg=0.5)
        self.assertEqual(advice["confidence"], "medium")

    def test_low_confidence_when_insufficient(self):
        analysis = {"best_hour_bucket": None, "hour_bucket": {}, "coverage_hour": "2/12"}
        advice = build_publish_advice(analysis, market_avg=0.5)
        self.assertIsNone(advice["best_hour_bucket"])
        self.assertEqual(advice["confidence"], "low")


class TestRenderPublishNote(unittest.TestCase):
    """advice → publish_note.md 内容渲染（交付物发布时机提示）。"""

    def test_high_confidence_shows_recommendation(self):
        advice = {
            "best_hour_bucket": "evening",
            "confidence": "high",
            "best_avg_reach": 0.7,
            "market_avg_reach": 0.5,
            "coverage_hour": "10/12",
        }
        note = render_publish_note(advice)
        self.assertIn("晚间", note)            # 桶中文
        self.assertIn("high", note)            # 置信度
        self.assertIn("⭐", note)              # high 标记
        self.assertIn("关联非因果", note)       # 免责提醒

    def test_low_confidence_no_best_shows_insufficient(self):
        advice = {"best_hour_bucket": None, "confidence": "low"}
        note = render_publish_note(advice)
        self.assertIn("样本不足", note)

    def test_none_advice_shows_insufficient(self):
        note = render_publish_note(None)
        self.assertIn("样本不足", note)


if __name__ == "__main__":
    unittest.main()
