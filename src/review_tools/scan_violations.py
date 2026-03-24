#!/usr/bin/env python3
"""scan-violations — Scan PR diff for checklist violations.

Usage: uv run scan-violations <owner/repo> <pr> [options]

Options:
  --checklist FILE     Custom checklist (default: built-in patterns)
  --file-pattern P     Scan only files matching regex (multiple OK)
  --output FILE        Save review payload to JSON
  --dry-run            Preview violations
  --post               Post directly (caution: skips file review)

Built-in: useEffect/useCallback deps, floating promises, eslint-disable, 'as any',
barrel imports, missing img alt, URL concat.

Custom rules via checklist tags:
  - [ ] **Rule** — description
    @detect: regex|alt_pattern  @anti: exclude_pattern  @msg: message  @fix: how to fix

Examples:
  uv run scan-violations owner/repo 42 --dry-run
  uv run scan-violations owner/repo 42 --checklist docs/checklist.md --output review.json
  uv run scan-violations owner/repo 42 --file-pattern "*.tsx" --output review.json

⚠️ Always review --output file before posting. Never use --post without review.
"""

import argparse
import json
import re
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

from platformdirs import user_cache_dir
from rich.console import Console
from rich.progress import track
from rich.table import Table

# Setup cache directory and console
CACHE_DIR = Path(user_cache_dir("review-tools"))
CACHE_DIR.mkdir(parents=True, exist_ok=True)
console = Console()


@dataclass
class Rule:
    """A detection rule for checklist violations."""
    category: str
    name: str
    patterns: list[str]
    anti_patterns: list[str]
    message: str
    fix: str
    _compiled_patterns: list[re.Pattern] = field(default_factory=list, repr=False)
    _compiled_anti: list[re.Pattern] = field(default_factory=list, repr=False)

    def __post_init__(self):
        """Compile regex patterns for performance."""
        if not self._compiled_patterns:
            self._compiled_patterns = [re.compile(p) for p in self.patterns]
        if not self._compiled_anti:
            self._compiled_anti = [re.compile(a) for a in self.anti_patterns]

    def matches(self, line: str) -> bool:
        """Check if line matches any pattern without matching anti-patterns."""
        # Check if any pattern matches
        if not any(p.search(line) for p in self._compiled_patterns):
            return False
        # Check anti-patterns (exclusions)
        return not any(a.search(line) for a in self._compiled_anti)

