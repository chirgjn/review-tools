#!/usr/bin/env python3
"""reply-review — Reply to and react on PR review comments.

Usage: uv run reply-review <owner/repo> <pr> [command] [options]

Commands:
  --list                 List comments with IDs
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
  uv run reply-review owner/repo 45 1234567890 "Fixed"
  uv run reply-review owner/repo 45 --reply-all --prefix "✅ Fixed"
  uv run reply-review owner/repo 45 --react-all eyes

Reply quality: "Done" (simple), "Extracted to helper" (complex), or ask for clarification.
Avoid: Commit SHAs (break on rebase), vague "OK", reacting when code changes needed.
"""

import argparse
import subprocess
import sys
from dataclasses import dataclass

import httpx
from rich.console import Console
from rich.progress import track
from rich.table import Table

console = Console()

VALID_EMOJIS = {"+1", "-1", "laugh", "confused", "heart", "hooray", "eyes", "rocket"}


@dataclass
class ReviewComment:
    id: int
    path: str
    line: int
    body: str
    author: str


def get_gh_token() -> str:
    """Get GitHub CLI auth token."""
    try:
        result = subprocess.run(["gh", "auth", "token"], capture_output=True, text=True, check=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        console.print("[red]Error: gh not authenticated. Run `gh auth login`[/red]")
        sys.exit(1)


def get_current_user(token: str) -> str | None:
    """Get current GitHub user."""
    try:
        resp = httpx.get(
            "https://api.github.com/user",
            headers={"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"},
        )
        resp.raise_for_status()
        return resp.json().get("login")
    except httpx.HTTPError:
        return None


def fetch_comments(repo: str, pr: int, token: str) -> list[ReviewComment]:
    """Fetch review comments from PR."""
    try:
        resp = httpx.get(
            f"https://api.github.com/repos/{repo}/pulls/{pr}/comments",
            headers={"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"},
        )
        resp.raise_for_status()
        data = resp.json()
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


def list_comments(comments: list[ReviewComment]) -> None:
    """Display review comments in a table."""
    if not comments:
        console.print("[yellow]No comments on PR[/yellow]")
        return

    table = Table(title=f"{len(comments)} Review Comments", show_header=True)
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("File", style="blue")
    table.add_column("Line", style="yellow", justify="right")
    table.add_column("Author", style="magenta")
    table.add_column("Body Preview", style="white")

    for c in comments:
        preview = c.body[:60] + "..." if len(c.body) > 60 else c.body
        table.add_row(str(c.id), c.path, str(c.line), c.author, preview)

    console.print(table)


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

    # List mode
    if args.list:
        comments = fetch_comments(args.repo, args.pr, token)
        list_comments(comments)
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
        # Skip own comments
        to_reply = [c for c in comments if c.author != current_user]

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
        to_react = [c for c in comments if c.author != current_user]

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
