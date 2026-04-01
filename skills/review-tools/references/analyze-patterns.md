# Analyze PR Patterns → Update Checklist

Extract recurring themes from past PR reviews.

## Workflow

### 1. Fetch Comments

```bash
uv run pr-threads owner/repo#35 owner/repo#36 owner/repo#37 --all
uv run pr-threads owner/repo#35 owner/repo#36 --all > /tmp/threads.txt  # Save to file
```

**Filter options:**
- `--all` — include all reviewers
- `--file-pattern .tsx` — filter by file type
- `--body-filter useCallback` — filter by content

### 2. Analyze Patterns

```bash
# Basic analysis - pipe directly from pr_threads to analyzer
uv run pr-threads owner/repo#35 owner/repo#36 --all | \
    uv run suggest-checklist

# Filter by file type then analyze
uv run pr-threads owner/repo#35 owner/repo#36 --all --file-pattern ".tsx" | \
    uv run suggest-checklist --threshold 2

# Compare against existing checklist (shows only new suggestions)
uv run pr-threads owner/repo#35 owner/repo#36 --all | \
    uv run suggest-checklist \
        --checklist ${CLAUDE_SKILL_DIR}/references/review-checklist.md \
        --new-only

# Stricter threshold (only very frequent patterns)
uv run suggest-checklist --input /tmp/threads.txt --threshold 5
```

### 3. Update the Checklist

The analysis outputs:

```
==================================================
PATTERN ANALYSIS
==================================================
Total comments: 47

Top keywords:
   12x  useeffect
    8x  dependency
    5x  exhaustive

Top clusters:
   5x  'useeffect' + 'dependency'
   3x  'as' + 'any'

==================================================
SUGGESTED UPDATES
==================================================
[5x] useeffect + dependency (seen 5 times)
[8 comments] React Hooks: useeffect, dependency, exhaustive
```

Add to checklist: `- [ ] useEffect has exhaustive deps — add all dependencies or document why empty`

> **Rule of thumb:** Only add patterns appearing 3+ times.

## Tools

### pr-threads

Fetch PR review comments with threading and context.

```bash
# Your comments only (default)
uv run pr-threads owner/repo#35

# All reviewers
uv run pr-threads owner/repo#35 --all

# Specific reviewer
uv run pr-threads owner/repo#35 --reviewer username

# Filter by file pattern (includes diff context)
uv run pr-threads owner/repo#35 --file-pattern ".tsx"

# Filter by content
uv run pr-threads owner/repo#35 --body-filter "useCallback"

# Inspect specific comment IDs
uv run pr-threads owner/repo#35 --comments 1234567890

# Custom slug mapping
uv run pr-threads owner/short#3 --slug-map short=owner/full-repo
```

**Output format:** `Thread:` or `File:` lines, compatible with `suggest-checklist`.

### suggest-checklist

Analyze pr-threads output and suggest checklist items.

```bash
# From pipe
uv run pr-threads ... | uv run suggest-checklist

# From file
uv run suggest-checklist --input /tmp/threads.txt

# With checklist deduplication
uv run suggest-checklist --input /tmp/threads.txt \
    --checklist ${CLAUDE_SKILL_DIR}/references/review-checklist.md

# Only new suggestions
uv run suggest-checklist --input /tmp/threads.txt \
    --checklist ${CLAUDE_SKILL_DIR}/references/review-checklist.md --new-only

# Save report
uv run suggest-checklist --input /tmp/threads.txt \
    --output /tmp/analysis.txt
```

**Options:** `--threshold N` (default: 3), `--checklist FILE`, `--new-only`, `--apply`

- `--threshold N` — only suggest patterns appearing N or more times (default: 3; matches the "3+ times" rule of thumb)
- `--apply` — write suggestions directly into the checklist file; review output first before using

**How it works:** Extracts keywords → clusters → categorizes → ranks by frequency → suggests.

## Example

```bash
# 1. Fetch comments from 5 recent PRs and analyze in one pipeline
uv run pr-threads \
    owner/repo#40 owner/repo#41 owner/repo#42 \
    owner/repo#43 owner/repo#44 --all | \
    uv run suggest-checklist \
        --checklist ${CLAUDE_SKILL_DIR}/references/review-checklist.md \
        --new-only

# 2. Review suggestions, manually update checklist
# 3. Commit checklist update
```

**Save to file for repeated analysis passes:**

```bash
uv run pr-threads owner/repo#35 owner/repo#36 --all > /tmp/review_threads.txt

uv run suggest-checklist --input /tmp/review_threads.txt --threshold 3
uv run suggest-checklist --input /tmp/review_threads.txt --threshold 5 --new-only
```