BUILTIN = {
    "React Hooks": {
        "useEffect deps": {
            "patterns": [r'useEffect\s*\(\s*\(\s*\)\s*=>', r'useEffect\s*\([^,]+\)(?!\s*[,\)])'],
            "anti": [r'useEffect\s*\([^)]+,\s*\[[^\]]+\]\s*\)'],
            "msg": "useEffect is missing its dependency array or has incomplete dependencies. This can cause stale closures and unexpected behavior when state/props change.",
            "fix": "Add all reactive values (props, state, functions) used inside useEffect to the dependency array []. If intentionally empty, add a comment explaining why (e.g., 'runs once on mount').",
        },
        "useCallback deps": {
            "patterns": [r'useCallback\s*\(\s*\(\s*\)\s*=>', r'useCallback\s*\([^,]+\)(?!\s*[,\)])'],
            "anti": [r'useCallback\s*\([^)]+,\s*\[[^\]]*\]\s*\)'],
            "msg": "useCallback is missing its dependency array or has incomplete dependencies. This causes the function to be recreated on every render, defeating the purpose of useCallback and potentially causing child components to re-render unnecessarily.",
            "fix": "Add all reactive values (props, state) that the callback uses to the dependency array []. If the callback has no dependencies, use an empty array [].",
        },
        "floating promise": {
            "patterns": [r'(?<!void\s)(?<!await\s)(\w+\([^)]*\))\s*\.(then|catch|finally)'],
            "anti": [r'void\s+\w+\([^)]*\)\s*\.(then|catch)', r'await\s+\w+\([^)]*\)'],
            "msg": "A Promise is being used without being awaited or handled. This creates a 'floating promise' that may fail silently without proper error handling, making debugging difficult and potentially leaving the application in an inconsistent state.",
            "fix": "If the async operation is intentional and you don't need to wait: prefix with 'void' (void fetchData()). If you need the result: use 'await' with proper try/catch error handling.",
        },
    },
    "ESLint": {
        "file-level disable": {
            "patterns": [r'/\*\s*eslint-disable\s*\*/', r'//\s*eslint-disable(?!-next-line)'],
            "anti": [],
            "msg": "File-level ESLint disable detected. This disables linting for the entire file, which can hide real issues and allow problematic patterns to slip through code review undetected.",
            "fix": "Use eslint-disable-next-line with a specific rule name (e.g., // eslint-disable-next-line @typescript-eslint/no-explicit-any) and include a comment explaining why the disable is necessary.",
        },
        "exhaustive-deps disable": {
            "patterns": [r'eslint-disable.*exhaustive-deps'],
            "anti": [],
            "msg": "The react-hooks/exhaustive-deps rule is being disabled. This rule catches missing dependencies in useEffect/useCallback that can cause subtle, hard-to-debug bugs like stale closures and infinite loops.",
            "fix": "Instead of disabling, fix the dependency array. If you truly need to disable (rare), add a detailed comment in the PR description explaining the rationale and potential risks.",
        },
    },
    "TypeScript": {
        "broad cast": {
            "patterns": [r'as\s+any\s*[;\)]', r':\s*any\s*[;=,\)]'],
            "anti": [r'as\s+(string|number|boolean|\w+Type)'],
            "msg": "Using 'as any' bypasses TypeScript's type checking. This defeats the purpose of using TypeScript and can mask real type errors that would be caught at compile time, leading to runtime crashes.",
            "fix": "Use type-safe alternatives: type predicates (isString(x)), proper type narrowing (if typeof x === 'string'), or specific type assertions (as SpecificType). If the type is truly unknown, use 'unknown' instead of 'any' and narrow it.",
        },
    },
    "Code Organization": {
        "barrel import": {
            "patterns": [r'from\s+[\'"][\./]+\w+/index[\'"]', r'from\s+[\'"]\w+/index[\'"]'],
            "anti": [],
            "msg": "Barrel import (from index.ts) detected. While convenient, barrel imports can cause circular dependency issues, make tree-shaking less effective, and obscure the actual source of imported code.",
            "fix": "Import directly from the specific file that exports the function/type (e.g., import { Button } from './components/Button/Button' instead of './components').",
        },
    },
    "Accessibility": {
        "missing alt": {
            "patterns": [r'<img\s+[^>]*?(?!alt=)[^>]*?>'],
            "anti": [r'<img\s+[^>]*alt=["\'][^"\']*["\']', r'role=["\']presentation["\']'],
            "msg": "Image tag may be missing alt text. Missing alt text makes images inaccessible to screen readers, preventing visually impaired users from understanding the content or purpose of the image.",
            "fix": "Add descriptive alt text that conveys the image's purpose (e.g., alt='User profile picture' not alt='image'). For decorative images, use alt='' explicitly to indicate it's intentionally empty.",
        },
    },
    "Platform APIs": {
        "manual URL concat": {
            "patterns": [r'\+.*\?.*=', r'\`[^\`]*\?\w+=', r'"[^"]*\?\w+='],
            "anti": [r'new\s+URL\s*\(', r'URLSearchParams'],
            "msg": "Manual URL string concatenation detected (using + or template literals). This is error-prone: special characters may not be properly encoded, leading to malformed URLs or security issues like open redirects.",
            "fix": "Use the URL class: new URL(path, base). Then use url.searchParams.set('key', value) to safely add query parameters with proper encoding.",
        },
    },
}


def gh(args, cache_ttl: int = 0):
    """Run gh CLI command and return stdout with optional disk caching.
    
    Args:
        args: gh CLI arguments
        cache_ttl: Cache time-to-live in seconds (0 = no cache)
    """
    cache_key = f"gh_{hash(tuple(args))}.json"
    cache_file = CACHE_DIR / cache_key
    
    # Check disk cache if TTL specified
    if cache_ttl > 0 and cache_file.exists():
        age = time.time() - cache_file.stat().st_mtime
        if age < cache_ttl:
            return json.loads(cache_file.read_text())
    
    # Run gh CLI
    try:
        result = subprocess.run(["gh"] + args, capture_output=True, text=True, check=True)
        output = result.stdout
        
        # Write to disk cache if TTL specified
        if cache_ttl > 0:
            cache_file.write_text(json.dumps(output))
        
        return output
    except subprocess.CalledProcessError as e:
        console.print(f"[red]Error running 'gh {' '.join(args)}': {e.stderr}[/red]")
        raise


def fetch_files(repo, pr, patterns=None):
    """Fetch changed files from PR, optionally filtered by patterns."""
    out = gh(["api", f"repos/{repo}/pulls/{pr}/files", "--paginate", "--jq", ".[]"])

    files = []
    for line in out.strip().split('\n'):
        if not line:
            continue
        try:
            f = json.loads(line)
        except json.JSONDecodeError:
            continue

        filename = f.get('filename', '')

        # Apply file pattern filter if specified
        if patterns and not any(re.search(p, filename) for p in patterns):
            continue

        # Only process TypeScript/JavaScript files
        if filename.endswith(('.ts', '.tsx', '.js', '.jsx')):
            files.append(f)

    return files


