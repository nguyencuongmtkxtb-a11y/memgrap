# Phase 5 — Testing & CI/CD Design

## Overview

Add comprehensive unit tests for Python MCP server + indexer modules, reorganize existing integration tests, and create GitHub Actions CI pipeline running lint + unit tests.

## Decisions

- **Test strategy**: Unit tests (mocked deps) + integration tests (real Neo4j, local only)
- **CI scope**: Lint + unit tests only (no Docker service in CI)
- **Python linter**: ruff (fast, comprehensive)
- **Mocking**: stdlib `unittest.mock` (no extra deps)
- **pytest markers**: `@pytest.mark.integration` to separate test tiers

## Test Structure

```
tests/
├── conftest.py                    # shared fixtures, marker registration
├── unit/
│   ├── test_result_formatters.py  # pure functions, no mocks needed
│   ├── test_config.py             # defaults, env override
│   ├── test_graph_service.py      # mock Graphiti + subprocess
│   ├── test_mcp_tools.py          # mock GraphService, test tool return strings
│   ├── test_ast_parser.py         # real parsing on temp sample files
│   ├── test_neo4j_ingestor.py     # mock Neo4jDriver.execute_query
│   └── test_incremental_indexer.py # mock Neo4j + filesystem
├── integration/                   # existing tests moved here
│   ├── test_neo4j_connect.py
│   ├── test_session_save.py
│   └── test_session_recall.py
└── fixtures/                      # sample source files for ast_parser tests
    ├── sample.py
    ├── sample.js
    └── sample.ts
```

## Unit Test Coverage Plan

### `test_result_formatters.py`
- `format_edge`: valid edge → correct dict keys/values
- `format_edge`: missing `valid_at`/`invalid_at` → None
- `format_node`: node with/without summary/labels
- `format_episode`: content truncation at 200 chars

### `test_config.py`
- Default values for all settings fields
- Environment variable override (monkeypatch)

### `test_graph_service.py`
- `initialize()`: idempotent (second call is no-op)
- `initialize()`: retry logic on Neo4j failure (mock sleep)
- `initialize()`: raises RuntimeError after max retries
- `_ensure_neo4j_container()`: skips when Docker not on PATH
- `_ensure_neo4j_container()`: skips when container already running
- `add_memory()`: correct args passed to Graphiti
- `recall()`: returns formatted edges
- `search_nodes()`: returns formatted nodes
- `get_status()`: healthy response
- `get_status()`: error response on exception

### `test_mcp_tools.py`
- `remember()`: success response format
- `remember()`: error handling
- `recall()`: empty results → "No relevant memories found."
- `recall()`: non-empty results → JSON string
- `understand_code()`: empty/non-empty cases
- `get_history()`: empty/non-empty cases
- `search_facts()`: empty/non-empty cases
- `index_codebase()`: full mode flow
- `index_codebase()`: incremental mode flow
- `index_codebase()`: extension parsing
- `get_status()`: returns formatted JSON
- `_ensure_init()`: raises on missing OpenAI key

### `test_ast_parser.py`
- `parse_file()`: Python file → functions, classes, imports
- `parse_file()`: JS/TS file → functions, classes, imports
- `parse_file()`: unsupported extension → empty list
- `parse_file()`: unreadable file → empty list
- `_find_parent_scope()`: nested function in class
- `_extract_import_name()`: long import truncation
- `parse_directory()`: walks dirs, skips ignored dirs

### `test_neo4j_ingestor.py`
- `clear_file()`: correct Cypher query
- `index_symbols()`: empty list → zero stats
- `index_symbols()`: groups by file, calls clear + upsert
- `_upsert_functions()`: batch Cypher with UNWIND
- `_upsert_classes()`: batch Cypher
- `_upsert_imports()`: batch Cypher

### `test_incremental_indexer.py`
- `_collect_files()`: finds matching files, skips ignored dirs
- `_needs_reindex()`: new file (no indexed_at) → True
- `_needs_reindex()`: file modified after index → True
- `_needs_reindex()`: file unchanged → False
- `run_incremental_index()`: skips when no changes
- `run_incremental_index()`: indexes only changed files

## Dashboard Tests

Existing 10 Jest test files cover API routes + components. Phase 5 will:
- Verify all existing tests pass
- Add missing tests only if critical gaps found during verification

## GitHub Actions CI

```yaml
# .github/workflows/ci.yml
name: CI
on: [push, pull_request]

jobs:
  python:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.11' }
      - run: pip install -e ".[dev]" ruff
      - run: ruff check src/ tests/
      - run: pytest -m "not integration" --tb=short

  dashboard:
    runs-on: ubuntu-latest
    defaults:
      run: { working-directory: dashboard }
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: '20' }
      - run: npm ci
      - run: npm run lint
      - run: npm test -- --forceExit
```

Two parallel jobs, ~2-3 min total.

## Dev Dependencies Changes

**Python (`pyproject.toml`):**
- Add `ruff` to `[project.optional-dependencies].dev`

**No new dashboard deps** — Jest + Testing Library already configured.

## pyproject.toml Updates

```toml
[tool.pytest.ini_options]
pythonpath = ["."]
asyncio_mode = "auto"
markers = ["integration: requires running Neo4j instance"]

[tool.ruff]
target-version = "py310"
line-length = 120

[tool.ruff.lint]
select = ["E", "F", "I"]
```

## Success Criteria

- All unit tests pass without external deps (no Neo4j, no OpenAI)
- Integration tests pass with local Neo4j
- `pytest -m "not integration"` runs in < 10s
- GitHub Actions CI green on push/PR
- ruff lint passes with zero errors
