#!/usr/bin/env python
"""
rm_guard.py — Claude Code pre-tool-use hook.

Block `rm` commands that target protected project files.
Only intercepts direct rm calls from Claude Code Bash tool;
subprocess rm inside cleanup_project.sh is NOT affected.

Exit codes:
  0 = allow
  2 = block
"""

import sys
import json
import re
import os
import fnmatch

PROTECTED = {
    # Core outputs
    "final.mp4", "final_no_bgm.mp4",
    "output.mp4", "output_no_bgm.mp4",
    # Cover
    "cover.html", "cover.png", "cover_params.json",
    # Source (re-render required)
    "index.html", "design.md",
    "narration_segments.json", "narration.txt",
    "segment_durations.json",
    "sentence_timestamps.json", "phase_timings.json",
    # Delivery
    "douyin.md", "score_report.json",
    "content.md", "content_summary.md",
    # Audio (optional but costly to regenerate)
    "narration.mp3",
}


def parse_sub_commands(cmd_str):
    parts = re.split(r"[;&|]|\n", cmd_str)
    return [p.strip() for p in parts if p.strip()]


def extract_rm_targets(cmd):
    if not re.search(r"\brm\s", cmd):
        return []
    tokens = cmd.split()
    targets = []
    for token in tokens[1:]:
        if token.startswith("-"):
            continue
        if token.startswith(">") or token.startswith("2>") or token == "&":
            break
        targets.append(token)
    return targets


def matches_protected(target):
    basename = os.path.basename(target.rstrip("/\\"))

    if basename in PROTECTED:
        return basename

    if any(c in basename for c in "*?["):
        for p in PROTECTED:
            if fnmatch.fnmatch(p, basename):
                return p

    return None


def main():
    try:
        raw = sys.stdin.read()
        if not raw.strip():
            sys.exit(0)
        data = json.loads(raw)
    except Exception:
        sys.exit(0)

    tool_input = data.get("tool_input", data)
    command = tool_input.get("command", "")

    if not command or not re.search(r"\brm\s", command):
        sys.exit(0)

    blocked = []
    for sub_cmd in parse_sub_commands(command):
        for target in extract_rm_targets(sub_cmd):
            matched = matches_protected(target)
            if matched:
                blocked.append((target, matched))

    if blocked:
        lines = ["rm_guard: BLOCKED — protected file(s) detected"]
        for target, matched in blocked:
            lines.append(f"  {target}  ->  {matched}")
        lines.append("Use cleanup_project.sh to delete files.")
        print("\n".join(lines), file=sys.stderr)
        sys.exit(2)

    sys.exit(0)


if __name__ == "__main__":
    main()
