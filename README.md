# review-tools

> **AI agent?** Read [AGENTS.md](AGENTS.md) first.

A Claude Code skill for doing GitHub PR reviews. File-first, batched reviews — no timeline noise.

| Principle      | Why It Matters                                                                                                                |
| -------------- | ----------------------------------------------------------------------------------------------------------------------------- |
| **File-first** | Review your comments before posting. GitHub review comments are permanent—no undo without leaving dismissed timeline entries. |
| **Batching**   | One review per PR, not one per comment. Multiple reviews = permanent timeline clutter that can't be cleaned up.               |
| **Quality**    | Comments explain WHY, not just WHAT. Minimum 10 words (except LGTM, Approved, etc.).                                         |

## Structure

```
skills/
  review-tools/         — the installable skill
    SKILL.md                — entry point: philosophy and workflow routing
    references/             — workflow guides and the review checklist
    scripts/                — Python CLI tools
      src/review_tools/     — source for all CLI commands
      pyproject.toml
      uv.lock
```

## Installation

```bash
git clone <repo>
cd review-tools/skills/review-tools/scripts
uv sync
```

Or run without installing:

```bash
cd skills/review-tools/scripts
uv run pr-threads owner/repo#35 --all
```

## Pick Your Workflow

| I want to...                                          | Go to                                                                                               |
| ----------------------------------------------------- | --------------------------------------------------------------------------------------------------- |
| **Extract patterns from past PRs** → update checklist | [analyze-patterns.md](skills/review-tools/references/analyze-patterns.md)                          |
| **Review a PR** → post checklist-based comments       | [review-a-pr.md](skills/review-tools/references/review-a-pr.md)                                    |
| **Respond to reviews** → reply/react on my PR         | [respond-to-reviews.md](skills/review-tools/references/respond-to-reviews.md)                      |

## Quick Examples

Run all commands from `skills/review-tools/scripts/`.

**Extract patterns and update checklist:**

```bash
uv run pr-threads owner/repo#35 owner/repo#36 --all | \
    uv run suggest-checklist --checklist ../references/review-checklist.md
```

**Review a PR (file → post workflow):**

```bash
# STEP 1: Scan and save to file
uv run scan-violations owner/repo 42 --checklist ../references/review-checklist.md --output /tmp/review.json

# STEP 2: Review/modify the file (optional)
cat /tmp/review.json | jq '.comments[] | {path, body}'

# STEP 3: Post batched review
uv run post-review owner/repo 42 --input /tmp/review.json --review-body "Checklist review" --event REQUEST_CHANGES
```

**Respond to review comments:**

```bash
uv run reply-review owner/repo 45 --list --with-context
uv run reply-review owner/repo 45 1234567890 "Extracted to helper as suggested"
```

## Requirements

- Python 3.11+
- [GitHub CLI (`gh`)](https://cli.github.com/) authenticated
- [uv](https://docs.astral.sh/uv/) for running Python scripts

## Help

All commands have built-in help:

```bash
uv run pr-threads --help
uv run scan-violations --help
uv run post-review --help
uv run reply-review --help
```
