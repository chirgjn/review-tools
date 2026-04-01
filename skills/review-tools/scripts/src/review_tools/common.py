#!/usr/bin/env python3
"""Common utilities for review tools."""

import re
import subprocess
import sys
from collections import OrderedDict
from typing import Any

import httpx


def get_gh_token() -> str:
    """Get GitHub CLI auth token."""
    try:
        result = subprocess.run(
            ["gh", "auth", "token"], capture_output=True, text=True, check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        print("Error: gh not authenticated. Run `gh auth login`", file=sys.stderr)
        sys.exit(1)


def get_current_user(token: str) -> str | None:
    """Get current GitHub user."""
    try:
        resp = httpx.get(
            "https://api.github.com/user",
            headers={
                "Authorization": f"token {token}",
                "Accept": "application/vnd.github.v3+json",
            },
        )
        resp.raise_for_status()
        return resp.json().get("login")
    except httpx.HTTPError:
        return None


def fetch_pr_comments(repo: str, pr: int, token: str) -> list[dict[str, Any]]:
    """Fetch ALL review comments from PR via GitHub API (with pagination)."""
    all_comments: list[dict[str, Any]] = []
    url = f"https://api.github.com/repos/{repo}/pulls/{pr}/comments"

    while url:
        resp = httpx.get(
            url,
            headers={
                "Authorization": f"token {token}",
                "Accept": "application/vnd.github.v3+json",
            },
        )
        resp.raise_for_status()
        all_comments.extend(resp.json())

        # Parse Link header for next page
        link_header = resp.headers.get("link", "")
        url = None
        if 'rel="next"' in link_header:
            match = re.search(r'<([^>]+)>; rel="next"', link_header)
            if match:
                url = match.group(1)

    return all_comments


def fetch_issue_comments(repo: str, pr: int, token: str) -> list[dict[str, Any]]:
    """Fetch issue comments from PR via GitHub API."""
    resp = httpx.get(
        f"https://api.github.com/repos/{repo}/issues/{pr}/comments",
        headers={
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json",
        },
    )
    resp.raise_for_status()
    return resp.json()


def build_threads(
    comments: list[dict[str, Any]],
) -> OrderedDict[int, dict[str, Any]]:
    """Build thread mapping: root_id -> {root, replies[]}.

    Args:
        comments: List of review comment dicts from GitHub API.

    Returns:
        OrderedDict mapping root comment ID to dict with 'root' and 'replies'.
    """
    threads: OrderedDict[int, dict[str, Any]] = OrderedDict()
    for c in comments:
        rid = c.get("in_reply_to_id")
        if rid is None:
            threads[c["id"]] = {"root": c, "replies": []}
        else:
            if rid in threads:
                threads[rid]["replies"].append(c)
            else:
                # Nested reply - find parent thread
                for t in threads.values():
                    if any(r["id"] == rid for r in t["replies"]):
                        t["replies"].append(c)
                        break
    return threads


def is_bot(login: str) -> bool:
    """Check if user is a bot."""
    return "bot" in login.lower()


def print_comment_body(body: str, indent: int = 2, max_lines: int | None = None) -> None:
    """Print comment body with proper indentation.

    Args:
        body: The comment body text.
        indent: Number of spaces to indent each line.
        max_lines: Maximum number of lines to print. None for all.
    """
    prefix = " " * indent
    lines = body.split("\n")
    if max_lines and len(lines) > max_lines:
        lines = lines[:max_lines]
    for line in lines:
        print(f"{prefix}{line}")
    if max_lines and len(body.split("\n")) > max_lines:
        print(f"{prefix}...")


def print_diff_hunk(diff_hunk: str, max_lines: int | None = None, indent: int = 2) -> None:
    """Print diff hunk with proper indentation.

    Args:
        diff_hunk: The diff hunk text from GitHub API.
        max_lines: Maximum number of lines to print (from end). None for all.
        indent: Number of spaces to indent each line.
    """
    prefix = " " * indent
    lines = diff_hunk.split("\n")
    if max_lines and len(lines) > max_lines:
        lines = lines[-max_lines:]
    for line in lines:
        print(f"{prefix}{line}")
