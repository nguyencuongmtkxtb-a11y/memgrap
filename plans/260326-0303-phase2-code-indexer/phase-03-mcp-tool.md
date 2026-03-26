# Phase 3: MCP Tool `index_codebase`

## Overview
- **Priority:** High
- **Status:** Pending
- **Description:** MCP tool cho Claude Code trigger indexing

## Requirements
### Functional
- `index_codebase(path, extensions?)` — scan, parse, ingest
- Default extensions: .py, .js, .ts, .tsx, .jsx
- Ignore: __pycache__, node_modules, .git, .venv, dist, build
- Return summary: files scanned, symbols found, nodes created

### Non-functional
- Progress logging to stderr
- mcp_server.py đã 192L → tách tools ra module riêng

## Architecture
```
src/mcp-tools/           — new package for tool handlers
  __init__.py
  indexer-tools.py       — index_codebase tool handler
src/mcp_server.py        — register tools from mcp-tools/
```

## Implementation Steps
1. Create `src/mcp-tools/` package
2. Move index_codebase logic to `src/mcp-tools/indexer-tools.py`
3. Wire: parse_directory() → CodeIndexer.index_symbols()
4. Register tool in mcp_server.py (thin import + @mcp.tool)
5. Test end-to-end: call index_codebase("D:/MEMGRAP") → check Neo4j

## Success Criteria
- Claude Code gọi `index_codebase("D:/MEMGRAP")` → graph có code entities
- __pycache__, .git skipped
- Summary response cho biết số files + symbols
