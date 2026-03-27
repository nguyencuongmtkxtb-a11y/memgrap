# Development Roadmap

## Phase 1 — MCP Server
**Status:** Complete

Core MCP server with 7 tools (remember, recall, understand_code, get_history, search_facts, index_codebase, get_status). Graphiti Core integration with OpenAI extraction + embeddings. Neo4j graph database via Docker.

## Phase 2 — Code Indexer
**Status:** Complete

tree-sitter AST parsing for source files. Direct Neo4j writes (zero OpenAI cost) for CodeFile, CodeFunction, CodeClass, CodeImport nodes.

## Phase 3 — Session Hooks
**Status:** Complete

Auto-capture git context (branch, recent commits, changed files) on session start/end. SessionEvent nodes written directly to Neo4j. CJS hook scripts for Claude Code integration.

## Phase 4 — Dashboard UI
**Status:** Complete (all fixes shipped)

Next.js 16 dashboard with 4 pages (Graph Explorer, Sessions, Code Index, Stats) and 8 API routes. shadcn/ui v4 + Tailwind CSS v4, dark mode only. Docker standalone build.

**Fixes shipped:**
- Neo4j DateTime/Date type conversion (`toPlain()` helper)
- Force-dynamic rendering on sessions/stats pages
- SSR/client hydration mismatch (deterministic date formatting)
- Neo4j Integer `{low, high}` sanitization in API routes
- Node labels included in code files API
- `serverExternalPackages` for neo4j-driver standalone build
- Input validation (clamp negative/NaN limit params)

## Phase 5 — Testing & CI/CD
**Status:** Complete

Comprehensive unit test suite (56 tests, ~1.4s) + GitHub Actions CI pipeline.

- 7 unit test files covering: result_formatters, config, graph_service, mcp_server tools, ast_parser, neo4j_ingestor, incremental_indexer
- Integration tests reorganized into `tests/integration/` with `@pytest.mark.integration`
- ruff linter configured (E/F/I rules, line-length 120)
- GitHub Actions CI: Python (ruff + pytest unit) + Dashboard (eslint + jest) — two parallel jobs
- pytest-asyncio auto mode, `get_settings.cache_clear()` fixture for test isolation

## Phase 6 — Error Boundaries
**Status:** Complete

React ErrorBoundary class component wrapping all pages with retry button. ConnectionStatus indicator in sidebar footer polling lightweight `/api/health` endpoint every 30s (green/red/yellow dot).

## Phase 7 — Multi-project Support
**Status:** Complete

Global `ProjectContext` (React Context + localStorage) with project selector dropdown in sidebar. All 6 API routes accept `?project=` param, mapping to `group_id` for Entity/Episodic nodes and `project` for Code/Session nodes. Python indexer writes `project` property to CodeFile nodes. `/api/projects` endpoint returns distinct project list.

## Phase 8 — Search & Filter
**Status:** Complete

Global fulltext search bar with 400ms debounce across 4 Neo4j indexes (entity_name, session_search, code_file_search, code_function_search). DateRangePicker component on Graph, Sessions, Code pages with `?from=&to=` query params. Fulltext indexes auto-created by Python indexer on startup.

## Phase 9 — Dashboard Realtime (SSE)
**Status:** Complete

Server-Sent Events via ReadableStream API route (`/api/events`). In-memory EventBus singleton for pub/sub. Python MCP server sends fire-and-forget HTTP POST to `/api/notify` after remember/index/session operations. `useEventSource` React hook with auto-reconnect. Configurable `DASHBOARD_URL` in settings.

## Phase 10 — Export/Import
**Status:** Complete

JSON export (`GET /api/export/json?project=`) with downloadable file. JSON import (`POST /api/import/json`) with additive MERGE and label whitelist (Cypher injection prevention). Export page in dashboard with CLI backup instructions. Neo4j dump/restore CLI scripts (`scripts/backup.sh`, `scripts/restore.sh` + Windows variants).

## Phase 11 — Code Relationship Analysis
**Status:** Complete

Tree-sitter relation queries for function calls, class inheritance, and import sources across all 15 languages. `relation_extractor.py` with CodeRelation dataclass. `import_resolver.py` for language-specific import path resolution. Neo4j edges: CALLS (function->function), EXTENDS (class->class), IMPORTS_FROM (file->file). Integrated into incremental indexer pipeline. Dashboard Code Graph page with interactive force-directed visualization (react-force-graph-2d), node/edge type filters, and node detail panel. Fixed broken Kotlin and Swift tree-sitter queries.

## Phase 12 — Code Graph MCP Tools
**Status:** Complete

5 new MCP tools for direct Neo4j code graph queries (zero OpenAI cost). `find_callers`, `find_callees`, `find_class_hierarchy`, `find_file_imports`, `search_code`. New `src/code_graph_service.py` module with async Neo4j driver, independent from Graphiti/OpenAI. Total MCP tools: 12 (7 memory + 5 code graph). `.mcp.json` updated with cwd.

## Stability & Portability (Cross-cutting)
**Status:** Complete

- Auto-start Neo4j container + retry with backoff
- OpenAI key validation before Graphiti init
- Absolute path resolution everywhere (no CWD dependency)
- Dynamic hook paths (no hardcoded MEMGRAP_DIR)
- One-click installers (setup.bat / setup.sh)
- Expanded language support: 15 languages
- Vietnamese user guide
