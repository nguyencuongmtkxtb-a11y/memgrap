# Phase 2: Neo4j Direct Ingestion

## Overview
- **Priority:** High
- **Status:** Pending
- **Description:** Write parsed CodeSymbols directly to Neo4j via Cypher — bypass Graphiti LLM extraction

## Why Neo4j Direct (not Graphiti add_episode)
- AST already gives deterministic, structured data — LLM extraction is redundant
- 500 files × add_episode() = 500 OpenAI API calls = slow + expensive
- Direct Cypher gives full control over node labels, relationships, dedup

## Requirements
### Functional
- Node labels: `CodeFile`, `Function`, `Class`, `Import`
- Relationships: `CONTAINS` (file→symbol), `IMPORTS` (file→module)
- Properties: name, file_path, line, language, indexed_at
- MERGE-based upsert — re-indexing updates, not duplicates
- Clear stale symbols when file is re-indexed

### Non-functional
- Batch Cypher queries (UNWIND) for performance
- Separate from Graphiti's graph namespace (label prefix or property tag)

## Architecture
```
src/indexer/neo4j-ingestor.py
  - CodeIndexer class
    - __init__(driver) — takes Neo4j driver from Graphiti
    - index_symbols(symbols: list[CodeSymbol]) → stats dict
    - clear_file(file_path) → remove old symbols for file
    - _batch_upsert(symbols) — MERGE via UNWIND
```

## Access Neo4j Driver
```python
# Graphiti exposes driver via internal attribute
driver = graph_service.graphiti.driver
```

## Cypher Pattern
```cypher
// Upsert file node
MERGE (f:CodeFile {path: $path})
SET f.language = $lang, f.indexed_at = datetime()

// Upsert function contained in file
UNWIND $functions AS func
MERGE (fn:Function {name: func.name, file_path: func.file_path})
SET fn.line = func.line, fn.parent = func.parent
MERGE (f)-[:CONTAINS]->(fn)
```

## Implementation Steps
1. Create `src/indexer/neo4j-ingestor.py`
2. Get Neo4j driver from Graphiti instance
3. Implement clear_file() — delete old nodes for a file path
4. Implement _batch_upsert() — MERGE CodeFile + Function/Class/Import nodes
5. Implement IMPORTS relationships (file → imported module)
6. Test: index memgrap src/ → verify nodes in Neo4j browser

## Success Criteria
- After indexing, Neo4j browser shows CodeFile/Function/Class/Import nodes
- Re-index same file → no duplicates, updated timestamps
- `understand_code("parse_file")` can find indexed functions (via existing search)
