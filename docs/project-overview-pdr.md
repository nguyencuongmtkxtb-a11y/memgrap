# Memgrap — Project Overview

## What
Temporal knowledge graph memory system for Claude Code, powered by Graphiti + Neo4j.

## Why
Claude Code loses context between sessions. Flat file memory (CLAUDE.md, MEMORY.md) lacks structure, relationships, and temporal tracking. Memgrap provides:
- Structured entity/relationship extraction from conversations
- Temporal fact tracking (valid_at/invalid_at)
- Hybrid semantic search (BM25 + cosine + graph traversal)
- MCP integration for seamless Claude Code access

## Architecture
```
Claude Code (stdio) --> MCP Server (FastMCP) --> Graphiti Core --> Neo4j (Docker)
                                                      |
                                              OpenAI API (LLM + embeddings)
```

## Tech Stack
- **Python 3.10+** (async)
- **Graphiti Core 0.28.2** — temporal knowledge graph engine
- **Neo4j 5.26** — graph database (Docker)
- **OpenAI gpt-4o-mini** — entity/relationship extraction
- **OpenAI text-embedding-3-small** — vector embeddings
- **FastMCP** — MCP server framework (stdio transport)
- **pydantic-settings** — config from .env

## Phases
| Phase | Description | Status |
|-------|-------------|--------|
| 1 | MCP Server — 7 tools (remember, recall, understand_code, etc.) | ✅ Done |
| 2 | Code Indexer — tree-sitter AST → Neo4j direct writes (zero OpenAI cost) | ✅ Done |
| 3 | Session Hooks — auto-capture git context on session start/end | ✅ Done |
| 4 | Dashboard UI — Next.js 16 + Neo4j graph explorer (4 pages, 8 API routes) | ✅ Done |

## MCP Tools (7)
| Tool | Purpose |
|------|---------|
| `remember` | Store info into knowledge graph |
| `recall` | Semantic search for relevant memories |
| `understand_code` | Search code entities (nodes) |
| `get_history` | Memory timeline |
| `search_facts` | Find relationships/facts |
| `index_codebase` | Parse + index source files (tree-sitter → Neo4j) |
| `get_status` | Health check |

## Dashboard (Phase 4)
- **Stack:** Next.js 16 + shadcn/ui v4 + Tailwind CSS v4 (dark mode)
- **Pages:** Graph Explorer (force-graph-2d), Sessions, Code Index, Stats
- **API routes:** 8 routes querying Neo4j via bolt protocol
- **Docker:** Multi-stage build, served on port 3001

## Stability & Portability (P0 Fixes)
- **Auto-start Neo4j** container on first tool call (Docker compose)
- **Retry with backoff** (3x) for Neo4j connection during init
- **OpenAI key validation** — clear error before Graphiti init
- **Absolute path resolution** everywhere — no CWD dependency
- **Dynamic hook paths** — no hardcoded `MEMGRAP_DIR` in CJS hooks
- **Portable `.mcp.json`** — removed hardcoded cwd
- **One-click setup** — `setup.bat` / `setup.sh` installers

## Entity Types
**Memory (8):** CodePattern, TechDecision, ProjectContext, Person, Tool, Concept, BugReport, Requirement
**Code Index (4):** CodeFile, CodeFunction, CodeClass, CodeImport
**Sessions:** SessionEvent (auto-captured by hooks)
