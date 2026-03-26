# Phase 3 — Unit Tests: GraphService + MCP Tools

**Priority**: High | **Status**: Pending | **Deps**: Phase 1

## Overview
Test `graph_service.py` and `mcp_server.py` tool functions with mocked Graphiti/Neo4j.

## Implementation Steps

### `tests/unit/test_graph_service.py`
Mock: `create_graphiti`, `subprocess.run`, `shutil.which`, `asyncio.sleep`

1. `test_initialize_idempotent` — second call skips init
2. `test_initialize_retries_on_failure` — mock build_indices to fail then succeed
3. `test_initialize_raises_after_max_retries` — all attempts fail → RuntimeError
4. `test_ensure_neo4j_container_skips_no_docker` — shutil.which returns None
5. `test_ensure_neo4j_container_skips_already_running` — subprocess returns "running"
6. `test_add_memory_returns_summary` — mock add_episode result
7. `test_recall_returns_formatted_edges` — mock search result
8. `test_search_nodes_returns_formatted` — mock search_ result
9. `test_get_status_healthy` — mock retrieve_episodes success
10. `test_get_status_error` — mock retrieve_episodes raises

### `tests/unit/test_mcp_tools.py`
Mock: `graph_service` module-level instance, `_ensure_init`

1. `test_remember_success` — returns "Stored. Extracted..." string
2. `test_remember_error` — exception → "Error storing memory: ..."
3. `test_recall_empty` — [] → "No relevant memories found."
4. `test_recall_with_results` — returns JSON string
5. `test_understand_code_empty` — "No code entities found."
6. `test_understand_code_with_results` — returns JSON string
7. `test_get_history_empty` — "No memory history found."
8. `test_get_history_with_results` — returns JSON string
9. `test_search_facts_empty` — "No facts found."
10. `test_search_facts_with_results` — JSON string
11. `test_index_codebase_incremental` — calls run_incremental_index
12. `test_index_codebase_full` — calls parse_directory + CodeIndexer
13. `test_index_codebase_extension_parsing` — ".py,.js" → {".py", ".js"}
14. `test_get_status_returns_json` — formatted JSON
15. `test_ensure_init_no_api_key` — raises RuntimeError

## Files to Create
- `tests/unit/test_graph_service.py`
- `tests/unit/test_mcp_tools.py`

## Success Criteria
- All tests pass with `pytest tests/unit/test_graph_service.py tests/unit/test_mcp_tools.py -v`
- No real Neo4j/OpenAI/Graphiti connections
