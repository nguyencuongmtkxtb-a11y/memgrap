# Phase 5 — Reorganize Integration Tests

**Priority**: Medium | **Status**: Pending | **Deps**: Phase 1

## Overview
Move existing 3 integration test files into `tests/integration/` and add `@pytest.mark.integration` marker.

## Implementation Steps

1. Create `tests/integration/` directory with `__init__.py`
2. Move files:
   - `tests/test_neo4j_connect.py` → `tests/integration/test_neo4j_connect.py`
   - `tests/test_session_save.py` → `tests/integration/test_session_save.py`
   - `tests/test_session_recall.py` → `tests/integration/test_session_recall.py`
3. Add `pytestmark = pytest.mark.integration` at top of each file
4. Verify: `pytest -m integration -v` runs all 6 integration tests
5. Verify: `pytest -m "not integration" -v` runs only unit tests

## Files to Move
- 3 test files → `tests/integration/`

## Files to Create
- `tests/integration/__init__.py`

## Success Criteria
- `pytest -m integration` runs 6 tests (requires Neo4j)
- `pytest -m "not integration"` runs only unit tests
- No test files remain in `tests/` root (except conftest.py and __init__.py)