def _find_builtin_rule(category: str, title: str) -> Rule | None:
    """Find a matching BUILTIN rule by category and title."""
    if category not in BUILTIN:
        return None

    for name, data in BUILTIN[category].items():
        if name.lower() in title.lower():
            return Rule(
                category=category,
                name=title,
                patterns=list(data.get("patterns", [])),
                anti_patterns=list(data.get("anti", [])),
                message=data.get("msg", title),
                fix=data.get("fix", "")
            )
    return None


def _parse_tags(line: str, rule: Rule) -> Rule:
    """Parse @detect/@anti/@msg/@fix tags and update the rule."""
    tag_match = re.match(r'\s*@(\w+):\s*(.+)', line)
    if not tag_match:
        return rule

    tag, value = tag_match.group(1), tag_match.group(2).strip()
    patterns = [p.strip() for p in value.split('|') if p.strip()]

    if tag == 'detect':
        return Rule(rule.category, rule.name, patterns, rule.anti_patterns, rule.message, rule.fix)
    elif tag == 'anti':
        return Rule(rule.category, rule.name, rule.patterns, patterns, rule.message, rule.fix)
    elif tag == 'msg':
        return Rule(rule.category, rule.name, rule.patterns, rule.anti_patterns, value, rule.fix)
    elif tag == 'fix':
        return Rule(rule.category, rule.name, rule.patterns, rule.anti_patterns, rule.message, value)

    return rule


def parse_checklist(path: str) -> list[Rule]:
    """Parse checklist with inline @detect/@anti/@msg/@fix tags for custom rules.
    
    Format:
      - [ ] **Item** — description
        @detect: regex_pattern|or_pattern
        @anti: exclusion_pattern
        @msg: Custom violation message
        @fix: How to fix this
    """
    # Return built-in rules if no custom checklist
    if not Path(path).exists():
        return [
            Rule(cat, name, d.get("patterns", []), d.get("anti", []), d.get("msg", name), d.get("fix", ""))
            for cat, items in BUILTIN.items()
            for name, d in items.items()
        ]

    content = Path(path).read_text()
    rules: list[Rule] = []
    current_category = ""
    current_rule: Rule | None = None
    in_code_block = False

    for line in content.split('\n'):
        # Toggle code block state
        if line.strip().startswith('```'):
            in_code_block = not in_code_block
            continue
        if in_code_block:
            continue

        # Track category headers
        if line.startswith('## '):
            if current_rule:
                rules.append(current_rule)
                current_rule = None
            current_category = line[3:].strip()
            continue

        # Parse checklist items: - [ ] **Title** — description
        checklist_match = re.match(r'\s*-\s*\[\s*\]\s*\*\*([^*]+)\*\*\s*[—:-]\s*(.+)', line)
        if checklist_match:
            if current_rule:
                rules.append(current_rule)

            title, desc = checklist_match.group(1).strip(), checklist_match.group(2).strip()
            # Try to find matching BUILTIN rule for defaults
            builtin = _find_builtin_rule(current_category, title)

            if builtin:
                current_rule = builtin
            else:
                current_rule = Rule(current_category, title, [], [], title, desc)
            continue

        # Parse @tags that follow a checklist item
        if current_rule and line.strip().startswith('@'):
            current_rule = _parse_tags(line, current_rule)
            continue

        # Non-tag line ends current rule
        if current_rule and line.strip() and not line.strip().startswith(('@', '-')):
            rules.append(current_rule)
            current_rule = None

    # Don't forget the last rule
    if current_rule:
        rules.append(current_rule)

    return rules


# Pre-compile regex for diff hunk parsing
_RE_DIFF_HUNK = re.compile(r'@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@')


def get_position(diff, path, target_line):
    """Convert file line number to GitHub diff position."""
    lines = diff.split('\n')
    in_file, in_hunk, new_line, pos = False, False, 0, 0

    for i, line in enumerate(lines, 1):
        # Use startswith checks (faster than regex)
        if line.startswith('diff --git'):
            in_file, in_hunk = False, False
        elif line.startswith('+++ b/'):
            in_file = path in line[6:]
        elif not in_file:
            continue
        elif line.startswith('@@'):
            in_hunk = True
            m = _RE_DIFF_HUNK.match(line)
            if m:
                new_line, pos = int(m.group(1)), i
        elif not in_hunk:
            continue
        elif line[0:1] in ('+', ' '):
            if new_line == target_line:
                return pos + 1
            new_line += 1
            pos = i

    return None


