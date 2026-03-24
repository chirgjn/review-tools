# Workflow: Respond to Review Comments on Your PR

Reply to and react on review feedback.

## Workflow

### 1. List Comments

```bash
uv run reply-review owner/repo 45 --list
```

Shows: ID, file, line, author, preview.

### 2. Respond

**Single:**
```bash
uv run reply-review owner/repo 45 2983284330 "Fixed"
uv run reply-review owner/repo 45 2983284330 "Handled" --react +1
uv run reply-review owner/repo 45 2983284330 --react eyes
```

**Bulk (skips your own):**
```bash
uv run reply-review owner/repo 45 --reply-all --prefix "✅ Fixed"
uv run reply-review owner/repo 45 --react-all eyes
```

## Tool Reference

### reply-review

Reply to and react on PR review comments.

```bash
# List all comments with IDs
uv run reply-review owner/repo 45 --list

# Reply to single comment
uv run reply-review owner/repo 45 <comment_id> "Your message"

# Reply and react together
uv run reply-review owner/repo 45 <comment_id> "Handled" --react +1

# React only
uv run reply-review owner/repo 45 <comment_id> --react eyes

# Reply to all comments (skips your own)
uv run reply-review owner/repo 45 --reply-all --prefix "✅ Fixed"

# React to all comments (skips your own)
uv run reply-review owner/repo 45 --react-all +1
```

**Emojis:** `+1`, `-1`, `laugh`, `confused`, `heart`, `hooray`, `eyes`, `rocket`

**Reply-all options:**

- `--prefix TEXT` — Prefix all replies
- `--suffix TEXT` — Suffix all replies

**Behaviors:**

- `--reply-all` and `--react-all` skip your own comments (auto-detected)
- Replies appear as threaded responses under original comment
- Reactions are idempotent (reacting twice = same as once)

## Reply Quality

Help reviewers verify fixes quickly:

| Situation | Reply |
|-----------|-------|
| Simple fix | "Done", "Fixed", "Resolved" |
| Complex | "Extracted to helper as suggested" |
| Deferred | "Will fix in follow-up PR - tracked in #123" |
| Unclear | Ask for clarification |

**Avoid:** Commit SHAs (break on rebase), vague "OK", reacting when code changes are needed.

## Common Patterns

**Pattern 1: Acknowledge all feedback quickly**

```bash
uv run reply-review owner/repo 45 --list
uv run reply-review owner/repo 45 --react-all eyes
```

**Pattern 2: Fixed everything, request re-review**

```bash
uv run reply-review owner/repo 45 --reply-all \
    --prefix "✅ Fixed" \
    --suffix "PTAL"
```

**Pattern 3: Selective responses**

```bash
# List first
uv run reply-review owner/repo 45 --list

# Respond to specific ones differently
uv run reply-review owner/repo 45 1111111111 "Fixed"
uv run reply-review owner/repo 45 2222222222 "Will do in follow-up PR" --react +1
uv run reply-review owner/repo 45 3333333333 "Discussed offline - resolving"
```

## Requirements

- `gh auth login` (authenticated)

## Troubleshooting

| Error | Fix |
|-------|-----|
| "GitHub CLI not authenticated" | `gh auth login` |
| "Could not determine current user" | Token needs `read:user` scope |

## Example

```bash
# Acknowledge
uv run reply-review owner/repo 45 --list
uv run reply-review owner/repo 45 --react-all eyes

# After fixes
uv run reply-review owner/repo 45 --reply-all --prefix "✅ Fixed" --suffix "PTAL"

# Deferred items
uv run reply-review owner/repo 45 9876543210 "Will address in follow-up PR - tracked in #123"
```

## vs Posting Reviews

|               | This Workflow                    | Posting Reviews                      |
| ------------- | -------------------------------- | -------------------------------------|
| **Your role** | PR author responding to feedback | Reviewer giving feedback             |
| **Action**    | Reply to existing comments       | Create new review with comments       |
| **Tool**      | `reply-review`                   | `post-review` / `scan-violations`    |
| **Result**    | Threaded replies under comments  | New review on PR timeline            |
