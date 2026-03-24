#!/usr/bin/env python3
"""reply-review — Reply to and react on PR review comments.

Usage: uv run reply-review <owner/repo> <pr> [command] [options]

Commands:
  --list                 List comments with IDs (preview)
  --list --with-context  List with full body + diff context
  --inspect ID           Deep inspect: full body, diff hunk, thread
  <comment_id> "msg"     Reply to single comment
  <comment_id> --react E React to single comment
  --reply-all            Reply to all (skips your own)
  --react-all E          React to all (skips your own)

Options:
  --prefix TEXT          Prefix for --reply-all
  --suffix TEXT          Suffix for --reply-all

Emojis: +1, -1, laugh, confused, heart, hooray, eyes, rocket

Examples:
  uv run reply-review owner/repo 45 --list
  uv run reply-review owner/repo 45 --list --with-context
  uv run reply-review owner/repo 45 --inspect 1234567890
  uv run reply-review owner/repo 45 1234567890 "Extracted to helper as suggested"
  uv run reply-review owner/repo 45 1234567890 "Fixed" --react +1
  uv run reply-review owner/repo 45 --react-all eyes

Reply quality: "Done" (simple), "Extracted to helper" (complex), or ask for clarification.
Avoid: Commit SHAs (break on rebase), vague "OK", reacting when code changes needed.
"""

import argparse
import sys
from dataclasses import dataclass

import httpx
from rich.console import Console
from rich.progress import track

from review_tools.common import (
    build_threads,
    fetch_pr_comments,
    get_current_user,
    get_gh_token,
    is_bot,
    print_comment_body,
    print_diff_hunk,
)

console = Console()

VALID_EMOJIS = {"+1", "-1", "laugh", "confused", "heart", "hooray", "eyes", "rocket"}


@dataclass
class ReviewComment:
    id: int
    path: str
    line: int
    body: str
    author: str


def fetch_comments(repo: str, pr: int, token: str) -> list[ReviewComment]:
    """Fetch review comments from PR (truncated for list view)."""
    try:
        data = fetch_pr_comments(repo, pr, token)
        return [
            ReviewComment(
                id=c["id"],
                path=c["path"],
                line=c.get("line", 0),
                body=c.get("body", "")[:100],  # Truncate for display
                author=c["user"]["login"],
            )
            for c in data
        ]
    except httpx.HTTPError as e:
        console.print(f"[red]Error fetching comments: {e}[/red]")
        sys.exit(1)


def reply(repo: str, pr: int, comment_id: int, message: str, token: str) -> bool:
    """Reply to a review comment."""
    try:
        resp = httpx.post(
            f"https://api.github.com/repos/{repo}/pulls/{pr}/comments",
            headers={"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"},
            json={"body": message, "in_reply_to": comment_id},
        )
        resp.raise_for_status()
        return True
    except httpx.HTTPError:
        return False


def react(repo: str, comment_id: int, emoji: str, token: str) -> bool:
    """Add reaction to a review comment."""
    if emoji not in VALID_EMOJIS:
        console.print(f"[red]Invalid emoji: {emoji}. Valid: {', '.join(VALID_EMOJIS)}[/red]")
        return False

    try:
        resp = httpx.post(
            f"https://api.github.com/repos/{repo}/pulls/comments/{comment_id}/reactions",
            headers={
                "Authorization": f"token {token}",
                "Accept": "application/vnd.github.squirrel-girl-preview+json",
            },
            json={"content": emoji},
        )
        resp.raise_for_status()
        return True
    except httpx.HTTPError:
        return False


def list_comments(repo: str, pr: int, comments: list[ReviewComment]) -> None:
    """Display review comments in pr-threads format."""
    if not comments:
        console.print("No comments on PR")
        return

    print(f"=== PR #{pr} ({repo}): Review Comments ===\n")
    for c in comments:
        print(f"Comment: {c.path}:{c.line}")
        print(f"  id={c.id} repo={repo} pr={pr}")
        print(f"  [id={c.id}] @{c.author}:")
        body = c.body[:100] if len(c.body) > 100 else c.body
        print_comment_body(body, indent=4)
        if len(c.body) > 100:
            print(f"    ... ({len(c.body) - 100} more chars)")
        print()


