---
docs: references/
---

# review-tools skill

An installable Claude Code skill for GitHub PR reviews. Self-sufficient — all paths resolve via `${CLAUDE_SKILL_DIR}` with no dependency on the host repo.

## Contents

```
SKILL.md              — skill entry point and routing table
references/           — workflow guides and the review checklist
  review-a-pr.md      — scan → file → post workflow
  respond-to-reviews.md — replying to comments on your own PR
  analyze-patterns.md — extracting patterns to update the checklist
  parallel-pr-review.md — running reviews across multiple PRs with tmux
  review-checklist.md — violation rules consulted during scanning
scripts/              — Python CLI tools (uv-managed)
  pyproject.toml
  src/review_tools/   — source for all CLI commands
```

## What Lives Here

- Skill entry point (`SKILL.md`)
- Workflow reference docs (`references/`)
- CLI source and dependency lockfile (`scripts/`)

## What Doesn't Live Here

- Temporary artifacts — write to `/tmp/`
- Project-level agent instructions — those live at the repo root