def scan(content, path, rules):
    """Scan content for violations against detection rules."""
    violations = []
    lines = content.split('\n')

    for i, line in enumerate(lines, 1):
        for rule in rules:
            if not rule.patterns:
                continue

            # Use compiled patterns for faster matching
            if rule.matches(line):
                violations.append({
                    'path': path,
                    'line': i,
                    'cat': rule.category,
                    'rule': rule.name,
                    'msg': rule.message,
                    'fix': rule.fix
                })

    return violations


def main():
    parser = argparse.ArgumentParser(description="Scan PR for checklist violations", epilog=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("repo", help="owner/repo")
    parser.add_argument("pr", type=int, help="PR number")
    parser.add_argument("--checklist", "-c", help="Checklist file (default: built-in)")
    parser.add_argument("--file-pattern", "-p", action="append", help="File regex pattern (multiple OK)")
    parser.add_argument("--output", "-o", help="Save payload to JSON file")
    parser.add_argument("--dry-run", "-n", action="store_true", help="Preview only")
    parser.add_argument("--post", action="store_true", help="Post directly")
    parser.add_argument("--review-body", default="Automated checklist review", help="Review summary")
    parser.add_argument("--cache-ttl", type=int, default=300, help="Cache GitHub API calls for N seconds (default: 300)")
    args = parser.parse_args()
    
    # Load rules
    rules = parse_checklist(args.checklist) if args.checklist else [
        Rule(cat, n, d.get("patterns", []), d.get("anti", []), d.get("msg", n), d.get("fix", ""))
        for cat, items in BUILTIN.items() for n, d in items.items()
    ]
    console.print(f"[dim]Loaded {len(rules)} rules[/dim]")
    
    # Fetch files with progress bar
    with console.status("[bold green]Fetching changed files..."):
        files = fetch_files(args.repo, args.pr, args.file_pattern)
    console.print(f"[dim]Scanning {len(files)} files[/dim]")
    
    # Get head commit
    with console.status("[bold green]Getting PR info..."):
        head = gh(["api", f"repos/{args.repo}/pulls/{args.pr}", "--jq", ".head.sha"], cache_ttl=args.cache_ttl).strip()
    
    # Scan files with progress
    all_v = []
    for f in track(files, description="Scanning files...", console=console):
        path, patch = f.get('filename', ''), f.get('patch', '')
        if not patch:
            continue
        content = '\n'.join(line[1:] if line[0] in '+ ' else '' for line in patch.split('\n') if line and line[0] in '+ - ')
        for v in scan(content, path, rules):
            v['pos'] = get_position(patch, path, v['line'])
            if v['pos']:
                all_v.append(v)
    
    console.print(f"[bold {'red' if all_v else 'green'}]Found {len(all_v)} violations[/bold {'red' if all_v else 'green'}]")
    
    if args.dry_run:
        # Rich table output
        if all_v:
            table = Table(title="Checklist Violations", show_header=True, header_style="bold magenta")
            table.add_column("File", style="cyan", no_wrap=True)
            table.add_column("Line", style="yellow", justify="right")
            table.add_column("Category", style="blue")
            table.add_column("Rule", style="red")
            table.add_column("Fix", style="green")
            
            for v in all_v:
                table.add_row(v['path'], str(v['line']), v['cat'], v['rule'], v['fix'])
            
            console.print(table)
        else:
            console.print("[green]✓ No violations found[/green]")
        return
    
    comments = [{'path': v['path'], 'position': v['pos'], 'body': f"**{v['rule']}**\n\n{v['msg']}\n\n💡 {v['fix']}"} for v in all_v]
    payload = {'commit_id': head, 'body': args.review_body, 'event': 'REQUEST_CHANGES' if all_v else 'COMMENT', 'comments': comments}
    
    if args.output:
        Path(args.output).write_text(json.dumps(payload, indent=2))
        console.print(f"[dim]Saved to {args.output}[/dim]")
    
    if args.post and comments:
        with console.status("[bold green]Posting review..."):
            r = subprocess.run(["gh", "api", f"repos/{args.repo}/pulls/{args.pr}/reviews", "-X", "POST", "--input", "-"], input=json.dumps(payload), capture_output=True, text=True)
        if r.returncode == 0:
            url = json.loads(r.stdout).get('html_url', 'OK')
            console.print(f"[green]✓ Posted: {url}[/green]")
        else:
            console.print(f"[red]Error: {r.stderr}[/red]")
            sys.exit(1)
    elif not args.output:
        console.print_json(json.dumps(payload))


if __name__ == "__main__":
    main()
