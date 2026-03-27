"""Unit tests for src.code_graph_service — CodeGraphService Neo4j queries."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.config import Settings
from src.code_graph_service import CodeGraphService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_settings(**overrides) -> Settings:
    defaults = {
        "neo4j_uri": "bolt://localhost:7687",
        "neo4j_user": "neo4j",
        "neo4j_password": "password",
        "openai_api_key": "sk-test",
        "llm_model": "gpt-4o-mini",
        "llm_small_model": "gpt-4o-mini",
        "embedding_model": "text-embedding-3-small",
        "group_id": "test-group",
        "semaphore_limit": 5,
    }
    defaults.update(overrides)
    return Settings(_env_file=None, **defaults)


def _make_service_with_mock_driver():
    """Create CodeGraphService with a mocked async driver."""
    svc = CodeGraphService(_make_settings())
    mock_driver = AsyncMock()
    svc._driver = mock_driver
    return svc, mock_driver


def _mock_session_run(mock_driver, data: list[dict]):
    """Configure mock driver session to return given data."""
    mock_result = AsyncMock()
    mock_result.data = AsyncMock(return_value=data)
    mock_session = AsyncMock()
    mock_session.run = AsyncMock(return_value=mock_result)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)
    mock_driver.session = MagicMock(return_value=mock_session)
    return mock_session


# ---------------------------------------------------------------------------
# _ensure_driver
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ensure_driver_creates_driver():
    """_ensure_driver creates async driver when None."""
    svc = CodeGraphService(_make_settings())
    assert svc._driver is None

    with patch("src.code_graph_service.AsyncGraphDatabase") as mock_agdb:
        mock_agdb.driver = MagicMock(return_value=AsyncMock())
        await svc._ensure_driver()
        mock_agdb.driver.assert_called_once()
        assert svc._driver is not None


@pytest.mark.asyncio
async def test_ensure_driver_idempotent():
    """_ensure_driver is a no-op when driver already exists."""
    svc, mock_driver = _make_service_with_mock_driver()
    with patch("src.code_graph_service.AsyncGraphDatabase") as mock_agdb:
        await svc._ensure_driver()
        mock_agdb.driver.assert_not_called()


# ---------------------------------------------------------------------------
# close
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_close_clears_driver():
    """close() closes driver and sets it to None."""
    svc, mock_driver = _make_service_with_mock_driver()
    await svc.close()
    mock_driver.close.assert_awaited_once()
    assert svc._driver is None


@pytest.mark.asyncio
async def test_close_noop_when_no_driver():
    """close() is a no-op when driver is None."""
    svc = CodeGraphService(_make_settings())
    await svc.close()  # Should not raise


# ---------------------------------------------------------------------------
# find_callers
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_find_callers_returns_data():
    """find_callers returns list of caller dicts."""
    svc, mock_driver = _make_service_with_mock_driver()
    expected = [{"caller": "main", "caller_file": "src/main.py", "caller_line": 5}]
    _mock_session_run(mock_driver, expected)

    result = await svc.find_callers("helper")
    assert result == expected


@pytest.mark.asyncio
async def test_find_callers_empty():
    """find_callers returns empty list when no callers."""
    svc, mock_driver = _make_service_with_mock_driver()
    _mock_session_run(mock_driver, [])

    result = await svc.find_callers("orphan_func")
    assert result == []


@pytest.mark.asyncio
async def test_find_callers_with_project():
    """find_callers passes project param to query."""
    svc, mock_driver = _make_service_with_mock_driver()
    mock_session = _mock_session_run(mock_driver, [])

    await svc.find_callers("func", project="myproject")
    mock_session.run.assert_awaited_once()
    # _run passes params dict as second positional arg: session.run(query, params)
    call_args = mock_session.run.call_args[0]
    params_dict = call_args[1]  # second positional arg is the params dict
    assert params_dict["project"] == "myproject"


# ---------------------------------------------------------------------------
# find_callees
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_find_callees_returns_data():
    """find_callees returns list of callee dicts."""
    svc, mock_driver = _make_service_with_mock_driver()
    expected = [{"callee": "process", "callee_file": "src/proc.py"}]
    _mock_session_run(mock_driver, expected)

    result = await svc.find_callees("main")
    assert result == expected


@pytest.mark.asyncio
async def test_find_callees_empty():
    """find_callees returns empty list when no callees."""
    svc, mock_driver = _make_service_with_mock_driver()
    _mock_session_run(mock_driver, [])

    result = await svc.find_callees("leaf_func")
    assert result == []


# ---------------------------------------------------------------------------
# find_class_hierarchy
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_find_class_hierarchy_returns_data():
    """find_class_hierarchy returns parents and children."""
    svc, mock_driver = _make_service_with_mock_driver()
    expected = [{"children": [{"child": "Dog"}], "parents": [{"parent": "Animal"}]}]
    _mock_session_run(mock_driver, expected)

    result = await svc.find_class_hierarchy("Pet")
    assert result == expected


@pytest.mark.asyncio
async def test_find_class_hierarchy_empty():
    """find_class_hierarchy returns empty list for unknown class."""
    svc, mock_driver = _make_service_with_mock_driver()
    _mock_session_run(mock_driver, [])

    result = await svc.find_class_hierarchy("NonExistentClass")
    assert result == []


# ---------------------------------------------------------------------------
# find_file_imports
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_find_file_imports_returns_data():
    """find_file_imports returns imports and imported_by."""
    svc, mock_driver = _make_service_with_mock_driver()
    expected = [{"imports": [{"imports": "utils.py"}], "imported_by": []}]
    _mock_session_run(mock_driver, expected)

    result = await svc.find_file_imports("main.py")
    assert result == expected


# ---------------------------------------------------------------------------
# search_code
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_search_code_returns_data():
    """search_code returns matching symbols."""
    svc, mock_driver = _make_service_with_mock_driver()
    expected = [{"type": "function", "name": "parse_file", "file_path": "src/parser.py"}]
    _mock_session_run(mock_driver, expected)

    result = await svc.search_code("parse")
    assert result == expected


@pytest.mark.asyncio
async def test_search_code_with_limit():
    """search_code passes limit param to query."""
    svc, mock_driver = _make_service_with_mock_driver()
    mock_session = _mock_session_run(mock_driver, [])

    await svc.search_code("test", limit=5)
    # _run passes params dict as second positional arg: session.run(query, params)
    call_args = mock_session.run.call_args[0]
    params_dict = call_args[1]
    assert params_dict["limit"] == 5


@pytest.mark.asyncio
async def test_search_code_empty():
    """search_code returns empty list when no matches."""
    svc, mock_driver = _make_service_with_mock_driver()
    _mock_session_run(mock_driver, [])

    result = await svc.search_code("zzz_no_match")
    assert result == []
