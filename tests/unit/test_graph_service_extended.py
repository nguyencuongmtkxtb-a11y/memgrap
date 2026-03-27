"""Extended unit tests for src.graph_service — _gid helper, group_id override, close."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.config import Settings
from src.graph_service import GraphService


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
        "group_id": "default-group",
        "semaphore_limit": 5,
    }
    defaults.update(overrides)
    return Settings(_env_file=None, **defaults)


# ---------------------------------------------------------------------------
# _gid — resolve effective group_id
# ---------------------------------------------------------------------------


def test_gid_returns_explicit_value():
    """_gid returns explicit group_id when provided."""
    svc = GraphService(_make_settings())
    assert svc._gid("custom-project") == "custom-project"


def test_gid_returns_settings_default_when_none():
    """_gid returns settings.group_id when param is None."""
    svc = GraphService(_make_settings(group_id="my-default"))
    assert svc._gid(None) == "my-default"


def test_gid_returns_settings_default_when_empty():
    """_gid returns settings.group_id when param is empty string."""
    svc = GraphService(_make_settings(group_id="fallback"))
    assert svc._gid("") == "fallback"


# ---------------------------------------------------------------------------
# graphiti property
# ---------------------------------------------------------------------------


def test_graphiti_property_raises_when_not_initialized():
    """Accessing graphiti before initialize() raises RuntimeError."""
    svc = GraphService(_make_settings())
    with pytest.raises(RuntimeError, match="not initialized"):
        _ = svc.graphiti


def test_graphiti_property_returns_instance():
    """Accessing graphiti after setting _graphiti returns the instance."""
    svc = GraphService(_make_settings())
    mock_graphiti = MagicMock()
    svc._graphiti = mock_graphiti
    assert svc.graphiti is mock_graphiti


# ---------------------------------------------------------------------------
# add_memory — group_id override
# ---------------------------------------------------------------------------


async def test_add_memory_uses_gid_override():
    """add_memory passes explicit group_id through _gid."""
    svc = GraphService(_make_settings(group_id="default"))
    svc._initialized = True

    mock_graphiti = AsyncMock()
    node = SimpleNamespace(name="E1")
    mock_graphiti.add_episode = AsyncMock(
        return_value=SimpleNamespace(nodes=[node], edges=[])
    )
    svc._graphiti = mock_graphiti

    await svc.add_memory("test content", group_id="override-project")

    call_kwargs = mock_graphiti.add_episode.call_args[1]
    assert call_kwargs["group_id"] == "override-project"


async def test_add_memory_uses_default_gid():
    """add_memory uses settings group_id when no override."""
    svc = GraphService(_make_settings(group_id="the-default"))
    svc._initialized = True

    mock_graphiti = AsyncMock()
    mock_graphiti.add_episode = AsyncMock(
        return_value=SimpleNamespace(nodes=[], edges=[])
    )
    svc._graphiti = mock_graphiti

    await svc.add_memory("test content")

    call_kwargs = mock_graphiti.add_episode.call_args[1]
    assert call_kwargs["group_id"] == "the-default"


# ---------------------------------------------------------------------------
# recall — group_id override
# ---------------------------------------------------------------------------


async def test_recall_uses_gid_override():
    """recall passes explicit group_id to search."""
    svc = GraphService(_make_settings(group_id="default"))
    svc._initialized = True

    mock_graphiti = AsyncMock()
    mock_graphiti.search = AsyncMock(return_value=[])
    svc._graphiti = mock_graphiti

    await svc.recall("test", group_id="project-x")

    call_kwargs = mock_graphiti.search.call_args[1]
    assert call_kwargs["group_ids"] == ["project-x"]


# ---------------------------------------------------------------------------
# search_nodes — group_id override
# ---------------------------------------------------------------------------


async def test_search_nodes_uses_gid_override():
    """search_nodes passes explicit group_id to search_."""
    svc = GraphService(_make_settings(group_id="default"))
    svc._initialized = True

    mock_graphiti = AsyncMock()
    mock_graphiti.search_ = AsyncMock(
        return_value=SimpleNamespace(nodes=[], edges=[])
    )
    svc._graphiti = mock_graphiti

    await svc.search_nodes("test", group_id="proj-y")

    call_kwargs = mock_graphiti.search_.call_args[1]
    assert call_kwargs["group_ids"] == ["proj-y"]


# ---------------------------------------------------------------------------
# search_facts — group_id override
# ---------------------------------------------------------------------------


async def test_search_facts_uses_gid_override():
    """search_facts passes explicit group_id to search_."""
    svc = GraphService(_make_settings(group_id="default"))
    svc._initialized = True

    mock_graphiti = AsyncMock()
    mock_graphiti.search_ = AsyncMock(
        return_value=SimpleNamespace(nodes=[], edges=[])
    )
    svc._graphiti = mock_graphiti

    await svc.search_facts("test", group_id="proj-z")

    call_kwargs = mock_graphiti.search_.call_args[1]
    assert call_kwargs["group_ids"] == ["proj-z"]


# ---------------------------------------------------------------------------
# get_episodes — group_id override
# ---------------------------------------------------------------------------


async def test_get_episodes_uses_gid_override():
    """get_episodes passes explicit group_id to retrieve_episodes."""
    svc = GraphService(_make_settings(group_id="default"))
    svc._initialized = True

    mock_graphiti = AsyncMock()
    mock_graphiti.retrieve_episodes = AsyncMock(return_value=[])
    svc._graphiti = mock_graphiti

    await svc.get_episodes(group_id="proj-ep")

    call_kwargs = mock_graphiti.retrieve_episodes.call_args[1]
    assert call_kwargs["group_ids"] == ["proj-ep"]


# ---------------------------------------------------------------------------
# close
# ---------------------------------------------------------------------------


async def test_close_clears_initialized():
    """close() sets _initialized to False."""
    svc = GraphService(_make_settings())
    svc._initialized = True
    svc._graphiti = AsyncMock()

    await svc.close()

    assert svc._initialized is False


async def test_close_noop_when_no_graphiti():
    """close() is a no-op when _graphiti is None."""
    svc = GraphService(_make_settings())
    await svc.close()  # Should not raise
    assert svc._initialized is False


# ---------------------------------------------------------------------------
# add_memory — auto-generated episode name
# ---------------------------------------------------------------------------


async def test_add_memory_auto_episode_name():
    """add_memory generates episode name when name=None."""
    svc = GraphService(_make_settings())
    svc._initialized = True

    mock_graphiti = AsyncMock()
    mock_graphiti.add_episode = AsyncMock(
        return_value=SimpleNamespace(nodes=[], edges=[])
    )
    svc._graphiti = mock_graphiti

    result = await svc.add_memory("test content")

    assert result["episode"].startswith("memory-")
    assert len(result["episode"]) > len("memory-")
