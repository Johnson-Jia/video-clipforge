# CLAUDE.md

This file is the project entry point for Claude Code.

Before any video production task, **read [`.claude/commands/clipforge.md`](.claude/commands/clipforge.md)** — the authoritative workflow for the 8-stage video pipeline, DAG orchestration, and mode selection.

## What is ClipForge

ClipForge is an AI-driven general-purpose short video production system. A DAG-orchestrated pipeline converts any content (text, URLs, PDFs, GitHub data, and more) into Douyin-ready vertical videos with narration, BGM, and covers. Content categories (GitHub, comics, novels, etc.) are defined via category profiles in `clipforge/categories/`.

**Core Pipeline**: `Content → Design → Narration → Audio → Video → Delivery → Cleanup`

## Architecture

- `.claude/commands/clipforge.md` — Main controller: DAG semantics, mode selection, error recovery
- `.claude/commands/clipforge/schema.yaml` — Artifact DAG definition (single source of truth)
- `.claude/commands/clipforge/stage*.md` — Stage skill files (generic, self-contained execution guides)
- `.claude/commands/clipforge/categories/` — Category profiles (per-category overrides for data, style, audio, delivery)
- `.claude/commands/clipforge/_*.md` — Shared rules (content norms, cleanup, cron renewal)
- `.claude/commands/github-*.md` — Cron orchestration files (fully automated SubAgent dispatch)
- `scripts/` — Utility scripts (trending fetcher, BGM generator, quality gate)

## Key Principles

1. **Schema is truth.** All artifact dependencies, outputs, and completion states are defined in `schema.yaml`. Nothing else.
2. **State = File.** An artifact is complete when its `generates` files exist on disk. No status database. To resume an interrupted run, just re-run `/clipforge` — completed stages are skipped automatically.
3. **Delegate, don't rewrite.** HTML composition and rendering are delegated to HyperFrames skills.
4. **Audio embedded.** Narration and BGM are embedded via `<audio>` elements in HTML. HyperFrames handles mixing natively.
5. **Cleanup is mandatory.** After delivery, `_cleanup-rules` must run. No exceptions.

## Category Integration

When a category is specified, each stage reads `categories/{id}.md` to load category-specific overrides (data source, voice, hashtags, etc.). Generic stage files provide defaults; categories declare only what's different. Without a category, all stages use their built-in defaults.

## Commands

| Command | Purpose |
|---------|---------|
| `/clipforge` | Interactive video production (manual mode) |
| `/github-daily-trending` | Daily GitHub trending video (cron, fully automated) |
| `/github-weekly-trending` | Weekly GitHub trending summary (cron, fully automated) |
| `/github-weekly-zhihu` | Weekly GitHub article for Zhihu (cron, fully automated) |

## Compatibility

- This is a skill/workflow package for Claude Code, not a standalone app or API.
- Video rendering requires [HyperFrames](https://github.com/heygen-com/hyperframes) (installed via `npx skills add`).
- On conflict with generic coding skills, prioritize `clipforge.md` and this file.
- `workspace/` is the output directory (gitignored). Project artifacts live there.
