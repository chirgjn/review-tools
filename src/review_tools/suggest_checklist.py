#!/usr/bin/env python3
"""
suggest_checklist_updates.py — Analyze review patterns and suggest checklist updates.

Usage: uv run scripts/pr_threads.py ... | uv run scripts/suggest_checklist_updates.py [options]

Input Format: Expects output from pr_threads.py:
  Thread: path/to/file:line
    id=... repo=... pr=... commit=...
    [id=...] @author:
      Comment body line 1
      Comment body line 2

Options:
  --input FILE         Read from file instead of stdin
  --threshold N        Min frequency to suggest (default: 3)
  --checklist FILE     Compare against existing checklist (deduplicate)
  --apply              Actually modify checklist (default: dry-run)
  --new-only           Show only new suggestions
  --output FILE        Save report to file

Examples:
  uv run scripts/pr_threads.py owner/repo#35 owner/repo#36 --all | uv run scripts/suggest_checklist_updates.py
  uv run scripts/pr_threads.py owner/repo#35 --all | uv run scripts/suggest_checklist_updates.py --threshold 5
  uv run scripts/suggest_checklist_updates.py --input threads.txt --checklist docs/review-checklist.md
  uv run scripts/suggest_checklist_updates.py --input threads.txt --checklist docs/checklist.md --apply

Output: Keyword clusters, categories, and suggested checklist items.
"""

import argparse
import re
import sys
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path

# Pre-compute category patterns for O(1) lookup
_CATEGORY_PATTERNS = {
    "Code Organization": frozenset({"barrel", "index.ts", "import", "folder", "co-located", "domain"}),
    "ESLint / Linting": frozenset({"eslint", "eslint-disable", "exhaustive-deps", "naming-convention"}),
    "React Hooks": frozenset({"useeffect", "usecallback", "dependency", "deps", "exhaustive", "hook"}),
    "TypeScript": frozenset({"typescript", "type", "union", "discriminated", "as any", "narrowing"}),
    "API Layer": frozenset({"api", "fetch", "handler", "status", "response", "request"}),
    "Platform APIs": frozenset({"url", "urlsearchparams", "query param", "location", "window"}),
    "Accessibility": frozenset({"alt", "aria", "screen reader", "a11y", "img"}),
    "Assets": frozenset({"svg", "image", "asset", "currentcolor", "fill"}),
}

EXCLUDE = [r"^lgtm", r"^looks good", r"^approved", r"^merged", r"^done", r"^ok$", r"^thanks", r"^nit"]


def exclude(text):
    t = text.lower().strip()
    return any(re.match(p, t, re.I) for p in EXCLUDE)


# Pre-compile regex patterns for performance
_RE_CODE_BLOCK = re.compile(r'```[\s\S]*?```')
_RE_INLINE_CODE = re.compile(r'`[^`]*`')
_RE_URL = re.compile(r'https?://\S+')
_RE_PUNCT = re.compile(r'[^\w\s]')

# Pre-compute stop words for O(1) lookup
_STOP_WORDS = frozenset({'this', 'that', 'with', 'from', 'have', 'should'})


def keywords(text):
    """Extract keywords, bigrams, and trigrams from text."""
    # Remove code blocks, inline code, URLs, and punctuation (re-use compiled patterns)
    t = _RE_CODE_BLOCK.sub(' ', text.lower())
    t = _RE_INLINE_CODE.sub(' ', t)
    t = _RE_URL.sub(' ', t)
    t = _RE_PUNCT.sub(' ', t)

    words = t.split()

    # Single words (>3 chars, not stop words)
    singles = [w for w in words if len(w) > 3 and w not in _STOP_WORDS]

    # Bigrams and trigrams using zip (avoid indexing overhead)
    if len(words) >= 2:
        bigrams = [f"{a} {b}" for a, b in zip(words, words[1:])]
    else:
        bigrams = []

    if len(words) >= 3:
        trigrams = [f"{a} {b} {c}" for a, b, c in zip(words, words[1:], words[2:])]
    else:
        trigrams = []

    return singles + bigrams + trigrams


