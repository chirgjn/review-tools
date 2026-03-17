"""
pr_threads.py — fetch and display human review threads for one or more PRs.

Accepts PR references in any of these formats, mixed freely:
    https://github.com/razorpay/wallet-frontend/pull/35
    razorpay/wallet-frontend#35
    razorpay/wallet#3          (repo slug resolved via --slug-map or default org)

Usage:
    uv run scripts/review/pr_threads.py \\
        https://github.com/razorpay/wallet-frontend/pull/35 \\
        razorpay/wallet-frontend#36 \\
        razorpay/wallet#3

    # Your own comments — default, no flag needed
    uv run scripts/review/pr_threads.py <refs...>

    # Explicit reviewer
    uv run scripts/review/pr_threads.py <refs...> --reviewer chirgjn
    uv run scripts/review/pr_threads.py <refs...> --reviewer @me

    # All reviewers (no filter)
    uv run scripts/review/pr_threads.py <refs...> --all

    # Show diff for a specific file pattern
    uv run scripts/review/pr_threads.py <refs...> --diff useKycFlowHandler

    # Inspect specific comment IDs
    uv run scripts/review/pr_threads.py <refs...> --comments 2888363711 2888364162

    # Map short slugs to full repo names
    uv run scripts/review/pr_threads.py razorpay/wallet#3 \\
        --slug-map wallet=razorpay/wallet-frontend

Requires: gh CLI authenticated
"""

import argparse
import collections
import json
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed


# ---------------------------------------------------------------------------
# Parsing PR references
# ---------------------------------------------------------------------------

# Default slug expansions: short name -> full owner/repo
DEFAULT_SLUG_MAP: dict[str, str] = {
    "wallet": "razorpay/wallet-frontend",
}

# Patterns
_URL_RE = re.compile(r"https://github\.com/([^/]+/[^/]+)/pull/(\d+)")
_SLUG_RE = re.compile(r"([^/]+)/([^#]+)#(\d+)")  # owner/repo#number or owner/slug#number


def parse_ref(ref: str, slug_map: dict[str, str]) -> tuple[str, int]:
    """Return (repo, pr_number) from a URL, slug, or owner/repo#number string."""
    m = _URL_RE.match(ref)
    if m:
        return m.group(1), int(m.group(2))

    m = _SLUG_RE.match(ref)
    if m:
        owner, name, number = m.group(1), m.group(2), int(m.group(3))
        full = f"{owner}/{name}"
        # Expand slug if known
        resolved = slug_map.get(name) or slug_map.get(full) or full
        return resolved, number

    raise ValueError(f"Cannot parse PR reference: {ref!r}")


def parse_slug_map(pairs: list[str]) -> dict[str, str]:
    """Parse ['wallet=razorpay/wallet-frontend', ...] into a dict."""
    result = dict(DEFAULT_SLUG_MAP)
    for pair in pairs or []:
        if "=" not in pair:
            raise ValueError(f"--slug-map entries must be key=owner/repo, got: {pair!r}")
        key, val = pair.split("=", 1)
        result[key.strip()] = val.strip()
    return result


# ---------------------------------------------------------------------------
# GitHub API
# ---------------------------------------------------------------------------

