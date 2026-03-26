# Dashboard UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a read-only web dashboard at `dashboard/` for browsing Memgrap's Neo4j knowledge graph — entities, facts, sessions, code index, and system stats.

**Architecture:** Next.js 15 App Router in `dashboard/` sub-directory; API routes use the `neo4j-driver` JS package to query Neo4j directly (bolt://neo4j:7687 in Docker, bolt://localhost:7687 locally); all queries are filtered by `GROUP_ID` from `.env`; no mutations, no auth.

**Tech Stack:** Next.js 15, TypeScript, shadcn/ui, Tailwind CSS (dark only), react-force-graph-2d, neo4j-driver (JS), Docker

---

## Phases

| Phase | File | Status |
|-------|------|--------|
| 1 | [phase-01-scaffold.md](phase-01-scaffold.md) | Pending |
| 2 | [phase-02-neo4j-client.md](phase-02-neo4j-client.md) | Pending |
| 3 | [phase-03-stats-page.md](phase-03-stats-page.md) | Pending |
| 4 | [phase-04-sessions-page.md](phase-04-sessions-page.md) | Pending |
| 5 | [phase-05-code-page.md](phase-05-code-page.md) | Pending |
| 6 | [phase-06-graph-explorer.md](phase-06-graph-explorer.md) | Pending |
| 7 | [phase-07-docker.md](phase-07-docker.md) | Pending |

## Key Dependencies

- Neo4j running: `docker compose up -d` (from `D:\MEMGRAP`)
- `.env` at `D:\MEMGRAP\.env` with `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`, `GROUP_ID`
- Node.js 20+ and npm on PATH
- All dashboard work done inside `D:\MEMGRAP\dashboard\`
