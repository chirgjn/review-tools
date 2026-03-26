---
name: parallel-claude-sessions
description: Use when running multiple Claude Code instances simultaneously on independent tasks — sets up tmux sessions, prompt files, an auto-approver for unattended runs, and cleanup. Apply when the user wants to parallelize work across Claude sessions, run agents in parallel with tmux, or orchestrate multiple Claude instances on separate tasks.
---

# Parallel Claude Sessions with tmux

Run multiple Claude Code instances simultaneously on independent tasks. Each session gets its own terminal pane, an optional auto-approver handles permission prompts unattended, and you collect results when all sessions complete.

---

## 1. Plan Session Isolation

Before launching, decide:

| Question | Why it matters |
|---|---|
| Do tasks share a repo? | If yes, use git worktrees so each session has an independent working directory |
| Do tasks write files? | Define separate output directories per session to avoid collisions |
| Do tasks share tools/scripts? | Scripts dirs are fine to share; output dirs must be separate |

**Git worktree setup (when tasks share a repo):**
```bash
cd /path/to/repo

# Add one worktree per task
git worktree add .worktrees/task-a <branch-or-sha>
git worktree add .worktrees/task-b <branch-or-sha>

# Verify
git worktree list
```

> `git worktree list` is the source of truth. A directory under `.worktrees/` that doesn't appear there is stale — remove it and re-add.

---

## 2. Write Prompt Files

Create one prompt file per session at `/tmp/prompt-<task>.txt`. Keep them structurally identical, varying only task-specific details.

**Template:**
```
Do NOT invoke or use any skills. Do not use slash commands. Do not call the Skill tool. Proceed directly with your own capabilities.

You are working on: <task description>

Working directory: <path>
Output directory: <path>/.output/   ← write all artifacts here

## Task
<specific instructions>

IMPORTANT: Do NOT <action you want to prevent, e.g. push to remote, send messages>.

Present your findings when complete, then stop. Do not wait for further input.
```

Key directives:
- **"Do NOT invoke skills"** — prevents skill consent prompts that block the session.
- **Separate output directory per session** — prevents file collisions across parallel sessions.
- **"Stop when complete"** — session stays open in tmux so you can read output.

---

## 3. Write the Auto-Approver Script (optional)

Use when sessions need to run unattended. The approver polls each session every 2 seconds, approves tool permission prompts with Enter, and dismisses skill consent dialogs with Escape.

Save as `/tmp/auto-approve.sh` and make executable:

```bash
chmod +x /tmp/auto-approve.sh
```

```bash
#!/usr/bin/env bash
# Auto-approver for parallel Claude Code tmux sessions

SESSIONS=(session-a session-b session-c)  # ← update to match your session names
LOGFILE=/tmp/auto-approve.log

echo "[$(date)] Auto-approver started" >> "$LOGFILE"

while true; do
  for session in "${SESSIONS[@]}"; do
    if ! tmux has-session -t "$session" 2>/dev/null; then
      continue
    fi

    pane_content=$(tmux capture-pane -t "${session}:0.0" -p 2>/dev/null)

    # Only act when there's an interactive prompt
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

    # APPROVE: all other prompts (tool permissions)
    label=$(echo "$pane_content" | grep -m1 "Do you want\|Allow Claude\|Run shell\|Bash command\|reading from\|writing to" | xargs)
    echo "[$(date)] $session: approving — ${label}" >> "$LOGFILE"
    tmux send-keys -t "${session}:0.0" Enter
    sleep 1

  done
  sleep 2
done
```

> Update `SESSIONS` to exactly match the session names used in step 4.

---

## 4. Launch Sessions

```bash
TASKS=(a b c)  # ← your task identifiers

# Kill any leftover sessions
for task in "${TASKS[@]}"; do
  tmux kill-session -t "session-${task}" 2>/dev/null || true
done
tmux kill-session -t auto-approver 2>/dev/null || true

# Launch one session per task, cd'd into its working directory
for task in "${TASKS[@]}"; do
  tmux new-session -d -s "session-${task}" -c "/path/to/workdir-${task}" "bash"
  tmux send-keys -t "session-${task}" "claude" Enter
done

# Launch the auto-approver (omit if running attended)
tmux new-session -d -s auto-approver "/tmp/auto-approve.sh"
```

Wait for Claude to initialise, then send prompts:

```bash
sleep 6

for task in "${TASKS[@]}"; do
  tmux load-buffer -b "buf${task}" "/tmp/prompt-${task}.txt"
  tmux paste-buffer -b "buf${task}" -t "session-${task}"
  sleep 0.5
  tmux send-keys -t "session-${task}" Enter
done
```

> **Why `load-buffer` + `paste-buffer`?** Claude Code's TUI doesn't handle multi-line `send-keys` input correctly. `paste-buffer` triggers bracketed paste mode, which Claude handles as `[Pasted text #1 +N lines]` — that means the paste worked.

---

## 5. Monitor

**Quick status check across all sessions:**
```bash
for task in a b c; do
  echo "=== session-${task} ==="
  tmux capture-pane -t "session-${task}" -p | tail -4
done
```

**Full output of one session:**
```bash
tmux capture-pane -t session-a -p -S -100
```

**What to look for:**

| Indicator | Meaning |
|---|---|
| `esc to interrupt` | Claude is actively working — all good |
| `[Pasted text #1 +N lines]` with no response | Paste landed but Enter wasn't sent — send it manually |
| `Esc to cancel · Tab to amend` persisting | Stuck on a prompt; check approver log or unblock manually |

**Watch the approver log:**
```bash
tail -f /tmp/auto-approve.log
```

**Attach to intervene in a specific session:**
```bash
tmux attach -t session-a
# Detach without stopping: Ctrl-B then D
```

---

## 6. Wrap Up

```bash
# Stop the auto-approver
tmux kill-session -t auto-approver

# Exit Claude in any sessions still running
for task in a b c; do
  tmux send-keys -t "session-${task}" "/exit" Enter 2>/dev/null || true
done

# Kill all sessions
for task in a b c; do
  tmux kill-session -t "session-${task}" 2>/dev/null || true
done
```

To exit a single session early while others run:
```bash
tmux send-keys -t session-a "/exit" Enter
```

---

## Troubleshooting

**Sessions stuck on a prompt despite approver running:**
```bash
# See what prompt is showing
tmux capture-pane -t session-a -p | grep -B10 "Esc to cancel" | head -15

# Manually unblock
tmux send-keys -t "session-a:0.0" Enter
```

**Skill consent prompts not being dismissed:**
```bash
for task in a b c; do
  tmux send-keys -t "session-${task}:0.0" Escape
done
```

**Claude is operating in the wrong directory:**
The worktree directory exists but isn't registered. Check with `git worktree list`, then:
```bash
rm -rf .worktrees/task-a
git worktree add .worktrees/task-a <sha>
```

**`PreToolUse:Bash hook error` in output:**
Non-blocking — a configured hook failed but Claude continues. Ignore unless a command actually fails.
