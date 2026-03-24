# Workflow: Analyze PR Patterns → Update Checklist

Extract recurring themes from past PR reviews to update your checklist.

## When to Use This

- After reviewing several PRs and noticing repeated feedback
- When onboarding new reviewers and need documented standards
- To codify implicit team knowledge into explicit rules

## Workflow

### Step 1: Fetch Comments from Multiple PRs

```bash
# Analyze 3-5 PRs at once (mix of recent and older for variety)
uv run pr-threads owner/repo#35 owner/repo#36 owner/repo#37 --all

# Save to file for analysis
uv run pr-threads owner/repo#35 owner/repo#36 --all > threads.txt
```

**Tips:**

- Use `--all` to see all reviewers (not just your comments)
- Use `--file-pattern hooks.ts` to focus on specific file types (output can be piped to `suggest-checklist`)
- Use `--body-filter "useCallback"` to find specific themes
- Pipe directly to `suggest-checklist` or save to file with `--input`

### Step 2: Analyze for Recurring Patterns

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
        --checklist docs/review-checklist.md \
        --new-only

# Stricter threshold (only very frequent patterns)
uv run suggest-checklist --input threads.txt --threshold 5
```

### Step 3: Review Suggestions and Update Checklist

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

Add to `docs/review-checklist.md`:

```markdown
## React Hooks

- [ ] **`useEffect` has exhaustive deps** — add all dependencies or document why empty
```

**Rule of thumb:** Only add patterns appearing 3+ times across multiple PRs.

## Tool Reference

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

**Output format (compatible with `suggest-checklist`):**

```
Thread: src/hooks.ts:45
  id=1234567890 repo=owner/repo pr=35 commit=abc1234
  URL: https://github.com/...
  [id=1234567890] @reviewer:
    Add useCallback here for performance

File: src/utils.ts:12
  id=1234567891 repo=owner/repo pr=35 commit=abc1234
  [id=1234567891] @reviewer:
    Check dependency array
```

Both `Thread:` and `File:` formats are parsed correctly by `suggest-checklist`.

### suggest-checklist

Analyze pr-threads output and suggest checklist items.

```bash
# From pipe
uv run pr-threads ... | uv run suggest-checklist

# From file
uv run suggest-checklist --input threads.txt

# With checklist deduplication
uv run suggest-checklist --input threads.txt \
    --checklist docs/review-checklist.md

# Only new suggestions
uv run suggest-checklist --input threads.txt \
    --checklist docs/review-checklist.md --new-only

# Save report
uv run suggest-checklist --input threads.txt \
    --output analysis.txt
```

**Options:**

- `--threshold N` — Minimum frequency to suggest (default: 3)
- `--checklist FILE` — Compare against existing checklist
- `--new-only` — Show only suggestions not in checklist
- `--apply` — Actually modify checklist (default: dry-run)

**How it works:**

1. Extracts keywords and 2-3 word phrases
2. Clusters terms that appear together
3. Auto-categorizes (React Hooks, ESLint, TypeScript, etc.)
4. Ranks by frequency
5. Suggests new checklist items

## Complete Example

```bash
# 1. Fetch comments from 5 recent PRs and analyze in one pipeline
uv run pr-threads \
    owner/repo#40 owner/repo#41 owner/repo#42 \
    owner/repo#43 owner/repo#44 --all | \
    uv run suggest-checklist \
        --checklist docs/review-checklist.md \
        --new-only

# 2. Review suggestions, manually update checklist
# 3. Commit checklist update
```

**Alternative: Save to file for repeated analysis**

```bash
# Save output for multiple analysis passes
uv run pr-threads owner/repo#35 owner/repo#36 --all > review_threads.txt

# Analyze with different thresholds
uv run suggest-checklist --input review_threads.txt --threshold 3
uv run suggest-checklist --input review_threads.txt --threshold 5 --new-only
```
