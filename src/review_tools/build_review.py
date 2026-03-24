#!/usr/bin/env python3
"""
build_review.py — Build GitHub review payload incrementally.

Usage: ./scripts/build_review.py [options]

Options:
  --file FILE          Payload file (default: review_payload.json)
  --path P             File path for comment
  --position N         Diff position (use get_positions.sh to get)
  --body TEXT          Comment body
  --body-file FILE     Read body from file (for complex markdown)
  --show               Display current payload
  --export-comments    Output comments array (for piping)
  --clear              Clear all comments
  --post REPO PR       Post review (requires gh CLI)
  --review-body TEXT   Review summary (default: "Review from checklist")
  --event TYPE         COMMENT (default), APPROVE, REQUEST_CHANGES

Examples:
  ./build_review.py --path src/hooks.ts --position 42 --body "Add useCallback"
  ./build_review.py --path src/hooks.ts --position 42 --body-file comment.md
  ./build_review.py --show
  ./build_review.py --post owner/repo 42 --review-body "Checklist review" --event REQUEST_CHANGES
  ./build_review.py --export-comments | ./gh_post_review.sh owner/repo 42 --comments-json -

Position: Use get_positions.sh to convert file:line to diff position.
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path


def load(path):
    return json.loads(Path(path).read_text()) if Path(path).exists() else {"comments": []}


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
    parser.add_argument("--post", nargs=2, metavar=("REPO", "PR"), help="Post review")
    parser.add_argument("--review-body", default="Review from checklist", help="Review summary")
    parser.add_argument("--event", default="COMMENT", choices=["COMMENT", "APPROVE", "REQUEST_CHANGES"], help="Review type")
    args = parser.parse_args()
    data = load(args.file)
    body = args.body
    if args.body_file:
        body = Path(args.body_file).read_text()
    if args.path or args.position is not None or body:
        if not all([args.path, args.position is not None, body]):
            print("Error: --path, --position, and --body/--body-file required together", file=sys.stderr)
            sys.exit(1)
        data["comments"].append({"path": args.path, "position": args.position, "body": body})
        save(args.file, data)
    if args.clear:
        data["comments"] = []
        save(args.file, data)
    if args.show:
        print(json.dumps(data, indent=2))
    if args.export_comments:
        print(json.dumps(data["comments"]))
    if args.post:
        if not data["comments"]:
            print("Error: No comments to post", file=sys.stderr)
            sys.exit(1)
        repo, pr = args.post
        head = subprocess.run(["gh", "api", f"repos/{repo}/pulls/{pr}", "--jq", ".head.sha"], capture_output=True, text=True, check=True).stdout.strip()
        payload = {"commit_id": head, "body": args.review_body, "event": args.event, "comments": data["comments"]}
        r = subprocess.run(["gh", "api", f"repos/{repo}/pulls/{pr}/reviews", "-X", "POST", "--input", "-"], input=json.dumps(payload), capture_output=True, text=True)
        if r.returncode == 0:
            print(f"Posted: {json.loads(r.stdout).get('html_url', 'OK')}")
        else:
            print(f"Error: {r.stderr}", file=sys.stderr)
            sys.exit(1)
    if not any([args.path, args.show, args.export_comments, args.clear, args.post]):
        parser.print_help()


if __name__ == "__main__":
    main()
