# Workflow: Review a PR → Post Comments

Perform a checklist-based code review and post **batched** comments.

## Core Intentions (Why We Built It This Way)

### 1. File-First Workflow
**Intention:** Comments should be reviewable before posting.  
**Why:** Once posted to GitHub, review comments are permanent. You should be able to read, edit, and validate your feedback before it goes live.

### 2. Batching is Mandatory  
**Intention:** One review per PR, not one review per comment.  
**Why:** GitHub creates **permanent timeline entries** for each review. Posting 5 separate reviews creates 5 timeline entries that clutter history forever.

### 3. Discourage Inline Command-Line Comments
**Intention:** Substantive comments should come from files, not command-line arguments.  
**Why:** `--body "long text here"` is hard to write, easy to mess up quotes, and impossible to review. Write to a file, review it, then post.

---

> ⚠️ **CRITICAL: Always batch comments into ONE review.**  
> GitHub creates **permanent timeline entries** for each review. Posting comments one at a time creates noise that can't be undone.

## When to Use This

- Reviewing a teammate's PR against your checklist
- Want to auto-detect common violations before manual review
- **Batching multiple inline comments** into a single review (recommended)
- ⚠️ Avoid: Posting single comments (creates permanent timeline noise)

## The Golden Rule: File First, Then Post

**✓ ALWAYS:** Save comments to file, review, then post:
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

**✗ NEVER:** Skip the file step or post multiple times:
```bash
# WRONG: Immediate post (no chance to review)
uv run scan-violations owner/repo 42 --post

# WRONG: Multiple separate reviews (timeline spam)
uv run post-review ... --path a.ts --body "Fix A"
uv run post-review ... --path b.ts --body "Fix B"

# WRONG: Piping inline (hard to review, easy to mess up)
uv run post-review ...
```

## Workflow

### Option A: Auto-Scan for Violations (Recommended First Step)

```bash
# 1. Preview what the tool finds
uv run scan-violations owner/repo 42 --dry-run

# 2. Generate review payload with checklist and SAVE TO FILE
uv run scan-violations owner/repo 42 \
    --checklist docs/review-checklist.md \
    --output review_payload.json

# 3. Review the generated payload manually
# 4. Post when ready via --input (not
uv run post-review owner/repo 42 \
    --input review_payload.json \
    --review-body "Checklist violations" \
    --event REQUEST_CHANGES
```

**Built-in detection:**

- Missing useEffect/useCallback dependency arrays
- Floating promises (not awaited)
- File-level eslint-disable
- `as any` type casts
- Barrel imports (from index.ts)
- Missing img alt attributes
- Manual URL string concatenation

### Option B: Manual Review with Position Helper

For issues the auto-scanner doesn't catch:

```bash
# 1. Identify issue at file:line (e.g., src/hooks.ts line 45)
# 2. Get diff position
uv run get-positions owner/repo 42 src/hooks.ts:45
# Output: src/hooks.ts:45 → position 127

# 3. Post single comment
uv run post-review owner/repo 42 \
    --path src/hooks.ts --position 127 \
    --body "Add useCallback here" \
    --review-body "Performance suggestion"
```

### Option C: Build Review Incrementally

For complex reviews built over multiple passes:

```bash
# Add comments as you find them
uv run build-review --path src/a.ts --position 42 --body "Fix A"
uv run build-review --path src/b.ts --position 15 --body-file comment_b.md

# Preview before posting
uv run build-review --show

# Post when ready
uv run build-review --post owner/repo 42 \
    --review-body "Checklist review" --event REQUEST_CHANGES
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

**Options:**

- `--checklist FILE` — Use custom checklist (default: built-in patterns)
- `--file-pattern P` — Only scan files matching regex (multiple OK)
- `--output FILE` — Save review payload to JSON
- `--dry-run` — Preview violations without generating payload
- `--post` — Post review directly
- `--review-body TEXT` — Review summary (default: "Automated checklist review")

**Output payload format:**

```json
{
  "commit_id": "abc123...",
  "body": "Review summary",
  "event": "COMMENT",
  "comments": [
    { "path": "src/file.ts", "position": 42, "body": "**Rule**\\n\\nMessage" }
  ]
}
```

### get-positions

Convert file:line to GitHub diff position.

```bash
# Single reference
uv run get-positions owner/repo 42 src/hooks.ts:45

# Multiple references
uv run get-positions owner/repo 42 src/hooks.ts:45 src/utils.ts:12

# From file (one per line, # comments OK)
cat > refs.txt << 'EOF'
src/hooks.ts:45
src/utils.ts:12
EOF
uv run get-positions owner/repo 42 --file refs.txt

# JSON output for scripting
uv run get-positions owner/repo 42 src/hooks.ts:45 --json
```

**Output:** `src/hooks.ts:45 → position 127`

**Why needed:** GitHub API requires diff position (line in unified diff from `@@` header), not file line number.

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
   
    --review-body "Items" --event REQUEST_CHANGES

# Via heredoc (no escaping, supports markdown)
uv run post-review owner/repo 42 \
    --review-body "Review" --event REQUEST_CHANGES \
   
[
  {"path": "src/hooks.ts", "position": 42, "body": "Use `useCallback`"},
  {"path": "src/utils.ts", "position": 8, "body": "Type this"}
]
EOF
```

**Event types:** `COMMENT` (default), `APPROVE`, `REQUEST_CHANGES`

**Rules:**

- Always batch comments into one call
- Never post comments one at a time (creates permanent timeline noise)

### build-review

Build review payload incrementally.

```bash
# Add comments
uv run build-review --path src/a.ts --position 5 --body "Fix A"
uv run build-review --path src/b.ts --position 10 --body-file complex.md

# View current payload
uv run build-review --show

# Post
uv run build-review --post owner/repo 42 \
    --review-body "Review" --event REQUEST_CHANGES

# Or export for post-review
uv run build-review --export-comments | \
    uv run post-review owner/repo 42
```

**Options:**

- `--file FILE` — Payload file (default: review_payload.json)
- `--path P`, `--position N`, `--body TEXT` — Add comment
- `--body-file FILE` — Read body from file
- `--show` — Display current payload
- `--export-comments` — Output comments array only
- `--clear` — Clear all comments
- `--post REPO PR` — Post review
- `--review-body TEXT` — Review summary
- `--event TYPE` — COMMENT, APPROVE, REQUEST_CHANGES

## Position vs Line Number

GitHub API needs **diff position**, not file line number:

```
File line 45                    ← What you see in editor
       ↓
  get-positions
       ↓
Diff position 127               ← What GitHub API needs
```

**Workflow:**

1. Find issue at `src/hooks.ts:45`
2. Run `./get-positions owner/repo 42 src/hooks.ts:45` → outputs `position 127`
3. Use `--position 127` in `post-review`

## Complete Examples

**Example 1: Auto-scan workflow**

```bash
# Scan, review output, post
uv run scan-violations owner/repo 42 --checklist docs/review-checklist.md --output review.json
# ... manually review review.json ...
uv run post-review owner/repo 42 \
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
