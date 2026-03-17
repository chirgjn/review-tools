# PR Review Checklist Generator

A workflow toolkit for creating and maintaining code review checklists from recurring PR feedback.

## What This Is

Code review feedback often contains recurring themes. This toolkit helps you extract patterns from past PR reviews, codify them into a living checklist, and ensure consistent quality standards across your codebase.

## Documentation

| Document | What You'll Find There |
|----------|------------------------|
| **[Generating the Checklist](docs/pr-review-checklist-generation-guide.md)** | How to fetch PR review comments, analyze them for recurring patterns, and update your checklist |
| **[The Checklist](docs/review-checklist.md)** | Example checklist derived from real PR reviews — use as a template or starting point |
| **[Posting GitHub Reviews](docs/posting-github-reviews.md)** | How to post batched inline comments via the GitHub CLI (with important pitfalls to avoid) |

## Quick Start

```bash
# Fetch review threads from PRs
uv run scripts/pr_threads.py \
    https://github.com/owner/repo/pull/35 \
    owner/repo#36

# Then follow the workflow in the generation guide
```

## Project Structure

```
docs/              # Guides and the checklist itself
scripts/           # Python tools for fetching PR data
└── pr_threads.py  # Main entry point (see generation guide)
```

## Requirements

- Python 3.11+
- [GitHub CLI (`gh`)](https://cli.github.com/) authenticated
- [uv](https://docs.astral.sh/uv/) for running scripts
