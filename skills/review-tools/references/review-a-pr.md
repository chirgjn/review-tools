# Review a PR → Post Comments

Perform a checklist-based code review and post **batched** comments.

## Artifact Naming

Use `mktemp` to generate unique paths — avoids collisions when running parallel reviews. Include the PR number in the template for traceability:

```bash
review=$(mktemp -t review-42-XXXX.json)
summary=$(mktemp -t summary-42-XXXX.md)
```

## Review Workflows

### A. Auto-Scan

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

### B. Manual Review

```bash
# 1. Get diff positions with content preview
uv run get-positions owner/repo 42 "src/hooks.ts:45:useEffect("
# → [{"path":"src/hooks.ts","line":45,"position":127,"content_preview":"useEffect(() => {...}"}]

# Extract position and content
result=$(uv run get-positions owner/repo 42 "src/hooks.ts:45:useEffect(")
position=$(echo "$result" | jq -r '.[0].position')
content=$(echo "$result" | jq -r '.[0].content_preview')

# 2. Build review with content hint (for verification)
review=$(mktemp -t review-42-XXXX.json)
uv run build-review --file "$review" \
  --path src/hooks.ts --line 45 --position "$position" \
  --content "$content" \
  --body "Add dependency array"

# 3. Post (automatically verifies)
uv run post-review owner/repo 42 --input "$review" --event REQUEST_CHANGES
```

### C. Incremental Build

```bash
# Set the review summary first (write it to a temp file)
summary=$(mktemp -t summary-42-XXXX.md)
review=$(mktemp -t review-42-XXXX.json)
uv run build-review --file "$review" --summary-file "$summary"

# Add comments over time (with content hints for verification)
uv run build-review --file "$review" --path src/a.ts --line 42 --position 48 --content "useEffect(()" --body "Fix A"
uv run build-review --file "$review" --path src/b.ts --line 15 --position 21 --content "const config" --body-file comment_b.md
uv run build-review --file "$review" --show      # Preview

# Post (automatically verifies)
uv run post-review owner/repo 42 --input "$review" --event REQUEST_CHANGES
```

### D. Plain PR Comment

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
      "file_line": 45,
      "position": 42,
      "content_hint": "useEffect(()",
      "body": "**Bug:** explanation of the problem and why it matters..."
    }
  ]
}
```

- `review_body` — required; top-level review summary
- `comments` — inline diff comments; may be empty `[]` for a body-only review
- `file_line` — **source file line number** (informational only; for human reference when editing the JSON)
- `position` — **GitHub diff position** (required by the API); use `get-positions` to convert `file:line:content → position` (outputs JSON). Extract with `jq -r '.[0].position'`. This is a per-file counter over the unified diff, not a line number.
- `content_hint` — **content preview for verification** (first 20 words of the line). Stored by `build-review`, checked by `post-review` before submitting. Prevents commenting on wrong lines.

`file_line` and `position` are separate because GitHub's API requires a diff position, not a line number. `scan-violations` and `build-review` populate both; `post-review` verifies `content_hint` matches the actual line content, then strips it before posting to GitHub.

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

Convert file:line:content to GitHub diff position (required for API).
Always outputs JSON array with content preview.

```bash
uv run get-positions owner/repo 42 "src/hooks.ts:45:useEffect("
# → [{"path":"src/hooks.ts","line":45,"position":127,"content_preview":"useEffect(() => {...}"}]

# Multiple positions
uv run get-positions owner/repo 42 "src/a.ts:10:const x" "src/b.ts:20:function"

# Extract position and content for build-review
result=$(uv run get-positions owner/repo 42 "src/hooks.ts:45:useEffect(")
position=$(echo "$result" | jq -r '.[0].position')
content=$(echo "$result" | jq -r '.[0].content_preview')

# From file (one per line, format: file:line:content)
uv run get-positions owner/repo 42 --file refs.txt
```

### post-review

Post batched review with inline comments. **Always batch—never post one at a time.**
**Automatically verifies positions** against stored content hints before posting.

`review_body` must be set in the input JSON file — there is no `--review-body` flag.

```bash
# Batch from file (recommended) — auto-verifies before posting
uv run post-review owner/repo 42 --input "$review" --event REQUEST_CHANGES
# → ✓ All positions verified
# → ✓ Posted: https://github.com/...

# Verification failure (content doesn't match)
# → ✗ Verification failed: content mismatch at src/hooks.ts:45
# → Expected: useEffect(()  Actual: const x = 1

# Body-only review (no inline comments)
uv run post-review owner/repo 42 --input "$review"

# Single inline comment (anti-pattern — creates separate review entry)
# --content required for verification
uv run post-review owner/repo 42 \
    --i-know-this-creates-separate-review \
    --path src/hooks.ts --position 42 --content "useEffect(()" \
    --body "Add useCallback"

```

**Events:** `COMMENT` (default), `APPROVE`, `REQUEST_CHANGES`

### build-review

Build review incrementally. `review_body` is stored in the payload file — set it once with `--summary-file FILE`.
**--content is required** for verification (first 20 words of the line).

```bash
review=$(mktemp -t review-42-XXXX.json)
summary=$(mktemp -t summary-42-XXXX.md)
uv run build-review --file "$review" --summary-file "$summary"

# Add comment with content hint (required for verification)
uv run build-review --file "$review" \
  --path src/a.ts --line 45 --position 5 \
  --content "useEffect(()" \
  --body "Fix A"

uv run build-review --file "$review" --show                    # Preview

# Post (build-review --post also verifies; or use post-review)
uv run build-review --file "$review" --post owner/repo 42 --event REQUEST_CHANGES
```

**Options:** `--file`, `--summary-file`, `--path`, `--line`, `--position`, `--content`, `--body`, `--body-file`, `--show`, `--export-comments`, `--clear`, `--post`

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

# Get positions with content preview
result=$(uv run get-positions owner/repo 42 "src/hooks.ts:45:useEffect(")
position=$(echo "$result" | jq -r '.[0].position')
content=$(echo "$result" | jq -r '.[0].content_preview')

# Build review with content hint
uv run build-review --file "$review" \
  --path src/hooks.ts --line 45 --position "$position" \
  --content "$content" \
  --body "Add dependency array to prevent stale closure"

# Post (auto-verifies)
uv run post-review owner/repo 42 --input "$review" --event REQUEST_CHANGES
```

**Example 3: Incremental review building**

```bash
review=$(mktemp -t review-42-XXXX.json)
summary=$(mktemp -t summary-42-XXXX.md)
uv run build-review --file "$review" --summary-file "$summary"
uv run build-review --file "$review" --path src/auth.ts --line 15 --position 21 --content "const auth" --body "Add useMemo"
uv run build-review --file "$review" --path src/utils.ts --line 42 --position 48 --content "export function" --body-file complex_suggestion.md
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
