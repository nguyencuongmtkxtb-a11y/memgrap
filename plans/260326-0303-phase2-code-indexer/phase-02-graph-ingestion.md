# Phase 2: Entity Types + Graph Ingestion

## Overview
- **Priority:** High
- **Status:** Pending
- **Description:** New entity/edge types for code symbols, ingestion service to feed parsed AST into Graphiti

## Requirements
### Functional
- New entity types: CodeFile, Function, Class, Module, Import
- New relationship types: CONTAINS, CALLS, IMPORTS, INHERITS
- Batch ingest parsed symbols into graph via GraphService
- Deduplicate — re-indexing same file updates existing nodes, not duplicates

### Non-functional
- Batch episodes to minimize OpenAI API calls
- Group code entities under separate group_id (e.g. "code_index")

## Architecture
```
src/entity_types.py          — add new code entity types
src/indexer/graph-ingestor.py — convert CodeSymbols → Graphiti episodes
```

## Related Code Files
- Modify: `src/entity_types.py`
- Create: `src/indexer/graph-ingestor.py`

## Implementation Steps
1. Add CodeFile, Function, Class, Module, Import to entity_types.py
2. Create CODE_ENTITY_TYPES registry (separate from conversation entities)
3. Build ingestor: CodeSymbol[] → structured episode text → add_episode()
4. Batch symbols per file (1 episode per file, listing all symbols)
5. Handle re-indexing: clear old file data before re-ingesting

## Todo
- [ ] New entity types in entity_types.py
- [ ] CODE_ENTITY_TYPES registry
- [ ] graph-ingestor.py
- [ ] Batch episode strategy
- [ ] Re-index dedup logic

## Success Criteria
- After indexing, `understand_code("parse_file")` returns the Function entity
- Re-indexing same file doesn't create duplicates
