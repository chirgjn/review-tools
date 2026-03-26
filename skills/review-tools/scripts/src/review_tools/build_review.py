#!/usr/bin/env python3
"""build-review — Build GitHub review payload incrementally.

Usage: uv run build-review [options]

Options:
  --file FILE              Payload file (e.g. review-42.json — include PR number to avoid collisions)
  --path P                 File path
  --position N             Diff position (from get-positions)
  --body TEXT              Comment body
  --body-file FILE         Read body from file
  --summary-file FILE      Set the review summary from a file (stored in the payload file)
  --show                   Display current payload
  --export-comments        Output comments array for piping
  --clear                  Clear all comments
  --post REPO PR           Post review via post-review
  --event TYPE             COMMENT (default), APPROVE, REQUEST_CHANGES

Examples:
  uv run build-review --summary-file summary-42.md
  uv run build-review --path src/hooks.ts --position 42 --body-file comment.md
  uv run build-review --show
  uv run build-review --post owner/repo 42 --event REQUEST_CHANGES
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path


def load(path):
    return json.loads(Path(path).read_text()) if Path(path).exists() else {"review_body": "", "comments": []}


def save(path, data):
    Path(path).write_text(json.dumps(data, indent=2))
    print(f"Saved {len(data['comments'])} comments to {path}", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(description="Build review payload incrementally", epilog=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--file", "-f", default="review_payload.json", help="Payload file")
    parser.add_argument("--path", help="File path")
    parser.add_argument("--position", type=int, help="Diff position")
    parser.add_argument("--body", help="Comment body")
    parser.add_argument("--body-file", help="File with comment body")
    parser.add_argument("--show", action="store_true", help="Show payload")
    parser.add_argument("--export-comments", action="store_true", help="Export comments array")
    parser.add_argument("--clear", action="store_true", help="Clear all comments")
    parser.add_argument("--post", nargs=2, metavar=("REPO", "PR"), help="Post review via post-review")
    parser.add_argument("--summary-file", help="Set the review summary from a file (stored in payload file)")
    parser.add_argument("--event", default="COMMENT", choices=["COMMENT", "APPROVE", "REQUEST_CHANGES"], help="Review type")
    args = parser.parse_args()
    data = load(args.file)
    body = args.body
    if args.body_file:
        body = Path(args.body_file).read_text()
    if args.summary_file:
        if not Path(args.summary_file).exists():
            print(f"Error: Summary file not found: {args.summary_file}", file=sys.stderr)
            sys.exit(1)
        data["review_body"] = Path(args.summary_file).read_text()
        save(args.file, data)
    if args.path or args.position is not None or body:
        if not all([args.path, args.position is not None, body]):
            print("Error: --path, --position, and --body/--body-file required together", file=sys.stderr)
            sys.exit(1)
        data["comments"].append({"path": args.path, "position": args.position, "body": body})
        save(args.file, data)
    if args.clear:
        data["review_body"] = ""
        data["comments"] = []
        save(args.file, data)
    if args.show:
        print(json.dumps(data, indent=2))
    if args.export_comments:
        print(json.dumps(data["comments"]))
    if args.post:
        repo, pr = args.post
        subprocess.run(
            ["uv", "run", "post-review", repo, pr, "--input", args.file, "--event", args.event],
            check=True,
        )
    if not any([args.summary_file, args.path, args.show, args.export_comments, args.clear, args.post]):
        parser.print_help()


if __name__ == "__main__":
    main()
