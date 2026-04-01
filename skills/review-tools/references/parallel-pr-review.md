# Parallel PR Review

> **Orchestrator rule:** Do not post reviews to GitHub. Your job is to orchestrate review sessions and collect findings only.

Run multiple Claude Code instances simultaneously, one per PR, each reviewing in an isolated git worktree. A background poller auto-approves tool permission prompts so reviews run unattended. Each agent saves its findings to the worktree and exits when done.

## Prerequisites

- `tmux` installed (`brew install tmux`)
- `gh` CLI authenticated
- `uv` installed
- This skill's `scripts/` directory on PATH or accessible via `uv run`
- Claude Code (`claude`) on PATH

---

## 1. Set Up Git Worktrees

Each PR needs a proper git worktree — not just a directory.

```bash
cd /path/to/repo

# Check what's already registered
git worktree list

# Add a worktree for each PR by its HEAD SHA
git worktree add .worktrees/pr-<N> <sha>
```

**Fetch the SHA for each PR:**
```bash
gh pr view <N> --json headRefOid --jq '.headRefOid'

# Or fetch all at once
for pr in 38 39 40 41 42; do
  gh pr view $pr --json headRefName,headRefOid \
    --jq --arg pr "$pr" '"PR \($pr): \(.headRefName)  \(.headRefOid)"'
done
```

> **Important:** `git worktree list` is the source of truth. If a directory exists under `.worktrees/` but doesn't appear in `git worktree list`, it's stale — remove it and re-add.

---

## 2. Write Prompt Files

Create one prompt file per PR at `/tmp/prompt-pr<N>.txt`. Keep them identical in structure, varying only PR number, title, and worktree path.

### Prompt Template
```
Do NOT invoke or use any skills. Do not use slash commands. Do not call the Skill tool. Proceed directly with your own capabilities.

You are a code reviewer for PR #<N> on <owner>/<repo>.
PR title: "<title>"

Worktree: <worktree-path>
Review tools: <path-to-skill>/scripts/ (run uv commands from there; read references/ docs to understand workflows)

## Artifact isolation
The scripts/ directory is shared across parallel reviews — do NOT write any files into it.
All artifacts must go into <worktree-path>/.review/.

## Task
Review this PR thoroughly using the review tools. Read the references/ docs for workflow and file format guidance. Save your findings to <worktree-path>/.review/review.json.

IMPORTANT — diff positions: Every comment in review.json must use a GitHub diff position, not a source file line number. Use `uv run get-positions <owner>/<repo> <N> <file>:<line>:<content>` to convert each file:line:content to its diff position before writing the JSON. The content hint verifies you're commenting on the correct line. Comments with source line numbers outside the diff will be rejected by the API.

IMPORTANT: Do NOT post the review to GitHub under any circumstances. Do NOT ask for permission to post. Do NOT suggest posting. Your only output is the saved artifacts and a summary presented in the session.

Present your findings when complete, then stop. Do not wait for further input.
```

### Key Points
- **"Do NOT invoke skills"** — prevents Claude from triggering skill consent prompts that block the session.
- **Artifact isolation** — all output files go into the PR's own worktree, not into the shared review-tools directory.
- **"Do NOT post"** — the review agent must not post to GitHub; that decision stays with the orchestrator.
- **"Stop when complete"** — the agent presents findings and stops; the session stays open in tmux so you can read output and decide what to post.

---

## 3. Write the Auto-Approver Script

The auto-approver runs in its own tmux session and polls all review sessions every 2 seconds. It presses Enter to approve tool permission prompts and Escape to dismiss skill consent dialogs.

Save as `/tmp/review-auto-approve.sh` and `chmod +x` it. **Replace the PR numbers in `SESSIONS` to match the sessions you create in step 4** — they must stay in sync.

```bash
#!/usr/bin/env bash
# Auto-approver for Claude Code tmux sessions

SESSIONS=(review-pr38 review-pr39 review-pr40 review-pr41 review-pr42)  # ← update to match your PRs
LOGFILE=/tmp/review-auto-approve.log

echo "[$(date)] Auto-approver started" >> "$LOGFILE"

while true; do
  for session in "${SESSIONS[@]}"; do
    if ! tmux has-session -t "$session" 2>/dev/null; then
      continue
    fi

    pane_content=$(tmux capture-pane -t "${session}:0.0" -p 2>/dev/null)

    # Only act on interactive prompts
    if ! echo "$pane_content" | grep -q "Esc to cancel"; then
      continue
    fi

    # DISMISS: skill consent prompts
    if echo "$pane_content" | grep -q "Use skill"; then
      echo "[$(date)] $session: dismissing skill prompt" >> "$LOGFILE"
      tmux send-keys -t "${session}:0.0" Escape
      sleep 1
      continue
    fi

    # APPROVE: all other prompts (tool permissions) — Enter confirms the default Yes
    label=$(echo "$pane_content" | grep -m1 "Do you want\|Allow Claude\|Run shell\|Bash command\|reading from\|writing to" | xargs)
    echo "[$(date)] $session: approving — ${label}" >> "$LOGFILE"
    tmux send-keys -t "${session}:0.0" Enter
    sleep 1

  done
  sleep 2
done
```

