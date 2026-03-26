# review-tools

A collection of Claude Code skills for GitHub PR workflows. Each skill is self-sufficient and installable independently.

## Structure

```
skills/review-tools/          — PR review skill (scan → file → post)
skills/parallel-claude-sessions/ — run multiple Claude sessions in parallel with tmux
```

See `layout.md` for the full directory map.

## Conventions

- `AGENTS.md` is the canonical file; `CLAUDE.md` is a symlink (`ln -s AGENTS.md CLAUDE.md`) — never edit `CLAUDE.md` directly
- Each skill under `skills/` is self-sufficient — all paths inside resolve via `${CLAUDE_SKILL_DIR}` with no dependency on anything outside the skill directory
- Write temporary artifacts (`review.json`, threads) to `/tmp/` — not into this repo

## Routing

| When you are...                                           | Read                                          |
| --------------------------------------------------------- | --------------------------------------------- |
| Understanding the repo's project structure and layout     | `layout.md`                                   |
| Reviewing a PR or responding to review comments           | `skills/review-tools/SKILL.md`                |
| Running multiple Claude sessions in parallel with tmux    | `skills/parallel-claude-sessions/SKILL.md`    |
| Installing a skill into another repo                      | `skills/review-tools/SKILL.md`                |
