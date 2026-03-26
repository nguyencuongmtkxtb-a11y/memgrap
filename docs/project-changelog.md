# Project Changelog

## 2026-03-26 — Dashboard Stability & Codebase Hardening

### Incremental Codebase Indexing
- **feat: incremental codebase indexing on session start** — `src/indexer/incremental_indexer.py` compares file mtime vs Neo4j `indexed_at`; only new/modified files are re-indexed
- **feat: auto-index on session start** — SessionStart hook runs incremental index in background (no user action needed)
- **feat: `full` parameter for `index_codebase`** — `full=False` (default) for incremental, `full=True` for complete re-index

### Dashboard Bug Fixes (Phase 4)
- **fix(dashboard): sanitize Neo4j integers in code files API** — Convert `{low, high}` Integer objects to plain numbers in `code/files` route
- **fix(dashboard): include Neo4j node labels in code files API** — Code-tree now receives `labels` array for proper icon rendering
- **fix(dashboard): deterministic date formatting** — Replace `toLocaleString()` with `toISOString()` to prevent SSR/client hydration mismatch
- **fix(dashboard): handle Neo4j DateTime/Date types in runQuery** — Added `toPlain()` helper to convert temporal types before JSON serialization
- **fix(dashboard): force dynamic rendering on sessions/stats pages** — Prevent static pre-rendering crash from live Neo4j queries
- **fix(dashboard): clamp negative/NaN limit params in graph API routes** — Input validation on query parameters
- **fix(dashboard): neo4j-driver standalone build** — Added `serverExternalPackages: ["neo4j-driver"]` to `next.config.ts`

### Core Improvements
- **feat: auto-start Neo4j container** — `graph_service.py` checks Docker container state on init, starts via `docker compose up -d` if needed
- **feat: retry with backoff** — Neo4j connection retries 3x (2s/4s/6s delay) for container startup
- **feat: OpenAI key validation** — Clear error message before Graphiti init if key missing
- **feat: absolute .env path resolution** — `config.py` resolves from `Path(__file__)`, no CWD dependency
- **feat: dynamic hook path resolution** — CJS hooks resolve `MEMGRAP_DIR` from env/config, no hardcoded paths
- **feat: expanded language support** — Code indexer now supports 15 languages (added Go, Rust, Java, C, C++, C#, Ruby, PHP, Kotlin, Swift)
- **feat: one-click installers** — `setup.bat` (Windows) / `setup.sh` (Unix)
- **docs: Vietnamese user guide** — `docs/user-guide.md`

## 2026-03-25 — Phase 4 Dashboard UI

- **feat(dashboard): Next.js 16 dashboard** — 4 pages (Graph Explorer, Sessions, Code Index, Stats), 8 API routes, shadcn/ui v4 + Tailwind CSS v4, dark mode
- **docs: Phase 4 design spec and implementation plan**

## 2026-03-24 — Phase 3 Session Hooks

- **feat: session hooks** — Auto-capture git context (branch, commits, changed files) on session start/end
- **feat: SessionEvent nodes** — Written directly to Neo4j (zero OpenAI cost)

## 2026-03-23 — Phase 2 Code Indexer

- **feat: code indexer** — tree-sitter AST parsing, direct Neo4j writes for CodeFile/CodeFunction/CodeClass/CodeImport nodes

## 2026-03-22 — Phase 1 MCP Server

- **feat: MCP server** — 7 tools (remember, recall, understand_code, get_history, search_facts, index_codebase, get_status)
- **feat: Graphiti Core integration** — temporal knowledge graph with OpenAI extraction + embeddings
