# PR Review Checklist Generator

Workflow toolkit for creating and maintaining code review checklists.

## Why This Exists

**Problem:** Code review feedback is often inconsistent, untracked, and creates permanent GitHub timeline noise when posted carelessly.

**Solution:** A file-first workflow that:
1. **Builds comments in files first** → review before posting (no permanent mistakes)
2. **Batches into single reviews** → clean PR history (no timeline spam)
3. **Enforces quality standards** → explain WHY not just WHAT

## Installation

```bash
# Clone and install
git clone <repo>
cd review-tools
uv sync  # Installs with dev dependencies
```

Or run without installing:
```bash
uv run pr-threads owner/repo#35 --all
```

## Pick Your Workflow

| I want to...                                          | Go to                                               |
| ----------------------------------------------------- | --------------------------------------------------- |
| **Extract patterns from past PRs** → update checklist | [analyze-patterns.md](docs/analyze-patterns.md)     |
| **Review a PR** → post checklist-based comments       | [review-a-pr.md](docs/review-a-pr.md)               |
| **Respond to reviews** → reply/react on my PR         | [respond-to-reviews.md](docs/respond-to-reviews.md) |
| **Contribute/extend** the toolkit                     | [agent-guide.md](docs/agent-guide.md)               |

## Quick Examples

**Extract patterns and update checklist (pipeline):**

```bash
uv run pr-threads owner/repo#35 owner/repo#36 --all | \
    uv run suggest-checklist --checklist docs/review-checklist.md
```

**Analyze specific file types:**

```bash
uv run pr-threads owner/repo#35 --all --file-pattern ".tsx" | \
    uv run suggest-checklist --threshold 2
```

**Review a PR (file → post workflow):**

```bash
# STEP 1: Scan and save to file
uv run scan-violations owner/repo 42 --checklist docs/review-checklist.md --output review.json

# STEP 2: Review/modify the file (optional)
cat review.json | jq '.comments[] | {path, body}'

# STEP 3: Post batched review
uv run post-review owner/repo 42 --input review.json --review-body "Checklist review" --event REQUEST_CHANGES
```

**Build complex reviews incrementally:**

```bash
# Build up comments in a file
uv run build-review --path src/a.ts --position 42 --body-file suggestion_a.md
uv run build-review --path src/b.ts --position 15 --body "Extract this logic for reusability"
uv run build-review --show  # Preview
uv run build-review --post owner/repo 42 --review-body "Refactoring suggestions"
```

**Respond to review comments:**

```bash
uv run reply-review owner/repo 45 --reply-all --prefix "✅ Fixed"
```

## Commands

| Command | Purpose |
|---------|---------|
| `uv run pr-threads` | Fetch PR review comments |
| `uv run suggest-checklist` | Suggest checklist items from patterns |
| `uv run scan-violations` | Auto-detect violations in PRs |
| `uv run build-review` | Build review payload incrementally |
| `uv run get-positions` | Convert file:line to GitHub diff position |
| `uv run post-review` | Post batched GitHub review |
| `uv run reply-review` | Reply/react to PR comments |

## Development

```bash
# Run linting
uv run ruff check src/

# Run type checking
uv run basedpyright src/

# Format code
uv run ruff format src/
```

## Requirements

- Python 3.11+
- [GitHub CLI (`gh`)](https://cli.github.com/) authenticated
- [uv](https://docs.astral.sh/uv/) for running Python scripts

## Help

All commands have built-in help: `--help` or `-h`

```bash
uv run pr-threads --help
uv run scan-violations --help
uv run post-review --help
uv run reply-review --help
```

## Example Checklist

See [review-checklist.md](docs/review-checklist.md) for an example checklist derived from real PR reviews.
