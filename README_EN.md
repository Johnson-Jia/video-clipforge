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

### Why not just use HyperFrames directly?

[HyperFrames](https://github.com/heygen-com/hyperframes) is an excellent HTML-to-Video renderer, but it only solves the "last mile" — turning HTML into MP4. A complete short video still requires solving these problems:

| Problem | HyperFrames | What ClipForge adds on top |
|---------|-------------|---------------------------|
| **Where does content come from?** | Not involved | Stage 1 fetches from URL/PDF/GitHub/text; category system defines selection strategy per content type |
| **How to define visual style?** | Not involved | Stage 2 director's toolkit (5 must-answer questions + visual vocabulary) derives palette, typography, immersion mode from content's emotional core |
| **What to narrate?** | Not involved | Stage 3 scene breakdown + 6-beat emotional rhythm + segmented narration, each segment independently TTS'd with precise duration tracking |
| **How to sync audio?** | Native mixing, but no audio generation | Stage 4 segmented TTS → loudnorm normalization → BGM selection + 7-level volume table → frame-accurate A/V alignment |
| **How to write HTML?** | Renders what you give it | Stage 5-6 three-layer architecture (bg/content/fx) + 13 composable components + GSAP animation choreography + A/V gate validation |
| **How to adapt to different content?** | Not involved | Category system (`categories/`) gives each content type its own data source, voice, hashtag strategy — no code changes needed |
| **How to batch automate?** | Not involved | DAG orchestration + SubAgent batch dispatch + cron scheduling + auto-renewal — produces videos unattended daily |
| **How to recover from errors?** | Not involved | DAG-driven cascading rollback table — only rolls back to the minimum necessary stage |
| **Will disk fill up?** | Not involved | Auto-cleanup policy keeps each project under 30MB after delivery |

**In short:** HyperFrames is the rendering engine; ClipForge is the complete orchestration layer from content to final delivery. HyperFrames solves "how to turn HTML into video"; ClipForge solves "where does the HTML come from, what content goes in it, how is the style determined, how is audio synchronized, and how to produce at scale."

## Overview

ClipForge converts any content — text, URLs, PDFs, GitHub trending data, and more — into vertical short videos (1080x1920) with:

- **DAG-orchestrated pipeline** — each stage is a self-contained skill with explicit inputs/outputs
- **Category system** — content-specific rules (data, style, voice, hashtags) via pluggable category profiles
- **Three video modes** — standard multi-topic (45-55s), deep-dive single topic (45-60s), movie commentary (3-5min)
- **Embedded audio** — narration and BGM embedded in HTML via `<audio>`, mixed natively by HyperFrames
- **Segment-precise A/V sync** — segmented TTS with per-segment duration tracking eliminates lip-sync drift
- **Cron automation** — daily/weekly content videos run unattended with self-renewing cron jobs
- **Auto-cleanup** — intermediate artifacts are deleted after delivery; each project stays under 30MB

### Stage Pipeline

| Stage | Artifact | Description |
|-------|----------|-------------|
| 0 | env-check | Dependency detection and auto-install |
| 1 | content | Content acquisition from text/file/URL/category data source |
| 2 | design | Director's visual derivation (emotional core → palette → immersion mode → storyboard) |
| 3 | narration | Scene breakdown + 6-beat emotional rhythm + segmented narration |
| 4 | audio | Segmented TTS + loudnorm + BGM selection + 7-level volume calibration |
| 5 | assets | Visual asset preparation (optional, pure CSS/HTML) |
| 6 | video | Three-layer HTML + 52 components + GSAP animation → HyperFrames rendering |
| 7 | delivery | Cover frame embedding + cover image + 3 Douyin copy styles + dual-version output |
| — | machine-scoring | Post-delivery gate check + machine prediction score |
| 8 | feedback | Playback data + human rating → machine scoring calibration (manual trigger, optional) |
| — | cleanup | Intermediate file removal per retention policy |

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

**Prerequisites:** Node.js >= 22, FFmpeg, edge-tts, yt-dlp. See [Getting Started](docs/快速开始.md) for full setup.

## Usage

### Interactive Mode

```
/clipforge Generate a video from this article: https://...
```

Claude guides you through each stage with confirmation at every step.

### Data Feedback

```
/clipforge-feedback
```

Analyze playback data and calibrate machine scoring. See below for details.

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
2. **Skills are self-contained.** Each stage file includes its own execution guide, anti-rationalization table, and red flags. No external context files needed.
3. **Delegate, don't rewrite.** HTML composition and rendering are handled by HyperFrames. Audio mixing is native to the renderer — no FFmpeg post-processing.

### Core Subsystems

| Subsystem | File | Purpose |
|-----------|------|---------|
| Director's Toolkit | `shared/director-toolkit.md` | 5 must-answer questions + visual vocabulary + viral case studies; required before Stage 2/3/6 |
| Render Safety | `shared/render-safety.md` | HyperFrames incident post-mortems: no CSS anim-in, three-layer architecture, safe area padding |
| Content Norms | `shared/shared-rules.md` | Phrasing, on-screen text language, CTA timing, URL prohibition, golden 3-second rule |
| Machine Scoring | `shared/machine-scoring.md` | Post-delivery gate check producing machine prediction score |
| Visual Phasing | `shared/visual-phasing.md` | Phase splitting rules for scenes > 15s |
| Category Config | `categories/github.md` | GitHub-specific data source, selection strategy, voice, hashtag overrides |

See [Architecture Guide](docs/架构设计.md) for the full DAG semantics, SubAgent dispatch, and error recovery strategy. For the self-evolution engine internals, see [Self-Evolution Architecture](docs/Agent自进化架构设计.md).

## Self-Evolution

ClipForge doesn't produce fixed output — it learns from playback data and continuously evolves.

**How it works:**

```
Produce video → Machine scoring → Publish → You import playback data → Compare prediction vs actual → Auto-adjust rules
```

1. After each video is produced, ClipForge automatically generates a **machine prediction score** (`score_report.json`)
2. 1-2 days after publishing, export playback data from each platform
3. ClipForge compares "machine prediction" vs "actual performance", identifies deviations and produces calibration signals
4. Calibration signals are written to the rule library after human confirmation, making the next prediction more accurate

**How to import data:**

Place platform export files in `workspace/sources/视频数据/YYYY-MM-DD/`:

| Platform | Export path |
|----------|-------------|
| Douyin | Creator Center → Data Center → Video Analysis → Published → List → Select All → Export |
| Bilibili | Creator Center → Data Overview → Recent Videos Comparison → Export (10 per export, repeat as needed) |
| WeChat Video | Video Account Assistant → Data Center → Video Data → Single Video → Download |
| Xiaohongshu | Creator Platform → Data Dashboard → Content Analysis → Note Data → All → Export |

**Three trigger methods:**

- **Automatic**: After producing a video, ClipForge auto-detects new data and prompts you to analyze
- **Manual**: Run `/clipforge-feedback` to select a project for scoring calibration
- **Guided**: Simply tell ClipForge "analyze recent playback data" and it handles the full flow

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
- **New stage:** Add an artifact to `schema.yaml` and create a corresponding `stages/stageN-xxx.md` skill file
- **New video mode:** Define mode rules in the stage files; the controller auto-selects based on content

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## Project Structure

```
clipforge/
├── CLAUDE.md                              # AI agent entry point
├── README.md                              # 中文说明（默认）
├── README_EN.md                           # English README (this file)
├── LICENSE                                # Apache 2.0
├── CONTRIBUTING.md                        # Contribution guidelines
├── docs/
│   ├── 架构设计.md                           # DAG + stage pipeline deep dive
│   └── 快速开始.md                          # Setup and first video
├── .claude/commands/
│   ├── clipforge.md                       # Main controller (DAG, modes, error recovery)
│   ├── github-daily-trending.md           # Daily cron
│   ├── github-weekly-trending.md          # Weekly cron
│   ├── github-weekly-zhihu.md             # Weekly article cron
│   └── clipforge/
│       ├── schema.yaml                    # Artifact DAG (single source of truth)
│       ├── stages/                        # Stage execution guides (stage0 ~ stage8)
│       ├── shared/                        # Shared skills (render safety, cleanup, etc.)
│       ├── categories/                    # Category profiles
│       │   ├── _category-schema.md        # Category config format spec
│       │   ├── github.md                  # GitHub category
│       │   └── intro.md                   # Channel intro category
│       ├── engine/                        # Self-evolution engine (gates/attribution/trace/observability/lint)
│       ├── rules/                         # Constraint rules (YAML)
│       ├── skills/                        # Skill declarations (four-atom model)
│       ├── patterns/                      # Empirical patterns (data-driven)
│       ├── scripts/                       # Tool scripts
│       └── components/                    # Visual component library (52 total)
├── install.sh                             # One-shot dependency installer
└── workspace/                             # Output (gitignored)
```

## License

[Apache License 2.0](LICENSE)
