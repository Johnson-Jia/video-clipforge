#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Stop hook: 会话 cwd 漂移检测 + 自动拉回项目根。

定时任务管线（github-daily-* / goldminer / evolve-daily 等）的脚本需要
cd 进 .claude/commands/clipforge 执行，任务结束后会话 shell 的 cwd 停留在
技能目录，下一条相对路径命令会误写误读（历史事故：CF_DIR/workspace 误建）。

本 hook 在主 agent 停止响应时触发（含每次定时任务执行完成）：
- cwd 已在项目根        → 静默放行（exit 0 无输出，零打扰）
- cwd 漂移              → decision:block + reason 指示 Claude cd 回项目根
- stop_hook_active=true  → 放行（已被拉回过一次仍漂移，防死循环）
- stdin 无 cwd / 无项目根 → 放行（检测条件不足时不干预）
"""
import json
import os
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")  # Windows 默认 GBK 会把中文 reason 输出成乱码
except Exception:
    pass


def _norm(p: str) -> str:
    """路径归一化：MSYS /d/foo → D:/foo，再统一大小写与分隔符供比较。"""
    if len(p) >= 3 and p[0] == "/" and p[2] == "/" and p[1].isalpha():
        p = p[1] + ":" + p[2:]
    try:
        return os.path.normcase(os.path.normpath(os.path.realpath(p)))
    except Exception:
        return os.path.normcase(os.path.normpath(p))


def main() -> None:
    try:
        data = json.load(sys.stdin)
    except Exception:
        return  # stdin 非 JSON：放行
    if data.get("stop_hook_active"):
        return  # 已因 Stop hook 拉回过一次：防死循环，放行
    cwd = str(data.get("cwd") or "")
    project = os.environ.get("CLAUDE_PROJECT_DIR") or ""
    if not cwd or not project:
        return  # 检测条件不足：放行
    if _norm(cwd) == _norm(project):
        return  # 已在项目根：静默放行
    # cwd 漂移 → 拉回（reason 会注入给 Claude）
    out = {
        "decision": "block",
        "reason": (
            f"shell 工作目录已漂移到 {cwd}（管线脚本 cd 所致）。"
            f"请执行 `cd \"{project}\"` 把会话工作目录切回项目根，"
            "确认后直接结束本轮回复，无需做其他事。"
        ),
    }
    print(json.dumps(out, ensure_ascii=False))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass  # 任何异常都放行，绝不阻塞会话停止
