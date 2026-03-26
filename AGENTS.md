# PR Review Tools

Tools and guides for doing GitHub PR reviews as an agent. File-first, batched reviews — no timeline noise.

## Philosophy

GitHub review comments are permanent with no undo. Every decision you make before posting is cheap; every mistake after posting creates clutter that can't be cleaned up.

- **File-first** — always save to a file and review before posting. Never pipe directly to `post-review`.
- **Batch** — one review submission per PR. Multiple submissions create permanent timeline noise.
- **Explain WHY** — minimum 10 words per comment (except LGTM, Approved, Done, Fixed). Teach the consequence, not just what to change.

## Routing

| When you are...                                           | Read                                                              |
| --------------------------------------------------------- | ----------------------------------------------------------------- |
| Reviewing a PR (scan → file → post workflow)              | `skills/review-tools/references/review-a-pr.md`                  |
| Responding to review comments on your own PR              | `skills/review-tools/references/respond-to-reviews.md`           |
| Extracting patterns from past PRs to update the checklist | `skills/review-tools/references/analyze-patterns.md`             |
| Running multiple PR reviews in parallel with tmux         | `skills/review-tools/references/parallel-pr-review.md`           |
| Running multiple Claude sessions in parallel (generic)    | `skills/parallel-claude-sessions/SKILL.md`                       |
| Consulting the review checklist for violation rules       | `skills/review-tools/references/review-checklist.md`             |
| Installing the skill to use these tools in another repo   | `skills/review-tools/SKILL.md`                                   |

## Running Commands

All `uv run` commands must be run from `skills/review-tools/scripts/`. When invoked as a skill, use `${CLAUDE_SKILL_DIR}` to reference paths:

```bash
cd ${CLAUDE_SKILL_DIR}/scripts
uv run pr-threads owner/repo#35 --all
uv run scan-violations owner/repo 42 --checklist ${CLAUDE_SKILL_DIR}/references/review-checklist.md --output /tmp/review.json
uv run post-review owner/repo 42 --input /tmp/review.json --event REQUEST_CHANGES
uv run reply-review owner/repo 45 --list --with-context
gh pr comment owner/repo#42 --body-file /tmp/comment.md  # plain comment, no review state
```

Write temporary artifacts (review.json, threads.txt) to `/tmp/` — not into this repo.

## Conventions

- `AGENTS.md` is the canonical file; `CLAUDE.md` is a symlink (`ln -s AGENTS.md CLAUDE.md`) — never edit `CLAUDE.md` directly
- `skills/review-tools/` is a self-sufficient package — it is installed and consumed independently of this repo; all paths inside it must work via `${CLAUDE_SKILL_DIR}` with no dependency on anything outside the skill directory
