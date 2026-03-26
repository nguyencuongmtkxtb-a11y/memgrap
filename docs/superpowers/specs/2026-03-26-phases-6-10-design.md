# Phases 6-10 Design Spec

## Overview

Five phases to harden and expand the Memgrap dashboard: error boundaries, multi-project support, search/filter, realtime updates, and data export/import.

**Scope:** Dashboard (Next.js 16) + Python MCP server modifications.

---

## Phase 6 — Error Boundaries

**Goal:** Friendly UI when Neo4j is down instead of white crash screen.

### Components
- `ErrorBoundary` — React class component wrapping each page
  - Props: `fallback?: ReactNode`, `children`
  - State: `hasError`, `error`
  - Shows: icon + error message + "Retry" button
  - "Retry" calls `window.location.reload()` or resets state + re-renders

- `ConnectionStatus` — Small indicator in sidebar
  - Polls lightweight `/api/health` endpoint every 30s (single Neo4j ping, not full stats)
  - Green dot = connected, Red dot = disconnected
  - Clicking red dot shows last error detail

### Integration
- Wrap each page's content in `<ErrorBoundary>` in layout or page level
- API routes already return 503 with detail — no backend changes needed
- Existing `error-banner.tsx` is for inline API errors — `ErrorBoundary` catches unhandled React crashes. Both coexist (different layers)
- Data fetching uses existing `fetch()` + `useState/useEffect` pattern (no SWR dependency)

### Files to create/modify
- `dashboard/components/error-boundary.tsx` — new
- `dashboard/components/connection-status.tsx` — new
- `dashboard/app/api/health/route.ts` — new, lightweight Neo4j ping
- `dashboard/app/graph/page.tsx` — wrap content
- `dashboard/app/code/page.tsx` — wrap content
- `dashboard/app/sessions/page.tsx` — wrap content
- `dashboard/app/stats/page.tsx` — wrap content
- `dashboard/components/sidebar.tsx` — add ConnectionStatus

---

## Phase 7 — Multi-project Support

**Goal:** Filter all dashboard data by project.

### Data Model Changes
- `CodeFile` nodes: add `project` property (derived from index path)
- `CodeFunction/CodeClass/CodeImport`: inherit project from parent CodeFile
- Entity/Episodic: already scoped by `group_id` (= project name in Graphiti)
- SessionEvent: already has `project` property

### Backend Changes

**New API:** `GET /api/projects`
- Query: `MATCH (n) WHERE n.project IS NOT NULL RETURN DISTINCT n.project AS project UNION MATCH (n) WHERE n.group_id IS NOT NULL RETURN DISTINCT n.group_id AS project`
- Returns: `string[]`

**Modify all existing APIs** to accept `?project=` query param:
- `/api/graph/viz` — filter Entity nodes by `group_id = project`
- `/api/graph/nodes` — filter Entity nodes by `group_id = project`
- `/api/graph/nodes/[id]` — no change (single node lookup)
- `/api/code/files` — filter CodeFile nodes by `project` property
- `/api/sessions` — filter SessionEvent nodes by `project` property
- `/api/stats` — scoped counts: Entity by `group_id`, CodeFile/Session by `project`

**Key: `group_id` vs `project` mapping:**
- Entity/Episodic (Graphiti-managed) → filter by `group_id`
- CodeFile/CodeFunction/CodeClass/CodeImport (direct Neo4j) → filter by `project`
- SessionEvent (direct Neo4j) → filter by `project`
- The `?project=` query param maps to the correct field per node type internally

**Python MCP server changes:**
- `neo4j_ingestor.py`: Add `project` param to CodeFile MERGE queries
- `index_codebase` tool: Derive project name from directory path (last folder component or explicit param)
- `incremental_indexer.py`: Pass project to ingestor

### Frontend Changes

**ProjectContext** (React Context + localStorage):
```
ProjectProvider → { project: string | null, setProject }
```
- `null` = "All Projects"
- Persisted in `localStorage('memgrap-project')`

