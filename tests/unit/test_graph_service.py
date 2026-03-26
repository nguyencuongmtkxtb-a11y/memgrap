"""Unit tests for src.graph_service — GraphService wrapper around Graphiti Core."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.config import Settings
from src.graph_service import GraphService, _ensure_neo4j_container

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_settings(**overrides) -> Settings:
    """Build a Settings instance without reading .env."""
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


def _make_edge(fact="test fact", name="edge1", valid_at=None, invalid_at=None, uuid="e-uuid"):
    return SimpleNamespace(fact=fact, name=name, valid_at=valid_at, invalid_at=invalid_at, uuid=uuid)


def _make_node(name="TestNode", summary="A summary", labels=None, uuid="n-uuid"):
    return SimpleNamespace(name=name, summary=summary, labels=labels or ["Entity"], uuid=uuid)


# ---------------------------------------------------------------------------
# initialize — idempotency
# ---------------------------------------------------------------------------


@patch("src.graph_service.create_graphiti")
@patch("src.graph_service._ensure_neo4j_container")
async def test_initialize_idempotent(mock_neo4j, mock_factory):
    """Second call to initialize() should be a no-op when already initialized."""
    svc = GraphService(_make_settings())
    svc._initialized = True

    await svc.initialize()

    mock_factory.assert_not_called()
    mock_neo4j.assert_not_called()


# ---------------------------------------------------------------------------
# initialize — retry on failure then succeed
# ---------------------------------------------------------------------------


@patch("src.graph_service.asyncio.sleep", new_callable=AsyncMock)
@patch("src.graph_service.create_graphiti")
@patch("src.graph_service._ensure_neo4j_container")
async def test_initialize_retries_on_failure(mock_neo4j, mock_factory, mock_sleep):
    """build_indices_and_constraints fails once, succeeds on retry."""
    mock_graphiti = AsyncMock()
    mock_graphiti.build_indices_and_constraints = AsyncMock(
        side_effect=[ConnectionError("neo4j down"), None]
    )
    mock_factory.return_value = mock_graphiti

    svc = GraphService(_make_settings())
    await svc.initialize()

    assert svc._initialized is True
    assert mock_graphiti.build_indices_and_constraints.call_count == 2
    mock_sleep.assert_called_once()


# ---------------------------------------------------------------------------
# initialize — raises after max retries
# ---------------------------------------------------------------------------


@patch("src.graph_service.asyncio.sleep", new_callable=AsyncMock)
@patch("src.graph_service.create_graphiti")
@patch("src.graph_service._ensure_neo4j_container")
async def test_initialize_raises_after_max_retries(mock_neo4j, mock_factory, mock_sleep):
    """All 3 attempts fail -> RuntimeError raised."""
    mock_graphiti = AsyncMock()
    mock_graphiti.build_indices_and_constraints = AsyncMock(
        side_effect=ConnectionError("still down")
    )
    mock_factory.return_value = mock_graphiti

    svc = GraphService(_make_settings())

    with pytest.raises(RuntimeError, match="Failed to connect to Neo4j after 3 attempts"):
        await svc.initialize()

    assert mock_graphiti.build_indices_and_constraints.call_count == 3


# ---------------------------------------------------------------------------
# _ensure_neo4j_container — Docker not found
# ---------------------------------------------------------------------------


@patch("src.graph_service.shutil.which", return_value=None)
@patch("src.graph_service.subprocess.run")
def test_ensure_neo4j_container_skips_no_docker(mock_run, mock_which):
    """When docker binary is absent, subprocess should never be called."""
    _ensure_neo4j_container()

    mock_which.assert_called_once_with("docker")
    mock_run.assert_not_called()


# ---------------------------------------------------------------------------
# _ensure_neo4j_container — already running
# ---------------------------------------------------------------------------


@patch("src.graph_service.shutil.which", return_value="/usr/bin/docker")
@patch("src.graph_service.subprocess.run")
def test_ensure_neo4j_container_skips_already_running(mock_run, mock_which):
    """When container status is 'running', docker compose up should not be called."""
    mock_run.return_value = MagicMock(returncode=0, stdout="running\n")

    _ensure_neo4j_container()

    # Only the inspect call, no compose up
    assert mock_run.call_count == 1
    assert "inspect" in mock_run.call_args[0][0]


# ---------------------------------------------------------------------------
# add_memory
# ---------------------------------------------------------------------------


async def test_add_memory_returns_summary():
    """add_memory should return a dict with episode name, counts, and lists."""
    svc = GraphService(_make_settings())
    svc._initialized = True

    mock_graphiti = AsyncMock()
    node1 = SimpleNamespace(name="EntityA")
    node2 = SimpleNamespace(name="EntityB")
    edge1 = SimpleNamespace(fact="A relates to B")
    mock_graphiti.add_episode = AsyncMock(
        return_value=SimpleNamespace(nodes=[node1, node2], edges=[edge1])
    )
    svc._graphiti = mock_graphiti

    result = await svc.add_memory("test content", source="test", name="test-ep")

    assert result["episode"] == "test-ep"
    assert result["nodes_count"] == 2
    assert result["edges_count"] == 1
    assert result["nodes"] == ["EntityA", "EntityB"]
    assert result["facts"] == ["A relates to B"]


# ---------------------------------------------------------------------------
# recall
# ---------------------------------------------------------------------------


async def test_recall_returns_formatted_edges():
    """recall() should return list of dicts matching format_edge output."""
    svc = GraphService(_make_settings())
    svc._initialized = True

    edge = _make_edge(fact="Python is used", name="lang_choice", uuid="e-1")
    mock_graphiti = AsyncMock()
    mock_graphiti.search = AsyncMock(return_value=[edge])
    svc._graphiti = mock_graphiti

    results = await svc.recall("Python")

    assert len(results) == 1
    assert results[0]["fact"] == "Python is used"
    assert results[0]["name"] == "lang_choice"
    assert results[0]["uuid"] == "e-1"


# ---------------------------------------------------------------------------
# search_nodes
# ---------------------------------------------------------------------------


async def test_search_nodes_returns_formatted():
    """search_nodes() should return list of dicts matching format_node output."""
    svc = GraphService(_make_settings())
    svc._initialized = True

    node = _make_node(name="FastAPI", summary="Web framework", labels=["Tool"], uuid="n-1")
    mock_graphiti = AsyncMock()
    mock_graphiti.search_ = AsyncMock(
        return_value=SimpleNamespace(nodes=[node], edges=[])
    )
    svc._graphiti = mock_graphiti

    results = await svc.search_nodes("FastAPI")

    assert len(results) == 1
    assert results[0]["name"] == "FastAPI"
    assert results[0]["summary"] == "Web framework"
    assert results[0]["labels"] == ["Tool"]
    assert results[0]["uuid"] == "n-1"


# ---------------------------------------------------------------------------
# get_status — healthy
# ---------------------------------------------------------------------------


async def test_get_status_healthy():
    """get_status() returns healthy dict when retrieve_episodes succeeds."""
    settings = _make_settings()
    svc = GraphService(settings)
    svc._initialized = True

    mock_graphiti = AsyncMock()
    mock_graphiti.retrieve_episodes = AsyncMock(return_value=[])
    svc._graphiti = mock_graphiti

    status = await svc.get_status()

    assert status["status"] == "healthy"
    assert status["neo4j_uri"] == settings.neo4j_uri
    assert status["initialized"] is True


# ---------------------------------------------------------------------------
# get_status — error
# ---------------------------------------------------------------------------


async def test_get_status_error():
    """get_status() returns error dict when retrieve_episodes raises."""
    svc = GraphService(_make_settings())
    svc._initialized = True

    mock_graphiti = AsyncMock()
    mock_graphiti.retrieve_episodes = AsyncMock(side_effect=ConnectionError("connection lost"))
    svc._graphiti = mock_graphiti

    status = await svc.get_status()

    assert status["status"] == "error"
    assert "connection lost" in status["error"]
    assert "fix" in status
