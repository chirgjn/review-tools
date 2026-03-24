# PR Review Checklist Generator

**Philosophy:** File-first, batched code reviews with no timeline noise.

| Principle      | Why It Matters                                                                                                                |
| -------------- | ----------------------------------------------------------------------------------------------------------------------------- |
| **File-first** | Review your comments before posting. GitHub review comments are permanent—no undo without leaving dismissed timeline entries. |
| **Batching**   | One review per PR, not one per comment. Multiple reviews = permanent timeline clutter that can't be cleaned up.               |
| **Quality**    | Comments explain WHY, not just WHAT. Minimum 10 words (except LGTM, Approved, etc.).                                          |

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
| **Contribute/extend** the toolkit                     | [Code patterns](#development) below                 |

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

**Approve a PR:**

```bash
# Pure approval
uv run post-review owner/repo 42 --review-body "LGTM" --event APPROVE

# Approve with minor comments
uv run post-review owner/repo 42 --input nits.json --review-body "Approved with suggestions" --event APPROVE
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
# List and reply individually (preferred)
uv run reply-review owner/repo 45 --list
uv run reply-review owner/repo 45 1234567890 "Extracted to helper as suggested"

# Or acknowledge all with reactions
uv run reply-review owner/repo 45 --react-all eyes
```

## Commands

| Command                    | Purpose                                   |
| -------------------------- | ----------------------------------------- |
| `uv run pr-threads`        | Fetch PR review comments                  |
| `uv run suggest-checklist` | Suggest checklist items from patterns     |
| `uv run scan-violations`   | Auto-detect violations in PRs             |
| `uv run build-review`      | Build review payload incrementally        |
| `uv run get-positions`     | Convert file:line to GitHub diff position |
| `uv run post-review`       | Post batched GitHub review                |
| `uv run reply-review`      | Reply/react to PR comments                |

## Development

```bash
# Run linting
uv run ruff check src/

# Run type checking
uv run basedpyright src/

# Format code
uv run ruff format src/
```

### Code Patterns

**Performance:**

- Pre-compile regex at module level
- Use `functools.lru_cache` for API calls
- Use `frozenset` for O(1) lookups

**Error Handling:**

- Use `rich.console` for colored output
- Show helpful context, not just raw errors
- Provide `--force-*` flags for user overrides

**Adding Commands:**

1. Follow `verb-noun` naming (e.g., `scan-violations`)
2. Add entry point in `pyproject.toml`
3. Use file-based patterns (read from `--input`, write to `--output`)
4. Update this README with examples

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
