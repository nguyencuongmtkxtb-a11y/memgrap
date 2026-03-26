"""Unit tests for src.mcp_server — MCP tool functions."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _parse_json(text: str):
    """Parse JSON string, raise AssertionError with context on failure."""
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        raise AssertionError(f"Expected valid JSON, got: {text!r}") from e


# ---------------------------------------------------------------------------
# _ensure_init — missing API key
# ---------------------------------------------------------------------------


async def test_ensure_init_no_api_key():
    """_ensure_init raises RuntimeError when openai_api_key is empty."""
    with patch("src.mcp_server.settings") as mock_settings:
        mock_settings.openai_api_key = ""
        # Re-import to get a fresh reference to the function
        from src.mcp_server import _ensure_init

        with pytest.raises(RuntimeError, match="OPENAI_API_KEY is not set"):
            await _ensure_init()


# ---------------------------------------------------------------------------
# remember
# ---------------------------------------------------------------------------


@patch("src.mcp_server._ensure_init", new_callable=AsyncMock)
@patch("src.mcp_server.graph_service")
async def test_remember_success(mock_gs, mock_init):
    """remember() returns 'Stored. Extracted...' on success."""
    mock_gs.add_memory = AsyncMock(return_value={
        "nodes_count": 2,
        "edges_count": 1,
        "nodes": ["EntityA", "EntityB"],
        "facts": ["A relates to B"],
    })

    from src.mcp_server import remember
    result = await remember(content="test memory", source="test", name="ep1")

    assert result.startswith("Stored. Extracted 2 entities, 1 facts.")
    assert "EntityA" in result
    assert "A relates to B" in result
    mock_gs.add_memory.assert_awaited_once()


@patch("src.mcp_server._ensure_init", new_callable=AsyncMock)
@patch("src.mcp_server.graph_service")
async def test_remember_error(mock_gs, mock_init):
    """remember() returns 'Error storing memory: ...' on exception."""
    mock_gs.add_memory = AsyncMock(side_effect=RuntimeError("boom"))

    from src.mcp_server import remember
    result = await remember(content="fail")

    assert result.startswith("Error storing memory:")
    assert "boom" in result


# ---------------------------------------------------------------------------
# recall
# ---------------------------------------------------------------------------


@patch("src.mcp_server._ensure_init", new_callable=AsyncMock)
@patch("src.mcp_server.graph_service")
async def test_recall_empty(mock_gs, mock_init):
    """recall() returns 'No relevant memories found.' when results are empty."""
    mock_gs.recall = AsyncMock(return_value=[])

    from src.mcp_server import recall
    result = await recall(query="anything")

    assert result == "No relevant memories found."


@patch("src.mcp_server._ensure_init", new_callable=AsyncMock)
@patch("src.mcp_server.graph_service")
async def test_recall_with_results(mock_gs, mock_init):
    """recall() returns JSON string when results are non-empty."""
    mock_gs.recall = AsyncMock(return_value=[
        {"fact": "sky is blue", "name": "color", "uuid": "u1"},
    ])

    from src.mcp_server import recall
    result = await recall(query="sky")

    parsed = _parse_json(result)
    assert len(parsed) == 1
    assert parsed[0]["fact"] == "sky is blue"


# ---------------------------------------------------------------------------
# understand_code
# ---------------------------------------------------------------------------


@patch("src.mcp_server._ensure_init", new_callable=AsyncMock)
@patch("src.mcp_server.graph_service")
async def test_understand_code_empty(mock_gs, mock_init):
    """understand_code() returns 'No code entities found.' when empty."""
    mock_gs.search_nodes = AsyncMock(return_value=[])

    from src.mcp_server import understand_code
    result = await understand_code(query="auth")

    assert result == "No code entities found."


@patch("src.mcp_server._ensure_init", new_callable=AsyncMock)
@patch("src.mcp_server.graph_service")
async def test_understand_code_with_results(mock_gs, mock_init):
    """understand_code() returns JSON when results exist."""
    mock_gs.search_nodes = AsyncMock(return_value=[
        {"name": "AuthService", "summary": "Handles auth", "labels": ["Class"], "uuid": "n1"},
    ])

    from src.mcp_server import understand_code
    result = await understand_code(query="auth")

    parsed = _parse_json(result)
    assert len(parsed) == 1
    assert parsed[0]["name"] == "AuthService"


# ---------------------------------------------------------------------------
# get_history
# ---------------------------------------------------------------------------


@patch("src.mcp_server._ensure_init", new_callable=AsyncMock)
@patch("src.mcp_server.graph_service")
async def test_get_history_empty(mock_gs, mock_init):
    """get_history() returns 'No memory history found.' when empty."""
    mock_gs.get_episodes = AsyncMock(return_value=[])

    from src.mcp_server import get_history
    result = await get_history()

    assert result == "No memory history found."


@patch("src.mcp_server._ensure_init", new_callable=AsyncMock)
@patch("src.mcp_server.graph_service")
async def test_get_history_with_results(mock_gs, mock_init):
    """get_history() returns JSON when episodes exist."""
    mock_gs.get_episodes = AsyncMock(return_value=[
        {"name": "ep1", "content": "decision made", "created_at": "2024-01-01", "uuid": "ep-1"},
    ])

    from src.mcp_server import get_history
    result = await get_history()

    parsed = _parse_json(result)
    assert len(parsed) == 1
    assert parsed[0]["name"] == "ep1"


# ---------------------------------------------------------------------------
# search_facts
# ---------------------------------------------------------------------------


@patch("src.mcp_server._ensure_init", new_callable=AsyncMock)
@patch("src.mcp_server.graph_service")
async def test_search_facts_empty(mock_gs, mock_init):
    """search_facts() returns 'No facts found.' when empty."""
    mock_gs.search_facts = AsyncMock(return_value=[])

    from src.mcp_server import search_facts
    result = await search_facts(query="anything")

    assert result == "No facts found."


@patch("src.mcp_server._ensure_init", new_callable=AsyncMock)
@patch("src.mcp_server.graph_service")
async def test_search_facts_with_results(mock_gs, mock_init):
    """search_facts() returns JSON when facts exist."""
    mock_gs.search_facts = AsyncMock(return_value=[
        {"fact": "uses PostgreSQL", "name": "db_choice", "uuid": "f1"},
    ])

    from src.mcp_server import search_facts
    result = await search_facts(query="database")

    parsed = _parse_json(result)
    assert len(parsed) == 1
    assert parsed[0]["fact"] == "uses PostgreSQL"


# ---------------------------------------------------------------------------
# index_codebase
# ---------------------------------------------------------------------------


@patch("src.mcp_server._ensure_init", new_callable=AsyncMock)
@patch("src.mcp_server.graph_service")
async def test_index_codebase_incremental(mock_gs, mock_init):
    """index_codebase with full=False uses run_incremental_index."""
    mock_stats = {"files_parsed": 5, "files_skipped": 2, "symbols_indexed": 20}

    with patch("src.mcp_server.graph_service"):
        from src.mcp_server import index_codebase

        with patch(
            "src.indexer.incremental_indexer.run_incremental_index",
            new_callable=AsyncMock,
            return_value=mock_stats,
        ):
            result = await index_codebase(path="/tmp/project", full=False)

    parsed = _parse_json(result)
    assert parsed["status"] == "indexed_incremental"
    assert parsed["path"] == "/tmp/project"


@patch("src.mcp_server._ensure_init", new_callable=AsyncMock)
@patch("src.mcp_server.graph_service")
async def test_index_codebase_full(mock_gs, mock_init):
    """index_codebase with full=True uses parse_directory + CodeIndexer."""
    mock_indexer_instance = AsyncMock()
    mock_indexer_instance.index_symbols = AsyncMock(return_value={"nodes_created": 10})

    with patch("src.indexer.ast_parser.parse_directory", return_value=[MagicMock(), MagicMock()]):
        with patch("src.indexer.neo4j_ingestor.CodeIndexer", return_value=mock_indexer_instance):
            # Give graphiti a driver attribute
            mock_gs.graphiti = MagicMock()
            mock_gs.graphiti.driver = MagicMock()

            from src.mcp_server import index_codebase
            result = await index_codebase(path="/tmp/project", full=True)

    parsed = _parse_json(result)
    assert parsed["status"] == "indexed_full"
    assert parsed["symbols"] == 2


@patch("src.mcp_server._ensure_init", new_callable=AsyncMock)
@patch("src.mcp_server.graph_service")
async def test_index_codebase_extension_parsing(mock_gs, mock_init):
    """Extensions string '.py,.js' should be parsed into a set with dots."""
    captured_ext = {}

    async def _capture_ext(path, extensions=None, project=None):
        captured_ext["ext"] = extensions
        return {"files_parsed": 0, "files_skipped": 0, "symbols_indexed": 0}

    with patch(
        "src.indexer.incremental_indexer.run_incremental_index",
        side_effect=_capture_ext,
    ):
        from src.mcp_server import index_codebase
        await index_codebase(path="/tmp/proj", extensions=".py,.js", full=False)

    assert captured_ext["ext"] == {".py", ".js"}


# ---------------------------------------------------------------------------
# get_status
# ---------------------------------------------------------------------------


@patch("src.mcp_server._ensure_init", new_callable=AsyncMock)
@patch("src.mcp_server.graph_service")
async def test_get_status_returns_json(mock_gs, mock_init):
    """get_status() returns a formatted JSON string."""
    mock_gs.get_status = AsyncMock(return_value={
        "status": "healthy",
        "neo4j_uri": "bolt://localhost:7687",
        "initialized": True,
    })

    from src.mcp_server import get_status
    result = await get_status()

    parsed = _parse_json(result)
    assert parsed["status"] == "healthy"
    assert parsed["initialized"] is True
