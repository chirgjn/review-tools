# Agent Guide: Working with review-tools

This guide is for AI coding assistants working with the review-tools codebase.

## The Core Intentions (Read This First)

### Intention 1: Comments Must Be Reviewable Before Posting
**The Rule:** Always construct comments in a file first. Review the file. Then post.  
**Why:** GitHub review comments are **permanent** once posted. You cannot "undo" a review without leaving a "dismissed" timeline entry. The file-based workflow lets you see exactly what you'll post before it goes live.

### Intention 2: One Review Per PR, Not One Review Per Comment
**The Rule:** Batch all comments into a single `--input FILE` review.  
**Why:** GitHub creates a **permanent timeline entry** for every review. Posting 5 separate reviews creates 5 timeline entries. This clutter is permanent and makes PR history unreadable. The toolkit enforces this via validation (max 1 comment via inline flags).

### Intention 3: Never Pass Substantive Comments on Command Line
**The Rule:** Use `--body-file`, not `--body`, for anything longer than "LGTM"  
**Why:** 
- Shell escaping is fragile: `--body "It's broken"` fails with quotes
- Long text on command line is unreadable and unreviewable
- Files can be previewed, edited, and shared
- The toolkit warns when you use `--body` with substantive text

### Intention 4: Zero Dependencies (Except Absolutely Necessary)
**The Rule:** The toolkit works with just Python 3.11+ and `gh` CLI  
**Why:** 
- `uv run <command>` works immediately without pip installs
- No virtualenv activation needed
- No dependency conflicts
- Portable: works on any machine with `gh` installed

---

## File-Based Everything (Critical)

### Why Zero-Dependencies Matter
```bash
# This just works anywhere - no pip install needed beyond uv
uv run pr-threads owner/repo#35 --all
```

## File-Based Everything

### NEVER Use HEREDOCs or Stdin for Data

**✗ DON'T:**
```bash
# Don't do this - passing JSON via stdin
[{"path": "...", "body": "..."}]
EOF
```

**✓ DO:**
```bash
# Save to file, then reference
uv run scan-violations owner/repo 42 --output review.json
uv run post-review owner/repo 42 --input review.json --review-body "..."
```

### Always Prefer Files Over Inline Arguments

| Instead of | Use |
|-----------|-----|
| `--body "long text"` | `--body-file comment.md` |
| Inline JSON strings | `--input` with file |

## The Golden Rule: File First, Then Post

### ALWAYS Construct Comments in a File First

**The Workflow:**
1. Build up comments incrementally (via `build-review` or `scan-violations --output`)
2. Review the generated file
3. Post ONE batched review via `--input`

**✗ NEVER:**
```bash
# Don't post immediately - always save to file first
uv run scan-violations owner/repo 42 --post  # ← WRONG: Immediate post

# Don't use inline flags for multiple comments
uv run post-review ... --path a.ts --body "A" --path b.ts --body "B"  # ← WRONG
```

**✓ ALWAYS:**
```bash
# STEP 1: Build/scan and SAVE TO FILE
uv run scan-violations owner/repo 42 \
  --checklist docs/review-checklist.md \
  --output review.json

# STEP 2: Review the file (optional but recommended)
cat review.json | jq '.comments[] | {path: .path, body: .body}'

# STEP 3: Post batched review
uv run post-review owner/repo 42 \
  --input review.json \
  --review-body "Checklist review - see inline comments" \
  --event REQUEST_CHANGES
```

### Why This Matters
- **GitHub creates PERMANENT timeline entries** for each review
- File-based workflow lets you review before posting
- You can edit the JSON file to add/remove/tweak comments
- No accidental spam from iterative development

### For Manual/Complex Reviews

Use `build-review` to incrementally construct:

```bash
# Add comments as you find them
uv run build-review \
  --path src/hooks.ts --position 42 \
  --body-file detailed_suggestion.md

uv run build-review \
  --path src/utils.ts --position 15 \
  --body "Extract this into a helper function to improve readability"

# Preview before posting
uv run build-review --show

# Post when ready
uv run build-review --post owner/repo 42 \
  --review-body "Refactoring suggestions" \
  --event REQUEST_CHANGES
```

### post-review Validates This
- Single comment via inline = **OK** (quick one-offs only)
- Multiple comments via inline = **ERROR** (use `--input`)
- Any count via `--input` = **OK** (recommended)

## Comment Quality Standards

### Word Count, Not Character Count
- **Minimum 10 words** per inline comment
- **Allowed short responses**: LGTM, Approved, +1, 👍, nice, etc.
- **Must explain WHY**, not just WHAT

