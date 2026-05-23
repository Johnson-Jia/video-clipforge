<div align="center">

<img src="docs/images/logo.png" width="100%" alt="ClipForge Logo">

# ClipForge

**AI-powered general-purpose short video production pipeline for Claude Code**

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Claude Code Skills](https://img.shields.io/badge/Claude%20Code-Skills-orange)](https://docs.anthropic.com/en/docs/claude-code/skills)

[English](#overview) · [中文](README.md)

From any content to Douyin-ready vertical video — fully automated.

Powered by [HyperFrames](https://github.com/heygen-com/hyperframes) for native audio mixing and MP4 rendering.

</div>

---

## Why ClipForge

Most AI video tools are GUI apps with fixed templates. ClipForge takes a different approach: it's a **code-native pipeline** built on Claude Code's skill system. Every stage is a self-contained skill file with explicit inputs, outputs, and error recovery paths. The DAG dependency graph is defined once in `schema.yaml` and drives everything — SubAgent scheduling, state detection, and retry logic.

**The result:** You get a production-quality video pipeline that's auditable, extensible, and runs unattended on a cron schedule.

## Overview

ClipForge converts any content — text, URLs, PDFs, GitHub trending data, and more — into vertical short videos (1080x1920) with:

- **DAG-orchestrated 8-stage pipeline** — each stage is a self-contained skill with explicit inputs/outputs
- **Category system** — content-specific rules (data, style, voice, hashtags) via pluggable category profiles
- **Three video modes** — standard multi-topic (25-55s), deep-dive single topic (45-60s), movie commentary (3-5min)
- **Embedded audio** — narration and BGM embedded in HTML via `<audio>`, mixed natively by HyperFrames
- **Segment-precise A/V sync** — segmented TTS with per-segment duration tracking eliminates lip-sync drift
- **Cron automation** — daily/weekly content videos run unattended with self-renewing cron jobs
- **Auto-cleanup** — intermediate artifacts are deleted after delivery; each project stays under 30MB

### Stage Pipeline

| Stage | Artifact | Description |
|-------|----------|-------------|
| 0 | env-check | Dependency detection and auto-install |
| 1 | content | Content acquisition from text/file/URL/category data source |
| 2 | design | Visual style derivation (mood → palette → typography) |
| 3 | narration | Scene breakdown + narration script per segment |
| 4 | audio | Segmented TTS narration + BGM selection + volume analysis |
| 5 | assets | Visual asset preparation (optional, pure CSS/HTML) |
| 6 | video | HTML composition with `<audio>` + HyperFrames rendering |
| 7 | delivery | Cover generation + Douyin copywriting + final export |
| 8 | cleanup | Intermediate file removal |

The DAG is defined in [`schema.yaml`](.claude/commands/clipforge/schema.yaml) — artifact dependencies, conditional stages, optional stages, all in one place.

## Quick Start

```bash
# 1. Clone the repository
git clone https://github.com/Johnson-Jia/video-clipforge.git
cd video-clipforge

# 2. Start Claude Code (skills auto-load)
claude

# 3. Generate a video
/clipforge Make a video about this topic: ...
```

First run auto-detects and installs dependencies (HyperFrames).

**Prerequisites:** Node.js >= 22, FFmpeg, edge-tts, yt-dlp. See [Getting Started](docs/getting-started.md) for full setup.

## Usage

### Interactive Mode

```
/clipforge Generate a video from this article: https://...
```

Claude guides you through each stage with confirmation at every step.

### Cron Automation

| Task | Command | Description |
|------|---------|-------------|
| Daily trending | `/github-daily-trending` | Runs daily automatically |
| Weekly summary | `/github-weekly-trending` | Runs weekly automatically |
| Weekly article | `/github-weekly-zhihu` | Runs weekly automatically |

Fully automated: data collection (triple-source cross-validation) → video production → delivery → cleanup → cron self-renewal.

## Architecture

ClipForge follows three design principles:

1. **Schema is truth.** `schema.yaml` defines all artifacts, dependencies, and completion criteria. State detection uses file existence (glob patterns), no database.
2. **Skills are self-contained.** Each stage file (`stage0-env.md` through `stage7-delivery.md`) includes its own execution guide, anti-rationalization table, and red flags. No external context files needed.
3. **Delegate, don't rewrite.** HTML composition and rendering are handled by HyperFrames. Audio mixing is native to the renderer — no FFmpeg post-processing.

See [Architecture Guide](docs/architecture.md) for the full DAG semantics, SubAgent dispatch, and error recovery strategy.

## Design Philosophy

ClipForge is inspired by two open-source projects:

- **[OpenSpec](https://github.com/nicholasgriffintn/openspec)** — DAG-driven workflows where the schema is the single source of truth. Dependencies enable, not gate. Filesystem as database.
- **[Superpowers](https://github.com/nicholasgriffintn/superpowers)** — Anti-rationalization as a first-class concern. Each skill has explicit Red Flags and Common Rationalizations. Token budgets keep skills focused.

## Dependencies

### Auto-installed

| Dependency | Purpose |
|------------|---------|
| HyperFrames Skills | HTML-to-video rendering with native audio mixing |

### Manual install

| Dependency | Purpose | Install |
|------------|---------|---------|
| Node.js >= 22 | HyperFrames CLI | `winget install OpenJS.NodeJS.LTS` |
| FFmpeg | Audio/video processing | `winget install Gyan.FFmpeg` |
| edge-tts | Chinese TTS narration | `pip install edge-tts` |
| yt-dlp | YouTube royalty-free music | `pip install yt-dlp` |

## Extending ClipForge

- **New content source:** Add a cron file (like `github-daily-trending.md`) that fetches data and dispatches SubAgents
- **New category:** Create a config file in `categories/` defining category-specific rule overrides
- **New stage:** Add an artifact to `schema.yaml` and create a corresponding `stageN-xxx.md` skill file
- **New video mode:** Define mode rules in the stage files; the controller auto-selects based on content

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## Project Structure

```
clipforge/
├── CLAUDE.md                              # AI agent entry point
├── README.md                              # 中文说明（默认）
├── README_EN.md                           # English README
├── LICENSE                                # Apache 2.0
├── CONTRIBUTING.md                        # Contribution guidelines
├── docs/
│   ├── architecture.md                    # DAG + stage pipeline deep dive
│   └── getting-started.md                 # Setup and first video
├── .claude/commands/
│   ├── clipforge.md                       # Main controller
│   ├── github-daily-trending.md           # Daily cron
│   ├── github-weekly-trending.md          # Weekly cron
│   ├── github-weekly-zhihu.md             # Weekly article cron
│   └── clipforge/
│       ├── schema.yaml                    # Artifact DAG (single source of truth)
│       ├── categories/                    # Category profiles
│       │   ├── _category-schema.md        # Category config format spec
│       │   └── github.md                  # GitHub category (first category)
│       ├── stage0-env.md ... stage7-delivery.md   # Stage skill files
│       ├── _shared-rules.md               # Content norms
│       ├── _cleanup-rules.md              # File retention rules
│       ├── _cron-renew.md                 # Cron self-renewal
│       ├── _movie-clips.md                # Movie clip extraction (conditional)
│       └── _bgm-pixabay.md                # BGM download helper
│       ├── scripts/                       # Tool scripts
│       │   ├── github_trending.py         # GitHub Trending scraper
│       │   ├── generate_bgm.py            # MusicGen BGM generator
│       │   ├── merge_video_audio.sh       # Audio/video merge utility
│       │   └── quality_gate.sh            # Video quality gate
│       └── components/                    # Visual component library
│           ├── hero_card.html             # Hero card
│           └── ... (13 components total)
├── install.sh                             # One-shot dependency installer
└── workspace/                             # Output (gitignored)
```

## License

[Apache License 2.0](LICENSE)
