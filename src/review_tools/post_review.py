#!/usr/bin/env python3
"""post-review — Post batched GitHub PR review.

⚠️ ALWAYS batch comments into ONE review. Never post multiple reviews (creates permanent noise).

Usage: uv run post-review <owner/repo> <pr> --input FILE --review-body TEXT [options]

RECOMMENDED (for 2+ comments):
  --input FILE          Read full review payload from JSON file
  --review-body TEXT    Review summary (required)
  --event TYPE          COMMENT (default), APPROVE, REQUEST_CHANGES

Single comment only (use sparingly):
  --path P              File path for single inline comment
  --position N          Diff position (from get-positions)
  --body-file FILE      Read comment body from file (RECOMMENDED)
  --body TEXT           Comment body directly (discouraged - use --body-file)

⚠️ GUIDELINES:
- For multiple comments: Use --input FILE (one review, clean history)
- For single comments: Use --body-file (review text before posting)
- Inline --body is for quick one-liners only (min 10 words)
- Multiple inline comments will ERROR (use --input)

Examples:
  ✓ RECOMMENDED - Batch multiple comments:
    uv run scan-violations owner/repo 42 --output review.json
    uv run post-review owner/repo 42 \\
      --input review.json \\
      --review-body "Checklist review - 5 items need attention" \\
      --event REQUEST_CHANGES

  ✓ OK - Single comment from file:
    echo "Add useCallback here to prevent unnecessary re-renders..." > comment.md
    uv run post-review owner/repo 42 \\
      --path src/hooks.ts --position 42 \\
      --body-file comment.md \\
      --review-body "Performance suggestion"

  △ Discouraged - Inline body (quick one-liners only):
    uv run post-review owner/repo 42 \\
      --path src/hooks.ts --position 42 \\
      --body "LGTM" \\
      --review-body "Approved"

  ✗ NOT SUPPORTED - Multiple inline comments:
    uv run post-review owner/repo 42 \\
      --path a.ts --position 1 --body "Fix A" \\
      --path b.ts --position 2 --body "Fix B"  # ← Will ERROR

Comment guidelines:
- Use --body-file for substantive comments (review before posting)
- Use --body only for quick responses: LGTM, Approved, +1, etc.
- Minimum 10 words for inline --body (except allowed short responses)
- Review body: "LGTM", "Approved", or 3+ word summary
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
    parser.add_argument("--review-body", required=True, help="Review summary")
    parser.add_argument(
        "--event",
        choices=["COMMENT", "APPROVE", "REQUEST_CHANGES"],
        default="COMMENT",
        help="Review type",
    )
    parser.add_argument("--input", help="Read full payload from file (recommended for batch reviews)")
    parser.add_argument("--force-short", action="store_true", help="Allow short comments (discouraged)")
    args = parser.parse_args()

    # Warn about inline usage (discourage single comments, encourage batching)
    using_inline = args.path or args.position or args.body
    if using_inline and not args.input:
        console.print("[yellow]⚠️  WARNING: Using inline comment flags creates a review with few comments.[/yellow]")
        console.print("[yellow]   This creates permanent timeline noise. Consider using --input FILE to batch comments.[/yellow]")
        console.print("[dim]   Example: uv run scan-violations owner/repo 42 --output review.json[/dim]")
        console.print("[dim]            uv run post-review owner/repo 42 --input review.json --review-body '...'[/dim]")
        console.print()

    # Validate comment word count (discourage short comments, allow common short responses)
    allowed_short_responses = frozenset({
        "lgtm", "looks good", "looks good to me", "approved", "approve",
        "+1", "👍", "🚀", "nice", "great", "good job", "well done",
        "done", "fixed", "resolved", "ack", "acknowledged", "thanks",
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
        if word_count < min_words_req and not is_allowed_short(text) and not args.force_short:
            console.print(f"[yellow]⚠️  {context} is very short ({word_count} words, min {min_words_req})[/yellow]")
            console.print(f"[dim]   Text: '{text[:60]}{'...' if len(text) > 60 else ''}'[/dim]")
            console.print("[dim]   Short responses allowed: LGTM, Approved, Looks good, +1, etc.[/dim]")
            console.print("[dim]   Or add context: explain WHY the change is needed, not just WHAT.[/dim]")
            return False
        return True

    # Check review body word count (review body can be shorter - min 3 words or allowed short)
    review_word_count = count_words(args.review_body)
    if review_word_count < 3 and not is_allowed_short(args.review_body) and not args.force_short:
        console.print(f"[yellow]⚠️  Review body is very short ({review_word_count} words)[/yellow]")
        console.print("[dim]   Hint: Use 'LGTM', 'Approved', or a brief summary of the review.[/dim]")
        console.print("[red]Error: Review body too short. Use --force-short to override.[/red]")
        sys.exit(1)

    # Build comments
    if args.input:
        if not Path(args.input).exists():
            console.print(f"[red]Error: Input file not found: {args.input}[/red]")
            sys.exit(1)
        with open(args.input) as f:
            data = json.load(f)
            comments = data.get("comments", [])
    else:
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

    # Warn if using --body instead of --body-file (discourage inline text)
    if args.body and not args.body_file and not args.force_short:
        console.print("[yellow]⚠️  Using --body with inline text (discouraged).[/yellow]")
        console.print("[dim]   For better reviewability, write comment to file and use --body-file:[/dim]")
        console.print("[dim]     echo 'Your detailed comment here' > comment.md[/dim]")
        console.print("[dim]     uv run post-review ... --body-file comment.md[/dim]")
        console.print("[yellow]   Use --force-short to skip this warning (discouraged).[/yellow]")
        console.print()

    # Only allow single inline comment - use --input FILE for multiple comments
    if using_inline and len(comments) > 1 and not args.force_short:
        console.print(f"[red]Error: Attempting to post {len(comments)} comments via inline flags.[/red]")
        console.print("[yellow]   Inline flags only support SINGLE comments.[/yellow]")
        console.print("[dim]   For multiple comments, use --input FILE to batch into ONE review:[/dim]")
        console.print("[dim]     uv run scan-violations owner/repo 42 --output review.json[/dim]")
        console.print("[dim]     uv run post-review owner/repo 42 --input review.json --review-body '...'[/dim]")
        console.print("[yellow]   Use --force-short to override (creates timeline noise).[/yellow]")
        sys.exit(1)

    # Validate comment word counts
    short_comments = []
    for i, c in enumerate(comments):
        body_text = c.get("body", "")
        word_count = count_words(body_text)
        if word_count < min_words and not is_allowed_short(body_text):
            short_comments.append((i, body_text[:60], word_count))

    if short_comments and not args.force_short:
        console.print(f"[yellow]⚠️  Found {len(short_comments)} short comment(s):[/yellow]")
        for idx, preview, words in short_comments:
            console.print(f"  [dim]Comment {idx} ({words} words): '{preview}{'...' if len(preview) >= 60 else ''}'[/dim]")
        console.print("[yellow]   Comments should explain WHY (not just WHAT) to help the author learn.[/yellow]")
        console.print("[dim]   Allowed short responses: LGTM, Approved, Looks good, +1, etc.[/dim]")
        console.print("[red]Error: Use --force-short to post anyway (discouraged).[/red]")
        sys.exit(1)

    # Fetch head commit
    with console.status("[bold green]Fetching head commit..."):
        head = fetch_head(args.repo, args.pr)

    # Build payload
    payload = {
        "commit_id": head,
        "body": args.review_body,
        "event": args.event,
        "comments": comments,
    }

    # Preview
    console.print("[bold blue]Preview:[/bold blue]")
    syntax = Syntax(json.dumps(payload, indent=2), "json", theme="monokai")
    console.print(Panel(syntax, expand=False))

    # Confirm
    if args.event == "REQUEST_CHANGES":
        confirm = console.input("[yellow]Post as REQUEST_CHANGES? (y/N): [/yellow]")
        if confirm.lower() not in ("y", "yes"):
            console.print("[dim]Aborted[/dim]")
            return

    # Post
    with console.status("[bold green]Posting review..."):
        resp = post_review(args.repo, args.pr, payload)

    url = resp.get("html_url", "OK")
    console.print(f"[green]✓ Posted: {url}[/green]")
    console.print_json(json.dumps({"id": resp.get("id"), "state": resp.get("state"), "url": url}))


if __name__ == "__main__":
    main()