def categorize(text):
    """Categorize text based on keyword patterns."""
    text_lower = text.lower()

    # Use any() with generator for short-circuit evaluation
    categories = []
    for cat, patterns in _CATEGORY_PATTERNS.items():
        if any(p in text_lower for p in patterns):
            categories.append(cat)

    return categories if categories else ["Uncategorized"]


def parse_input(data):
    """Parse pr_threads.py output format into structured comments."""
    comments = []
    lines = data.strip().split('\n')

    def is_header(line):
        return line.startswith(('Thread:', 'File:'))

    def is_author_line(line):
        return '[id=' in line or line.strip().startswith('[@')

    i = 0
    while i < len(lines):
        if not is_header(lines[i]) or i + 2 >= len(lines):
            i += 1
            continue

        # Found a thread/file header, look for comment bodies
        j = i + 2
        while j < len(lines) and not is_header(lines[j]):
            if is_author_line(lines[j]):
                # Collect indented body lines following author line
                body_lines = []
                k = j + 1
                while k < len(lines) and lines[k].startswith('    '):
                    body_lines.append(lines[k].strip())
                    k += 1

                if body_lines:
                    body = '\n'.join(body_lines)
                    if not exclude(body):
                        comments.append({
                            'body': body,
                            'keywords': keywords(body),
                            'categories': categorize(body)
                        })
                j = k - 1  # Skip processed body lines
            j += 1
        i += 1

    return comments


def analyze(comments, min_freq=2):
    """Analyze comments for keyword patterns and clusters."""
    kw_counts = Counter()
    cat_comments = defaultdict(list)

    # Single pass: count keywords and categorize
    for c in comments:
        kw_counts.update(c['keywords'])
        for cat in c['categories']:
            cat_comments[cat].append(c)

    # Build cluster counter: only for keywords meeting min_freq
    clusters = Counter()
    valid_kws = {kw for kw, count in kw_counts.items() if count >= min_freq}

    for c in comments:
        # Filter to valid keywords once per comment
        valid = [kw for kw in c['keywords'] if kw in valid_kws]
        # Generate all unique pairs using combinations (faster than nested loops)
        for k1, k2 in combinations(valid, 2):
            clusters[tuple(sorted((k1, k2)))] += 1

    return {
        'total': len(comments),
        'kw_counts': kw_counts,
        'clusters': clusters,
        'categories': dict(cat_comments),
    }


def suggest(analysis, threshold=3):
    suggestions = []
    for (k1, k2), count in analysis['clusters'].most_common(20):
        if count >= threshold:
            suggestions.append({'type': 'pattern', 'keywords': [k1, k2], 'freq': count, 'text': f"{k1} + {k2} ({count}x)"})
    for cat, comments in analysis['categories'].items():
        if len(comments) >= threshold:
            top = [k for k, _ in Counter([kw for c in comments for kw in c['keywords']]).most_common(3)]
            suggestions.append({'type': 'category', 'category': cat, 'freq': len(comments), 'keywords': top})
    return suggestions


def load_checklist(path):
    """Load existing checklist items and extract keywords for deduplication."""
    if not Path(path).exists():
        return set()

    content = Path(path).read_text().lower()
    items = re.findall(r'\[\s*\]\s*\*\*(.+?)\*\*', content)

    # Flatten all keywords from all checklist items
    all_keywords = set()
    for item in items:
        all_keywords.update(keywords(item))

    return all_keywords


def diff(suggestions, checklist_path):
    existing = load_checklist(checklist_path)
    return [s for s in suggestions if s['type'] != 'pattern' or not any(k in existing for k in s.get('keywords', []))]


