# Phase 6 — GitHub Actions CI

**Priority**: High | **Status**: Pending | **Deps**: Phase 2, 3, 4

## Overview
Create `.github/workflows/ci.yml` with two parallel jobs: Python (ruff + pytest unit) and Dashboard (eslint + jest).

## Implementation Steps

1. Create `.github/workflows/ci.yml`
2. Python job:
   - `actions/checkout@v4`
   - `actions/setup-python@v5` with python 3.11
   - `pip install -e ".[dev]" ruff`
   - `ruff check src/ tests/`
   - `pytest -m "not integration" --tb=short`
3. Dashboard job:
   - `actions/checkout@v4`
   - `actions/setup-node@v4` with node 20
   - `npm ci` in dashboard/
   - `npm run lint`
   - `npm test -- --forceExit`
4. Trigger: push + pull_request

## Files to Create
- `.github/workflows/ci.yml`

## Success Criteria
- Both jobs pass locally via `act` or on GitHub push
- Total CI time < 3 minutes