**Project Selector** — Dropdown in sidebar above nav items:
- Fetches from `/api/projects`
- Options: "All Projects" + project list
- Selection updates context → all pages re-fetch with new project param

**All data-fetching pages** include `project` in fetch URL query param.

### Files to create/modify
- `dashboard/contexts/project-context.tsx` — new
- `dashboard/app/layout.tsx` — wrap with ProjectProvider
- `dashboard/components/sidebar.tsx` — add project selector
- `dashboard/app/api/projects/route.ts` — new
- All existing API routes — add project filter
- `dashboard/lib/neo4j.ts` — update `getGroupId()` helper for project scoping
- `src/indexer/neo4j_ingestor.py` — add project property
- `src/indexer/incremental_indexer.py` — pass project
- `src/mcp_server.py` — pass project to indexer

---

## Phase 8 — Search & Filter

**Goal:** Full-text search + date range filtering across all data types.

### Search

**API:** `GET /api/search?q=<query>&type=<entity|session|code>&from=<iso>&to=<iso>&project=<name>`

**Implementation:**
- Entity: Use existing Neo4j fulltext index `entity_name` (CALL db.index.fulltext.queryNodes)
- Session: Create fulltext index on SessionEvent (branch, summary, commits)
- Code: Create fulltext index on CodeFile (path), CodeFunction (name)
- Return unified results: `{ type, id, name, summary, score }`

**Fulltext indexes to create (migration):**
```cypher
CREATE FULLTEXT INDEX session_search IF NOT EXISTS
FOR (s:SessionEvent) ON EACH [s.branch, s.summary]

CREATE FULLTEXT INDEX code_search IF NOT EXISTS
FOR (c:CodeFile) ON EACH [c.path]

CREATE FULLTEXT INDEX code_function_search IF NOT EXISTS
FOR (f:CodeFunction) ON EACH [f.name]
```

### Date Range Filter
- Component: `DateRangePicker` using shadcn/ui calendar
- Filters `created_at` for entities, `started_at` for sessions, `indexed_at` for code
- Applied via query params `?from=&to=`
- Added to Graph, Sessions, Code pages

### UI
- Search bar in top area of layout (not sidebar — sidebar is for nav)
- Results shown in a dropdown/panel below search bar
- Click result → navigate to relevant page with item focused
- Date range filter inline per page (near existing filters)

### Files to create/modify
- `dashboard/components/search-bar.tsx` — new
- `dashboard/components/date-range-picker.tsx` — new
- `dashboard/app/api/search/route.ts` — new
- `dashboard/app/layout.tsx` — add search bar
- Per-page files — add date range filter
- `src/indexer/neo4j_ingestor.py` — ensure fulltext indexes exist (migration on startup)

---

## Phase 9 — Dashboard Realtime (SSE)

**Goal:** Auto-refresh dashboard when new data is ingested.

**Why SSE over WebSocket:** Dashboard uses `output: 'standalone'` for Docker. Custom WS server conflicts with standalone mode. SSE works as a normal API route — no architectural changes needed.

### Architecture
```
MCP Server (Python) --HTTP POST--> /api/notify --> SSE broadcast --> client refetch
```

### Notification Source (Python side)
After successful operations, MCP server sends HTTP POST to dashboard:
- `POST ${DASHBOARD_URL}/api/notify` with body `{ event: "entity:created" | "session:created" | "code:indexed", project?: string }`
- `DASHBOARD_URL` configurable via env var (default: `http://localhost:3001`, Docker: `http://dashboard:3000`)
- Fire-and-forget (catch errors silently — dashboard may not be running)
- Added to: `remember()`, `index_codebase()`, session_save.py

### SSE Server (Dashboard side)
- `GET /api/events` — SSE endpoint (ReadableStream with `text/event-stream`)
- In-memory subscriber list (Set of response streams)
- `POST /api/notify` — receives event from MCP, writes to all active SSE streams
- No heartbeat needed (SSE has built-in reconnection via `retry:` field)

