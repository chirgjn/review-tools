# Workflow: Review a PR → Post Comments

Perform a checklist-based code review and post **batched** comments.

## Artifact naming

Use `mktemp` to generate unique paths — avoids collisions when running parallel reviews. Include the PR number in the template for traceability:

```bash
review=$(mktemp -t review-42-XXXX.json)
summary=$(mktemp -t summary-42-XXXX.md)
```

## Workflows

### A. Auto-Scan (Recommended)

```bash
# 1. Preview what the tool finds
uv run scan-violations owner/repo 42 --dry-run

# 2. Generate review payload and SAVE TO FILE
review=$(mktemp -t review-42-XXXX.json)
uv run scan-violations owner/repo 42 \
    --checklist ${CLAUDE_SKILL_DIR}/references/review-checklist.md \
    --output "$review"

# 3. Edit review_body in the file, review comments, then post
uv run post-review owner/repo 42 \
    --input "$review" \
    --event REQUEST_CHANGES
```

The output JSON includes a `review_body` field set to `"Automated checklist review"`. Edit it before posting.

**Built-in detection:** Missing deps, floating promises, `as any`, barrel imports, missing `img alt`, file-level eslint-disable, manual URL concat.

### B. Manual (for auto-scanner misses)

```bash
# 1. Get diff positions for each file:line
uv run get-positions owner/repo 42 src/hooks.ts:45 src/utils.ts:12

# 2. Write review JSON to a temp file, then post
review=$(mktemp -t review-42-XXXX.json)
uv run post-review owner/repo 42 --input "$review" --event REQUEST_CHANGES
```

### C. Incremental Build (complex reviews)

```bash
# Set the review summary first (write it to a temp file)
summary=$(mktemp -t summary-42-XXXX.md)
review=$(mktemp -t review-42-XXXX.json)
uv run build-review --file "$review" --summary-file "$summary"

# Add comments over time
uv run build-review --file "$review" --path src/a.ts --position 42 --body "Fix A"
uv run build-review --file "$review" --path src/b.ts --position 15 --body-file comment_b.md
uv run build-review --file "$review" --show      # Preview
uv run build-review --file "$review" --post owner/repo 42 --event REQUEST_CHANGES
```

### D. Plain PR comment (no review state)

For remarks not tied to any diff line, use `gh` directly:

```bash
gh pr comment owner/repo#42 --body "Needs design sign-off before merge."
gh pr comment owner/repo#42 --body-file "$(mktemp -t comment-42-XXXX.md)"
```

## review.json format

`post-review --input` reads this format:

```json
{
  "review_body": "Summary shown at the top of the review",
  "comments": [
    {
      "path": "src/hooks/useKycNavigation.ts",
      "position": 42,
      "body": "**Bug:** explanation of the problem and why it matters..."
    }
  ]
}
```

- `review_body` — required; top-level review summary
- `comments` — inline diff comments; may be empty `[]` for a body-only review
- `position` — diff position (not line number); use `get-positions` to convert `file:line → position`

**Files not in the diff** cannot have inline comments. Put observations about missing files/types/exports in `review_body` instead.

## Tool Reference

### scan-violations

Auto-detect checklist violations in PR changed files.

> **`--post` skips file review — never use it.** Always `--output "$review"`, inspect, then `post-review --input`.

```bash
# Preview only (recommended first step)
uv run scan-violations owner/repo 42 --dry-run

# Generate review payload
review=$(mktemp -t review-42-XXXX.json)
uv run scan-violations owner/repo 42 \
    --checklist ${CLAUDE_SKILL_DIR}/references/review-checklist.md \
    --output "$review"

# Scan only specific file types
uv run scan-violations owner/repo 42 \
    --file-pattern "*.tsx" --file-pattern "*.ts"
```

**Options:** `--checklist FILE`, `--file-pattern P`, `--output FILE`, `--dry-run`

### get-positions

Convert file:line to GitHub diff position (required for API).

```bash
uv run get-positions owner/repo 42 src/hooks.ts:45 src/utils.ts:12
# Output: src/hooks.ts:45 → position 127

# From file (one per line)
uv run get-positions owner/repo 42 --file refs.txt
```

### post-review

Post batched review with inline comments. **Always batch—never post one at a time.**

`review_body` must be set in the input JSON file — there is no `--review-body` flag.

```bash
# Batch from file (recommended)
uv run post-review owner/repo 42 --input "$review" --event REQUEST_CHANGES

# Body-only review (no inline comments)
uv run post-review owner/repo 42 --input "$review"

# Single inline comment (anti-pattern — creates separate review entry)
uv run post-review owner/repo 42 \
    --i-know-this-creates-separate-review \
    --path src/hooks.ts --position 42 \
    --body "Add useCallback"
```

**Events:** `COMMENT` (default), `APPROVE`, `REQUEST_CHANGES`

### build-review

Build review incrementally. `review_body` is stored in the payload file — set it once with `--summary-file FILE`.

```bash
review=$(mktemp -t review-42-XXXX.json)
summary=$(mktemp -t summary-42-XXXX.md)
uv run build-review --file "$review" --summary-file "$summary"
uv run build-review --file "$review" --path src/a.ts --position 5 --body "Fix A"
uv run build-review --file "$review" --show                    # Preview
uv run build-review --file "$review" --post owner/repo 42 --event REQUEST_CHANGES
```

**Options:** `--file`, `--summary-file`, `--path`, `--position`, `--body`, `--body-file`, `--show`, `--export-comments`, `--clear`, `--post`

## Examples

**Example 1: Auto-scan workflow**

```bash
review=$(mktemp -t review-42-XXXX.json)
uv run scan-violations owner/repo 42 --checklist ${CLAUDE_SKILL_DIR}/references/review-checklist.md --output "$review"
# Edit $review: update review_body, trim false positives
uv run post-review owner/repo 42 --input "$review" --event REQUEST_CHANGES
```

**Example 2: Manual review with position helper**

```bash
review=$(mktemp -t review-42-XXXX.json)
uv run get-positions owner/repo 42 src/hooks.ts:45 src/utils.ts:12 src/api.ts:88
# Write $review with review_body + comments using the returned positions
uv run post-review owner/repo 42 --input "$review" --event REQUEST_CHANGES
```

**Example 3: Incremental review building**

```bash
review=$(mktemp -t review-42-XXXX.json)
summary=$(mktemp -t summary-42-XXXX.md)
uv run build-review --file "$review" --summary-file "$summary"
uv run build-review --file "$review" --path src/auth.ts --position 15 --body "Add useMemo"
uv run build-review --file "$review" --path src/utils.ts --position 42 --body-file complex_suggestion.md
uv run build-review --file "$review" --show
uv run build-review --file "$review" --post owner/repo 42 --event REQUEST_CHANGES
```

**Example 4: Approve a PR**

```bash
# Pure approval — review_body in JSON set to "LGTM"
review=$(mktemp -t review-42-XXXX.json)
uv run post-review owner/repo 42 --input "$review" --event APPROVE
```

**Example 5: Plain comment (not a review)**

```bash
comment=$(mktemp -t comment-42-XXXX.md)
gh pr comment owner/repo#42 --body-file "$comment"
```
