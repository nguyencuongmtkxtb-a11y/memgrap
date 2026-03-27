# Project Changelog

## 2026-03-27 — Fix: full-mode index_codebase missing relation extraction

### Bug Fix
- **fix(mcp): `index_codebase(full=True)` now runs Phase 2 (relation extraction)** — full mode only ran symbol extraction (Phase 1), skipping `extract_relations()` + `index_relations()`. Result: 0 CALLS/EXTENDS/IMPORTS_FROM edges. Incremental mode was unaffected. Added relation extraction loop + `index_relations()` call to full mode path in `mcp_server.py`.

## 2026-03-27 — Config: Export OPENAI_API_KEY to env

### Bug Fix
- **fix(config): export OPENAI_API_KEY to `os.environ`** — Graphiti Core internals read the env var directly, bypassing the key passed via factory. pydantic-settings loads from `.env` but doesn't set `os.environ`, causing `api_key client option must be set` error on MCP tool calls.

## 2026-03-27 — Code Graph MCP Tools (Phase 12)

### New MCP Tools (5 tools, zero OpenAI cost)
- **feat(mcp): `find_callers(function_name, project)`** — impact analysis, returns all functions that call the given function
- **feat(mcp): `find_callees(function_name, project)`** — execution flow, returns all functions called by the given function
- **feat(mcp): `find_class_hierarchy(class_name, project)`** — inheritance tree (parents + children)
- **feat(mcp): `find_file_imports(file_path, project)`** — module dependencies (imports + imported_by)
- **feat(mcp): `search_code(query, project, limit)`** — search functions/classes/files by name pattern

### Code Graph Service
- **feat: `src/code_graph_service.py`** — async Neo4j driver for code graph queries, independent from Graphiti/OpenAI stack
- **chore: `.mcp.json` updated** — includes cwd configuration

### MCP Tool Count
- Total MCP tools: 12 (7 memory + 5 code graph)

## 2026-03-27 — Code Relationship Analysis (Phase 11)

### Relation Extraction Engine
- **feat(indexer): relation queries for all 15 languages** — tree-sitter S-expression queries for function calls, class inheritance, and import sources across Python, JS, TS, JSX, TSX, Go, Rust, Java, C, C++, C#, Ruby, PHP, Kotlin, Swift
- **feat(indexer): `relation_extractor.py`** — new module with `CodeRelation` dataclass and `extract_relations()` function, deduplication, enclosing scope detection
- **feat(indexer): `import_resolver.py`** — resolves import source strings to indexed file paths with language-specific strategies (dotted modules, relative paths, package imports)
- **fix(indexer): Kotlin symbol query** — tree-sitter-kotlin uses `identifier` not `simple_identifier`/`type_identifier`, and has no `interface_declaration` (interfaces are `class_declaration`)
- **fix(indexer): Swift symbol query** — tree-sitter-swift uses `class_declaration` for structs/enums too, removed invalid `struct_declaration`/`enum_declaration`

### Neo4j Relationship Ingestion
- **feat(ingestor): `index_relations()` method** — batch upsert CALLS, EXTENDS, IMPORTS_FROM edges between existing code nodes
- **feat(ingestor): CALLS edges** — CodeFunction -> CodeFunction (cross-file within project)
- **feat(ingestor): EXTENDS edges** — CodeClass -> CodeClass (inheritance/implementation)
- **feat(ingestor): IMPORTS_FROM edges** — CodeFile -> CodeFile (resolved import source)

### Pipeline Integration
- **feat(indexer): relation extraction in incremental pipeline** — after symbol indexing, extracts and ingests relations for all changed files
- **feat(indexer): CLI relation stats** — output includes relation counts (calls, extends, imports_from)

### Dashboard: Code Graph Visualization
- **feat(dashboard): `/api/code/graph` endpoint** — returns nodes (files, functions, classes) and edges (CALLS, EXTENDS, IMPORTS_FROM) with project/search filters
- **feat(dashboard): Code Graph page** — interactive force-directed graph with react-force-graph-2d, node type filters, relationship filters, legend, node detail panel
- **feat(dashboard): `code-graph-viewer.tsx`** — custom canvas rendering (squares=files, circles=functions, diamonds=classes), color-coded edges by type
- **feat(dashboard): sidebar "Code Graph" link** — new navigation entry with Network icon

## 2026-03-27 — Indexer Fixes & Global MCP Config

### Indexer Fixes
- **fix(indexer): separate TS_QUERY from JS_QUERY** — tree-sitter-typescript uses `type_identifier` for class names, not `identifier` like JS. Shared query caused `Impossible pattern` crash on all TS/TSX files
- **fix(indexer): try/except around parse_file** — single file parse errors no longer crash the entire incremental indexer
- **fix(indexer): --project CLI arg** — incremental indexer now accepts `--project` flag, defaults to directory basename. Session hook passes project name
- **fix(hook): pass project to indexer** — `memgrap-session-start.cjs` now passes `--project` so CodeFile nodes are tagged per-project

