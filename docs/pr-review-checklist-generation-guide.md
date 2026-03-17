# How to Update the Review Checklist

This guide explains how to fetch PR review comments, analyse them, and update `docs/review-checklist.md` with new patterns.

---

## Tool: `scripts/review/pr_threads.py`

A single script that accepts PR references in any format, fetches all data sources in parallel, and groups comments into reply threads.

Requires the `gh` CLI to be authenticated.

### PR Reference Formats

All of the following are valid and can be mixed freely in one command:

```
https://github.com/razorpay/wallet-frontend/pull/35   # full URL
razorpay/wallet-frontend#36                            # owner/repo#number
razorpay/wallet#3                                      # short slug (resolved via slug map)
```

Built-in slug mappings (no flag needed):

| Slug | Resolves to |
|------|-------------|
| `wallet` | `razorpay/wallet-frontend` |

Add more with `--slug-map`:

```bash
uv run scripts/review/pr_threads.py razorpay/payments#12 \
    --slug-map payments=razorpay/payments-frontend
```

---

### Commands

**Threads across PRs from different repos:**
```bash
uv run scripts/review/pr_threads.py \
    https://github.com/razorpay/wallet-frontend/pull/35 \
    razorpay/wallet-frontend#36 \
    razorpay/wallet#3
```

**Your own comments (default — no flag needed):**
```bash
uv run scripts/review/pr_threads.py \
    razorpay/wallet-frontend#35 razorpay/wallet-frontend#36
```

**A specific reviewer's comments:**
```bash
uv run scripts/review/pr_threads.py \
    razorpay/wallet-frontend#35 razorpay/wallet-frontend#36 \
    --reviewer chirgjn
```

**All reviewers (no filter):**
```bash
uv run scripts/review/pr_threads.py \
    razorpay/wallet-frontend#35 razorpay/wallet-frontend#36 \
    --all
```

**Show diff for a specific file across PRs:**
```bash
uv run scripts/review/pr_threads.py razorpay/wallet-frontend#37 --diff useKycFlowHandler
```

**Inspect specific comment IDs:**
```bash
uv run scripts/review/pr_threads.py razorpay/wallet-frontend#38 --comments 2888363711 2888364162
```

---

## How It Works

For each PR, three GitHub API calls run in parallel:
- `gh pr view` — title and metadata
- `gh api pulls/:pr/comments` — inline review comments
- `gh api issues/:pr/comments` — PR-level comments

All PRs are also fetched in parallel, so a batch of 10 PRs takes roughly the same time as fetching 1.

Comments are grouped into threads by `in_reply_to_id` chain. All-bot threads are filtered out automatically. Output preserves the original input order of PR references.

---

## Updating the Checklist

After running the script across a batch of PRs:

1. Identify comments that appear on **multiple files or multiple PRs** — these signal a project-wide pattern worth adding to the checklist
2. Distinguish **already-fixed** issues (visible in the diff) from **recurring** ones (same pattern repeated across files)
3. Add new items to the appropriate section in `docs/review-checklist.md`
4. If a pattern is one-off or context-specific, do not add it to the checklist

---

## Legacy Scripts

The following scripts in `scripts/review/` predate the consolidated tool and are kept for reference:

| Script | What it did |
|--------|-------------|
| `parse_pr.py` | Flat list of non-bot comments from a pre-fetched temp file |
| `parse_threads.py` | Thread-grouped comments from a pre-fetched temp file |
| `get_pr_files.py` | List changed filenames (equivalent to `gh api ... \| jq '.[].filename'`) |
| `get_diff.py` | Print patch for a filename substring from stdin |
| `get_comment.py` | Inspect specific comment IDs from a pre-fetched temp file |

These required manually fetching to a temp file first and processing PRs one at a time. `pr_threads.py` supersedes all of them.
