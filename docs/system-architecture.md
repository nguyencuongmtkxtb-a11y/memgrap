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
- **Pages:** Graph Explorer (react-force-graph-2d), Sessions, Code Index, Stats
- **API routes (8):** viz, nodes, nodes/[id], edges, sessions, sessions/[id], code/files, stats
- **Components:** sidebar, graph-viewer, node-detail, code-tree, session-list, stat-cards, error-banner
- **UI:** shadcn/ui v4 + Tailwind CSS v4, dark mode only
- **Neo4j client:** `lib/neo4j.ts` — singleton driver, session-per-query, Integer handling

## Infrastructure
- Neo4j 5.26 via Docker Compose (ports 7474/7687)
- Dashboard via Docker Compose (port 3001 → 3000 internal)
- 24 range indices + 4 fulltext indices (auto-created by Graphiti)
- Persistent Docker volumes for data/logs

## Setup & Portability
- **One-click installers:** `setup.bat` (Windows) / `setup.sh` (Unix) — installs deps, creates .env, starts Neo4j
- **`.mcp.json`** no longer contains hardcoded cwd — portable across machines
- **All path resolution is absolute** via `Path(__file__).resolve()` — no CWD dependency
- **Neo4j auto-start** eliminates manual `docker compose up` step
