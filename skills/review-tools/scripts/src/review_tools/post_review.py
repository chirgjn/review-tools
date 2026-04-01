#!/usr/bin/env python3
"""post-review — Post batched GitHub PR review with automatic verification.

⚠️ ALWAYS batch comments into ONE review. Never post multiple reviews (creates permanent timeline noise).

Verifies comment positions match stored content hints before posting.

Usage: uv run post-review <owner/repo> <pr> --input FILE [options]

RECOMMENDED:
  --input FILE          Read review payload from JSON (batch multiple comments)
                        JSON must include a "review_body" field and a "comments" array.
                        Each comment should have: path, position, content_hint, body
  --event TYPE          COMMENT (default), APPROVE, REQUEST_CHANGES

Single comment (use sparingly):
  --path P              File path
  --position N          Diff position (from get-positions)
  --content TEXT        Content hint for verification (required with --path)
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
  uv run post-review owner/repo 42 --path X.ts --position 5 --content "def foo" --body-file comment.md

  # Single quick (opt-in to separate review entry)
  uv run post-review owner/repo 42 --i-know-this-creates-separate-review --path X.ts --position 5 --content "def foo" --body "LGTM"
"""

import argparse
import json
import re
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


def fetch_diff(repo: str, pr: int) -> str:
    """Fetch PR diff from GitHub API."""
    try:
        result = subprocess.run(
            ["gh", "api", f"repos/{repo}/pulls/{pr}", "-H", "Accept: application/vnd.github.v3.diff"],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        console.print(f"[red]Error fetching diff: {e.stderr}[/red]")
        sys.exit(1)


def get_content_at_line(diff: str, path: str, line: int) -> str | None:
    """Get content at specific line in file's diff."""
    lines = diff.split("\n")
    in_file = False
    in_hunk = False
    file_line = 0
    
    for diff_line in lines:
        if diff_line.startswith("+++ b/"):
            in_file = path in diff_line[6:]
            file_line = 0
        elif not in_file:
            continue
        elif diff_line.startswith("@@"):
            in_hunk = True
            m = re.match(r"@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@", diff_line)
            if m:
                file_line = int(m.group(2)) - 1
        elif in_hunk and diff_line.startswith("+"):
            file_line += 1
            if file_line == line:
                return diff_line[1:]
        elif in_hunk and not diff_line.startswith("-"):
            file_line += 1
    
    return None


def normalize(content: str, max_words: int = 20) -> str:
    """Normalize content to first N words."""
    words = content.split()
    return " ".join(words[:max_words])


def verify_comment(diff: str, comment: dict) -> tuple[bool, str]:
    """Verify a single comment's position matches content_hint.
    
    Returns: (verified, error_message)
    """
    path = comment.get("path")
    file_line = comment.get("file_line")
    content_hint = comment.get("content_hint")
    
    if not path or file_line is None:
        return False, "Missing path or file_line"
    
    if not content_hint:
        return False, "No content_hint stored. Use build-review --content"
    
    actual_content = get_content_at_line(diff, path, file_line)
    
    if actual_content is None:
        return False, "Line not found in diff"
    
    # Check if content matches
    normalized_hint = normalize(content_hint)
    normalized_actual = normalize(actual_content)
    
    if normalized_hint in normalized_actual or content_hint in actual_content:
        return True, ""
    else:
        return False, f"Content mismatch (expected: {normalized_hint[:40]}, actual: {normalized_actual[:40]})"


def verify_all_comments(diff: str, comments: list[dict]) -> tuple[bool, list[tuple[int, dict, str]]]:
    """Verify all comments in the review.
    
    Returns: (all_ok, failures) where failures is list of (index, comment, error)
    """
    failures = []
    
    for i, comment in enumerate(comments):
        # Only verify inline comments with position
        if comment.get("position") is None:
            continue
            
        verified, error = verify_comment(diff, comment)
        if not verified:
            failures.append((i, comment, error))
    
    return len(failures) == 0, failures


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


def build_comments_from_flags(paths: list[str], positions: list[int], bodies: list[str], contents: list[str]) -> list[dict]:
    """Build comments array from individual flag arguments."""
    if len(paths) != len(positions) or len(paths) != len(bodies):
        raise ValueError(f"Mismatch: {len(paths)} paths, {len(positions)} positions, {len(bodies)} bodies, {len(contents)} contents")

    return [
        {"path": p, "position": pos, "content_hint": c, "body": b}
        for p, pos, c, b in zip(paths, positions, contents, bodies, strict=True)
    ]


def main():
    parser = argparse.ArgumentParser(
        description="Post batched GitHub PR review with automatic verification",
        epilog=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("repo", help="owner/repo")
    parser.add_argument("pr", type=int, help="PR number")
    parser.add_argument("--path", action="append", default=[], help="File path")
    parser.add_argument("--position", type=int, action="append", default=[], help="Diff position")
    parser.add_argument("--content", action="append", default=[], help="Content hint for verification")
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
    using_inline = args.path or args.position or args.body or args.content
    if using_inline and not args.input and not args.i_know_this_creates_separate_review:
        console.print("[red]Error: Single comment reviews create separate GitHub review entries (clutters PR history).[/red]")
        console.print("[dim]   Option 1: Use --input FILE to batch multiple comments (recommended):[/dim]")
        console.print("[dim]     uv run scan-violations owner/repo 42 --output review.json[/dim]")
        console.print("[dim]     uv run post-review owner/repo 42 --input review.json[/dim]")
        console.print("[dim]   Option 2: Use --i-know-this-creates-separate-review to explicitly accept the anti-pattern:[/dim]")
        console.print("[dim]     uv run post-review owner/repo 42 --i-know-this-creates-separate-review --path X --position N --content 'def foo' --body 'LGTM'[/dim]")
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
    raw_comments: list[dict] = []
    
    if args.input:
        if not Path(args.input).exists():
            console.print(f"[red]Error: Input file not found: {args.input}[/red]")
            sys.exit(1)
        with open(args.input) as f:
            data = json.load(f)
            raw_comments = data.get("comments", [])
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
            console.print("[red]Error: Provide --path/--position/--content/--body or --input FILE[/red]")
            sys.exit(1)

        # Validate content hint required
        if not args.content:
            console.print("[red]Error: --content is required for verification (first 20 words of the line)[/red]")
            console.print("[dim]   Example: --content 'def handle_request'[/dim]")
            sys.exit(1)

        if len(args.content) != len(args.path):
            console.print(f"[red]Error: Mismatch: {len(args.path)} paths but {len(args.content)} content hints[/red]")
            sys.exit(1)

        raw_comments = build_comments_from_flags(args.path, args.position, [body], args.content)
        review_body = review_body or body  # fall back to comment body for single inline comments

    review_word_count = count_words(review_body)
    if review_word_count < 3 and not is_allowed_short(review_body):
        console.print(f"[yellow]⚠️  Review body is very short ({review_word_count} words)[/yellow]")
        console.print("[dim]   Hint: Use 'LGTM', 'Approved', or a brief summary of the review.[/dim]")
        console.print("[red]Error: Review body too short.[/red]")
        sys.exit(1)

    # Only allow single inline comment - use --input FILE for multiple comments
    if using_inline and len(raw_comments) > 1:
        console.print(f"[red]Error: Attempting to post {len(raw_comments)} comments via inline flags.[/red]")
        console.print("[yellow]   Inline flags only support SINGLE comments.[/yellow]")
        console.print("[dim]   For multiple comments, use --input FILE to batch into ONE review:[/dim]")
        console.print("[dim]     uv run scan-violations owner/repo 42 --output review.json[/dim]")
        console.print("[dim]     uv run post-review owner/repo 42 --input review.json[/dim]")
        sys.exit(1)

    # Validate comment word counts
    short_comments = []
    for i, c in enumerate(raw_comments):
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

    # VERIFICATION STEP
    with console.status("[bold green]Verifying positions against diff..."):
        diff = fetch_diff(args.repo, args.pr)
    
    all_ok, failures = verify_all_comments(diff, raw_comments)
    
    if not all_ok:
        console.print(f"[red]✗ Verification failed for {len(failures)} comment(s):[/red]\n")
        for i, comment, error in failures:
            path = comment.get("path", "unknown")
            line = comment.get("file_line", "unknown")
            console.print(f"  {i+1}. [red]{path}:{line}[/red]")
            console.print(f"      Error: {error}")
            console.print(f"      Body: {comment.get('body', 'N/A')[:50]}...")
        console.print("\n[yellow]Fix the positions or content hints and try again.[/yellow]")
        sys.exit(1)
    
    console.print(f"[green]✓ All {len(raw_comments)} position(s) verified[/green]\n")

    # Strip non-API fields before posting
    comments = [
        {k: v for k, v in c.items() if k in ("path", "position", "body")}
        for c in raw_comments
    ]

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
