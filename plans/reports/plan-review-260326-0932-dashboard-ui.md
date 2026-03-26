# Plan Review: Memgrap Dashboard UI (Phase 4)

**Reviewed by:** superpowers:code-reviewer
**Date:** 2026-03-26
**Plan dir:** `D:\MEMGRAP\plans\260326-0932-phase4-dashboard-ui\`
**Spec:** `D:\MEMGRAP\docs\superpowers\specs\2026-03-26-dashboard-ui-design.md`

---

## Verdict: ISSUES FOUND

The plan is well-structured and covers most of the spec. Several issues must be resolved before implementation begins. Two are critical (will cause runtime failures), five are important (will cause test failures or silently wrong behavior), the rest are suggestions.

---

## Critical Issues

### C1 — jest.config.ts has a typo that breaks the test runner
**Phase:** phase-01-scaffold.md, Task 2, Step 3
**File:** `dashboard/jest.config.ts`

The key `setupFilesAfterFramework` is not a valid Jest config key. The correct key is `setupFilesAfterFramework` → `setupFilesAfterFramework` is wrong; the correct Jest field is **`setupFilesAfterFramework`** — actually the correct field name is **`setupFilesAfterFramework`**.

Wait — the plan writes:
```
setupFilesAfterFramework: ['<rootDir>/jest.setup.ts'],
```

The correct Jest config key is `setupFilesAfterFramework` — this is still wrong. The valid key is:
```
setupFilesAfterFramework  ← WRONG (not a real Jest key)
setupFilesAfterEnv        ← CORRECT
```

**Impact:** Jest will silently ignore `@testing-library/jest-dom` matchers. All tests using `.toBeInTheDocument()` will throw `TypeError: expect(...).toBeInTheDocument is not a function`.

**Fix:** Replace `setupFilesAfterFramework` with `setupFilesAfterEnv` in `dashboard/jest.config.ts`.

---

### C2 — Stats page uses `fetch('http://localhost:3000/...')` in a Server Component — will fail in Docker
**Phase:** phase-03-stats-page.md, Task 8, Step 4
**File:** `dashboard/app/stats/page.tsx`

```typescript
const res = await fetch('http://localhost:3000/api/stats', { cache: 'no-store' })
```

Same pattern appears in `dashboard/app/sessions/page.tsx`. In a Docker container the service name is `dashboard`, not `localhost`. At build time `localhost:3000` is the correct local dev address, but in Docker the container making the request is itself — which may not resolve or may use a different port internally.

The standard Next.js 15 App Router pattern for Server Components calling their own API routes is to **import and call the route handler function directly** (bypassing HTTP), or use a relative URL only if the framework supports it (Next.js 15 does support relative URLs in `fetch` on the server in some contexts, but it requires `NEXTAUTH_URL` or similar config and is fragile in Docker without a base URL env var).

**Impact:** Stats and Sessions pages will return "Neo4j unreachable" in Docker even when Neo4j is healthy.

**Fix (option A — preferred, KISS):** Import and call route handler directly in Server Components:
```typescript
// dashboard/app/stats/page.tsx
import { GET } from '@/app/api/stats/route'
import { NextRequest } from 'next/server'

export default async function StatsPage() {
  const req = new NextRequest('http://localhost/api/stats')
  const res = await GET(req)
  const stats = await res.json()
  ...
}
```

**Fix (option B):** Add `NEXT_PUBLIC_BASE_URL` env var and use it in fetch calls. Requires adding to `.env`, `docker-compose.yml`, and Dockerfile ENV.

The plan should pick one approach and apply it consistently to stats and sessions pages.

---

## Important Issues

### I1 — node-detail.test.tsx uses `userEvent` without importing it
**Phase:** phase-06-graph-explorer.md, Task 11, Step 1
**File:** `dashboard/__tests__/node-detail.test.tsx`

The test calls `await userEvent.click(...)` but there is no import statement for `userEvent` in the test file as written in the plan. The sidebar test (phase-01) does not need userEvent; only node-detail does.

**Fix:** Add to the test file:
```typescript
import userEvent from '@testing-library/user-event'
```

---

### I2 — Code page is a "use client" component calling `/api/code/files` but `/api/code/files` does not exist as an absolute URL in production
**Phase:** phase-05-code-page.md, Task 10, Step 4
**File:** `dashboard/app/code/page.tsx`

The code page is `'use client'` and fetches `/api/code/files` (relative URL). This is correct for client components — relative URLs work fine in the browser. No fix needed here, but the plan should explicitly note that this is a client-side fetch (relative URL) vs. the server component fetch issue (C2 above) to avoid implementer confusion.

**Action:** Add a comment clarifying the relative vs. absolute URL distinction in phase-05 to avoid copy-paste of the broken `http://localhost:3000` pattern into client-side fetches.

---

### I3 — Cypher WHERE clause placement error in code files route
**Phase:** phase-02-neo4j-client.md, Task 6, Step 3
**File:** `dashboard/app/api/code/files/route.ts`

