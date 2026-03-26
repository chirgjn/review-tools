# PR Review Checklist

Most rules are React/TypeScript-specific — when installing this skill in a non-React repo, replace the React Hooks, ESLint, and TypeScript sections with patterns from that codebase's own review history.

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
- [ ] **No `eslint-disable @typescript-eslint/no-unnecessary-condition`** — fix the type inconsistency instead; if optional-chaining fires on a non-optional prop, either make the prop optional in the interface or remove the optional chain
      @detect: eslint-disable.*no-unnecessary-condition
      @msg: no-unnecessary-condition suppressed — fix the type instead
      @fix: Align the call site with the interface (remove ?. or make prop optional)

---

## React Hooks

- [ ] **`useEffect` has exhaustive deps** — if intentionally empty `[]`, add a comment explaining why (e.g. "registered once per session mount")
      @detect: useEffect\s*\(\s*\(\s*\)\s*=>|useEffect\s*\([^,]+\)(?!\s*[,\)])
      @anti: useEffect\s*\([^)]+,\s*\[[^\]]+\]\s*\)
      @msg: useEffect missing or incomplete deps
      @fix: Add exhaustive dependency array or document why empty

- [ ] **`useCallback` has exhaustive deps** — same rule
      @detect: useCallback\s*\(\s*\(\s*\)\s*=>|useCallback\s*\([^,]+\)(?!\s*[,\)])
      @anti: useCallback\s*\([^)]+,\s*\[[^\]]*\]\s*\)
      @msg: useCallback missing or incomplete deps

- [ ] **Polling interval closures capture stable refs** — if `startPolling`/`stopPolling` close over values derived from `searchParams` or other unstable sources, use `useRef` for the inner handler or document why the stale-closure risk is acceptable

- [ ] **Floating promises are handled** — use `void fn()` when not awaiting, not a bare `fn()`
      @detect: (?<!void\s)(?<!await\s)(\w+\([^)]*\))\s*\.then
      @anti: void\s+\w+\([^)]*\)\s*\.then|await\s+\w+\([^)]*\)
      @msg: Floating promise detected
      @fix: Use 'void fn()' when not awaiting

---

## TypeScript

- [ ] **Discriminated unions encode constraints** — conditional fields (e.g. `redirectionPath` only for `'internal'` redirect) live in union variants, not as optional properties on a flat type
- [ ] **Dynamic object keys are typed** — `delete obj[key]` requires `key` typed as `keyof typeof obj`
- [ ] **No broad casts** — use type-safe narrowing or specific cast targets, not `as any`
      @detect: as\s+any\s*[;\)]|:\s*any\s*[;=,\)]
      @anti: as\s+\w+Type
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
      @detect: \+.*\?.*=|`[^`]*\?\w+=|"[^"]*\?\w+=
      @anti: new\s+URL\s*\(|URLSearchParams
      @msg: Manual URL string concatenation
      @fix: Use URL class and URLSearchParams
- [ ] **Use `URLSearchParams`** for reading/writing query params, not manual string splitting

---

## Accessibility

- [ ] **All `<img>` tags have meaningful `alt` text** — not a machine key (e.g. `errorType`), but a human-readable label (e.g. `content.title`)
      @detect: <img\s+[^>]*?(?!alt=)[^>]*?>
      @anti: <img\s+[^>]*alt=["\'][^"\']+["\']|role=["\']presentation["\']
      @msg: img tag may be missing alt text
      @fix: Add alt text or alt="" for decorative images
- [ ] **Decorative images use `alt=""`** explicitly

---

## Assets

- [ ] **Icons are semantically appropriate** — the icon's visual meaning must match the context (e.g. don't use a business/finance icon for identity verification); if no suitable icon exists, track as design debt
- [ ] **SVG fill uses `currentColor` as fallback** — `$fill ?? 'currentColor'` in styled SVG containers so color inherits from context
- [ ] **New assets are optimized** — SVG size reduction attempted before committing

---

## Auto-Detection Tags

Items with `@detect` tags are automatically scanned by `scan_for_violations.py`. Add your own:

```markdown
- [ ] **Rule description** — explanation here
      @detect: pattern1|pattern2   ← use | for multiple patterns, NOT multiple @detect lines
      @anti: exclusion_pattern (optional)
      @msg: Short violation message
      @fix: How to fix it
```

> **Multiple `@detect` lines are silently broken** — only the last one is used, earlier ones are ignored without warning. Always combine patterns with `|` on a single line.

**Example — detect console.log:**

```markdown
- [ ] **No console.log in production** — use logger instead
      @detect: console\.(log|warn|error)\s*\(
      @msg: console.log found
      @fix: Replace with logger.debug()
```
