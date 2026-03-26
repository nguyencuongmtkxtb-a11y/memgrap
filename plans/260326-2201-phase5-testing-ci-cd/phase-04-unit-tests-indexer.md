# Phase 4 — Unit Tests: Indexer Modules

**Priority**: High | **Status**: Pending | **Deps**: Phase 1

## Overview
Test `ast_parser.py`, `neo4j_ingestor.py`, `incremental_indexer.py`. AST parser uses real parsing on fixture files; others mock Neo4j driver.

## Implementation Steps

### `tests/unit/test_ast_parser.py`
Uses fixture files from `tests/fixtures/`. No mocks — real tree-sitter parsing.

1. `test_parse_python_file` — sample.py → finds functions, classes, imports
2. `test_parse_js_file` — sample.js → finds functions, imports
3. `test_parse_ts_file` — sample.ts → finds classes, functions, imports
4. `test_parse_unsupported_extension` — .txt → empty list
5. `test_parse_nonexistent_file` — bad path → empty list
6. `test_find_parent_scope_nested` — method inside class has parent
7. `test_extract_import_name_truncation` — import > 100 chars truncated
8. `test_parse_directory` — walks fixture dir, finds symbols across files
9. `test_parse_directory_ignores_dirs` — __pycache__ skipped

### `tests/unit/test_neo4j_ingestor.py`
Mock: `Neo4jDriver.execute_query`

1. `test_index_symbols_empty` — empty list → zero stats
2. `test_index_symbols_groups_by_file` — 2 files → 2 clear_file calls
3. `test_clear_file_query` — verify Cypher contains DETACH DELETE
4. `test_upsert_functions_batch` — verify UNWIND in query
5. `test_upsert_classes_batch` — verify MERGE CodeClass
6. `test_upsert_imports_batch` — verify MERGE CodeImport

### `tests/unit/test_incremental_indexer.py`
Mock: `Neo4jDriver`, filesystem via tmp_path

1. `test_collect_files_finds_matching` — tmp dir with .py files → found
2. `test_collect_files_skips_ignored_dirs` — node_modules skipped
3. `test_needs_reindex_new_file` — None indexed_at → True
4. `test_needs_reindex_modified` — mtime > indexed_at → True
5. `test_needs_reindex_unchanged` — mtime < indexed_at → False
6. `test_run_incremental_no_changes` — all files up to date → skipped count
7. `test_run_incremental_indexes_changed` — mock driver, verify indexer called

## Files to Create
- `tests/unit/test_ast_parser.py`
- `tests/unit/test_neo4j_ingestor.py`
- `tests/unit/test_incremental_indexer.py`

## Success Criteria
- All pass with `pytest tests/unit/test_ast_parser.py tests/unit/test_neo4j_ingestor.py tests/unit/test_incremental_indexer.py -v`
- ast_parser tests use real tree-sitter, no mocks
- ingestor/indexer tests use only mocked Neo4j driver
