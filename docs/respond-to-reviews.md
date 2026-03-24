# Workflow: Respond to Review Comments on Your PR

Reply to and react on review feedback.

## Workflow

### 1. List Comments

**Quick preview (IDs, author, truncated body):**

```bash
uv run reply-review owner/repo 45 --list
```

**With full context (recommended):**

```bash
uv run reply-review owner/repo 45 --list --with-context
```

Shows: Full comment body, diff context around the line, thread replies.

### 2. Inspect Deeply (Before Replying)

For complex threads, inspect a specific comment first:

```bash
uv run reply-review owner/repo 45 --inspect 1234567890
```

Shows: Full body, complete diff hunk, thread history, metadata.

### 3. Respond

**Single:**

```bash
uv run reply-review owner/repo 45 2983284330 "Fixed"
uv run reply-review owner/repo 45 2983284330 "Handled" --react +1
uv run reply-review owner/repo 45 2983284330 --react eyes
```

**React to all (acknowledges feedback):**

```bash
uv run reply-review owner/repo 45 --react-all eyes
```

> **Note:** Avoid using `--reply-all` with generic prefixes like "✅ Fixed". Match reply quality to complexity — use individual replies with specific context like "Extracted to helper" for complex changes.

## Tool Reference

### reply-review

Reply to and react on PR review comments.

```bash
# List comments (preview mode)
uv run reply-review owner/repo 45 --list

# List with full context (body + diff)
uv run reply-review owner/repo 45 --list --with-context

# Deep inspect a specific comment
uv run reply-review owner/repo 45 --inspect <comment_id>

# Reply to single comment
uv run reply-review owner/repo 45 <comment_id> "Your message"

# Reply and react together
uv run reply-review owner/repo 45 <comment_id> "Handled" --react +1

# React only
uv run reply-review owner/repo 45 <comment_id> --react eyes

# Reply with specific context (preferred for complex items)
uv run reply-review owner/repo 45 <comment_id> "Extracted to helper as suggested"

# React to all comments (skips your own)
uv run reply-review owner/repo 45 --react-all +1
```

**Emojis:** `+1`, `-1`, `laugh`, `confused`, `heart`, `hooray`, `eyes`, `rocket`

**Reply-all options:**

- `--prefix TEXT` — Prefix all replies
- `--suffix TEXT` — Suffix all replies

**Behaviors:**

- `--reply-all` and `--react-all` skip your own comments (auto-detected)
- `--list --with-context` shows full body + last 8 lines of diff
- `--inspect` shows complete diff hunk + thread history
- Replies appear as threaded responses under original comment
- Reactions are idempotent (reacting twice = same as once)

## Reply Quality

Help reviewers verify fixes quickly:

| Situation  | Reply                                        |
| ---------- | -------------------------------------------- |
| Simple fix | "Done", "Fixed", "Resolved"                  |
| Complex    | "Extracted to helper as suggested"           |
| Deferred   | "Will fix in follow-up PR - tracked in #123" |
| Unclear    | Ask for clarification                        |

**Avoid:** Commit SHAs (break on rebase), vague "OK", reacting when code changes are needed.

## Common Patterns

**Pattern 1: Full context workflow (recommended)**

```bash
# See everything before deciding
uv run reply-review owner/repo 45 --list --with-context

# Inspect complex ones deeply
uv run reply-review owner/repo 45 --inspect 1111111111

# Respond with confidence
uv run reply-review owner/repo 45 1111111111 "Extracted to helper as suggested"
uv run reply-review owner/repo 45 2222222222 "Fixed"
```

**Pattern 2: Acknowledge all feedback quickly**

```bash
uv run reply-review owner/repo 45 --list
uv run reply-review owner/repo 45 --react-all eyes
```

**Pattern 3: Request re-review after fixes**

```bash
# Reply individually with context, then add PR comment
uv run reply-review owner/repo 45 1111111111 "Extracted helper function"
uv run reply-review owner/repo 45 2222222222 "Added error handling as suggested"
gh pr comment owner/repo 45 --body "Fixed all items - PTAL"
```

**Pattern 4: Selective responses**

```bash
# List with context first
uv run reply-review owner/repo 45 --list --with-context

# Respond to specific ones differently
uv run reply-review owner/repo 45 1111111111 "Fixed"
uv run reply-review owner/repo 45 2222222222 "Will do in follow-up PR" --react +1
uv run reply-review owner/repo 45 3333333333 "Discussed offline - resolving"
```

## Requirements

- `gh auth login` (authenticated)

## Troubleshooting

| Error                              | Fix                           |
| ---------------------------------- | ----------------------------- |
| "GitHub CLI not authenticated"     | `gh auth login`               |
| "Could not determine current user" | Token needs `read:user` scope |

## Example

```bash
# Full context workflow
uv run reply-review owner/repo 45 --list --with-context

# Inspect a complex thread
uv run reply-review owner/repo 45 --inspect 1111111111

# Respond with context
uv run reply-review owner/repo 45 1111111111 "Extracted helper function"
uv run reply-review owner/repo 45 2222222222 "Fixed"

# Acknowledge remaining feedback
uv run reply-review owner/repo 45 --react-all eyes

# Deferred items
uv run reply-review owner/repo 45 3333333333 "Will address in follow-up PR - tracked in #123"
```

## vs Posting Reviews

|               | This Workflow                    | Posting Reviews                   |
| ------------- | -------------------------------- | --------------------------------- |
| **Your role** | PR author responding to feedback | Reviewer giving feedback          |
| **Action**    | Reply to existing comments       | Create new review with comments   |
| **Tool**      | `reply-review`                   | `post-review` / `scan-violations` |
| **Result**    | Threaded replies under comments  | New review on PR timeline         |
