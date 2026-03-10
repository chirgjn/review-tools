# Posting GitHub Reviews via CLI

## Rules — Read Before Doing Anything Else

> **ALWAYS use the batched `comments[]` API approach described below.**
>
> Do NOT use any of these alternatives, even if they seem simpler:
>
> - ❌ `gh pr review --comment` — no inline comment support
> - ❌ `gh api .../pulls/PR_NUMBER/comments -X POST` per comment — creates permanent, undeletable noise
> - ❌ Posting comments one at a time in a loop — same problem, at scale

Violating these rules creates permanent damage to the PR timeline that **cannot be undone via the API**. See [Why This Matters](#why-this-matters) for the full explanation.

---

## The Only Correct Approach: Single Batched Review

All inline comments must go into **one API call** using the `comments[]` array. This is how the GitHub web UI works internally.

### Step 1 — Fetch the head commit SHA

```bash
gh api repos/OWNER/REPO/pulls/PR_NUMBER --jq '.head.sha'
```

### Step 2 — Map diff positions

The `position` field is the **line number within the entire unified diff output** (1-indexed from line 1 of the full diff, not from the start of each file).

Fetch the diff with line numbers to find positions:

```bash
gh api repos/OWNER/REPO/pulls/PR_NUMBER \
  -H "Accept: application/vnd.github.v3.diff" | cat -n | grep -A2 -B2 "filename-or-pattern"
```

The `@@` hunk header is position 1 for that file's chunk. Count lines down from there.

### Step 3 — Build the payload

Write the full payload to a JSON file (e.g. `/tmp/review_payload.json`):

```json
{
  "commit_id": "<head-sha>",
  "body": "Overall review summary...",
  "event": "COMMENT",
  "comments": [
    {
      "path": "path/to/file.tsx",
      "position": 42,
      "body": "Inline comment text..."
    },
    {
      "path": "path/to/other.tsx",
      "position": 17,
      "body": "Another comment..."
    }
  ]
}
```

`event` must be one of: `COMMENT`, `APPROVE`, `REQUEST_CHANGES`.

### Step 4 — Submit

```bash
gh api repos/OWNER/REPO/pulls/PR_NUMBER/reviews \
  -X POST \
  --input /tmp/review_payload.json \
  --jq '{id, state, html_url}'
```

---

## Why This Matters

### Posting comments one at a time is irreversible

Using `gh api .../pulls/PR_NUMBER/comments -X POST` for each inline comment creates a **separate review event per comment**. On a 10-comment review, this litters the PR with 10 individual review events instead of 1.

These **cannot be cleaned up**:

- There is no API endpoint to delete a review
- `COMMENTED` reviews cannot be dismissed (only `APPROVED` / `CHANGES_REQUESTED` can be)
- The only removal path is via the GitHub web UI with repo admin access

The inline comments themselves *can* be deleted, leaving the review event as an empty shell — but the timeline noise remains.

### `gh pr review` does not support inline comments

`gh pr review --comment --body "..."` only posts a top-level review body with no file attachment. It is useful only when you have zero inline comments. Do not use it as a stepping stone — it just adds another undeletable `COMMENTED` event.

---

## Quick Reference

| Goal | Command |
| ---- | ------- |
| Single batched review with inline comments | `gh api .../pulls/N/reviews -X POST --input payload.json` |
| Approve or request changes (no inline comments) | `gh pr review N --approve` / `--request-changes` |
| Simple top-level comment (no inline) | `gh pr review N --comment --body "..."` |
| Delete a stray inline **comment** (not the review) | `gh api .../pulls/comments/ID -X DELETE` |
| Dismiss a review | Only works for `APPROVED`/`CHANGES_REQUESTED` state |

---

## Cleanup Reference (damage control only)

If inline comments were posted individually by mistake, you can delete the comments to reduce noise, but the review events will remain:

```bash
# List comment IDs attached to a specific review
gh api repos/OWNER/REPO/pulls/PR_NUMBER/reviews/REVIEW_ID/comments --jq '.[].id'

# Delete a specific inline comment
gh api repos/OWNER/REPO/pulls/comments/COMMENT_ID -X DELETE
```

The parent review event stays on the timeline as an empty shell. This is the best recoverable state without admin access to the repo.
