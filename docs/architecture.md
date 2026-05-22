# Architecture

ClipForge is a DAG-orchestrated video production pipeline. This document covers the core architecture decisions and how the pieces fit together.

## DAG Orchestration

### Schema as Single Source of Truth

All artifact definitions live in [`schema.yaml`](../.claude/commands/clipforge/schema.yaml). The schema defines:

- **`generates`** — File patterns that prove an artifact is complete (glob patterns like `**/output.mp4`)
- **`requires`** — Hard dependencies (must complete before this artifact starts)
- **`requires_any`** — Conditional dependencies (become hard when the condition artifact executes)
- **`optional`** — Optional artifacts (skip without blocking downstream)
- **`condition`** — Trigger condition for conditional stages

This is the only place where dependencies are declared. Stage files and cron files reference the schema but never re-declare dependencies.

### Dependency Graph

```
env-check → content → design ─┬→ narration → audio ──┬→ video → delivery → cleanup
                               │                assets ┘
                               └→ assets
                                                  narration → movie-clips (conditional)
```

### State Detection

State = File existence. The system checks whether `generates` glob patterns match actual files on disk. No database, no status API, no state machine.

- If `design.md` exists → design artifact is complete
- If `output.mp4` AND `output_no_bgm.mp4` exist → video artifact is complete
- If `final.mp4` AND `final_no_bgm.mp4` AND `cover.png` AND `douyin.md` exist → delivery artifact is complete

This means you can skip stages by manually creating the output files (useful for debugging or resuming interrupted runs).

## Stage Pipeline

### Stage Files

Each stage is a self-contained skill file (`.claude/commands/clipforge/stageN-xxx.md`) with:

1. **CSO description** — When this stage triggers (not what it does)
2. **Execution steps** — What to read, what to do, what to write
3. **Anti-rationalization table** — Red Flags and Common Rationalizations specific to this stage
4. **Completion criteria** — Which files must exist when done

### Shared Rules

Cross-cutting concerns live in shared files:

| File | Content | Used by |
|------|---------|---------|
| `_shared-rules.md` | Content norms, language rules, golden 3-second rule, URL prohibition | Stages 1, 3, 6, 7 |
| `_cleanup-rules.md` | File retention/deletion rules | cleanup |
| `_cron-renew.md` | Cron self-renewal protocol | All cron files |
| `_movie-clips.md` | Movie clip extraction | Conditional stage between narration and audio |
| `_bgm-pixabay.md` | BGM download helper | audio stage |

## Execution Modes

### Interactive Mode

User calls `/clipforge` in Claude Code. The controller:
1. Reads `schema.yaml` and parses the DAG
2. Scans for completed artifacts (file existence)
3. Topologically sorts remaining artifacts
4. Executes each ready artifact, showing results and asking for confirmation
5. Re-scans after each completion

### Automated Mode (Cron)

Cron files (like `github-daily-trending.md`) dispatch SubAgents in batches:

| Batch | Artifacts | Rationale |
|-------|-----------|-----------|
| SubAgent-1 | env-check → content → design → narration | Sequential, no parallelism opportunity |
| SubAgent-2 | audio | Depends on narration |
| SubAgent-3 | video | Depends on audio |
| SubAgent-4 | delivery → cleanup | Sequential finalization |

Each SubAgent starts with a fresh context window. The SubAgent prompt includes:
1. Project context (directory, mode, content type)
2. Which stage files to read and execute
3. Completion criteria (files to verify)

State passes between SubAgents through the filesystem — SubAgent-2 reads `narration_segments.json` written by SubAgent-1.

## Audio Architecture

### Segmented TTS

Narration is split into segments (one per scene). Each segment is TTS'd independently with `edge-tts`, producing individual MP3 files. Durations are recorded in `segment_durations.json`.

This solves A/V sync: each scene's duration in the HTML matches its actual narration duration, not an estimated value.

### Embedded Audio

Narration and BGM are embedded directly in the HTML via `<audio>` elements:

```html
<audio id="narration" src="narration.mp3"></audio>
<audio id="bgm" src="bgm.wav" data-volume="0.08"></audio>
```

HyperFrames reads these elements during rendering and mixes them natively into the output MP4. No FFmpeg post-processing needed.

### BGM Volume

BGM volume is analyzed per-segment (narration loudness varies). The `segment_durations.json` file includes `meta.bgm_volume` which the video stage reads to set `data-volume` on the BGM audio element.

## Error Recovery

The DAG structure enables minimal-scope rollbacks:

| Problem | Rollback to | Cascade |
|---------|-------------|---------|
| Narration timing off by 1-3s | video only | Adjust `data-duration`, re-render |
| Narration timing off by >3s | narration | narration → audio → video → delivery |
| Visual style mismatch | design | design → assets → video |
| BGM mood mismatch | audio | audio → video |
| Content error | narration | narration → audio → video → delivery |

**Principle:** Roll back to the minimum stage that must change. The DAG determines the cascade scope.

## Design Decisions

### Why schema.yaml instead of code?

The schema is a declarative contract. Both the interactive controller and cron files read it to understand dependencies. If we encoded this in code, cron files couldn't reuse the logic without importing a module — and Claude Code skills don't have a module system.

### Why file-based state instead of a database?

Simplicity and debuggability. You can check project state by running `ls`. You can resume a failed run by checking which files exist. No external dependencies.

### Why SubAgents instead of one long execution?

Context window limits. A full video production run involves reading content, writing narration, running TTS, composing HTML, and rendering. This exceeds a single context window. SubAgents isolate each batch, keeping each window focused.

### Why embedded audio instead of FFmpeg mixing?

HyperFrames provides native audio mixing during rendering. Adding FFmpeg as a post-processing step would be redundant and error-prone. The `<audio>` element approach is simpler, more maintainable, and produces better results (frame-accurate sync).

## Category System

### Architecture

ClipForge uses a **category profile** pattern to separate generic pipeline logic from content-specific rules:

```
categories/
├── _category-schema.md   # Format specification
├── github.md             # GitHub open-source projects
├── comics.md             # Comics (future)
└── novel.md              # Novels (future)
```

Each category file defines overrides for specific stages:

| Stage | What can be overridden |
|-------|----------------------|
| content | Data source, selection strategy, deep research methods, fallback |
| design | Default style direction, color bias |
| narration | Hook templates, special rules, word count range |
| audio | Default voice, rate |
| delivery | Hashtags, comment template, cover badge |
| shared-rules | Data validation rules |

### Why category profiles instead of separate pipelines?

A single generic pipeline with pluggable category configs is better than multiple independent pipelines:

1. **Shared infrastructure** — DAG orchestration, SubAgent dispatch, audio mixing, rendering, and cleanup are identical across categories. No duplication.
2. **Override, don't replace** — Categories only declare what's different. The generic stage files provide sensible defaults. Adding a new category requires only one new config file.
3. **Consistent quality** — Anti-rationalization tables, golden 3-second rule, and rendering safety rules apply to all categories uniformly.
