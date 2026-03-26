# Dashboard UI Design Spec

## Overview
Personal debug/explore dashboard for Memgrap knowledge graph. Read-only web UI to browse entities, facts, sessions, code index, and system stats.

## Tech Stack
- Next.js 15 (App Router) + TypeScript
- shadcn/ui + Tailwind CSS (dark theme default)
- react-force-graph-2d (graph visualization)
- neo4j-driver (JavaScript) for API routes
- Docker deployment alongside Neo4j

## Architecture
```
Browser → Next.js API Routes → neo4j-driver → Neo4j (bolt://localhost:7687)
```

Monorepo: `dashboard/` folder inside MEMGRAP root. Shared `.env` for Neo4j credentials.

## Pages

### 1. Graph Explorer (`/graph`) — default page
- **Left panel:** entity type filter checkboxes (8 types), text search input, recent entities list
- **Center:** react-force-graph-2d force-directed graph. Nodes colored by entity type. Click node → detail. Hover edge → fact label.
- **Right panel (on click):** node name, type, properties, connected facts with timestamps

API routes:
- `GET /api/graph/nodes` — list entities, filter by type, search query
- `GET /api/graph/nodes/[id]` — node detail + connected edges
- `GET /api/graph/edges` — list facts/relationships
- `GET /api/graph/viz?limit=200` — nodes + edges for force-graph {id, source, target, label}. Default cap 200 nodes.

### 2. Sessions (`/sessions`)
- List of SessionEvent nodes, sorted by ended_at DESC
- Each row: date, branch, commit count, files changed count
- Click row → detail: commits list, files list, summary text, duration

API routes:
- `GET /api/sessions` — list SessionEvent
- `GET /api/sessions/[id]` — session detail

### 3. Code Index (`/code`)
- Tree view: CodeFile → children (CodeFunction, CodeClass, CodeImport)
- Filter by language, search by name
- Each entry shows: name, line number, type icon

API route:
- `GET /api/code/files` — list CodeFile with children

### 4. Stats (`/stats`)
- Stat cards: total nodes, total facts, session count, indexed files count
- Recent activity: last 10 episodes with timestamp and content preview
- Health check: Neo4j status, LLM model, group_id

API route:
- `GET /api/stats` — aggregate counts + health

## File Structure
```
dashboard/
├── app/
│   ├── layout.tsx          # Root layout: sidebar + theme provider
│   ├── page.tsx            # Redirect → /graph
│   ├── graph/page.tsx
│   ├── sessions/page.tsx
│   ├── code/page.tsx
│   ├── stats/page.tsx
│   └── api/
│       ├── graph/nodes/route.ts
│       ├── graph/nodes/[id]/route.ts
│       ├── graph/edges/route.ts
│       ├── graph/viz/route.ts
│       ├── sessions/route.ts
│       ├── sessions/[id]/route.ts
│       ├── code/files/route.ts
│       └── stats/route.ts
├── components/
│   ├── sidebar.tsx
│   ├── graph-viewer.tsx    # react-force-graph-2d wrapper ("use client", dynamic import ssr:false)
│   ├── node-detail.tsx
│   ├── session-list.tsx
│   ├── code-tree.tsx
│   └── stat-cards.tsx
├── lib/
│   └── neo4j.ts            # Neo4j driver singleton
├── Dockerfile
├── package.json
├── tailwind.config.ts
└── next.config.ts
```

## Neo4j Labels
Verify exact labels with `CALL db.labels()` before implementation. Expected:
- `:EntityNode` — Graphiti entity nodes (not `:Entity`)
- `:EpisodicNode` — Graphiti episodes
- `:SessionEvent` — session hooks
- `:CodeFile`, `:CodeFunction`, `:CodeClass`, `:CodeImport` — code index
- Edge type: `RELATES_TO` between EntityNodes

## Neo4j Queries (key Cypher)
- Entities: `MATCH (n:EntityNode) WHERE n.group_id = $gid RETURN n LIMIT $limit`
- Edges: `MATCH (a:EntityNode)-[r:RELATES_TO]->(b:EntityNode) WHERE a.group_id = $gid RETURN a, r, b LIMIT $limit`
- Node detail: `MATCH (n:EntityNode)-[r]-(m) WHERE elementId(n) = $id RETURN n, r, m`
- Sessions list: `MATCH (s:SessionEvent) RETURN s, size(s.commits) AS commit_count, size(s.files_changed) AS files_count ORDER BY s.ended_at DESC`
- Session detail: `MATCH (s:SessionEvent) WHERE s.session_id = $id RETURN s`
- Code files: `MATCH (f:CodeFile)-[:CONTAINS|IMPORTS]->(c) RETURN f, collect(c) AS children`
- Episodes: `MATCH (e:EpisodicNode) WHERE e.group_id = $gid RETURN e ORDER BY e.created_at DESC LIMIT 10`
- Stats: `MATCH (n:EntityNode {group_id: $gid}) RETURN count(n)` + similar for edges, sessions, code files
- Graph viz: same as Entities + Edges but with `LIMIT 200` default cap for performance

## Env Vars (from .env)
- `NEO4J_URI` (existing)
- `NEO4J_USER` (existing)
- `NEO4J_PASSWORD` (existing)
- `GROUP_ID` (existing — used to filter graph data by project)
- `NEXT_PUBLIC_APP_NAME=Memgrap` (new, optional)

## Docker
Add to docker-compose.yml:
```yaml
dashboard:
  build: ./dashboard
  ports: ["3000:3000"]
  env_file: .env
  depends_on: [neo4j]
```

## Constraints
- Read-only: no mutations from dashboard
- Single user: no auth needed
- Dark theme only (no light toggle — keep scope minimal)
- All data from same Neo4j instance as MCP server
- All graph queries filter by GROUP_ID to scope to current project
- Error states: show "Neo4j unreachable" banner when connection fails
