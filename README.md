# review-tools

> **AI agent?** Read [AGENTS.md](AGENTS.md) first.

A collection of Claude Code skills for GitHub PR workflows.

## Skills

| Skill | What it does |
| ----- | ------------ |
| [review-tools](skills/review-tools/SKILL.md) | Review PRs, respond to review comments, keep a checklist current from past PRs, run reviews in parallel |
| [parallel-claude-sessions](skills/parallel-claude-sessions/SKILL.md) | Run multiple Claude Code instances simultaneously on independent tasks using tmux |

## Installation

Clone the repo, then sync the review-tools dependencies:

```bash
git clone <repo>
cd review-tools/skills/review-tools/scripts
uv sync
```

The `parallel-claude-sessions` skill has no dependencies beyond `tmux` and `claude` on PATH.

## Requirements

- [Claude Code (`claude`)](https://claude.ai/code) on PATH
- [GitHub CLI (`gh`)](https://cli.github.com/) authenticated (for review-tools)
- Python 3.11+ and [uv](https://docs.astral.sh/uv/) (for review-tools scripts)
- [tmux](https://github.com/tmux/tmux) (for parallel-claude-sessions)