### Setup Scripts: Global MCP Config

- **fix(setup): global MCP config** — `setup.bat` and `setup.sh` now write `~/.claude/mcp.json` (global) instead of only project-level `.mcp.json`, so graphiti-memory MCP server works in **all projects**
- **fix(setup): pass OPENAI_API_KEY via env** — MCP config includes `env.OPENAI_API_KEY` (read from `.env`) to avoid runtime failures from missing API key
- **fix(setup): keep project .mcp.json** — backward compat for users opening MEMGRAP directory directly

## 2026-03-26 — Phases 6-10 Dashboard Hardening & Features

### Phase 6 — Error Boundaries
- **feat(dashboard): ErrorBoundary class component** — wraps all pages with icon + error message + retry button
- **feat(dashboard): ConnectionStatus indicator** — sidebar footer polls `/api/health` every 30s, green/red/yellow dot
- **feat(dashboard): `/api/health` endpoint** — lightweight Neo4j ping (`RETURN 1`)

### Phase 7 — Multi-project Support
- **feat(dashboard): ProjectContext provider** — React Context + localStorage (`memgrap-project` key)
- **feat(dashboard): project selector dropdown** — sidebar, fetches `/api/projects`
- **feat(dashboard): `/api/projects` endpoint** — UNION of `n.project` and `n.group_id` for distinct list
- **feat(dashboard): project filter on all API routes** — `?project=` param maps to `group_id` (Entity) or `project` (Code/Session)
- **feat(indexer): project property on CodeFile** — `neo4j_ingestor.py` sets `project` on all MERGE queries
- **feat(dashboard): sessions/stats client component conversion** — rewrote from server to client components with useProject/ErrorBoundary

### Phase 8 — Search & Filter
- **feat(dashboard): global search bar** — 400ms debounce, dropdown results, click-to-navigate
- **feat(dashboard): `/api/search` endpoint** — fulltext search across 4 Neo4j indexes with Lucene escape
- **feat(dashboard): DateRangePicker component** — from/to date inputs on Graph, Sessions, Code pages
- **feat(indexer): fulltext index creation** — `ensure_fulltext_indexes()` creates session_search, code_file_search, code_function_search

### Phase 9 — Dashboard Realtime (SSE)
- **feat(dashboard): SSE endpoint `/api/events`** — ReadableStream with cancel() cleanup, 30s keepalive
- **feat(dashboard): EventBus singleton** — in-memory pub/sub for notify→SSE bridge
- **feat(dashboard): `/api/notify` endpoint** — receives POST from MCP server, broadcasts to SSE
- **feat(dashboard): `useEventSource` hook** — auto-reconnect with 5s backoff
- **feat(mcp): dashboard notification** — fire-and-forget POST after remember/index/session ops
- **feat(config): DASHBOARD_URL setting** — configurable via env (default: `http://localhost:3001`)

### Phase 10 — Export/Import
- **feat(dashboard): `/api/export/json` endpoint** — streams entities, facts, sessions, codeFiles as downloadable JSON
- **feat(dashboard): `/api/import/json` endpoint** — additive MERGE with ALLOWED_LABELS whitelist (Cypher injection prevention)
- **feat(dashboard): export page** — CLI backup instructions, JSON download, file upload
- **feat: backup/restore CLI scripts** — `scripts/backup.sh`, `scripts/restore.sh` + Windows variants

## 2026-03-26 — Phase 5 Testing & CI/CD

### Unit Tests
- **test: result_formatters** — 7 tests for format_edge, format_node, format_episode (pure functions)
- **test: config** — 3 tests for Settings defaults, env override, lru_cache isolation
- **test: graph_service** — 10 tests for init, retry, container check, memory ops, status
- **test: mcp_server tools** — 15 tests for all 7 MCP tools (success/error/empty paths)
- **test: ast_parser** — 9 tests for Python/JS/TS parsing, directory walk, ignore dirs
- **test: neo4j_ingestor** — 6 tests for Cypher upsert queries, batch operations
- **test: incremental_indexer** — 7 tests for file collection, reindex logic, incremental flow

### Test Infrastructure
- **chore: reorganize integration tests** — moved to `tests/integration/` with `@pytest.mark.integration`
- **chore: conftest.py** — `get_settings.cache_clear()` autouse fixture, marker registration
- **chore: test fixtures** — sample.py/js/ts for AST parser tests
- **chore: pytest-asyncio auto mode** — no per-test `@pytest.mark.asyncio` needed

### Linting
- **chore: ruff linter** — configured E/F/I rules, line-length 120, per-file ignores for tree-sitter queries and session scripts

### CI/CD
- **ci: GitHub Actions** — `.github/workflows/ci.yml` with 2 parallel jobs (Python lint+test, Dashboard lint+test)

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