def list_comments_with_context(repo: str, pr: int, full_comments: list[dict]) -> None:
    """Display comments with full body and diff context (pr-threads format)."""
    if not full_comments:
        print("No comments on PR")
        return

    threads = build_threads(full_comments)
    print(f"=== PR #{pr} ({repo}) — Review Comments with Context ===\n")

    for thread in threads.values():
        root = thread["root"]
        root_id = root["id"]
        path = root["path"]
        line = root.get("line") or root.get("original_line", "?")
        commit = root.get("commit_id", "unknown")[:8]
        author = root["user"]["login"]
        url = root.get("html_url", "")

        print(f"Thread: {path}:{line}")
        print(f"  id={root_id} repo={repo} pr={pr} commit={commit}")
        if url:
            print(f"  URL: {url}")

        # Root comment
        print(f"  [id={root_id}] @{author}:")
        print_comment_body(root["body"], indent=4)

        # Diff context
        if root.get("diff_hunk"):
            print("  diff_hunk:")
            print_diff_hunk(root["diff_hunk"], max_lines=8, indent=4)

        # Replies
        for reply in thread["replies"]:
            r_id = reply["id"]
            r_author = reply["user"]["login"]
            print(f"  [id={r_id}] @{r_author}:")
            print_comment_body(reply["body"], indent=4)

        print()


def inspect_comment(repo: str, pr: int, comment_id: int, full_comments: list[dict]) -> None:
    """Deep inspect a specific comment with full context (pr-threads format)."""
    # Find comment and its thread
    target = None
    is_reply = False
    parent_thread = None

    for c in full_comments:
        if c["id"] == comment_id:
            target = c
            is_reply = c.get("in_reply_to_id") is not None
            break

    if target is None:
        print(f"Comment {comment_id} not found")
        return

    # Find thread if it's a root comment
    threads = build_threads(full_comments)
    if comment_id in threads:
        parent_thread = threads[comment_id]
    elif is_reply:
        # Find which thread this reply belongs to
        for t in threads.values():
            if any(r["id"] == comment_id for r in t["replies"]):
                parent_thread = t
                break

    # Display in pr-threads format
    c = target
    path = c.get("path", "unknown")
    line = c.get("line") or c.get("original_line", "?")
    commit = c.get("commit_id", "unknown")
    author = c["user"]["login"]
    reply_to = c.get("in_reply_to_id", "")

    print(f"=== PR #{pr} ({repo}) — Comment Inspection ===\n")
    print(f"id={comment_id} repo={repo} pr={pr} path={path}:{line} commit={commit} reply_to={reply_to} user={author}")
    print("body:")
    print_comment_body(c["body"], indent=2)

    if c.get("diff_hunk"):
        print("diff_hunk:")
        print_diff_hunk(c["diff_hunk"], indent=2)

    # Thread context
    if parent_thread:
        if comment_id in threads and parent_thread["replies"]:
            # This is a root comment with replies
            print(f"\n-- Thread Replies ({len(parent_thread['replies'])}) --")
            for reply in parent_thread["replies"]:
                r_id = reply["id"]
                r_author = reply["user"]["login"]
                print(f"\n  [id={r_id}] @{r_author}:")
                print_comment_body(reply["body"], indent=4)
        elif is_reply:
            # This is a reply - show root context
            root = parent_thread["root"]
            print(f"\n-- In Reply To [id={root['id']}] @{root['user']['login']} --")
            print_comment_body(root["body"], max_lines=10, indent=2)

    print()