def format_output(analysis, suggestions):
    lines = ["=" * 50, "PATTERN ANALYSIS", "=" * 50, f"Total comments: {analysis['total']}", "", "Top keywords:"]
    for kw, count in analysis['kw_counts'].most_common(15):
        lines.append(f"  {count:3d}x  {kw}")
    lines.extend(["", "Top clusters:"])
    for (k1, k2), count in analysis['clusters'].most_common(10):
        lines.append(f"  {count:3d}x  '{k1}' + '{k2}'")
    lines.extend(["", "Categories:"])
    for cat, comments in sorted(analysis['categories'].items(), key=lambda x: -len(x[1])):
        lines.append(f"  {len(comments):3d}  {cat}")
    lines.extend(["", "=" * 50, "SUGGESTED UPDATES", "=" * 50])
    if not suggestions:
        lines.append("No new suggestions (all patterns already in checklist)")
    for s in suggestions:
        if s['type'] == 'pattern':
            lines.append(f"\n[{s['freq']}x] {s['text']}")
        elif s['type'] == 'category':
            lines.append(f"\n[{s['freq']} comments] {s['category']}: {', '.join(s['keywords'])}")
    return '\n'.join(lines)


def apply(suggestions, checklist_path, dry_run=True):
    if not Path(checklist_path).exists():
        return f"Checklist not found: {checklist_path}"
    content = Path(checklist_path).read_text()
    lines = content.split('\n')
    additions = []
    section_map = {}

    for s in suggestions:
        if s['type'] == 'category':
            cat = s['category']
            # Find existing section or determine where to add
            for i, line in enumerate(lines):
                if line.startswith('## ') and cat.lower() in line.lower():
                    section_map[cat] = i
                    # Find end of section (next ## or end of file)
                    end = len(lines)
                    for j in range(i + 1, len(lines)):
                        if lines[j].startswith('## '):
                            end = j
                            break
                    section_map[f"{cat}_end"] = end - 1
                    break

            if cat in section_map:
                item = f"- [ ] **{s['keywords'][0].title() if s['keywords'] else 'New Item'}** — {', '.join(s['keywords'][:3])}"
                additions.append((cat, section_map[cat], section_map.get(f"{cat}_end", len(lines)), item))

    if dry_run:
        if not additions:
            return "DRY RUN - no matching sections found for suggestions"
        out = ["DRY RUN - would add to:"]
        for cat, _, _, item in additions:
            out.append(f"  [{cat}] {item}")
        return '\n'.join(out)

    # Apply changes (in reverse order to preserve line numbers)
    for cat, section_start, section_end, item in sorted(additions, key=lambda x: x[2], reverse=True):
        insert_pos = section_end + 1 if section_end > section_start else section_start + 1
        lines.insert(insert_pos, item)
        print(f"Added to [{cat}]: {item[:60]}...", file=sys.stderr)

    Path(checklist_path).write_text('\n'.join(lines))
    return f"Applied {len(additions)} additions to {checklist_path}"


def main():
    parser = argparse.ArgumentParser(description="Suggest checklist updates from PR patterns", epilog=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--input", "-i", help="Input file (default: stdin)")
    parser.add_argument("--threshold", "-t", type=int, default=3, help="Min frequency (default: 3)")
    parser.add_argument("--checklist", "-c", help="Existing checklist for deduplication")
    parser.add_argument("--apply", action="store_true", help="Modify checklist (default: dry-run)")
    parser.add_argument("--new-only", "-n", action="store_true", help="Show only new suggestions")
    parser.add_argument("--output", "-o", help="Save report to file")
    args = parser.parse_args()
    data = Path(args.input).read_text() if args.input else sys.stdin.read()
    if not data.strip():
        print("Error: No input. Pipe pr_threads.py output or use --input", file=sys.stderr)
        sys.exit(1)
    comments = parse_input(data)
    analysis = analyze(comments)
    suggestions = suggest(analysis, args.threshold)
    if args.checklist:
        suggestions = diff(suggestions, args.checklist)
    output = format_output(analysis, suggestions)
    if args.checklist:
        output += "\n\n" + apply(suggestions, args.checklist, dry_run=not args.apply)
    if args.output:
        Path(args.output).write_text(output)
        print(f"Saved to {args.output}")
    else:
        print(output)


if __name__ == "__main__":
    main()
