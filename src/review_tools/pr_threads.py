#!/usr/bin/env python3
"""pr-threads — Fetch PR review threads for pattern analysis.

Usage: uv run pr-threads <refs> [options]

Refs: https://github.com/owner/repo/pull/35 | owner/repo#35 | owner/slug#35

Options:
  --all                All reviewers (default: yours only)
  --reviewer LOGIN     Filter to reviewer (@me = you)
  --file-pattern P     Filter files matching P (with diff context)
  --body-filter TEXT   Filter comments containing TEXT
  --comments ID...     Inspect specific comment IDs
  --slug-map K=V       Expand slugs (e.g., short=owner/full-repo)

Examples:
  uv run pr-threads owner/repo#35 owner/repo#36 --all
  uv run pr-threads owner/repo#35 --all --file-pattern hooks.ts
  uv run pr-threads owner/repo#35 --body-filter "useCallback" | uv run suggest-checklist

Output: Threaded comments (id, path:line, commit, author, body). Pipe to suggest-checklist.
"""

import argparse
import collections
import json
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

DEFAULT_SLUG_MAP = {"wallet": "razorpay/wallet-frontend"}
_URL_RE = re.compile(r"https://github\.com/([^/]+/[^/]+)/pull/(\d+)")
_SLUG_RE = re.compile(r"([^/]+)/([^#]+)#(\d+)")


def parse_ref(ref, slug_map):
    m = _URL_RE.match(ref)
    if m:
        return m.group(1), int(m.group(2))
    m = _SLUG_RE.match(ref)
    if m:
        owner, name, number = m.group(1), m.group(2), int(m.group(3))
        full = f"{owner}/{name}"
        resolved = slug_map.get(name) or slug_map.get(full) or full
        return resolved, number
    raise ValueError(f"Cannot parse PR reference: {ref!r}")


def parse_slug_map(pairs):
    result = dict(DEFAULT_SLUG_MAP)
    for pair in pairs or []:
        if "=" not in pair:
            raise ValueError(f"--slug-map entries must be key=owner/repo: {pair!r}")
        key, val = pair.split("=", 1)
        result[key.strip()] = val.strip()
    return result


def gh(args):
    """Run gh CLI command and return JSON output."""
    try:
        result = subprocess.run(["gh"] + args, capture_output=True, text=True, check=True)
        return json.loads(result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"Error running 'gh {' '.join(args)}': {e.stderr}", file=sys.stderr)
        raise
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON from 'gh {' '.join(args)}': {e}", file=sys.stderr)
        raise


def fetch_pr(repo, pr):
    with ThreadPoolExecutor(max_workers=3) as pool:
        f_info = pool.submit(gh, ["pr", "view", str(pr), "--repo", repo, "--json", "title,body,number"])
        f_reviews = pool.submit(gh, ["api", f"repos/{repo}/pulls/{pr}/comments", "--paginate"])
        f_issue = pool.submit(gh, ["api", f"repos/{repo}/issues/{pr}/comments", "--paginate"])
        info = f_info.result()
        reviews = f_reviews.result()
        issue_comments = f_issue.result()
    info["_repo"] = repo
    return {"info": info, "reviews": reviews, "issue_comments": issue_comments}


def resolve_reviewer(reviewer, all_reviewers=False):
    if all_reviewers:
        return None
    if reviewer is None or reviewer == "@me":
        return gh(["api", "user"])["login"]
    return reviewer


def is_bot(login):
    return "bot" in login.lower()


def build_threads(reviews):
    threads = collections.OrderedDict()
    for c in reviews:
        rid = c.get("in_reply_to_id")
        if rid is None:
            threads[c["id"]] = {"root": c, "replies": []}
        else:
            if rid in threads:
                threads[rid]["replies"].append(c)
            else:
                for t in threads.values():
                    if any(r["id"] == rid for r in t["replies"]):
                        t["replies"].append(c)
                        break
    return threads


def print_threads(pr_data, reviewer=None, comment_ids=None, body_filter=None):
    info = pr_data["info"]
    reviews = pr_data["reviews"]
    issue_comments = pr_data["issue_comments"]
    repo = info['_repo']
    pr_num = info['number']
    threads = build_threads(reviews)
    print(f"=== PR #{pr_num} ({repo}): {info['title']} ===\n")
    for t in threads.values():
        root = t["root"]
        all_msgs = [root] + t["replies"]
        human_msgs = [m for m in all_msgs if not is_bot(m["user"]["login"])]
        if not human_msgs:
            continue
        if reviewer and not any(m["user"]["login"] == reviewer for m in human_msgs):
            continue
        if comment_ids and not any(str(m["id"]) in comment_ids for m in all_msgs):
            continue
        if body_filter and not any(body_filter.lower() in m.get("body", "").lower() for m in human_msgs):
            continue
        commit = root.get('commit_id', 'unknown')[:8]
        root_id = root['id']
        path = root['path']
        line = root.get('line', root.get('original_line', '?'))
        print(f"Thread: {path}:{line}")
        print(f"  id={root_id} repo={repo} pr={pr_num} commit={commit}")
        print(f"  URL: {root['html_url']}")
        for m in all_msgs:
            msg_id = m['id']
            author = m['user']['login']
            body = m['body']
            print(f"  [id={msg_id}] @{author}:")
            for line in body[:500].split('\n'):
                print(f"    {line}")
            if len(body) > 500:
                print(f"    ... ({len(body) - 500} more chars)")
        print()
    human_issue = [c for c in issue_comments if not is_bot(c["user"]["login"])]
    if reviewer:
        human_issue = [c for c in human_issue if c["user"]["login"] == reviewer]
    if human_issue:
        print("-- Issue comments --")
        for c in human_issue:
            print(f"  [id={c['id']}] repo={repo} pr={pr_num} @{c['user']['login']}:")
            for line in c['body'][:300].split('\n'):
                print(f"    {line}")
            if len(c['body']) > 300:
                print(f"    ... ({len(c['body']) - 300} more chars)")
        print()