def main():
    parser = argparse.ArgumentParser(
        description="Reply to and react on PR review comments",
        epilog=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("repo", help="owner/repo")
    parser.add_argument("pr", type=int, help="PR number")
    parser.add_argument("comment_id", nargs="?", help="Comment ID to reply/react to")
    parser.add_argument("message", nargs="?", help="Reply message")
    parser.add_argument("--list", "-l", action="store_true", help="List all comments")
    parser.add_argument("--with-context", action="store_true", help="Show full context with --list")
    parser.add_argument("--inspect", type=int, metavar="ID", help="Inspect specific comment ID")
    parser.add_argument("--react", help="Add reaction (emoji)")
    parser.add_argument("--reply-all", "-a", action="store_true", help="Reply to all comments")
    parser.add_argument("--react-all", help="React to all comments with emoji")
    parser.add_argument("--prefix", default="Acknowledged", help="Prefix for --reply-all")
    parser.add_argument("--suffix", help="Suffix for --reply-all")
    args = parser.parse_args()

    # Validate repo format
    if "/" not in args.repo:
        console.print("[red]Error: Repository must be 'owner/repo'[/red]")
        sys.exit(1)

    # Get auth token
    token = get_gh_token()
    current_user = get_current_user(token)

    # Inspect single comment
    if args.inspect:
        try:
            full_comments = fetch_pr_comments(args.repo, args.pr, token)
            inspect_comment(args.repo, args.pr, args.inspect, full_comments)
        except httpx.HTTPError as e:
            console.print(f"[red]Error fetching comments: {e}[/red]")
            sys.exit(1)
        return

    # List mode (with or without full context)
    if args.list:
        if args.with_context:
            try:
                full_comments = fetch_pr_comments(args.repo, args.pr, token)
                list_comments_with_context(args.repo, args.pr, full_comments)
            except httpx.HTTPError as e:
                console.print(f"[red]Error fetching comments: {e}[/red]")
                sys.exit(1)
        else:
            comments = fetch_comments(args.repo, args.pr, token)
            list_comments(args.repo, args.pr, comments)
        return

    # Single comment reply/react
    if args.comment_id and not args.reply_all and not args.react_all:
        comment_id = int(args.comment_id)

        if args.message:
            with console.status(f"[bold green]Replying to {comment_id}..."):
                success = reply(args.repo, args.pr, comment_id, args.message, token)
            if success:
                console.print(f"[green]✓ Replied to {comment_id}[/green]")
            else:
                console.print(f"[red]✗ Failed to reply to {comment_id}[/red]")

        if args.react:
            with console.status(f"[bold green]Reacting to {comment_id}..."):
                success = react(args.repo, comment_id, args.react, token)
            if success:
                console.print(f"[green]✓ Reacted to {comment_id}[/green]")
            else:
                console.print(f"[red]✗ Failed to react to {comment_id}[/red]")

        if not args.message and not args.react:
            console.print("[red]Error: Provide message or --react[/red]")
            sys.exit(1)
        return

    # Reply all mode
    if args.reply_all:
        comments = fetch_comments(args.repo, args.pr, token)
        # Skip own comments and bots
        to_reply = [c for c in comments if c.author != current_user and not is_bot(c.author)]

        if not to_reply:
            console.print("[yellow]No comments to reply to[/yellow]")
            return

        for c in track(to_reply, description="Replying...", console=console):
            msg = args.prefix
            if args.suffix:
                msg = f"{msg} - {args.suffix}"
            success = reply(args.repo, args.pr, c.id, msg, token)
            if success:
                console.print(f"[dim]Replied to {c.id} by {c.author}[/dim]")
            else:
                console.print(f"[red]Failed to reply to {c.id}[/red]")
        return

    # React all mode
    if args.react_all:
        if args.react_all not in VALID_EMOJIS:
            console.print(f"[red]Invalid emoji: {args.react_all}[/red]")
            sys.exit(1)

        comments = fetch_comments(args.repo, args.pr, token)
        to_react = [c for c in comments if c.author != current_user and not is_bot(c.author)]

        if not to_react:
            console.print("[yellow]No comments to react to[/yellow]")
            return

        for c in track(to_react, description=f"Reacting {args.react_all}...", console=console):
            success = react(args.repo, c.id, args.react_all, token)
            if success:
                console.print(f"[dim]Reacted to {c.id} by {c.author}[/dim]")
            else:
                console.print(f"[red]Failed to react to {c.id}[/red]")
        return

    parser.print_help()
    sys.exit(1)


if __name__ == "__main__":
    main()
