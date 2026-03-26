# Phase 2: Code Indexer

Auto-parse codebase files → extract code entities + relationships → write directly to Neo4j.

## Phases

| # | Phase | Status |
|---|-------|--------|
| 1 | [AST Parser module](phase-01-ast-parser.md) | Pending |
| 2 | [Neo4j direct ingestion](phase-02-neo4j-ingestion.md) | Pending |
| 3 | [MCP tool `index_codebase`](phase-03-mcp-tool.md) | Pending |

## Key Decisions
- **Neo4j direct** (Cypher) instead of Graphiti add_episode() — deterministic, no OpenAI cost, fast
- **Individual grammar packages** over language-pack — leaner, only Python/JS/TS
- **CONTAINS + IMPORTS only** — CALLS/INHERITS deferred (need static analysis beyond AST)
- **Phase 4 (file watcher) dropped** — YAGNI, manual re-index via MCP tool is sufficient
- **Tách MCP tools** ra module riêng khi mcp_server.py vượt limit

## Dependencies
- tree-sitter + language grammars (Python, JS, TS)
- Neo4j driver (already available via Graphiti)
- Existing GraphService for Neo4j connection