### Validation in Code
```python
# This will be rejected (< 10 words, not in allowed list)
"fix this"  # ❌ 2 words

# This will pass
"LGTM"  # ✓ In allowed list

# This will pass
"Add useCallback here to prevent unnecessary re-renders when props change"  # ✓ 11 words
```

### Write Helpful Messages

**✗ Bad:**
```
"Fix this"
"Add dependency"
"Type error"
```

**✓ Good:**
```
"The useEffect dependency array is missing 'onChange'. This causes the effect to run with stale closure values when onChange updates. Add onChange to deps or extract the logic."

"This Promise is floating - if it rejects, it will be an unhandled rejection. Use void fetchData() if intentionally not awaiting, or add try/catch."
```

## Code Patterns to Follow

### Performance Optimizations
- Pre-compile regex patterns at module level
- Use `functools.lru_cache` for API calls
- Use `frozenset` for O(1) lookups
- Use `itertools.combinations` instead of nested loops

### Type Safety
- Use Python 3.11+ features
- Basic type hints are nice-to-have but not enforced strictly
- Basedpyright runs with relaxed settings

### Error Handling
- Use `rich.console` for colored output
- Show helpful context, not just errors
- Use `--force-short` flags to bypass validation (user override)

## Tool Reference for Agents

### Analysis Pipeline (File-based)
```bash
# Extract patterns from past PRs - pipe to suggest-checklist
uv run pr-threads owner/repo#35 owner/repo#36 --all | \
  uv run suggest-checklist --checklist docs/review-checklist.md
```

### Review Workflow (File → Post)

**Auto-scan (Recommended for quick reviews):**
```bash
# STEP 1: Scan and save to file
uv run scan-violations owner/repo 42 \
  --checklist docs/review-checklist.md \
  --output review.json

# STEP 2: Review the output (optional)
cat review.json | jq '.comments | length'  # See how many found

# STEP 3: Post batched review
uv run post-review owner/repo 42 \
  --input review.json \
  --review-body "Checklist review - see inline comments" \
  --event REQUEST_CHANGES
```

**Manual build (Recommended for nuanced reviews):**
```bash
# STEP 1: Build up comments incrementally (saved to review_payload.json)
uv run build-review --path src/hooks.ts --position 42 --body-file detailed_feedback.md
uv run build-review --path src/utils.ts --position 15 --body "Consider extracting this logic"

# STEP 2: Preview
uv run build-review --show

# STEP 3: Post (reads from review_payload.json automatically)
uv run build-review --post owner/repo 42 \
  --review-body "Refactoring suggestions" \
  --event REQUEST_CHANGES
```

### Quick Single Comment (Use sparingly)
```bash
# Only for true one-offs - single comment inline
uv run post-review owner/repo 42 \
  --path src/critical.ts --position 10 \
  --body "Critical fix needed: This security vulnerability must be addressed before merge" \
  --review-body "Security issue" \
  --event REQUEST_CHANGES
```

### Response Workflow
```bash
# Reply to reviews on your PR
uv run reply-review owner/repo 45 --list
uv run reply-review owner/repo 45 --reply-all --prefix "✅ Fixed"
```

## Adding New Features

### Before Adding a Dependency
1. Ask: "Can this be done with stdlib?"
2. Ask: "Is this dependency already used elsewhere in the project?"
3. Consider the install size impact

### Before Adding New Commands
1. Follow existing naming: `verb-noun` (e.g., `scan-violations`)
2. Add entry point in `pyproject.toml`
3. Update docs with examples
4. Follow the file-based pattern

### Testing Changes
```bash
# Run linting
uv run ruff check src/

# Run type checking
uv run basedpyright src/

# Test commands
uv run pr-threads --help
uv run scan-violations --help
```

## Common Pitfalls to Avoid

1. **Don't use `input()` or interactive prompts** - tools should be scriptable
2. **Don't assume TTY** - support piping and redirection
3. **Don't use global state** - each command should be self-contained
4. **Don't over-engineer** - simple is better than complex for CLI tools
5. **Don't break the batching rule** - GitHub timeline noise is permanent

## Documentation Updates

When adding features:
1. Update the relevant workflow doc in `docs/`
2. Add examples using `uv run <command>`
3. Show both ✓ DO and ✗ DON'T patterns
4. Update README.md quick examples

## Questions?

The codebase prioritizes:
1. **Simplicity** - easy to understand and modify
2. **Performance** - caching, compiled regex, efficient algorithms
3. **UX** - rich output, clear errors, helpful hints
4. **Clean GitHub history** - batching, no timeline spam
