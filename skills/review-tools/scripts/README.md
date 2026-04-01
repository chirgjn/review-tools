# review-tools scripts

Python CLI tools for the review-tools skill. Managed with [uv](https://docs.astral.sh/uv/).

## Requirements

- Python 3.11+
- [GitHub CLI (`gh`)](https://cli.github.com/) authenticated
- uv

## Commands

| Command             | What it does                                                                   |
| ------------------- | ------------------------------------------------------------------------------ |
| `pr-threads`        | Fetch PR review threads with context and filtering                           |
| `scan-violations`   | Scan PR diff for checklist violations (stores content_hint for verification) |
| `post-review`       | Post a batched review from JSON (auto-verifies content hints before posting)  |
| `reply-review`      | List, inspect, and reply to review threads on your PR                         |
| `suggest-checklist` | Analyze pr-threads output and suggest checklist updates                        |
| `get-positions`     | Convert file:line:content to diff position (outputs JSON with content preview) |
| `build-review`      | Incrementally build a review JSON file (requires --content for verification)  |

## Key Features

**Automatic Position Verification**: Every inline comment includes a `content_hint` (first 20 words of the line). Before posting, `post-review` verifies this matches the actual diff content to prevent comments on wrong lines.

## Usage

Run from this directory:

```bash
# Fetch threads
uv run pr-threads owner/repo#35 --all

# Auto-scan with verification built-in
review=$(mktemp -t review-42-XXXX.json)
uv run scan-violations owner/repo 42 \
  --checklist ../references/review-checklist.md \
  --output "$review"

# Post (auto-verifies before submitting)
uv run post-review owner/repo 42 --input "$review" --event REQUEST_CHANGES

# Manual comment with verification
position=$(uv run get-positions owner/repo 42 "src/file.py:45:useEffect(" | jq -r '.[0].position')
content=$(uv run get-positions owner/repo 42 "src/file.py:45:useEffect(" | jq -r '.[0].content_preview')

uv run build-review --file "$review" \
  --path src/file.py --line 45 --position "$position" \
  --content "$content" \
  --body "Add dependency array"

uv run post-review owner/repo 42 --input "$review"

# Reply to reviews
uv run reply-review owner/repo 45 --list --with-context
```

All commands have built-in help:

```bash
uv run <command> --help
```

Write temporary artifacts (`review.json`, `threads.txt`) to `/tmp/` — not into this directory.

## Workflow docs

Full workflows are in `../references/`. Start with `../SKILL.md` for routing.