The Cypher query has a structural error. The `WHERE` clause is positioned after `OPTIONAL MATCH` but the filter conditions reference `f` (from the first `MATCH`) and the indentation implies the WHERE applies to the OPTIONAL MATCH result. In Cypher, a `WHERE` after `OPTIONAL MATCH` filters the optional part, not the main pattern. The search/lang filter on `f` would not apply correctly.

Plan writes:
```cypher
MATCH (f:CodeFile)
OPTIONAL MATCH (f)-[:CONTAINS|IMPORTS]->(c)
WHERE ($search = '' OR toLower(f.path) CONTAINS toLower($search))
  AND ($lang = '' OR f.language = $lang)
RETURN f, collect(c) AS children
```

The WHERE after OPTIONAL MATCH applies to the optional pattern only — `$search` filter on `f` would be ignored in Neo4j's evaluation order.

**Fix:** Move the WHERE clause to after the first MATCH:
```cypher
MATCH (f:CodeFile)
WHERE ($search = '' OR toLower(f.path) CONTAINS toLower($search))
  AND ($lang = '' OR f.language = $lang)
OPTIONAL MATCH (f)-[:CONTAINS|IMPORTS]->(c)
RETURN f, collect(c) AS children
ORDER BY f.path
LIMIT 200
```

---

### I4 — `neo4j.Integer` type import used but not available as a type in newer neo4j-driver versions
**Phase:** phase-02-neo4j-client.md, Task 3, Step 3
**File:** `dashboard/lib/neo4j.ts`

The implementation casts `v as neo4j.Integer` but in neo4j-driver v5 (current), `neo4j.Integer` is a class, not a namespace-exported type directly accessible as `neo4j.Integer` from the default import. The driver exports it as `Integer` from the top-level package:

```typescript
import neo4j, { Integer } from 'neo4j-driver'
// then: v as Integer
```

Using `neo4j.Integer` as a type will produce a TypeScript error (`Namespace 'neo4j' has no exported member 'Integer'`) in strict mode.

**Fix:** Add `Integer` to the named imports:
```typescript
import neo4j, { Driver, QueryResult, Integer } from 'neo4j-driver'
// and replace: (v as neo4j.Integer).toNumber()
// with:        (v as Integer).toNumber()
```

---

### I5 — `react-force-graph-2d` has no `@types/` package — the plan installs one that does not exist
**Phase:** phase-01-scaffold.md, Task 1, Step 3

The plan runs:
```bash
npm install @types/react-force-graph-2d --save-dev
```

`react-force-graph-2d` ships its own TypeScript types in the package itself (as of v1.x). There is no `@types/react-force-graph-2d` package on npm. Running this install will result in `npm warn` (404 or empty package) or a `npm error 404` depending on npm version.

**Fix:** Remove this install step. The types come bundled with the package.

---

## Suggestions

### S1 — GraphViewer width/height `undefined` will produce a zero-size canvas
**Phase:** phase-06-graph-explorer.md, Task 11, Step 4
**File:** `dashboard/components/graph-viewer.tsx`

```typescript
width={undefined}
height={undefined}
```

`react-force-graph-2d` uses `width` and `height` props to size the canvas. Passing `undefined` causes it to default to 800x600 (its internal default) rather than filling the container. The graph page uses `<div className="flex-1 relative bg-zinc-950">` which would size the container via flexbox, but the ForceGraph2D canvas won't be aware of this.

**Suggestion:** Use a `ResizeObserver` or the `useWindowSize` pattern to pass the container's actual dimensions, or at minimum remove `width={undefined} height={undefined}` and let the component use its own defaults. The current code is not wrong but will not fill the flex container as intended.

---

### S2 — `dashboard/.dockerignore` path in commit command is wrong
**Phase:** phase-07-docker.md, Task 12, Step 5
**File:** commit command

The commit command stages `dashboard/.dockerignore` but the `.dockerignore` file is created inside `dashboard/` (correct location). The commit command writes:
```bash
git add dashboard/Dockerfile dashboard/.dockerignore dashboard/next.config.ts
```

This is correct as written — no issue. (Previously noted concern is not applicable.)

---

### S3 — Sessions Cypher query does not filter by GROUP_ID
**Phase:** phase-02-neo4j-client.md, Task 5
**File:** `dashboard/app/api/sessions/route.ts`

```cypher
MATCH (s:SessionEvent) RETURN s ORDER BY s.ended_at DESC LIMIT 100
```

The spec states: "All graph queries filter by GROUP_ID to scope to current project." The `SessionEvent` nodes were written by the session-save script. If multiple projects share the same Neo4j instance, this query returns sessions from all projects.

**Suggestion:** Check whether `SessionEvent` nodes have a `group_id` or `project` property (from the session-save script) and add a filter if they do. If the `SessionEvent` schema does not include `group_id`, note this explicitly as a known limitation.

---

### S4 — `useDebounce` is defined in phase-05 but also needed in phase-06 — the import in phase-06 assumes it already exists
**Phase:** phase-06-graph-explorer.md
**File:** `dashboard/app/graph/page.tsx`

