# PR Review Checklist

Derived from recurring review feedback on the CKYC PRs (#35–#38). Apply this checklist when reviewing any PR in this codebase.

---

## Code Organization

- [ ] **No barrel `index.ts` files** — imports must reference the file directly (e.g. `SvgContainer/SvgContainer`, not `SvgContainer`)
- [ ] **Types are domain-scoped** — no single monolithic `types/index.ts`; use per-feature or per-folder type files
- [ ] **Constants are co-located** — no flat barrel `constants/index.ts`; constants live next to the feature that owns them

---

## ESLint / Linting

- [ ] **No file-level `eslint-disable`** — only `eslint-disable-next-line` with a specific rule name
- [ ] **No `eslint-disable react-hooks/exhaustive-deps`** without a documented rationale in the PR description
- [ ] **No `eslint-disable @typescript-eslint/naming-convention`** for numeric object keys — use computed property syntax `[400]:`, `[401]:` instead
- [ ] **No `eslint-disable @typescript-eslint/no-dynamic-delete`** — prefer object spread or filter over `delete`

---

## React Hooks

- [ ] **`useEffect` has exhaustive deps** — if intentionally empty `[]`, add a comment explaining why (e.g. "registered once per session mount")
- [ ] **`useCallback` has exhaustive deps** — same rule
- [ ] **Floating promises are handled** — use `void fn()` when not awaiting, not a bare `fn()`

---

## TypeScript

- [ ] **Discriminated unions encode constraints** — conditional fields (e.g. `redirectionPath` only for `'internal'` redirect) live in union variants, not as optional properties on a flat type
- [ ] **Dynamic object keys are typed** — `delete obj[key]` requires `key` typed as `keyof typeof obj`
- [ ] **No broad casts** — use type-safe narrowing or specific cast targets, not `as any`
- [ ] **`@types/*` versions match runtime dep versions** — e.g. `@types/react` must match `react` in `package.json`

---

## API Layer

- [ ] **Status handler signatures are complete** — handlers in `StatusHandlerMap` must accept `{ request, response }` matching the `StatusHandler` type, even if params are unused
- [ ] **No file-level ESLint disables in `fetch-wrapper.ts`** — all suppression is line-level only

---

## Platform APIs

- [ ] **Use the `URL` class for URL construction** — no manual string concatenation or ternaries for URLs with query params; use `new URL(path, origin)` + `searchParams.set()`
- [ ] **Use `URLSearchParams`** for reading/writing query params, not manual string splitting

---

## Accessibility

- [ ] **All `<img>` tags have meaningful `alt` text** — not a machine key (e.g. `errorType`), but a human-readable label (e.g. `content.title`)
- [ ] **Decorative images use `alt=""`** explicitly

---

## Assets

- [ ] **SVG fill uses `currentColor` as fallback** — `$fill ?? 'currentColor'` in styled SVG containers so color inherits from context
- [ ] **New assets are optimized** — SVG size reduction attempted before committing
