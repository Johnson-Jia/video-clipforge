# Getting Started

## Prerequisites

### Required

| Dependency | Version | Purpose | Install |
|------------|---------|---------|---------|
| [Claude Code](https://docs.anthropic.com/en/docs/claude-code) | latest | AI agent runtime | `npm install -g @anthropic-ai/claude-code` |
| [Node.js](https://nodejs.org/) | >= 22 | HyperFrames CLI | `winget install OpenJS.NodeJS.LTS` or `brew install node@22` |
| [FFmpeg](https://ffmpeg.org/) | any | Audio/video processing | `winget install Gyan.FFmpeg` or `brew install ffmpeg` |
| [edge-tts](https://github.com/rany2/edge-tts) | any | Chinese TTS narration | `pip install edge-tts` |
| [yt-dlp](https://github.com/yt-dlp/yt-dlp) | any | YouTube royalty-free music | `pip install yt-dlp` |

### Auto-installed (by ClipForge)

| Dependency | Purpose |
|------------|---------|
| [HyperFrames](https://github.com/heygen-com/hyperframes) | HTML-to-video rendering with native audio mixing |

### Optional

| Dependency | Purpose | Install |
|------------|---------|---------|
| GitHub CLI (`gh`) | GitHub project real-time data | `winget install GitHub.cli` |
| jq | Precise volume normalization | `winget install jqlang.jq` |

## Setup

```bash
# 1. Clone the repository
git clone https://github.com/Johnson-Jia/video-clipforge.git
cd video-clipforge

# 2. (Optional) Run the one-shot installer
bash install.sh

# 3. Start Claude Code
claude
```

ClipForge skills are loaded automatically from `.claude/commands/`.

## Your First Video

### Interactive Mode

In Claude Code, type:

```
/clipforge Make a short video about the Rust programming language
```

Claude will guide you through each stage with confirmation:
1. **env-check** — Verifies dependencies are installed
2. **content** — Gathers information about Rust
3. **design** — Derives visual style (dark tech theme for a programming topic)
4. **narration** — Writes scene-by-scene narration script
5. **audio** — Generates TTS narration + selects BGM
6. **video** — Renders the HTML to MP4
7. **delivery** — Creates cover + Douyin copywriting
8. **cleanup** — Removes intermediate files

The final video lands at `workspace/YYYY/MM/DD/your-project/final.mp4`.

### From a URL

```
/clipforge Make a video from this article: https://example.com/article
```

### From a File

```
/clipforge Make a video from this PDF: /path/to/document.pdf
```

## Cron Automation

ClipForge includes three pre-built cron commands for automated content:

### Daily GitHub Trending

```
/github-daily-trending
```

Fetches today's GitHub trending projects, generates a 25-45s video. Runs fully automated with triple-source data validation.

### Weekly GitHub Summary

```
/github-weekly-trending
```

Summarizes the week's top GitHub projects, grouped by category (AI/ML, frontend, DevOps, etc.). Generates a 45-60s video.

### Weekly Zhihu Article

```
/github-weekly-zhihu
```

Generates a Zhihu article about the week's GitHub highlights (text content, not video).

### Setting Up Cron

In Claude Code, schedule the daily task:

```
/clipforge Schedule github-daily-trending to run daily at <your-preferred-time>
```

The cron files include self-renewal logic — they automatically extend their schedule before expiring.

## Video Modes

ClipForge automatically selects the mode based on content:

| Mode | Trigger | Duration | Scenes |
|------|---------|----------|--------|
| Standard | Multiple topics / quick roundup | 25-55s | 6-8 |
| Deep dive | Single topic detailed analysis | 45-60s | 7-8 |
| Movie commentary | Scenes contain `video_clip` type | 3-5min | unlimited |

You can override by specifying in your prompt: "make a deep-dive video about X".

## Content Categories

ClipForge supports multiple content categories via pluggable category profiles. Each category defines content-specific rules (data sources, visual style, TTS voice, hashtags) that override the generic stage defaults.

| Category | Description | Cron Command |
|----------|-------------|-------------|
| GitHub | Open-source project trending & analysis | `/github-daily-trending`, `/github-weekly-trending` |
| Comics | (Coming soon) | — |
| Novels | (Coming soon) | — |

Category configs live in `.claude/commands/clipforge/categories/`. When a category is active, each stage reads the config to load overrides (e.g., GitHub category sets YunjianNeural voice, dark tech style, and `#GitHub热门` hashtags). Without a category, all stages use their built-in defaults.

To add a new category, see `CONTRIBUTING.md` → "Add a New Category".

## Output Structure

Videos are organized by date under `workspace/`:

```
workspace/
└── 2026/
    └── 05/
        └── 22/
            └── my-project/
                ├── final.mp4           # Final video (with BGM)
                ├── final_no_bgm.mp4    # Final video (narration only)
                ├── cover.png           # Cover image
                ├── douyin.md           # 3 sets of Douyin copywriting
                ├── design.md           # Visual style spec
                ├── narration.txt       # Full narration text
                └── narration_segments.json  # Scene definitions
```

After cleanup, each project stays under 30MB.

## Resuming Interrupted Runs

ClipForge uses file-based state detection — an artifact is complete when its output files exist on disk. If a run is interrupted (timeout, error, or manual stop):

1. Re-run `/clipforge` with the same project directory
2. Completed stages are detected automatically via file existence and skipped
3. Execution resumes from the first incomplete stage

To force re-run a specific stage, delete its output files first. For example, to re-render the video:

```bash
rm workspace/2026/05/22/my-project/output.mp4 workspace/2026/05/22/my-project/output_no_bgm.mp4
```

Then re-run `/clipforge`.

For error recovery guidance by stage, see the [Architecture Guide](architecture.md) → "Error Recovery" section.

## Troubleshooting

### "HyperFrames not found"

Run `npx skills add heygen-com/hyperframes` in the project directory.

### "edge-tts failed"

Ensure edge-tts is installed: `pip install edge-tts`. Test with `edge-tts --text "hello" --write-media test.mp3`.

### "Video has no audio"

Check that `narration.mp3` and `bgm.wav` exist in the project directory. If they're missing, re-run the audio stage.

### "Rendering timeout"

Large videos (60s+) may need increased timeout. The stage files handle this automatically for standard durations.

### "BGM too loud/quiet"

BGM volume is auto-analyzed based on narration loudness. If the result isn't right, you can manually adjust `meta.bgm_volume` in `segment_durations.json` and re-run the video stage.

### "Stage failed mid-pipeline"

Re-run `/clipforge` — completed stages are skipped automatically. If the error persists, check the specific stage's output files and delete them to force re-execution.

### "yt-dlp download fails"

yt-dlp is used for BGM download. If it fails, the audio stage falls back to Pixabay search. Ensure yt-dlp is up to date: `pip install -U yt-dlp`.

### "Chinese characters in path cause issues"

Keep the project path in English only. `workspace/` directories use `YYYY/MM/DD/project-name/` format without Chinese characters.