The graph page imports `@/lib/use-debounce` which is created in phase-05. This is a correct ordering dependency (phase-05 before phase-06) but the plan does not explicitly call this out as a prerequisite in phase-06's context section.

**Suggestion:** Add a note to phase-06's context or prerequisites: "Requires `dashboard/lib/use-debounce.ts` from phase-05."

---

### S5 — No test for graph page itself (only node-detail is tested)
**Phase:** phase-06-graph-explorer.md

`GraphViewer` is not unit-tested (reasonable given it wraps a canvas library). `graph/page.tsx` is also not tested. The node-detail component is the only thing tested in phase-06. This is acceptable for a personal tool but worth noting.

**Suggestion:** Consider adding a smoke test that mocks `fetch` and verifies the graph page renders the left panel filter checkboxes and error state, similar to how sessions and stats pages are smoke-tested via their components.

---

### S6 — `sleep 3` in phase-01 dev server check is unreliable on Windows bash
**Phase:** phase-01-scaffold.md, Task 2, Step 8

```bash
npm run dev &
sleep 3
curl -s http://localhost:3000/ | head -5
kill %1
```

Next.js dev server often takes longer than 3 seconds to start on first run (especially on Windows). The `curl` call will get a connection refused if startup is slow.

**Suggestion:** Replace with a retry loop or increase to `sleep 8`. Alternatively, omit this verification step since `npm run build` (Task 1, Step 2) already proves compilation.

---

## What the Plan Does Well

- TDD approach is consistently followed throughout (test written first, run to confirm failure, implement, run to confirm pass) — all 7 tests in phases 1-6 follow this pattern correctly.
- Neo4j driver singleton with `connectionTimeout` and session-per-query pattern is correct and avoids connection pool exhaustion.
- `runQuery` helper correctly handles both `neo4j.Integer` conversion and node property extraction — the approach is sound (modulo I4 above).
- Phase-06 correctly identifies the `dynamic()` + `ssr: false` requirement for `react-force-graph-2d` and places the note prominently.
- Docker multi-stage build is correct — standalone output, no dev dependencies in runner image.
- All 8 API routes from the spec are implemented.
- Error handling (503 return with message) is present in every API route.
- Empty states are handled in all list components (SessionList, CodeTree, StatCards).
- `params: Promise<{ id: string }>` async params pattern is correct for Next.js 15 App Router.
- Commit messages follow conventional commits format throughout.
- File paths are consistent across all phases and match the spec's file structure exactly.

---

## Summary Table

| ID | Severity  | Phase  | Description |
|----|-----------|--------|-------------|
| C1 | Critical  | 01     | `setupFilesAfterFramework` typo → all jest-dom matchers fail |
| C2 | Critical  | 03, 04 | `fetch('http://localhost:3000/...')` in Server Components breaks in Docker |
| I1 | Important | 06     | `userEvent` not imported in node-detail test |
| I2 | Important | 05     | Needs clarifying comment (relative vs absolute URL), not a bug |
| I3 | Important | 02     | Cypher WHERE after OPTIONAL MATCH filters wrong node |
| I4 | Important | 02     | `neo4j.Integer` type reference will fail in TS strict mode |
| I5 | Important | 01     | `@types/react-force-graph-2d` does not exist on npm |
| S1 | Suggestion | 06    | `width={undefined}` won't fill flex container as intended |
| S3 | Suggestion | 02    | SessionEvent query lacks GROUP_ID filter |
| S4 | Suggestion | 06    | Phase-06 missing explicit dependency note on phase-05 |
| S5 | Suggestion | 06    | Graph page itself has no test |
| S6 | Suggestion | 01    | `sleep 3` too short for Next.js dev server on Windows |

---

## Required Fixes Before Implementation

1. **C1:** `setupFilesAfterFramework` → `setupFilesAfterEnv` in jest.config.ts template
2. **C2:** Replace `fetch('http://localhost:3000/api/...')` in Server Components with direct route handler imports, or add `NEXT_PUBLIC_BASE_URL` env var strategy
3. **I1:** Add `import userEvent from '@testing-library/user-event'` to node-detail test
4. **I3:** Move Cypher WHERE clause above OPTIONAL MATCH in code files route
5. **I4:** Change `neo4j.Integer` type reference to named import `Integer`
6. **I5:** Remove `npm install @types/react-force-graph-2d` step

---

## Unresolved Questions

1. Do `SessionEvent` nodes have a `group_id` or `project` property? The session-save script (`src/scripts/session-save.js`) should be checked before implementing the sessions API route to determine whether GROUP_ID filtering is needed.
2. Does the `EpisodicNode` schema use `content` or a different property name for the episode text? The stats page assumes `.content` — this should be verified with `CALL db.schema.nodeTypeProperties()` as recommended by the spec's "Verify exact labels" note.
3. The spec says the Graph Explorer is the **default page** (implied first in the page listing). The plan redirects `/` → `/graph` which is correct. Confirm this matches the intended user experience.