---

## 4. Launch Sessions

Replace `38 39 40 41 42` throughout this section with your actual PR numbers.

```bash
# Kill any leftover sessions
for pr in 38 39 40 41 42; do
  tmux kill-session -t "review-pr${pr}" 2>/dev/null || true
done
tmux kill-session -t review-approver 2>/dev/null || true

# Map PR numbers to their worktree directory names
declare -A worktrees
worktrees[38]="pr-38"
worktrees[39]="pr-39"
worktrees[40]="pr-40"
worktrees[41]="pr-41"
worktrees[42]="pr-42"

base="/path/to/repo/.worktrees"

# Launch one session per PR, cd'd into its worktree
# Use bash as the parent so the session stays open after Claude exits
for pr in 38 39 40 41 42; do
  tmux new-session -d -s "review-pr${pr}" -c "${base}/${worktrees[$pr]}" "bash"
  tmux send-keys -t "review-pr${pr}" "claude" Enter
done

# Launch the auto-approver
tmux new-session -d -s review-approver "/tmp/review-auto-approve.sh"
```

Wait 6 seconds for Claude to initialise, then send the prompts:

```bash
sleep 6

for pr in 38 39 40 41 42; do
  tmux load-buffer -b "buf${pr}" "/tmp/prompt-pr${pr}.txt"
  tmux paste-buffer -b "buf${pr}" -t "review-pr${pr}"
  sleep 0.5
  tmux send-keys -t "review-pr${pr}" Enter
done
```

> **Why `load-buffer` + `paste-buffer`?** Claude's TUI doesn't accept multi-line `send-keys`. `paste-buffer` triggers bracketed paste mode, showing `[Pasted text #1 +N lines]` when successful.

---

## 5. Monitor

**Check all sessions:**
```bash
for pr in 38 39 40 41 42; do
  echo "=== pr${pr} ==="
  tmux capture-pane -t "review-pr${pr}" -p | tail -4
done
```

**Check a specific session in full:**
```bash
tmux capture-pane -t review-pr38 -p -S -100
```

**What you're looking for:**
- `esc to interrupt` — Claude is actively working
- `[Pasted text #1 +N lines]` with no response — paste landed but Enter wasn't sent; send it manually
- `Esc to cancel · Tab to amend` persisting — Claude is stuck on a prompt; check the approver log

**Watch the approver:**
```bash
tail -f /tmp/review-auto-approve.log
```

---

## 6. Wrap Up

When all reviews are complete, stop the approver and clean up:

```bash
# Stop the auto-approver
tmux kill-session -t review-approver

# Exit Claude in any sessions still running
for pr in 38 39 40 41 42; do
  tmux send-keys -t "review-pr${pr}" "/exit" Enter 2>/dev/null || true
done

# Kill all review sessions
for pr in 38 39 40 41 42; do
  tmux kill-session -t "review-pr${pr}" 2>/dev/null || true
done
```

To exit a single session early while others are still running:
```bash
tmux send-keys -t "review-pr38" "/exit" Enter
```

---

## 7. Reading Results

Read findings from each worktree's `.review/` directory:

```bash
ls .worktrees/pr-38/.review/

# Show the review summary
jq '.review_body' .worktrees/pr-38/.review/review.json

# Show inline comments
jq '.comments[] | {path, body}' .worktrees/pr-38/.review/review.json
```

---

## Troubleshooting

**Course correction — attach to a session:**
If a session is stuck or going in the wrong direction, attach to intervene:
```bash
tmux attach -t review-pr38
# Detach without stopping: Ctrl-B then D
```

**Sessions stuck on a prompt despite approver running:**
```bash
# See what prompt is showing
tmux capture-pane -t review-pr38 -p | grep -B10 "Esc to cancel" | head -15

# Manually unblock
tmux send-keys -t "review-pr38:0.0" Enter
```

**Claude is reviewing the wrong branch:**
The directory exists but isn't a registered git worktree. Check with `git worktree list`, then remove and re-add:
```bash
rm -rf .worktrees/pr-38
git worktree add .worktrees/pr-38 <sha>
```

**`PreToolUse:Bash hook error` in output:**
Non-blocking — a configured hook failed but Claude continues. Ignore unless it causes a command to fail.

**Skill consent prompt not being dismissed:**
The approver sends Escape automatically. If sessions get stuck before it catches up, dismiss manually:
```bash
for pr in 38 39 40 41 42; do
  tmux send-keys -t "review-pr${pr}:0.0" Escape
done
```
