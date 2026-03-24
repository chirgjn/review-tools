#!/usr/bin/env python3
"""get-positions — Convert file:line to GitHub diff position.

GitHub API uses "position" (line in unified diff @@ header), not file line number.

Usage: uv run get-positions <owner/repo> <pr> <file:line>... [options]

Options:
  --file PATH    Read refs from file (one per line, # comments OK)
  --json         Output as JSON array
  --compact      Output one JSON per line

Examples:
  uv run get-positions owner/repo 42 src/hooks.ts:45
  uv run get-positions owner/repo 42 --file refs.txt
  uv run get-positions owner/repo 42 src/hooks.ts:45 src/utils.ts:12 --json
"""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

from rich.console import Console

console = Console()

# Pre-compile regex for diff hunk parsing
_RE_DIFF_HUNK = re.compile(r"@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@")


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


def find_position(diff: str, target_path: str, target_line: int) -> int | None:
    """Convert file line number to GitHub diff position."""
    lines = diff.split("\n")
    in_file, in_hunk, new_line, pos = False, False, 0, 0

    for i, line in enumerate(lines, 1):
        # Use startswith checks (faster than regex)
        if line.startswith("diff --git"):
            in_file, in_hunk = False, False
        elif line.startswith("+++ b/"):
            in_file = target_path in line[6:]
        elif not in_file:
            continue
        elif line.startswith("@@"):
            in_hunk = True
            m = _RE_DIFF_HUNK.match(line)
            if m:
                new_line = int(m.group(2))
                pos = i
        elif not in_hunk:
            continue
        elif line[0:1] in ("+", " "):
            if new_line == target_line:
                return pos + 1
            new_line += 1
            pos = i

    return None


def parse_ref(ref: str) -> tuple[str, int] | None:
    """Parse file:line reference."""
    match = re.match(r"^(.+):(\d+)$", ref)
    if not match:
        return None
    return match.group(1), int(match.group(2))


def main():
    parser = argparse.ArgumentParser(
        description="Convert file:line to GitHub diff position",
        epilog=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("repo", help="owner/repo")
    parser.add_argument("pr", type=int, help="PR number")
    parser.add_argument("refs", nargs="*", help="File:line references (e.g., src/file.ts:45)")
    parser.add_argument("--file", help="Read refs from file (one per line)")
    parser.add_argument("--json", action="store_true", help="Output as JSON array")
    parser.add_argument("--compact", action="store_true", help="Output one JSON per line")
    args = parser.parse_args()

    # Validate repo format
    if "/" not in args.repo:
        console.print("[red]Error: Repository must be 'owner/repo'[/red]")
        sys.exit(1)

    # Collect refs
    refs: list[str] = []
    if args.file:
        if not Path(args.file).exists():
            console.print(f"[red]Error: File not found: {args.file}[/red]")
            sys.exit(1)
        with open(args.file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    refs.append(line)

    refs.extend(args.refs)

    if not refs:
        console.print("[red]Error: No file:line references provided[/red]")
        sys.exit(1)

    # Fetch diff
    with console.status("[bold green]Fetching diff..."):
        diff = fetch_diff(args.repo, args.pr)

    # Find positions
    results: list[dict] = []
    for ref in refs:
        parsed = parse_ref(ref)
        if not parsed:
            console.print(f"[yellow]Skip: {ref}[/yellow]")
            continue

        path, line = parsed
        pos = find_position(diff, path, line)

        if pos:
            console.print(f"[green]✓ {path}:{line} → {pos}[/green]")
            results.append({"path": path, "line": line, "position": pos})
        else:
            console.print(f"[yellow]Not found: {path}:{line}[/yellow]")
            results.append({"path": path, "line": line, "position": None})

    # Output
    if args.json:
        console.print_json(json.dumps(results))
    elif args.compact:
        for r in results:
            console.print(json.dumps(r))
    # else: human-readable already printed above


if __name__ == "__main__":
    main()