### Client Integration
- `useEventSource` hook: connects via `EventSource` API on mount
- Auto-reconnects on disconnect (browser-native SSE behavior)
- On message received: triggers page data refetch
- Visual indicator: subtle "Updated" toast
- Fallback: if SSE fails, fall back to polling `setInterval` every 30s

### Files to create/modify
- `dashboard/hooks/use-event-source.ts` — new
- `dashboard/app/api/events/route.ts` — new, SSE endpoint
- `dashboard/app/api/notify/route.ts` — new, receives POST from MCP
- `dashboard/lib/event-bus.ts` — new, in-memory pub/sub for notify→SSE bridge
- `src/mcp_server.py` — add notify calls after remember/index
- `src/session/session_save.py` — add notify call after session save
- `src/config.py` — add DASHBOARD_URL setting

---

## Phase 10 — Export/Import

**Goal:** Backup/restore Neo4j data, export human-readable JSON.

### Neo4j Dump (full backup — CLI only)

**Why CLI-only:** Neo4j Community Edition requires DB stop for dump/load. Running via web API is fragile (requires Docker socket, mid-failure leaves DB inconsistent). CLI scripts are safer and simpler.

**Export:** `scripts/backup.sh` (bash) / `scripts/backup.bat` (Windows)
- Runs `docker exec memgrap-neo4j neo4j-admin database dump neo4j --to-path=/backups`
- Copies dump from container to host `./backups/memgrap-{timestamp}.dump`

**Import:** `scripts/restore.sh` / `scripts/restore.bat`
- Stops Neo4j, loads dump, restarts
- Requires confirmation prompt

### JSON Export (readable)

**Export:** `GET /api/export/json?project=<name>`
- Queries all nodes + relationships
- Streams JSON: `{ entities: [...], facts: [...], sessions: [...], codeFiles: [...] }`
- Optional project filter
- Filename: `memgrap-export-{project}-{timestamp}.json`

**Import:** `POST /api/import/json` (multipart JSON upload)
- Parses JSON, MERGE nodes + relationships
- Additive (doesn't delete existing data)
- Returns: `{ imported: { entities, facts, sessions, codeFiles } }`

### Dashboard Page: `/export`
- New page in sidebar nav
- Sections:
  1. **Backup** — Info text with CLI commands to run (not a button — dump requires CLI)
  2. **Export JSON** — Project selector + "Export" button → downloads .json
  3. **Import JSON** — File upload + preview → uploads .json

### Files to create/modify
- `dashboard/app/export/page.tsx` — new page
- `dashboard/app/api/export/json/route.ts` — new
- `dashboard/app/api/import/json/route.ts` — new
- `dashboard/components/sidebar.tsx` — add Export nav item
- `scripts/backup.sh` + `scripts/backup.bat` — new CLI scripts
- `scripts/restore.sh` + `scripts/restore.bat` — new CLI scripts

---

## Implementation Order

1. **Phase 6** (Error Boundaries) — Foundation, no dependencies
2. **Phase 7** (Multi-project) — Modifies APIs, needed by Phase 8
3. **Phase 8** (Search & Filter) — Builds on Phase 7 project filtering
4. **Phase 9** (Realtime) — Independent but benefits from stable API layer
5. **Phase 10** (Export/Import) — Independent, builds on final data model

## Testing Strategy

Each phase adds:
- Unit tests for new components/utilities
- API route tests (mocked Neo4j)
- Integration test for happy path (requires Neo4j)

## Risk Assessment

| Risk | Mitigation |
|------|-----------|
| SSE memory leak (orphan streams) | Cleanup on connection close; max 50 subscribers |
| Neo4j dump requires DB stop | CLI-only (not API); clear user instructions |
| Multi-project migration (adding project to CodeFile) | MERGE is idempotent; existing nodes get null project = "All" |
| Fulltext index creation on large graphs | CREATE IF NOT EXISTS is fast; run at startup |
| `group_id` vs `project` naming split | Document mapping clearly; API routes handle internally |
