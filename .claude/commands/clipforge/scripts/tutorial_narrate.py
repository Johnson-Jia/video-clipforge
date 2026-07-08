#!/usr/bin/env python3
"""tutorial_narrate.py — PPT notes 全自动配音 + 录屏对齐合成（tutorial A 方案自动化）。

读 ppt-master project 的 notes/*.md（每页旁白），edge-tts 每页合成 mp3 + ffprobe 取时长，
按各页时长驱动 screencast per-page 录屏（每页停留 = 该页旁白时长，视觉与旁白对齐），
ffmpeg 合成视频 + 拼接旁白 → 含配音的主体片段 mp4。

用法:
  python scripts/tutorial_narrate.py \
    --notes-dir "D:/AI-Agent/github-analyze/ppt-master/projects/<project>/notes" \
    --viewer-url "file:///D:/AI-Agent/github-analyze/ppt-master/viewer.html?project=<name>" \
    --output "workspace/.../screencast-e01-main-narrated.mp4" \
    --voice zh-CN-YunjianNeural --rate +0%

依赖: edge-tts（pip install edge-tts）+ ffmpeg + screencast.py（同目录）
"""
from __future__ import annotations
import argparse
import asyncio
import re
import subprocess
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


def get_duration(audio_path: Path) -> float:
    """ffprobe 取音频时长（秒）。"""
    out = subprocess.check_output([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", str(audio_path)
    ]).decode().strip()
    return float(out)


async def tts_one(text: str, out_mp3: Path, voice: str, rate: str) -> None:
    """edge-tts 单段合成。"""
    import edge_tts
    comm = edge_tts.Communicate(text, voice, rate=rate)
    await comm.save(str(out_mp3))


async def main() -> None:
    ap = argparse.ArgumentParser(description="PPT notes 全自动配音 + 录屏对齐合成")
    ap.add_argument("--notes-dir", required=True, help="ppt-master project notes/ 目录")
    ap.add_argument("--viewer-url", required=True, help="viewer.html?project=<name> URL")
    ap.add_argument("--output", required=True, help="输出 mp4（含配音）")
    ap.add_argument("--voice", default="zh-CN-YunjianNeural", help="edge-tts 音色（tutorial 默认 YunjianNeural +0%）")
    ap.add_argument("--rate", default="+0%", help="语速（教程类 +0%）")
    ap.add_argument("--width", type=int, default=1920)
    ap.add_argument("--height", type=int, default=1080)
    args = ap.parse_args()

    notes_dir = Path(args.notes_dir)
    notes = sorted([f for f in notes_dir.glob("*.md") if f.name != "total.md"])
    if not notes:
        print(f"[FAIL] notes 目录无 .md: {notes_dir}", file=sys.stderr)
        sys.exit(1)
    print(f"=== notes: {len(notes)} 页 ===")

    out_dir = Path(args.output).resolve().parent / "narration_pages"
    out_dir.mkdir(parents=True, exist_ok=True)

    # 1. TTS 每页 → mp3 + 时长
    durations: list[float] = []
    for i, note in enumerate(notes, 1):
        text = re.sub(r"\s+", " ", note.read_text(encoding="utf-8").strip())
        mp3 = out_dir / f"{i:02d}.mp3"
        print(f"  TTS {i:02d}/{len(notes)} {note.name} ({len(text)}字)")
        await tts_one(text, mp3, args.voice, args.rate)
        dur = get_duration(mp3)
        durations.append(dur)
        print(f"    → {mp3.name} {dur:.1f}s")

    total = sum(durations)
    print(f"=== 旁白总时长 {total:.1f}s（{len(notes)} 页）===")

    # 2. screencast per-page actions: wait:页1,next:1,wait:页2,next:1,...,wait:页N
    parts = []
    for i, dur in enumerate(durations):
        parts.append(f"wait:{dur:.1f}")
        if i < len(durations) - 1:
            parts.append("next:1")
    actions = ",".join(parts)

    # 3. screencast 录屏（每页停留 = 旁白时长，next:1 翻页）
    video_tmp = Path(args.output).resolve().parent / ".narrate_video_tmp.mp4"
    print(f"=== screencast 录屏（per-page 停留=旁白时长）===")
    screencast_py = Path(__file__).resolve().parent / "screencast.py"
    cmd = [
        sys.executable, str(screencast_py),
        "--url", args.viewer_url,
        "--output", str(video_tmp),
        "--duration", str(int(total) + 5),  # 补足缓冲
        "--width", str(args.width),
        "--height", str(args.height),
        "--actions", actions,
    ]
    r = subprocess.run(cmd)
    if r.returncode != 0:
        print("[FAIL] screencast 录屏失败", file=sys.stderr)
        sys.exit(1)

    # 4. 拼接旁白 mp3 → narration.wav（48kHz mono，跟视频对齐）
    concat_list = out_dir / "concat.txt"
    concat_list.write_text("\n".join(f"file '{i:02d}.mp3'" for i in range(1, len(notes) + 1)), encoding="utf-8")
    narration_wav = out_dir / "narration.wav"
    subprocess.run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_list),
        "-ac", "1", "-ar", "48000", str(narration_wav)
    ], check=True, capture_output=True)

    # 5. 合成：视频 + 旁白 → 输出
    subprocess.run([
        "ffmpeg", "-y", "-i", str(video_tmp), "-i", str(narration_wav),
        "-c:v", "copy", "-c:a", "aac", "-shortest", str(args.output)
    ], check=True, capture_output=True)

    video_tmp.unlink(missing_ok=True)
    final_dur = get_duration(Path(args.output))
    print(f"[OK] {args.output}（视频 + {len(notes)} 页配音，{final_dur:.1f}s）")


if __name__ == "__main__":
    asyncio.run(main())
