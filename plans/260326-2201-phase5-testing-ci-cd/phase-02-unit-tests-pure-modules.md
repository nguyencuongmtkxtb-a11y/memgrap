# Phase 2 — Unit Tests: Pure Modules

**Priority**: High | **Status**: Pending | **Deps**: Phase 1

## Overview
Test `result_formatters.py` and `config.py` — pure functions/classes, no mocks needed.

## Implementation Steps

### `tests/unit/test_result_formatters.py`
1. `test_format_edge_complete` — all fields present
2. `test_format_edge_null_timestamps` — valid_at/invalid_at None
3. `test_format_node_with_summary_and_labels` — full node
4. `test_format_node_without_summary` — no summary attr
5. `test_format_episode_truncates_content` — content > 200 chars truncated
6. `test_format_episode_empty_content` — empty string
7. `test_format_episode_none_content` — content is None → returns ""

### `tests/unit/test_config.py`
1. `test_default_settings_values` — verify all defaults match expected
2. `test_env_override` — monkeypatch env vars, verify Settings picks them up
3. `test_get_settings_cached` — calling twice returns same instance

## Files to Create
- `tests/unit/test_result_formatters.py`
- `tests/unit/test_config.py`

## Success Criteria
- `pytest tests/unit/test_result_formatters.py tests/unit/test_config.py -v` all pass
- No external deps needed
