# Workflow: Respond to Review Comments on Your PR

Reply to and react on review comments left on your PR.

## When to Use This

- Addressing feedback on your own PR
- Bulk-acknowledging review comments
- Adding reactions to show you've seen comments

## Workflow

### Step 1: List Comments to See What Needs Response

```bash
uv run reply-review owner/repo 45 --list
```

**Output:**

```
3 Review Comments
┌────────────┬─────────────────┬──────┬──────────┬────────────────────────────┐
│ ID         │ File            │ Line │ Author   │ Body Preview               │
├────────────┼─────────────────┼──────┼──────────┼────────────────────────────┤
│ 2983284330 │ src/hooks.ts    │ 42   │ reviewer │ Add useCallback here for...│
│ ...        │ ...             │ ...  │ ...      │ ...                        │
└────────────┴─────────────────┴──────┴──────────┴────────────────────────────┘
```

### Step 2: Respond to Comments

**Option A: Reply to specific comments**

```bash
# Simple reply
uv run reply-review owner/repo 45 2983284330 "Fixed in commit abc123"

# Reply with reaction
uv run reply-review owner/repo 45 2983284330 "Handled" --react +1

# Just react (no text)
uv run reply-review owner/repo 45 2983284330 --react eyes
```

**Option B: Bulk reply to all comments**

```bash
# Reply to all with same prefix (skips your own comments)
uv run reply-review owner/repo 45 --reply-all --prefix "✅ Fixed"

# With prefix and suffix
uv run reply-review owner/repo 45 --reply-all \
    --prefix "✅ Handled" \
    --suffix "Please re-review"
```

**Option C: Bulk react to all comments**

```bash
# React 👍 to all review comments
uv run reply-review owner/repo 45 --react-all +1

# React 👀 to show you're reviewing
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

| Error                              | Fix                           |
| ---------------------------------- | ----------------------------- |
| "GitHub CLI not authenticated"     | Run `gh auth login`           |
| "Could not determine current user" | Token needs `read:user` scope |

## Complete Example

```bash
# 1. See what needs response
uv run reply-review owner/repo 45 --list

# 2. Acknowledge with reactions
uv run reply-review owner/repo 45 --react-all eyes

# 3. Fix issues, commit

# 4. Reply to all with resolution status
uv run reply-review owner/repo 45 --reply-all \
    --prefix "✅ Fixed in commit abc123" \
    --suffix "Please re-review"

# 5. If some items deferred, reply individually
uv run reply-review owner/repo 45 9876543210 \
    "Will address in follow-up PR - tracked in issue #123"
```

## Difference from Posting Reviews

|               | This Workflow                    | Posting Reviews                      |
| ------------- | -------------------------------- | -------------------------------------|
| **Your role** | PR author responding to feedback | Reviewer giving feedback             |
| **Action**    | Reply to existing comments       | Create new review with comments       |
| **Tool**      | `reply-review`                   | `post-review` / `scan-violations`    |
| **Result**    | Threaded replies under comments  | New review on PR timeline            |
