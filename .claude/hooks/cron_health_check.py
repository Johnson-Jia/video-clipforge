#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SessionStart hook: cron 任务完整性自愈 + 应跑未跑检测。

两层检测（2026-08-16 审计 P0-8 升级）：
1. 定义缺失：读 .claude/scheduled_tasks.json 对比**动态解析** memory/cron-schedules.md
   的期望清单（单源——旧版硬编码 EXPECTED 五条 cron 全部过时且漏 ai-wind），
   缺失则警告 → Claude 启动即用 durable:true 重建（自愈闭环）。
2. 应跑未跑：durable cron 只持久化定义、执行需活 REPL——会话不在场即静默错过
   （2026-08-16 6:06 daily-trending 漏跑根因）。按任务日程检查当日产物是否存在，
   过了宽限时段仍缺 → 警告提示补跑。

始终 exit 0，不阻塞会话启动。
"""
import json
import os
import re
import sys
import glob
from datetime import datetime, timedelta

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

# 兜底期望清单（memory 解析失败时用；以 memory/cron-schedules.md 为第一真相源）
FALLBACK_EXPECTED = [
    ("github-daily-trending", "6 6 * * *", "/github-daily-trending"),
    ("github-daily-ai", "30 7 * * 3,5,0", "/github-daily-ai"),
    ("github-weekly-trending", "30 3 * * 1", "/github-weekly-trending"),
    ("github-weekly-zhihu", "30 2 * * 1", "/github-weekly-zhihu"),
    ("evolve-daily", "37 23 * * *", "/evolve-daily"),
    ("goldminer", "5 5 * * 6", "/goldminer"),
]

# 应跑未跑检测：任务 → 当日产物路径模板（相对 workspace 根）。
# 日程（星期/宽限小时）从 memory cron 动态推导（_cron_to_schedule），不在此硬编码。
MISSED_RUN_CHECKS = {
    "/github-daily-trending": "workspace/{Y}/{m}/{d}/github-trending",
    "/github-daily-ai": "workspace/{Y}/{m}/{d}/ai-wind",
    "/goldminer": "workspace/{Y}/{m}/{d}/goldminer",
}
# evolve-daily 特例：产物是滚动日期报告，检查最新报告不早于 2 天前
EVOLVE_REPORT_GLOB = "workspace/sources/evolution-report-*.json"


def load_expected_from_memory():
    """动态解析 memory/cron-schedules.md 的任务表（单源），失败返回 None。"""
    roots = glob.glob(os.path.join(os.path.expanduser("~"), ".claude", "projects",
                                   "*video-clipforge*", "memory", "cron-schedules.md"))
    if not roots:
        return None
    try:
        text = open(roots[0], encoding="utf-8").read()
    except Exception:
        return None
    cron_re = re.compile(r"^[\d*/,-]+\s+[\d*/,-]+\s+[\d*/,-]+\s+[\d*/,-A-Za-z,/\-]+\s+[\d*/,-A-Za-z,/\-]+$")
    expected = []
    for line in text.splitlines():
        if not line.strip().startswith("|") or "任务" in line or "---" in line:
            continue
        tokens = re.findall(r"`([^`]+)`", line)
        cmd = next((t for t in tokens if t.startswith("/")), None)
        cron = next((t for t in tokens if cron_re.match(t)), None)
        keyword = next((t for t in tokens if t != cmd and t != cron), cmd.strip("/") if cmd else "?")
        if cmd and cron:
            expected.append((keyword, cron, cmd))
    return expected or None


def _cron_to_schedule(cron_expr):
    """cron 表达式 → (宽限起始小时, 生效星期集合或 None)。

    星期映射：cron DOW 0=周日..6=周六 → Python weekday 0=周一..6=周日（(d+6)%7）。
    宽限小时 = cron 小时 + 1（给管线一个完整小时的执行窗口再判漏跑）。
    无法解析时返回 (None, None) 表示跳过该任务的漏跑检测。
    """
    try:
        parts = cron_expr.split()
        hour = int(parts[1])
        dow = parts[4]
        weekdays = None
        if dow != "*":
            days = set()
            for tok in dow.split(","):
                if "-" in tok:
                    a, b = tok.split("-")
                    days.update(range(int(a), int(b) + 1))
                else:
                    days.add(int(tok))
            weekdays = {(d + 6) % 7 for d in days}
        return hour + 1, weekdays
    except Exception:
        return None, None


def check_missed_runs(project, now, expected):
    """应跑未跑：过了宽限小时当日产物仍缺 → 警告。

    日程（星期/小时）从 memory 解析的 cron 动态推导——memory 改排期后漏跑检测
    自动跟随，不再硬编码副本（对抗审查 2026-08-16 M3）。
    """
    warns = []
    y, m, d = now.strftime("%Y"), now.strftime("%m"), now.strftime("%d")
    cron_by_cmd = {cmd: cron for _, cron, cmd in expected}
    for cmd, tpl in MISSED_RUN_CHECKS.items():
        after_hour, weekdays = _cron_to_schedule(cron_by_cmd.get(cmd, ""))
        if after_hour is None:
            continue  # 无 cron 可推导（memory 缺失且无兜底匹配），跳过
        if weekdays is not None and now.weekday() not in weekdays:
            continue
        if now.hour < after_hour:
            continue
        artifact = os.path.join(project, tpl.format(Y=y, m=m, d=d))
        if not os.path.exists(artifact):
            warns.append(f"   - {cmd}：今日（{y}-{m}-{d}）已过 {after_hour}:00 但无产物 {artifact}")
    # evolve-daily：最新报告 > 2 天前
    reports = glob.glob(os.path.join(project, EVOLVE_REPORT_GLOB))
    if reports:
        newest = max(os.path.getmtime(r) for r in reports)
        if datetime.fromtimestamp(newest) < now - timedelta(days=2):
            warns.append(f"   - /evolve-daily：最新 evolution-report 超过 2 天未更新（durable cron 需活会话，可能连续漏跑）")
    return warns


def main() -> int:
    project = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    tasks_file = os.path.join(project, ".claude", "scheduled_tasks.json")

    expected = load_expected_from_memory() or FALLBACK_EXPECTED

    existing = set()
    if os.path.exists(tasks_file):
        try:
            with open(tasks_file, encoding="utf-8") as f:
                data = json.load(f)
            for t in data.get("tasks", []):
                existing.add(t.get("prompt", "").strip())
        except Exception as e:
            print("⚠️ [cron 自愈] scheduled_tasks.json 读取失败: %s" % e)
            existing = None  # 无法判定，跳过定义检查但继续漏跑检查

    if existing is not None:
        missing = [(k, cron, cmd) for k, cron, cmd in expected if cmd not in existing]
        if missing:
            print("⚠️ [cron 自愈] 检测到 %d 个定时任务缺失（对 memory/cron-schedules.md 单源）：" % len(missing))
            for k, cron, cmd in missing:
                print("   - %-26s cron '%-14s' → CronCreate(prompt='%s', recurring=true, durable=true)"
                      % (k, cron, cmd))
            print("   立即用 durable=true 重建以上任务。")

    missed = check_missed_runs(project, datetime.now(), expected)
    if missed:
        print("⚠️ [cron 自愈] 应跑未跑（durable cron 需活会话触发，错过窗口即静默跳过）：")
        for w in missed:
            print(w)
        print("   补救：手动调用对应 /命令 立即执行本期（若当日已按指引决策跳过——如 pool 枯竭——可忽略本告警）；")
        print("   根治清晨空窗见审计 P0-8（headless 定时拉起）。")

    return 0


if __name__ == "__main__":
    sys.exit(main())
