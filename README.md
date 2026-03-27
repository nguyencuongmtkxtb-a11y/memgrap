# Memgrap

Persistent memory system for [Claude Code](https://docs.anthropic.com/en/docs/claude-code), powered by a temporal knowledge graph. Claude Code loses context between sessions — Memgrap fixes that by storing decisions, code patterns, and project context in a searchable graph database that survives across conversations.

Built on [Graphiti Core](https://github.com/getzep/graphiti) + Neo4j. Facts track **when** they became true and **when** they were superseded — so the graph knows how your project evolved over time, not just its current state.

## What It Does

```
You: "We chose PostgreSQL because of JSONB support for flexible schemas"
     ↓ remember()
Memgrap extracts entities (PostgreSQL, Project) + facts (chose PostgreSQL, reason: JSONB)
     ↓
Next session, different conversation:
You: "What database did we pick and why?"
     ↓ recall()
Memgrap: "PostgreSQL — chosen for JSONB support for flexible schemas" (with timestamp)
```

**12 MCP tools** exposed to Claude Code — 7 for memory, 5 for code intelligence:

| Tool | Cost | What it does |
|------|------|--------------|
| `remember` | OpenAI | Store decisions, patterns, context into knowledge graph |
| `recall` | OpenAI | Semantic search across memories (hybrid: BM25 + cosine + graph) |
| `understand_code` | OpenAI | Search code-related entities (patterns, tools, libraries) |
| `get_history` | OpenAI | Timeline of stored memories |
| `search_facts` | OpenAI | Find relationships with temporal validity |
| `consolidate_memory` | Free* | Clean duplicates, stale facts, orphans (*AI mode costs tokens) |
| `get_status` | Free | Health check |
| `index_codebase` | Free | Parse source files with tree-sitter, write to Neo4j |
| `find_callers` | Free | Impact analysis — who calls this function? |
| `find_callees` | Free | Execution flow — what does this function call? |
| `find_class_hierarchy` | Free | Inheritance tree for a class |
| `find_file_imports` | Free | Module dependency graph |
| `search_code` | Free | Search functions/classes/files by name |

## Architecture

```
Claude Code ──stdio──▸ MCP Server (FastMCP)
                           │
                     ┌─────┴─────┐
                     ▼           ▼
              Graphiti Core    Code Graph
              (memory tools)   (code tools)
                     │           │
                     ▼           ▼
                   Neo4j 5.26 (Docker)
                     │
              OpenAI gpt-4o-mini
              + text-embedding-3-small

Dashboard (Next.js 16) ──bolt──▸ Neo4j
```

**Key design choices:**
- **stdio transport** — MCP server spawned as subprocess by Claude Code, zero network config
- **Lazy init** — Neo4j connects on first tool call, not on import
- **Auto-start Neo4j** — if Docker container isn't running, starts it automatically
- **Cross-project** — one Neo4j instance, data isolated per project via `group_id`
- **Zero-cost code tools** — 5 code graph tools query Neo4j directly, no OpenAI calls

## Quick Start

### One-Click Setup

```bash
# Windows
setup.bat

# Linux / macOS
./setup.sh
```

The setup script validates Python 3.10+, Docker, installs dependencies, creates `.env`, starts Neo4j, and configures MCP globally.

### Manual Setup

```bash
# 1. Clone & install
git clone https://github.com/nguyencuongmtkxtb-a11y/MEMGRAP.git
cd MEMGRAP
pip install -e .

# 2. Configure
cp .env.example .env
# Edit .env — add your OPENAI_API_KEY

# 3. Start Neo4j
docker compose up -d neo4j

# 4. Restart Claude Code — MCP auto-loads from .mcp.json
```

### Dashboard (Optional)

```bash
docker compose up -d dashboard
# Open http://localhost:3001
```

4 pages: Graph Explorer, Sessions, Code Index, Code Graph — plus fulltext search, realtime SSE updates, and JSON export/import.

## Code Indexer

Parses source files with [tree-sitter](https://tree-sitter.github.io/tree-sitter/), extracts functions/classes/imports, and writes them to Neo4j — **zero OpenAI cost**.

**15 languages supported:** Python, JavaScript, TypeScript, JSX, TSX, Go, Rust, Java, C, C++, C#, Ruby, PHP, Kotlin, Swift

**What it extracts:**
- `CodeFile` — path, language, line count
- `CodeFunction` — name, signature, line range
- `CodeClass` — name, line range
- `CodeImport` — source module
- Edges: `CALLS`, `EXTENDS`, `IMPORTS_FROM`

**Incremental by default** — only re-indexes files that changed since last run (mtime comparison). Auto-runs in background on every Claude Code session start via hooks.

## Session Hooks

Auto-captures git context on session boundaries:

- **Session start:** branch, HEAD commit, uncommitted changes, recent commits → injected into Claude's system message
- **Session end:** commits made, files changed, summary → stored as `SessionEvent` node in Neo4j

Installed at `~/.claude/hooks/memgrap-session-{start,end}.cjs`. Works across all projects.

## Memory Consolidation

Automatic cleanup runs on first MCP init (zero cost):

1. **Merge duplicate entities** — same name + same project
2. **Remove stale facts** — superseded by newer facts
3. **Detect orphan entities** — no relationships
4. **Prune old episodes** — older than 30 days
5. **Deduplicate facts** — same entity pair + relation type

Optional AI-powered Phase 6 (`consolidate_memory(use_ai=True)`): semantic dedup, conflict resolution, fact summarization via OpenAI.

## Project Structure

```
src/
├── mcp_server.py              # FastMCP server, 12 tools
├── graph_service.py            # Graphiti Core wrapper
├── code_graph_service.py       # Direct Neo4j code queries
├── config.py                   # pydantic-settings config
├── entity_types.py             # 8 Pydantic entity models
├── indexer/                    # Code indexing pipeline
│   ├── ast_parser.py           # tree-sitter parsing
│   ├── incremental_indexer.py  # Mtime-based diffing
│   ├── relation_extractor.py   # Call/extend/import extraction
│   ├── import_resolver.py      # Module path resolution
│   ├── neo4j_ingestor.py       # Batch Neo4j writes
│   └── language_configs.py     # tree-sitter queries (15 langs)
└── session/                    # Git context capture
    ├── session_save.py
    ├── session_recall.py
    └── neo4j_connect.py

dashboard/                      # Next.js 16 + shadcn/ui v4
├── app/                        # 6 pages, 16 API routes
├── components/                 # 13 React components
└── Dockerfile                  # Multi-stage build

tests/                          # 84 tests (unit + integration)
scripts/                        # Backup/restore utilities
```

## Configuration

All config via `.env` file:

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENAI_API_KEY` | — | **Required.** OpenAI API key for LLM extraction + embeddings |
| `NEO4J_URI` | `bolt://localhost:7687` | Neo4j connection URI |
| `NEO4J_USER` | `neo4j` | Neo4j username |
| `NEO4J_PASSWORD` | `password` | Neo4j password |
| `LLM_MODEL` | `gpt-4o-mini` | Model for entity extraction |
| `EMBEDDING_MODEL` | `text-embedding-3-small` | Model for semantic search |
| `DASHBOARD_URL` | `http://localhost:3001` | Dashboard URL for SSE notifications |

## Backup & Restore

```bash
# Backup
scripts/backup.sh    # or backup.bat on Windows

# Restore
scripts/restore.sh   # or restore.bat on Windows
```

## Testing

```bash
# Unit tests
pytest tests/unit/

# Integration tests (requires running Neo4j)
pytest tests/integration/

# All tests
pytest
```

## License

MIT
