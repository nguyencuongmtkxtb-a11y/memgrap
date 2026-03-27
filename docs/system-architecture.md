# System Architecture

## Components

### MCP Server (`src/mcp_server.py`)
- FastMCP with stdio transport
- 7 tools exposed to Claude Code
- Lazy initialization on first tool call
- **OpenAI key validation** on first tool call — clear error if missing (before Graphiti init)
- All logging to stderr (stdout = MCP JSON-RPC)

### Graph Service (`src/graph_service.py`)
- Wraps Graphiti Core API
- Methods: add_memory, recall, search_nodes, search_facts, get_episodes, get_status
- Uses result_formatters for serialization
- **Auto-start Neo4j:** On `initialize()`, checks if Docker `memgrap-neo4j` container is running; starts it via `docker compose up -d` if not (gracefully skips if Docker unavailable)
- **Retry with backoff:** Connection retries up to 3x with increasing delay (2s, 4s, 6s) — handles container still starting
- **Health check guidance:** Failure messages include actionable fix steps (`docker compose ps`)

### Graphiti Factory (`src/graphiti_factory.py`)
- Creates configured Graphiti instance
- OpenAI LLM client (gpt-4o-mini) for extraction
- OpenAI embedder (text-embedding-3-small) for vectors

### Config (`src/config.py`)
- pydantic-settings BaseSettings
- .env path resolved absolute from `Path(__file__)` — works regardless of CWD
- Keys: OPENAI_API_KEY, NEO4J_URI/USER/PASSWORD, LLM_MODEL, GROUP_ID

### Entity Types (`src/entity_types.py`)
- 8 Pydantic models: CodePattern, TechDecision, ProjectContext, Person, Tool, Concept, BugReport, Requirement
- Passed to Graphiti's add_episode for guided extraction

### Result Formatters (`src/result_formatters.py`)
- format_edge, format_node, format_episode
- Serialize Graphiti objects to dicts for MCP responses

### Code Relationship Analysis (`src/indexer/`)
- **`relation_extractor.py`** — extracts CodeRelation objects (calls, extends, imports_from) using tree-sitter relation queries
- **`import_resolver.py`** — resolves import source strings to indexed file paths with language-specific strategies
- **`language_configs.py`** — each LangConfig now has `relation_query_src` for call/inheritance/import-source patterns
- **Neo4j edges:** CALLS (function->function), EXTENDS (class->class), IMPORTS_FROM (file->file)
- **Pipeline:** runs after symbol indexing in `incremental_indexer.py`, relations extracted for all changed files
- **15 languages:** Python, JS, TS, JSX, TSX, Go, Rust, Java, C, C++, C#, Ruby, PHP, Kotlin, Swift

## Data Flow
1. Claude Code invokes MCP tool (e.g. `remember`)
2. MCP Server delegates to GraphService
3. GraphService calls Graphiti Core (add_episode / search)
4. Graphiti calls OpenAI for entity extraction + embeddings
5. Results stored in / retrieved from Neo4j

### Session Hooks (`src/session/`)
- `session_start.py` / `session_end.py` — Python scripts invoked by Claude Code hooks
- `~/.claude/hooks/memgrap-session-{start,end}.cjs` — Node.js hook scripts
- Auto-capture git context (branch, recent commits, changed files) on session boundaries
- Write `SessionEvent` nodes to Neo4j directly (zero OpenAI cost)
- **Path resolution:** Python scripts use `Path(__file__).resolve()` (no sys.path hacks)
- **Dynamic hooks:** CJS hooks resolve `MEMGRAP_DIR` from env/config — no hardcoded paths

### Dashboard (`dashboard/`)
- **Next.js 16** App Router with standalone output for Docker
- **Pages:** Graph Explorer (react-force-graph-2d), Sessions, Code Index, Code Graph, Stats, Export
- **API routes (17):** viz, nodes, nodes/[id], edges, sessions, sessions/[id], code/files, code/graph, stats, health, projects, search, events (SSE), notify, export/json, import/json
- **Components:** sidebar, graph-viewer, code-graph-viewer, node-detail, code-tree, session-list, stat-cards, error-banner, error-boundary, connection-status, project-selector, search-bar, date-range-picker
- **Contexts:** ProjectContext (project selection with localStorage persistence)
- **Hooks:** useEventSource (SSE auto-reconnect with 5s backoff)
- **UI:** shadcn/ui v4 + Tailwind CSS v4, dark mode only
- **Neo4j client:** `lib/neo4j.ts` — singleton driver, session-per-query, Integer handling
- **EventBus:** `lib/event-bus.ts` — in-memory pub/sub singleton for SSE broadcast
- **Error Boundaries:** React class component wrapping all pages with retry button
- **Connection Status:** Sidebar footer indicator polling `/api/health` every 30s
- **Multi-project:** All API routes accept `?project=` param, mapping to `group_id` (Entity) or `project` (Code/Session)
- **Search:** Fulltext search across 4 Neo4j indexes with Lucene escape, 400ms debounce
- **Realtime:** SSE via ReadableStream + fire-and-forget POST from Python MCP server
- **Export/Import:** JSON export/import with ALLOWED_LABELS whitelist, CLI backup scripts
- **`serverExternalPackages: ["neo4j-driver"]`** in `next.config.ts` — prevents standalone build failures from native driver modules
- **`toPlain()` DateTime helper** (`lib/neo4j.ts`) — converts Neo4j `DateTime`/`Date` temporal types to plain JS objects before JSON serialization
- **Neo4j Integer sanitization:** API routes convert `{low, high}` Neo4j Integer objects to plain numbers; clamp negative/NaN `limit` params

### Incremental Indexer (`src/indexer/incremental_indexer.py`)
- Compares file `mtime` against Neo4j `indexed_at` timestamp — only indexes new or modified files
- SessionStart hook auto-runs incremental index in background on every session start
- `index_codebase` MCP tool accepts `full` parameter: `False` (default) for incremental, `True` for full re-index

### Language Support (`src/code_indexer/`)
- **15 languages:** Python, JavaScript, TypeScript, TSX, JSX, Go, Rust, Java, C, C++, C#, Ruby, PHP, Kotlin, Swift
- tree-sitter grammars loaded dynamically per file extension

### SSE Realtime Architecture
```
MCP Server (Python) --HTTP POST--> /api/notify --> EventBus --> /api/events (SSE) --> useEventSource hook --> page refetch
```
- Fire-and-forget: MCP server silently catches errors (dashboard may not be running)
- `DASHBOARD_URL` configurable via `src/config.py` Settings (default: `http://localhost:3001`)

### Fulltext Indexes (auto-created by `neo4j_ingestor.py`)
- `session_search` — SessionEvent: branch, summary
- `code_file_search` — CodeFile: path
- `code_function_search` — CodeFunction: name
- `entity_name` — Entity: name (created by Graphiti)

## Infrastructure
- Neo4j 5.26 via Docker Compose (ports 7474/7687)
- Dashboard via Docker Compose (port 3001 → 3000 internal)
- 24 range indices + 7 fulltext indices (4 Graphiti + 3 custom)
- Persistent Docker volumes for data/logs
- CLI backup/restore scripts: `scripts/backup.sh`, `scripts/restore.sh`

## Setup & Portability
- **One-click installers:** `setup.bat` (Windows) / `setup.sh` (Unix) — installs deps, creates .env, starts Neo4j
- **`.mcp.json`** no longer contains hardcoded cwd — portable across machines
- **All path resolution is absolute** via `Path(__file__).resolve()` — no CWD dependency
- **Neo4j auto-start** eliminates manual `docker compose up` step
