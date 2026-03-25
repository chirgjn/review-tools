---
name: review-tools
description: Use when asked to review a GitHub PR, respond to review comments on a PR, keep a review checklist current from past PRs, or run reviews across multiple PRs in parallel.
---

# PR Review

GitHub review comments are permanent with no undo. Every decision before posting is cheap; every mistake after posting creates clutter that can't be cleaned up.

- **File-first** — always save to a file and review before posting. Never pipe directly to `post-review`.
- **Batch** — one review submission per PR. Multiple submissions create permanent timeline noise.
- **Explain WHY** — minimum 10 words per comment (except LGTM, Approved, Done, Fixed). Teach the consequence, not just what to change.

## Commands

All `uv run` commands must be run from `scripts/` inside this skill directory. Resolve the skill root from the directory containing this file if `${CLAUDE_SKILL_DIR}` is not set.

```bash
cd <skill-root>/scripts
uv run pr-threads owner/repo#35 --all
uv run scan-violations owner/repo 42 --checklist <skill-root>/references/review-checklist.md --output /tmp/review.json
uv run post-review owner/repo 42 --input /tmp/review.json --review-body "Review" --event REQUEST_CHANGES
uv run reply-review owner/repo 45 --list --with-context
```

Write temporary artifacts to `/tmp/` — not into this skill directory.

## Workflows

### Reviewing a PR

Scan for violations, save to file, review, post once.

```bash
# 1. Scan and save
uv run scan-violations owner/repo 42 \
    --checklist <skill-root>/references/review-checklist.md \
    --output /tmp/review.json

# 2. Inspect before posting
cat /tmp/review.json | jq '.comments[] | {path, body}'

# 3. Post as one batched review
uv run post-review owner/repo 42 \
    --input /tmp/review.json \
    --review-body "Checklist review" \
    --event REQUEST_CHANGES
```

For manual comments, get the diff position first:

```bash
uv run get-positions owner/repo 42 src/hooks.ts:45   # → position 127
uv run post-review owner/repo 42 \
    --path src/hooks.ts --position 127 \
    --body "Add useCallback here — prevents referential instability on re-renders" \
    --review-body "Performance suggestion"
```

For the full workflow including incremental build and approve patterns → `references/review-a-pr.md`

---

### Responding to review comments on your PR

```bash
# See all comments with full context
uv run reply-review owner/repo 45 --list --with-context

# Inspect a complex thread
uv run reply-review owner/repo 45 --inspect 1234567890

# Reply with specific context
uv run reply-review owner/repo 45 1234567890 "Extracted to helper as suggested"

# React only (acknowledge without replying)
uv run reply-review owner/repo 45 1234567890 --react eyes

# Acknowledge all feedback at once
uv run reply-review owner/repo 45 --react-all eyes
```

Match reply quality to complexity — specific context ("Extracted to helper") for complex changes, "Fixed" for simple ones. Avoid commit SHAs in replies (break on rebase).

For full reply patterns → `references/respond-to-reviews.md`

---

### Extracting patterns → updating the checklist

```bash
# Fetch threads from recent PRs and analyze in one pipeline
uv run pr-threads owner/repo#40 owner/repo#41 owner/repo#42 --all | \
    uv run suggest-checklist \
        --checklist <skill-root>/references/review-checklist.md \
        --new-only
```

Only add patterns appearing 3+ times. Manually update the checklist — don't use `--apply` without reviewing suggestions first.

For filtering, threshold tuning, and saving threads for repeated analysis → `references/analyze-patterns.md`

---

### Parallel reviews across multiple PRs

Run one Claude Code session per PR in an isolated git worktree with an auto-approver handling tool prompts. Each agent saves findings to its worktree; you decide what to post after.

Requires: `tmux`, `gh` authenticated, `claude` on PATH.

For the full setup (worktrees, prompt files, auto-approver script, launch sequence) → `references/parallel-pr-review.md`

## Routing

| When you need detail on...                                | Read                               |
| --------------------------------------------------------- | ---------------------------------- |
| Full review workflow — incremental build, approve pattern | `references/review-a-pr.md`        |
| Responding to review comments on your own PR              | `references/respond-to-reviews.md` |
| Pattern extraction and checklist update workflow          | `references/analyze-patterns.md`   |
| Parallel reviews with tmux and auto-approver              | `references/parallel-pr-review.md` |
| Violation detection rules and regex patterns              | `references/review-checklist.md`   |
