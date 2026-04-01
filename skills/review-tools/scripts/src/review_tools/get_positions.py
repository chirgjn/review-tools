#!/usr/bin/env python3
"""get-positions — Convert file:line:content to GitHub diff position with verification.

GitHub API uses "position" (line in unified diff @@ header), not file line number.
Requires content hint to verify you're commenting on the correct line.

Always outputs JSON array format.

Usage: uv run get-positions <owner/repo> <pr> <file:line:content>...

Options:
  --file PATH    Read refs from file (one per line, # comments OK)

Examples:
  uv run get-positions owner/repo 42 "src/hooks.ts:45:useEffect("
  uv run get-positions owner/repo 42 "src/hooks.ts:45:useEffect(" | jq -r '.[0].position'
  uv run get-positions owner/repo 42 --file refs.txt
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


def normalize_content(content: str, max_words: int = 20) -> str:
    """Normalize content to first N words for display."""
    content = content.strip().strip('"').strip("'")
    words = content.split()
    return " ".join(words[:max_words])


def get_content_at_line(diff: str, target_path: str, target_line: int) -> str | None:
    """Get the actual content at a specific line in the file's diff."""
    lines = diff.split("\n")
    in_file, in_hunk = False, False
    file_line = 0
    
    for line in lines:
        if line.startswith("diff --git"):
            in_file, in_hunk = False, False
        elif line.startswith("+++ b/"):
            in_file = target_path in line[6:]
            file_line = 0
        elif not in_file:
            continue
        elif line.startswith("@@"):
            in_hunk = True
            m = _RE_DIFF_HUNK.match(line)
            if m:
                file_line = int(m.group(2)) - 1  # Will be incremented
        elif in_hunk and line.startswith("+"):
            file_line += 1
            if file_line == target_line:
                return line[1:]  # Remove + prefix
        elif in_hunk and not line.startswith("-"):
            file_line += 1
    
    return None


def find_position(diff: str, target_path: str, target_line: int) -> int | None:
    """Convert file line number to GitHub diff position.

    GitHub's position is 1-based and counts from the first @@ hunk header of
    the file's diff section (the @@ line itself is position 1).  It resets for
    every file — it is NOT cumulative across the whole diff.
    """
    lines = diff.split("\n")
    in_file, in_hunk = False, False
    new_line = 0
    file_pos = 0  # per-file position counter; resets at each "+++ b/" line

    for line in lines:
        if line.startswith("diff --git"):
            in_file, in_hunk = False, False
        elif line.startswith("+++ b/"):
            in_file = target_path in line[6:]
            file_pos = 0
        elif not in_file:
            continue
        elif line.startswith("@@"):
            in_hunk = True
            file_pos += 1
            m = _RE_DIFF_HUNK.match(line)
            if m:
                new_line = int(m.group(2))
        elif not in_hunk:
            continue
        elif line[0:1] == "-":
            file_pos += 1
        else:  # "+" or context line
            file_pos += 1
            if new_line == target_line:
                return file_pos
            new_line += 1

    return None


def parse_ref(ref: str) -> tuple[str, int, str] | None:
    """Parse file:line:content reference. Content hint is required for verification."""
    # Require file:line:content format
    match = re.match(r"^(.+):(\d+):(.+)$", ref)
    if match:
        return match.group(1), int(match.group(2)), match.group(3)
    
    # file:line without content is not allowed
    return None


def verify_and_report(diff: str, path: str, line: int, expected_hint: str) -> dict:
    """Find position and verify content matches expected hint."""
    pos = find_position(diff, path, line)
    actual_content = get_content_at_line(diff, path, line) if pos else None
    
    if pos is None:
        return {
            "path": path,
            "line": line,
            "position": None,
            "status": "not_found",
            "error": "Line not found in diff"
        }
    
    normalized_expected = normalize_content(expected_hint)
    normalized_actual = normalize_content(actual_content or "")
    
    if normalized_expected in normalized_actual or expected_hint in (actual_content or ""):
        return {
            "path": path,
            "line": line,
            "position": pos,
            "status": "verified",
            "content_preview": normalized_actual
        }
    else:
        return {
            "path": path,
            "line": line,
            "position": pos,
            "status": "mismatch",
            "expected": normalized_expected,
            "actual": normalized_actual
        }


# Results are always output as JSON, no human formatting needed


def main():
    parser = argparse.ArgumentParser(
        description="Convert file:line:content to GitHub diff position (with content verification)",
        epilog=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("repo", help="owner/repo")
    parser.add_argument("pr", type=int, help="PR number")
    parser.add_argument("refs", nargs="*", help="File:line:content references (content hint required for verification)")
    parser.add_argument("--file", help="Read refs from file (one per line)")
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
    all_ok = True
    
    for ref in refs:
        parsed = parse_ref(ref)
        if not parsed:
            results.append({
                "error": "Invalid format",
                "ref": ref,
                "hint": "Use: file:line:content (e.g., src/file.ts:45:useEffect()"
            })
            all_ok = False
            continue
        
        path, line, hint = parsed
        result = verify_and_report(diff, path, line, hint)
        results.append(result)
        
        if result["status"] in ("not_found", "mismatch"):
            all_ok = False

    # Always output JSON
    print(json.dumps(results, indent=2))
    
    if not all_ok:
        sys.exit(1)


if __name__ == "__main__":
    main()
