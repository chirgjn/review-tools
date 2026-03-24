# Workflow: Review a PR → Post Comments

Perform a checklist-based code review and post **batched** comments.

## Core Principles

| Principle              | Why                                                               | Enforcement                                                  |
| ---------------------- | ----------------------------------------------------------------- | ------------------------------------------------------------ |
| **File-first**         | GitHub comments are permanent—review before posting               | `--input FILE` required for batch                            |
| **Batching**           | One review per PR, not one per comment (permanent timeline noise) | Inline multiple comments errors                              |
| **No inline `--body`** | Hard to write, easy to break quotes, can't review                 | `--body-file` preferred                                      |
| **Explain WHY**        | Teach the consequence so author learns                            | ≥10 words (except LGTM, Approved, Done, Fixed, Acknowledged) |

| ✗ Don't          | ✓ Do                                                                |
| ---------------- | ------------------------------------------------------------------- |
| "Add dependency" | "Missing 'onChange' causes stale closure when prop updates"         |
| "Fix type"       | "Returns Promise<void> but caller expects User[]. Match interface." |

## The Workflow: File First, Then Post

```bash
# STEP 1: Build/scan and SAVE TO FILE
uv run scan-violations owner/repo 42 \
    --checklist docs/review-checklist.md \
    --output review.json

# STEP 2: Review the file (optional but recommended)
cat review.json | jq '.comments[] | {path: .path, body: .body}'

# STEP 3: Post batched review via --input
uv run post-review owner/repo 42 \
    --input review.json \
    --review-body "Checklist review - 5 items need attention" \
    --event REQUEST_CHANGES
```

**Avoid:** Immediate post, multiple reviews (timeline spam), or piping inline.

## Workflows

### A. Auto-Scan (Recommended)

```bash
# 1. Preview what the tool finds
uv run scan-violations owner/repo 42 --dry-run

# 2. Generate review payload with checklist and SAVE TO FILE
uv run scan-violations owner/repo 42 \
    --checklist docs/review-checklist.md \
    --output review_payload.json

# 3. Review the generated payload manually
# 4. Post when ready via --input
uv run post-review owner/repo 42 \
    --input review_payload.json \
    --review-body "Checklist violations" \
    --event REQUEST_CHANGES
```

**Built-in detection:** Missing deps, floating promises, `as any`, barrel imports, missing `img alt`, file-level eslint-disable, manual URL concat.

### B. Manual (for auto-scanner misses)

```bash
# Convert file:line to diff position, then post
uv run get-positions owner/repo 42 src/hooks.ts:45  # → position 127
uv run post-review owner/repo 42 \
    --path src/hooks.ts --position 127 \
    --body "Add useCallback here" \
    --review-body "Performance suggestion"
```

### C. Incremental Build (complex reviews)

```bash
# Add comments over time
uv run build-review --path src/a.ts --position 42 --body "Fix A"
uv run build-review --path src/b.ts --position 15 --body-file comment_b.md
uv run build-review --show      # Preview
uv run build-review --post owner/repo 42 --review-body "Review" --event REQUEST_CHANGES
```

## Tool Reference

### scan-violations

Auto-detect checklist violations in PR changed files.

```bash
# Preview only (recommended first step)
uv run scan-violations owner/repo 42 --dry-run

# Generate review payload
uv run scan-violations owner/repo 42 \
    --checklist docs/review-checklist.md \
    --output review.json

# Scan only specific file types
uv run scan-violations owner/repo 42 \
    --file-pattern "*.tsx" --file-pattern "*.ts"

# ⚠️ Post directly (skips file review - use with caution)
# Better: Use --output and review before posting
uv run scan-violations owner/repo 42 \
    --checklist docs/review-checklist.md \
    --output review.json
# Then: uv run post-review ... --input review.json
```

**Options:** `--checklist FILE`, `--file-pattern P`, `--output FILE`, `--dry-run`, `--post`

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

```bash
# Single short comment
uv run post-review owner/repo 42 \
    --path src/hooks.ts --position 42 \
    --body "Add useCallback" \
    --review-body "Suggestion"

# From file (for complex markdown, no escaping)
uv run post-review owner/repo 42 \
    --path src/hooks.ts --position 42 \
    --body-file comment.txt \
    --review-body "See inline"

# Multiple comments via JSON
uv run post-review owner/repo 42 \
    --input review.json \
    --review-body "Items" --event REQUEST_CHANGES

# Via heredoc (no escaping, supports markdown)
uv run post-review owner/repo 42 \
    --review-body "Review" --event REQUEST_CHANGES \
    --input - << 'EOF'
[
  {"path": "src/hooks.ts", "position": 42, "body": "Use `useCallback`"},
  {"path": "src/utils.ts", "position": 8, "body": "Type this"}
]
EOF
```

**Events:** `COMMENT` (default), `APPROVE`, `REQUEST_CHANGES`

### build-review

Build review incrementally.

```bash
uv run build-review --path src/a.ts --position 5 --body "Fix A"
uv run build-review --show                    # Preview
uv run build-review --post owner/repo 42 \
    --review-body "Review" --event REQUEST_CHANGES
```

**Options:** `--file`, `--path`, `--position`, `--body`, `--body-file`, `--show`, `--export-comments`, `--clear`, `--post`

## Examples

**Example 1: Auto-scan workflow**

```bash
# Scan, review output, post
uv run scan-violations owner/repo 42 --checklist docs/review-checklist.md --output review.json
# ... manually review review.json ...
uv run post-review owner/repo 42 \
    --input review.json \
    --review-body "Checklist violations" \
    --event REQUEST_CHANGES
```

**Example 2: Manual review with position helper**

```bash
# Find 3 issues, get positions, post batch
uv run get-positions owner/repo 42 src/hooks.ts:45 src/utils.ts:12 src/api.ts:88 > positions.txt
# Extract positions and build JSON comments...
uv run post-review owner/repo 42 \
    --review-body "Checklist review" \
    --event REQUEST_CHANGES \
    --input - << 'EOF'
[
  {"path": "src/hooks.ts", "position": 127, "body": "Add useCallback"},
  {"path": "src/utils.ts", "position": 45, "body": "Type this error"},
  {"path": "src/api.ts", "position": 203, "body": "Handle error case"}
]
EOF
```

**Example 3: Incremental review building**

```bash
# Review over time
uv run build-review --path src/auth.ts --position 15 --body "Add useMemo"
# ... later ...
uv run build-review --path src/utils.ts --position 42 --body-file complex_suggestion.md
# ... when done ...
uv run build-review --show
uv run build-review --post owner/repo 42 --review-body "Review" --event REQUEST_CHANGES
```

**Example 4: Approve a PR**

```bash
# Pure approval (no inline comments)
uv run post-review owner/repo 42 \
    --review-body "LGTM" \
    --event APPROVE

# Approve with minor comments (batched)
uv run post-review owner/repo 42 \
    --input review.json \
    --review-body "Approved with nits" \
    --event APPROVE
```
