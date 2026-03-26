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

## Stability & Portability (Cross-cutting)
**Status:** Complete

- Auto-start Neo4j container + retry with backoff
- OpenAI key validation before Graphiti init
- Absolute path resolution everywhere (no CWD dependency)
- Dynamic hook paths (no hardcoded MEMGRAP_DIR)
- One-click installers (setup.bat / setup.sh)
- Expanded language support: 15 languages
- Vietnamese user guide