def gh(args: list[str]) -> list | dict:
    result = subprocess.run(
        ["gh"] + args,
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(result.stdout)


def fetch_pr(repo: str, pr: int) -> dict:
    """Fetch PR metadata, review comments, and issue comments in parallel."""
    with ThreadPoolExecutor(max_workers=3) as pool:
        f_info = pool.submit(gh, ["pr", "view", str(pr), "--repo", repo, "--json", "title,body,number"])
        f_reviews = pool.submit(gh, ["api", f"repos/{repo}/pulls/{pr}/comments", "--paginate"])
        f_issue = pool.submit(gh, ["api", f"repos/{repo}/issues/{pr}/comments", "--paginate"])
        info = f_info.result()
        reviews = f_reviews.result()
        issue_comments = f_issue.result()
    info["_repo"] = repo
    return {"info": info, "reviews": reviews, "issue_comments": issue_comments}


def resolve_reviewer(reviewer: str | None, all_reviewers: bool = False) -> str | None:
    """Resolve the reviewer filter.

    - --all: return None (no filtering)
    - --reviewer LOGIN: return that login as-is
    - --reviewer @me or omitted: resolve to authenticated user's login
    """
    if all_reviewers:
        return None
    if reviewer is None or reviewer == "@me":
        return gh(["api", "user"])["login"]
    return reviewer


# ---------------------------------------------------------------------------
# Thread building
# ---------------------------------------------------------------------------

def is_bot(login: str) -> bool:
    return "bot" in login.lower()


def build_threads(reviews: list) -> collections.OrderedDict:
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


# ---------------------------------------------------------------------------
# Output modes
# ---------------------------------------------------------------------------

def print_threads(pr_data: dict, reviewer: str | None = None, comment_ids: set | None = None):
    info = pr_data["info"]
    reviews = pr_data["reviews"]
    issue_comments = pr_data["issue_comments"]

    threads = build_threads(reviews)

    print(f"=== PR #{info['number']} ({info['_repo']}): {info['title']} ===\n")

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

        print(f"Thread: {root['path']}:{root.get('line', root.get('original_line', '?'))}")
        print(f"URL: {root['html_url']}")
        for m in all_msgs:
            print(f"  @{m['user']['login']}: {m['body'][:300]}")
        print()

    human_issue = [c for c in issue_comments if not is_bot(c["user"]["login"])]
    if reviewer:
        human_issue = [c for c in human_issue if c["user"]["login"] == reviewer]
    if human_issue:
        print("-- Issue comments --")
        for c in human_issue:
            print(f"  @{c['user']['login']}: {c['body'][:300]}")
        print()


def print_diff(pr_data: dict, file_filter: str):
    repo = pr_data["info"]["_repo"]
    pr_num = pr_data["info"]["number"]
    files = gh(["api", f"repos/{repo}/pulls/{pr_num}/files", "--paginate"])
    print(f"=== PR #{pr_num} ({repo}) — files matching '{file_filter}' ===\n")
    for f in files:
        if file_filter not in f["filename"]:
            continue
        print(f"--- {f['filename']} ---")
        print(f.get("patch", "NO PATCH"))
        print()


def print_comments_by_id(pr_data: dict, comment_ids: set):
    for c in pr_data["reviews"]:
        if str(c["id"]) in comment_ids or str(c.get("in_reply_to_id", "")) in comment_ids:
            print(f"id={c['id']} reply_to={c.get('in_reply_to_id')} user={c['user']['login']}")
            print(f"body={c['body'][:400]}")
            print(f"diff_hunk=...{c['diff_hunk'][-300:]}")
            print()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Fetch and display PR review threads.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "refs",
        nargs="+",
        help="PR references: URLs, owner/repo#number, or slug#number",
    )
    parser.add_argument(
        "--slug-map",
        nargs="+",
        metavar="SLUG=OWNER/REPO",
        help="Map short repo slugs to full names, e.g. wallet=razorpay/wallet-frontend",
    )
    parser.add_argument(
        "--reviewer",
        default=None,
        metavar="LOGIN",
        help="Filter threads to a specific reviewer login or @me (default: authenticated user)",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        dest="all_reviewers",
        help="Show threads from all reviewers, not just the authenticated user",
    )
    parser.add_argument("--diff", metavar="FILE", help="Show diff for files matching this substring")
    parser.add_argument("--comments", nargs="+", help="Show specific comment IDs")
    args = parser.parse_args()

    slug_map = parse_slug_map(args.slug_map or [])
    comment_ids = set(args.comments) if args.comments else None
    reviewer = resolve_reviewer(args.reviewer, all_reviewers=args.all_reviewers)

    # Parse all refs
    targets: list[tuple[str, int]] = []
    for ref in args.refs:
        try:
            targets.append(parse_ref(ref, slug_map))
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

    # Fetch all PRs in parallel
    pr_data_list: list[tuple[tuple[str, int], dict]] = []
    with ThreadPoolExecutor(max_workers=min(len(targets), 8)) as pool:
        futures = {pool.submit(fetch_pr, repo, pr): (repo, pr) for repo, pr in targets}
        results: dict[tuple[str, int], dict] = {}
        for future in as_completed(futures):
            key = futures[future]
            results[key] = future.result()

    # Output in original input order
    for key in targets:
        data = results[key]
        if args.diff:
            print_diff(data, args.diff)
        elif args.comments:
            print_comments_by_id(data, comment_ids)
        else:
            print_threads(data, reviewer=reviewer, comment_ids=comment_ids)


if __name__ == "__main__":
    main()
