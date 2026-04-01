# Respond to Review Comments

You're the PR author and someone has left comments on your PR. Use this to list, inspect, and reply to feedback.
For giving feedback on someone else's PR, see `review-a-pr.md` instead.

## Reaction Protocol (How to Use Reactions)

Use reactions to communicate your intent clearly to reviewers:

| Reaction | Meaning | When to Use |
|----------|---------|-------------|
| 👀 `eyes` | "I've seen this" | React when you first read/acknowledge a comment. Signals you're aware of the feedback. |
| 👍 `+1` (thumbs up) | "I agree, and it's done" | Reply with the fix, then react with +1 to confirm it's addressed. |
| 👎 `-1` (thumbs down) | "I disagree" | React when you believe the comment is incorrect or not applicable. Reply explaining why. |

**Workflow:**
1. Read comment → react `eyes` (acknowledged)
2. Fix the issue → reply with what you changed → react `+1` (done)
3. Disagree → react `-1` → reply explaining your reasoning

## Response Workflow

### 1. List All Comments

**Quick preview (IDs, author, truncated body):**

```bash
uv run reply-review owner/repo 45 --list
```

**With full context (recommended):**

```bash
uv run reply-review owner/repo 45 --list --with-context
```

Shows: Full comment body, diff context around the line, thread replies.

### 2. Inspect Before Replying

For complex threads, inspect a specific comment first:

```bash
uv run reply-review owner/repo 45 --inspect 1234567890
```

Shows: Full body, complete diff hunk, thread history, metadata.

### 3. Send Replies

> **Never use `--reply-all`** — mass replies with generic text ("✅ Fixed") make it impossible for reviewers to verify what changed. Reply individually with specific context.

**Single reply:**

```bash
uv run reply-review owner/repo 45 2983284330 "Fixed"
uv run reply-review owner/repo 45 2983284330 "Handled" --react +1
uv run reply-review owner/repo 45 2983284330 --react eyes
```

**React to all (acknowledge without replying — use when you need more time):**

```bash
uv run reply-review owner/repo 45 --react-all eyes
```

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

**`--reply-all` — do not use.** Options exist but mass replies degrade review signal:

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

**Pattern 1: Reaction Protocol Workflow (recommended for clarity)**

```bash
# 1. First, acknowledge all comments you've read
uv run reply-review owner/repo 45 --list --with-context
uv run reply-review owner/repo 45 1111111111 --react eyes  # Acknowledged
uv run reply-review owner/repo 45 2222222222 --react eyes  # Acknowledged

# 2. After fixing, reply and mark as done with +1
uv run reply-review owner/repo 45 1111111111 "Extracted to helper as suggested" --react +1
uv run reply-review owner/repo 45 2222222222 "Fixed lock check by adding lock_acquired parameter" --react +1

# 3. If you disagree with a comment
uv run reply-review owner/repo 45 3333333333 "This is test-only code; refactoring to @patch decorators would not improve readability significantly" --react -1
```

**Pattern 2: Quick acknowledge-then-fix cycle**

```bash
# Acknowledge everything first (lets reviewer know you're engaged)
uv run reply-review owner/repo 45 --react-all eyes

# Later, as you fix each one, reply with +1
uv run reply-review owner/repo 45 1111111111 "Added timeout handling" --react +1
uv run reply-review owner/repo 45 2222222222 "Fixed TOCTOU race with O_EXCL" --react +1
```

**Pattern 3: Request re-review after all fixes**

```bash
# Reply individually with context and +1 reactions
uv run reply-review owner/repo 45 1111111111 "Extracted helper function" --react +1
uv run reply-review owner/repo 45 2222222222 "Added error handling as suggested" --react +1
gh pr comment owner/repo#45 --body "Fixed all items - PTAL"
```

**Pattern 4: Selective responses with disagreement**

```bash
# List with context first
uv run reply-review owner/repo 45 --list --with-context

# Fixed - mark as done
uv run reply-review owner/repo 45 1111111111 "Fixed line length violation" --react +1

# Acknowledge but defer
uv run reply-review owner/repo 45 2222222222 "Will address in follow-up PR - tracked in #123" --react +1

# Disagree with reasoning
uv run reply-review owner/repo 45 3333333333 "This is test-only style feedback that doesn't affect production code" --react -1
```

## Requirements

- `gh auth login` (authenticated)

## Troubleshooting

| Error                              | Fix                           |
| ---------------------------------- | ----------------------------- |
| "GitHub CLI not authenticated"     | `gh auth login`               |
| "Could not determine current user" | Token needs `read:user` scope |

