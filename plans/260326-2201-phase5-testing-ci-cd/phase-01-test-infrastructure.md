# Phase 1 — Test Infrastructure Setup

**Priority**: High | **Status**: Pending

## Overview
Configure pytest markers, conftest, ruff linter, and pyproject.toml updates before writing any tests.

## Implementation Steps

1. Update `pyproject.toml`:
   - Add `ruff` to dev deps
   - Add `asyncio_mode = "auto"` to pytest config
   - Add `markers = ["integration: requires running Neo4j instance"]`
   - Add `[tool.ruff]` section (target py310, line-length 120, select E/F/I)

2. Create `tests/conftest.py`:
   - Register `integration` marker
   - Autouse fixture: `get_settings.cache_clear()` after each test (isolation)
   - Shared fixtures (mock settings, mock graphiti)

3. Create `tests/unit/` directory (empty `__init__.py`)

4. Create `tests/fixtures/` with sample source files:
   - `sample.py` — Python with function, class, import
   - `sample.js` — JS with function, import
   - `sample.ts` — TS with class, function, import

5. Verify: `ruff check src/ tests/` passes (fix any lint issues)

## Files to Create
- `tests/conftest.py`
- `tests/unit/__init__.py`
- `tests/fixtures/sample.py`
- `tests/fixtures/sample.js`
- `tests/fixtures/sample.ts`

## Files to Modify
- `pyproject.toml`

## Success Criteria
- `pytest --collect-only` discovers test structure
- `ruff check src/ tests/` exits 0