def print_file_pattern(pr_data, file_pattern, reviewer=None, body_filter=None):
    repo = pr_data["info"]["_repo"]
    pr_num = pr_data["info"]["number"]
    reviews = pr_data["reviews"]
    header = f"=== PR #{pr_num} ({repo}) — comments on files matching '{file_pattern}'"
    if body_filter:
        header += f" with '{body_filter}'"
    header += " ==="
    print(header + "\n")
    found = False
    for c in reviews:
        if is_bot(c["user"]["login"]):
            continue
        if file_pattern not in c.get("path", ""):
            continue
        if body_filter and body_filter.lower() not in c.get("body", "").lower():
            continue
        if reviewer and c["user"]["login"] != reviewer:
            continue
        found = True
        comment_id = c['id']
        path = c['path']
        line = c.get('line') or c.get('original_line', '?')
        commit = c.get('commit_id', 'unknown')[:8]
        author = c['user']['login']
        body = c['body']
        print(f"File: {path}:{line}")
        print(f"  id={comment_id} repo={repo} pr={pr_num} commit={commit}")
        print(f"  [id={comment_id}] @{author}:")
        for line in body[:500].split('\n'):
            print(f"    {line}")
        if len(body) > 500:
            print(f"    ... ({len(body) - 500} more chars)")
        print()
    if not found:
        msg = f"No comments on files matching '{file_pattern}'"
        if body_filter:
            msg += f" with '{body_filter}'"
        print(msg)
        if reviewer:
            print(f"(filtered to: {reviewer})")


def print_comments_by_id(pr_data, comment_ids):
    repo = pr_data["info"]["_repo"]
    pr_num = pr_data["info"]["number"]
    print(f"=== PR #{pr_num} ({repo}) — comment inspection ===\n")
    for c in pr_data["reviews"]:
        if str(c["id"]) in comment_ids or str(c.get("in_reply_to_id", "")) in comment_ids:
            commit = c.get('commit_id', 'unknown')[:8]
            path = c.get('path', 'unknown')
            line = c.get('line') or c.get('original_line', '?')
            author = c['user']['login']
            body = c['body']
            print(f"id={c['id']} repo={repo} pr={pr_num} path={path}:{line} commit={commit} reply_to={c.get('in_reply_to_id')} user={author}")
            print("body:")
            for line in body.split('\n'):
                print(f"  {line}")
            print("diff_hunk:")
            diff = c.get('diff_hunk', '[No diff hunk available]')
            for line in diff.split('\n')[-10:]:
                print(f"  {line}")
            print()


def main():
    parser = argparse.ArgumentParser(description="Fetch PR review threads", epilog=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("refs", nargs="+", help="PR references: URL, owner/repo#N, or owner/slug#N")
    parser.add_argument("--slug-map", nargs="+", metavar="K=V", help="Expand short slugs (e.g., wallet=razorpay/wallet-frontend)")
    parser.add_argument("--reviewer", metavar="LOGIN", help="Filter to reviewer (@me = yourself, default)")
    parser.add_argument("--all", action="store_true", dest="all_reviewers", help="Show all reviewers (no filter)")
    parser.add_argument("--file-pattern", metavar="P", help="Show comments on matching files (with diff context)")
    parser.add_argument("--body-filter", metavar="TEXT", help="Filter comments containing TEXT")
    parser.add_argument("--comments", nargs="+", metavar="ID", help="Inspect specific comment IDs")
    args = parser.parse_args()
    slug_map = parse_slug_map(args.slug_map or [])
    comment_ids = set(args.comments) if args.comments else None
    reviewer = resolve_reviewer(args.reviewer, all_reviewers=args.all_reviewers)
    targets = []
    for ref in args.refs:
        try:
            targets.append(parse_ref(ref, slug_map))
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
    with ThreadPoolExecutor(max_workers=min(len(targets), 8)) as pool:
        futures = {pool.submit(fetch_pr, repo, pr): (repo, pr) for repo, pr in targets}
        results = {}
        for future in as_completed(futures):
            key = futures[future]
            results[key] = future.result()
    for key in targets:
        data = results[key]
        if args.file_pattern:
            print_file_pattern(data, args.file_pattern, reviewer=reviewer, body_filter=args.body_filter)
        elif args.body_filter:
            print_threads(data, reviewer=reviewer, comment_ids=comment_ids, body_filter=args.body_filter)
        elif args.comments:
            print_comments_by_id(data, comment_ids)
        else:
            print_threads(data, reviewer=reviewer, comment_ids=comment_ids)


if __name__ == "__main__":
    main()
