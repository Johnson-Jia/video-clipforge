# Contributing to ClipForge

Thanks for your interest in improving ClipForge. This guide covers how to contribute effectively.

## Ways to Contribute

### Report Issues

- Open a [GitHub Issue](https://github.com/Johnson-Jia/video-clipforge/issues)
- Include: what you expected, what happened, the stage where it failed, and relevant log output
- For video quality issues: attach the `design.md`, `narration_segments.json`, and `segment_durations.json` from the project directory

### Add a New Stage

1. Define the artifact in `schema.yaml` with `generates`, `requires`, and `template` fields
2. Create `stageN-name.md` in `.claude/commands/clipforge/stages/` following the existing pattern:
   - CSO `description` (trigger condition, not workflow summary)
   - Execution steps with explicit file reads/writes
   - Anti-rationalization table (Red Flags + Common Rationalizations)
   - Completion criteria (which files must exist)
3. Update `clipforge.md` to reference the new stage in the DAG section
4. Test with `/clipforge` in interactive mode before updating cron files

### Add a New Content Source

1. Create a new cron file (e.g., `.claude/commands/my-source.md`) modeled after `github-daily-trending.md`
2. The cron file handles: data fetching → SubAgent dispatch → verification → self-renewal
3. SubAgent prompts are self-contained — they read stage files directly, no external context files
4. Test manually before enabling cron scheduling

### Add a New Category

ClipForge uses category profiles to define content-specific rules (data acquisition, style, voice, hashtags). To add a new category:

1. Create `categories/{id}.md` in `.claude/commands/clipforge/categories/` following the format in `categories/_category-schema.md`
2. Define the category-specific overrides for each stage (content, design, narration, audio, delivery)
3. Create a corresponding cron file (if automated) or update the interactive controller
4. Test with `/clipforge` specifying the category, verify each stage correctly loads category overrides
5. Verify that generic stage files still work without a category (fallback behavior)

**Category design principles:**
- Categories **override** generic rules, they don't replace them. Only declare what's different.
- Each category file is self-contained. No cross-category references.
- Category ID = filename (lowercase English, e.g., `github`, `comics`, `novel`).

### Add a New Video Mode

1. Define mode selection criteria in `clipforge.md` (when to trigger the new mode)
2. Add mode-specific rules in the relevant stage files (scene count, duration targets, narration structure)
3. Include an anti-rationalization entry for the new mode's common failure patterns

## Development Guidelines

### Schema is Truth

All artifact dependencies and outputs are defined in `schema.yaml`. If you need to change a dependency or add a new output file, update the schema first. The cron files and stage files must be consistent with the schema.

### Skills are Self-Contained

Each stage file (`stages/stageN-xxx.md`) must include everything needed to execute that stage:
- What to read (input files from upstream artifacts)
- What to do (execution steps)
- What to write (output files declared in `generates`)
- What can go wrong (anti-rationalization table)

Do not create external context files. The stage file itself is the complete execution guide.

### Token Budget

Stage files should stay focused. Target under 500 words for the execution steps. Anti-rationalization tables are essential — they're not optional documentation, they're the guardrails that prevent common AI mistakes.

### No Dead Code

If a file is not read by any execution path (cron file or interactive mode), it should not exist. Before adding a new shared file, verify it will actually be loaded during execution.

### File Paths

- All paths in `.gitignore` use forward slashes
- `workspace/` paths use `YYYY/MM/DD/project-name/` format (English only, no Chinese characters)
- Video output is always `workspace/` (gitignored)

## Pull Request Process

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/my-feature`)
3. Make your changes
4. Test with Claude Code: run `/clipforge` and verify the affected stages work
5. Submit a PR with a clear description of what changed and why

### PR Checklist

- [ ] `schema.yaml` updated if artifacts changed
- [ ] Stage files updated if execution steps changed
- [ ] Cron files updated if SubAgent prompts affected
- [ ] No new files that aren't referenced in any execution path
- [ ] Tested with `/clipforge` in interactive mode

## Code of Conduct

Be respectful. This is a community project built on shared effort. Constructive feedback welcome; personal attacks are not.
