# review-tools scripts

Python CLI tools for the review-tools skill. Managed with [uv](https://docs.astral.sh/uv/).

## Requirements

- Python 3.11+
- [GitHub CLI (`gh`)](https://cli.github.com/) authenticated
- uv

## Commands

| Command             | What it does                                              |
| ------------------- | --------------------------------------------------------- |
| `pr-threads`        | Fetch PR review threads with context and filtering        |
| `scan-violations`   | Scan PR diff for checklist violations                     |
| `post-review`       | Post a batched review from a JSON file                    |
| `reply-review`      | List, inspect, and reply to review threads on your PR     |
| `suggest-checklist` | Analyze pr-threads output and suggest checklist updates   |
| `get-positions`     | Resolve file:line to diff position for manual comments    |
| `build-review`      | Incrementally build a review JSON file                    |

## Usage

Run from this directory:

```bash
uv run pr-threads owner/repo#35 --all
review=$(mktemp -t review-42-XXXX.json)
uv run scan-violations owner/repo 42 --checklist ../references/review-checklist.md --output "$review"
uv run post-review owner/repo 42 --input "$review" --event REQUEST_CHANGES
uv run reply-review owner/repo 45 --list --with-context
```

All commands have built-in help:

```bash
uv run <command> --help
```

Write temporary artifacts (`review.json`, `threads.txt`) to `/tmp/` — not into this directory.

## Workflow docs

Full workflows are in `../references/`. Start with `../SKILL.md` for routing.
