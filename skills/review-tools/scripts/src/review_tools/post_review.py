#!/usr/bin/env python3
"""post-review — Post batched GitHub PR review.

⚠️ ALWAYS batch comments into ONE review. Never post multiple reviews (creates permanent timeline noise).

Usage: uv run post-review <owner/repo> <pr> --input FILE [options]

RECOMMENDED:
  --input FILE          Read review payload from JSON (batch multiple comments)
                        JSON must include a "review_body" field and a "comments" array.
  --event TYPE          COMMENT (default), APPROVE, REQUEST_CHANGES

Single comment (use sparingly):
  --path P              File path
  --position N          Diff position (from get-positions)
  --body-file FILE      Read body from file (review before posting)
  --body TEXT           Inline body (discouraged; ≥10 words except LGTM, Approved, Done, Fixed, Acknowledged)

Guidelines:
- Batch via --input FILE (clean PR history)
- review_body must be set in the input JSON file
- Single comment via --body-file (reviewable)
- Inline --body only for quick status: LGTM, Approved, etc.
- Multiple inline comments = ERROR (use --input)

Examples:
  # Batch (recommended) — review_body comes from the JSON file
  uv run post-review owner/repo 42 --input review.json --event REQUEST_CHANGES

  # Single from file
  uv run post-review owner/repo 42 --path X.ts --position 5 --body-file comment.md

  # Single quick (opt-in to separate review entry)
  uv run post-review owner/repo 42 --i-know-this-creates-separate-review --path X.ts --position 5 --body "LGTM"
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax

console = Console()


def fetch_head(repo: str, pr: int) -> str:
    """Get PR head commit SHA."""
    try:
        result = subprocess.run(
            ["gh", "api", f"repos/{repo}/pulls/{pr}", "--jq", ".head.sha"],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        console.print(f"[red]Error fetching head: {e.stderr}[/red]")
        sys.exit(1)


def post_review(repo: str, pr: int, payload: dict) -> dict:
    """Post review to GitHub API."""
    try:
        result = subprocess.run(
            ["gh", "api", f"repos/{repo}/pulls/{pr}/reviews", "-X", "POST", "--input", "-"],
            input=json.dumps(payload),
            capture_output=True,
            text=True,
            check=True,
        )
        return json.loads(result.stdout)
    except subprocess.CalledProcessError as e:
        console.print(f"[red]Error posting review: {e.stderr}[/red]")
        sys.exit(1)


def build_comments_from_flags(paths: list[str], positions: list[int], bodies: list[str]) -> list[dict]:
    """Build comments array from individual flag arguments."""
    if len(paths) != len(positions) or len(paths) != len(bodies):
        raise ValueError(f"Mismatch: {len(paths)} paths, {len(positions)} positions, {len(bodies)} bodies")

    return [
        {"path": p, "position": pos, "body": b}
        for p, pos, b in zip(paths, positions, bodies, strict=True)
    ]


def main():
    parser = argparse.ArgumentParser(
        description="Post batched GitHub PR review with inline comments",
        epilog=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("repo", help="owner/repo")
    parser.add_argument("pr", type=int, help="PR number")
    parser.add_argument("--path", action="append", default=[], help="File path")
    parser.add_argument("--position", type=int, action="append", default=[], help="Diff position")
    parser.add_argument("--body", help="Comment body")
    parser.add_argument("--body-file", help="Read body from file")
    parser.add_argument(
        "--event",
        choices=["COMMENT", "APPROVE", "REQUEST_CHANGES"],
        default="COMMENT",
        help="Review type",
    )
    parser.add_argument("--input", help="Read full payload from file (recommended for batch reviews)")
    parser.add_argument("--i-know-this-creates-separate-review", action="store_true", help="Opt-in to create separate GitHub review entry (anti-pattern)")
    args = parser.parse_args()

    # Single comment reviews require explicit opt-in
    using_inline = args.path or args.position or args.body
    if using_inline and not args.input and not args.i_know_this_creates_separate_review:
        console.print("[red]Error: Single comment reviews create separate GitHub review entries (clutters PR history).[/red]")
        console.print("[dim]   Option 1: Use --input FILE to batch multiple comments (recommended):[/dim]")
        console.print("[dim]     uv run scan-violations owner/repo 42 --output review.json[/dim]")
        console.print("[dim]     uv run post-review owner/repo 42 --input review.json[/dim]")
        console.print("[dim]   Option 2: Use --i-know-this-creates-separate-review to explicitly accept the anti-pattern:[/dim]")
        console.print("[dim]     uv run post-review owner/repo 42 --i-know-this-creates-separate-review --path X --position N --body 'LGTM'[/dim]")
        sys.exit(1)

    # Validate comment word count (discourage short comments, allow common short responses)
    allowed_short_responses = frozenset({
        "lgtm", "looks good", "looks good to me", "approved", "approve",
        "done", "fixed", "resolved", "ack", "acknowledged",
    })
    min_words = 10

    def count_words(text: str) -> int:
        return len(text.strip().split())

    def is_allowed_short(text: str) -> bool:
        """Check if text is a common short response like 'LGTM'."""
        normalized = text.strip().lower().rstrip(".!?")
        return normalized in allowed_short_responses or len(normalized) <= 5

    def validate_comment_words(text: str, context: str, min_words_req: int = min_words) -> bool:
        word_count = count_words(text)
        if word_count < min_words_req and not is_allowed_short(text):
            console.print(f"[yellow]⚠️  {context} is very short ({word_count} words, min {min_words_req})[/yellow]")
            console.print(f"[dim]   Text: '{text[:60]}{'...' if len(text) > 60 else ''}'[/dim]")
            console.print("[dim]   Short responses allowed: LGTM, Approved, Done, Fixed, Acknowledged, etc.[/dim]")
            console.print("[dim]   Or add context: explain WHY the change is needed, not just WHAT.[/dim]")
            return False
        return True

    # Build comments (load file first so review_body can come from it)
    review_body: str | None = None
    if args.input:
        if not Path(args.input).exists():
            console.print(f"[red]Error: Input file not found: {args.input}[/red]")
            sys.exit(1)
        with open(args.input) as f:
            data = json.load(f)
            raw_comments = data.get("comments", [])
            # Strip informational fields (e.g. file_line) not accepted by GitHub API
            comments = [
                {k: v for k, v in c.items() if k in ("path", "position", "body")}
                for c in raw_comments
            ]
            review_body = data.get("review_body")

    if args.input and not review_body:
        console.print("[red]Error: review_body is required in the input JSON file:[/red]")
        console.print('[dim]  { "review_body": "...", "comments": [...] }[/dim]')
        sys.exit(1)

    # Check review body word count (review body can be shorter - min 3 words or allowed short)
    if not args.input:
        # Build from individual flags
        body = args.body
        if args.body_file:
            if not Path(args.body_file).exists():
                console.print(f"[red]Error: Body file not found: {args.body_file}[/red]")
                sys.exit(1)
            body = Path(args.body_file).read_text()

        if not args.path:
            console.print("[red]Error: Provide --path/--position/--body or --input FILE[/red]")
            sys.exit(1)

        comments = build_comments_from_flags(args.path, args.position, [body])
        review_body = review_body or body  # fall back to comment body for single inline comments

    review_word_count = count_words(review_body)
    if review_word_count < 3 and not is_allowed_short(review_body):
        console.print(f"[yellow]⚠️  Review body is very short ({review_word_count} words)[/yellow]")
        console.print("[dim]   Hint: Use 'LGTM', 'Approved', or a brief summary of the review.[/dim]")
        console.print("[red]Error: Review body too short.[/red]")
        sys.exit(1)

    # Only allow single inline comment - use --input FILE for multiple comments
    if using_inline and len(comments) > 1:
        console.print(f"[red]Error: Attempting to post {len(comments)} comments via inline flags.[/red]")
        console.print("[yellow]   Inline flags only support SINGLE comments.[/yellow]")
        console.print("[dim]   For multiple comments, use --input FILE to batch into ONE review:[/dim]")
        console.print("[dim]     uv run scan-violations owner/repo 42 --output review.json[/dim]")
        console.print("[dim]     uv run post-review owner/repo 42 --input review.json[/dim]")
        sys.exit(1)

    # Validate comment word counts
    short_comments = []
    for i, c in enumerate(comments):
        body_text = c.get("body", "")
        word_count = count_words(body_text)
        if word_count < min_words and not is_allowed_short(body_text):
            short_comments.append((i, body_text[:60], word_count))

    if short_comments:
        console.print(f"[yellow]⚠️  Found {len(short_comments)} short comment(s):[/yellow]")
        for idx, preview, words in short_comments:
            console.print(f"  [dim]Comment {idx} ({words} words): '{preview}{'...' if len(preview) >= 60 else ''}'[/dim]")
        console.print("[yellow]   Comments should explain WHY (not just WHAT) to help the author learn.[/yellow]")
        console.print("[dim]   Allowed short responses: LGTM, Approved, Done, Fixed, Acknowledged, etc.[/dim]")
        console.print("[red]Error: Comment quality check failed.[/red]")
        sys.exit(1)

    # Fetch head commit
    with console.status("[bold green]Fetching head commit..."):
        head = fetch_head(args.repo, args.pr)

    # Build payload
    payload = {
        "commit_id": head,
        "body": review_body,
        "event": args.event,
        "comments": comments,
    }

    # Preview
    console.print("[bold blue]Preview:[/bold blue]")
    syntax = Syntax(json.dumps(payload, indent=2), "json", theme="monokai")
    console.print(Panel(syntax, expand=False))

    # No confirmation prompt — this script runs non-interactively (agent use)

    # Post
    with console.status("[bold green]Posting review..."):
        resp = post_review(args.repo, args.pr, payload)

    url = resp.get("html_url", "OK")
    console.print(f"[green]✓ Posted: {url}[/green]")
    console.print_json(json.dumps({"id": resp.get("id"), "state": resp.get("state"), "url": url}))


if __name__ == "__main__":
    main()
