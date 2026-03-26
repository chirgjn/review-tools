---
docs: docs/
---

# review-tools

Root of the PR review tools repo. Contains the installable Claude Code skill and project-level docs.

## Contents

```
skills/
  review-tools/           — the installable review skill → skills/review-tools/layout.md
    SKILL.md              — skill entry point
    references/           — workflow guides and review checklist
    scripts/              — Python CLI tools (uv-managed)
  parallel-claude-sessions/ — skill for running multiple Claude sessions in parallel
    SKILL.md              — skill entry point

AGENTS.md                 — navigation, commands, conventions (canonical)
CLAUDE.md -> AGENTS.md    — symlink
README.md                 — human entry point
```

## What Lives Here

- Project-level agent instructions (`AGENTS.md`, `CLAUDE.md`)
- Human-facing README
- This structural map

## What Doesn't Live Here

- Skill logic, scripts, and references — those live under `skills/review-tools/`
- Temporary artifacts (`review.json`, threads) — write to `/tmp/`

## Sub-Directories

| Directory | What it owns |
|---|---|
| `skills/review-tools/` | The installable skill — references, scripts, entry point → `skills/review-tools/layout.md` |
