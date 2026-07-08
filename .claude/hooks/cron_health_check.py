#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SessionStart hook: cron 任务完整性自愈检测。

读 .claude/scheduled_tasks.json 对比应有任务清单，缺失则输出警告。
警告 stdout 会被注入 Claude context → Claude 启动即看到 → 用 durable:true 重建。

根因防护：cron-renew 是 LLM 读 md 执行（非脚本），CronCreate 的 durable:true 全靠
手动传参，漏传 = session-only = 会话退出蒸发。本 hook 把"任务丢失"从事后发现
变成会话启动即报警，配合 Claude 重建形成自愈闭环。
"""
import json
import os
import sys

# stdout 强制 UTF-8（Windows 默认 GBK 致中文乱码）
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

# 应有任务清单（关键词, cron, prompt）。加新任务时同步更新此处 + memory/cron-schedules.md
EXPECTED = [
    ("github-daily-trending", "3 7 * * *", "/github-daily-trending"),
    ("github-weekly-trending", "7 8 * * 1", "/github-weekly-trending"),
    ("github-weekly-zhihu", "30 9 * * 1", "/github-weekly-zhihu"),
    ("evolve-daily", "37 23 * * *", "/evolve-daily"),
    ("goldminer", "3 5 * * 6", "/goldminer"),
]


def main() -> int:
    project = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    tasks_file = os.path.join(project, ".claude", "scheduled_tasks.json")

    existing = set()
    if os.path.exists(tasks_file):
        try:
            with open(tasks_file, encoding="utf-8") as f:
                data = json.load(f)
            for t in data.get("tasks", []):
                existing.add(t.get("prompt", "").strip())
        except Exception as e:
            print("⚠️ [cron 自愈] scheduled_tasks.json 读取失败: %s" % e)
            return 0  # 不阻塞会话启动

    missing = [(k, cron, cmd) for k, cron, cmd in EXPECTED if cmd not in existing]
    if not missing:
        return 0

    print("⚠️ [cron 自愈] 检测到 %d 个定时任务缺失（cron-renew 漏传 durable:true → "
          "session-only 随会话蒸发）：" % len(missing))
    for k, cron, cmd in missing:
        print("   - %-26s cron '%-12s' → CronCreate(prompt='%s', recurring=true, durable=true)"
              % (k, cron, cmd))
    print("   立即用 durable=true 重建以上任务（见 memory/cron-schedules.md）。")
    return 0  # 始终 exit 0，不阻塞会话启动


if __name__ == "__main__":
    sys.exit(main())
