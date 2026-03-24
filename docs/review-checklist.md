# PR Review Checklist

Derived from recurring review feedback on the CKYC PRs (#35–#38). Apply this checklist when reviewing any PR in this codebase.

---

## Code Organization

- [ ] **No barrel `index.ts` files** — imports must reference the file directly (e.g. `SvgContainer/SvgContainer`, not `SvgContainer`)
      @detect: from\s+[\'"][\./]+\w+/index[\'"]|from\s+[\'"]\w+/index[\'"]
      @msg: Barrel import (index.ts) detected
      @fix: Import directly from file, not index.ts
- [ ] **Types are domain-scoped** — no single monolithic `types/index.ts`; use per-feature or per-folder type files
- [ ] **Constants are co-located** — no flat barrel `constants/index.ts`; constants live next to the feature that owns them

---

## ESLint / Linting

- [ ] **No file-level `eslint-disable`** — only `eslint-disable-next-line` with a specific rule name
      @detect: /\*\s*eslint-disable\s*\*/|//\s\*eslint-disable(?!-next-line)
      @msg: File-level ESLint disable detected
      @fix: Use eslint-disable-next-line with specific rule name

- [ ] **No `eslint-disable react-hooks/exhaustive-deps`** without a documented rationale in the PR description
      @detect: eslint-disable.\*exhaustive-deps
      @msg: react-hooks/exhaustive-deps disabled
      @fix: Document rationale in PR description if disabling

- [ ] **No `eslint-disable @typescript-eslint/naming-convention`** for numeric object keys — use computed property syntax `[400]:`, `[401]:` instead
- [ ] **No `eslint-disable @typescript-eslint/no-dynamic-delete`** — prefer object spread or filter over `delete`

---

## React Hooks

- [ ] **`useEffect` has exhaustive deps** — if intentionally empty `[]`, add a comment explaining why (e.g. "registered once per session mount")
      @detect: useEffect\s*\(\s*\(\s*\)\s*=>|useEffect\s*\([^,]+\)(?!\s*[,\)])
      @anti: useEffect\s*\([^)]+,\s*\[[^\]]+\]\s\*\)
      @msg: useEffect missing or incomplete deps
      @fix: Add exhaustive dependency array or document why empty

- [ ] **`useCallback` has exhaustive deps** — same rule
      @detect: useCallback\s*\(\s*\(\s*\)\s*=>|useCallback\s*\([^,]+\)(?!\s*[,\)])
      @anti: useCallback\s*\([^)]+,\s*\[[^\]]_\]\s_\)
      @msg: useCallback missing or incomplete deps

- [ ] **Floating promises are handled** — use `void fn()` when not awaiting, not a bare `fn()`
      @detect: (?<!void\s)(?<!await\s)(\w+\([^)]_\))\s_\.(then|catch|finally)
      @anti: void\s+\w+\([^)]_\)\s_\.(then|catch)|await\s+\w+\([^)]\*\)
      @msg: Floating promise detected
      @fix: Use 'void fn()' when not awaiting

---

## TypeScript

- [ ] **Discriminated unions encode constraints** — conditional fields (e.g. `redirectionPath` only for `'internal'` redirect) live in union variants, not as optional properties on a flat type
- [ ] **Dynamic object keys are typed** — `delete obj[key]` requires `key` typed as `keyof typeof obj`
- [ ] **No broad casts** — use type-safe narrowing or specific cast targets, not `as any`
      @detect: as\s+any\s*[;\)]|:\s*any\s\*[;=,\)]
      @anti: as\s+(string|number|boolean|\w+Type)
      @msg: Broad 'as any' cast detected
      @fix: Use type-safe narrowing or specific cast targets
- [ ] **`@types/*` versions match runtime dep versions** — e.g. `@types/react` must match `react` in `package.json`

---

## API Layer

- [ ] **Status handler signatures are complete** — handlers in `StatusHandlerMap` must accept `{ request, response }` matching the `StatusHandler` type, even if params are unused
- [ ] **No file-level ESLint disables in `fetch-wrapper.ts`** — all suppression is line-level only

---

## Platform APIs

- [ ] **Use the `URL` class for URL construction** — no manual string concatenation or ternaries for URLs with query params; use `new URL(path, origin)` + `searchParams.set()`
      @detect: \+._\?._=|\`[^\`]_\?\w+=|"[^"]_\?\w+=
      @anti: new\s+URL\s\*\(|URLSearchParams
      @msg: Manual URL string concatenation
      @fix: Use URL class and URLSearchParams
- [ ] **Use `URLSearchParams`** for reading/writing query params, not manual string splitting

---

## Accessibility

- [ ] **All `<img>` tags have meaningful `alt` text** — not a machine key (e.g. `errorType`), but a human-readable label (e.g. `content.title`)
      @detect: <img\s+[^>]_?(?!alt=)[^>]_?>
      @anti: <img\s+[^>]_alt=["\'][^"\']_["\']|role=["\']presentation["\']
      @msg: img tag may be missing alt text
      @fix: Add alt text or alt="" for decorative images
- [ ] **Decorative images use `alt=""`** explicitly

---

## Assets

- [ ] **SVG fill uses `currentColor` as fallback** — `$fill ?? 'currentColor'` in styled SVG containers so color inherits from context
- [ ] **New assets are optimized** — SVG size reduction attempted before committing

---

## Auto-Detection Tags

Items with `@detect` tags are automatically scanned by `scan_for_violations.py`. Add your own:

```markdown
- [ ] **Rule description** — explanation here
      @detect: regex_pattern|alternative_pattern
      @anti: exclusion_pattern (optional)
      @msg: Short violation message
      @fix: How to fix it
```

**Example — detect console.log:**

```markdown
- [ ] **No console.log in production** — use logger instead
      @detect: console\.(log|warn|error)\s\*\(
      @msg: console.log found
      @fix: Replace with logger.debug()
```

Use `|` to separate multiple patterns in one tag, or add multiple `@detect` lines (last one wins).
