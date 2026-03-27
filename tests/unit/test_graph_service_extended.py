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


# ---------------------------------------------------------------------------
# consolidate_memory — dry run
# ---------------------------------------------------------------------------


def _mock_driver_for_consolidate(
    dup_records=None,
    stale_records=None,
    orphan_records=None,
    ep_records=None,
    dup_fact_records=None,
):
    """Build a mock driver whose execute_query returns canned records."""
    driver = AsyncMock()

    # Default empty results
    if dup_records is None:
        dup_records = []
    if stale_records is None:
        stale_records = [{"stale_count": 0}]
    if orphan_records is None:
        orphan_records = [{"orphan_count": 0}]
    if ep_records is None:
        ep_records = [{"old_count": 0}]
    if dup_fact_records is None:
        dup_fact_records = [{"dup_fact_groups": 0, "removable": 0}]

    # execute_query is called with different Cypher queries.
    # We return results in call order:
    # 1. dup entities, 2. stale facts, 3. orphans, 4. episodes, 5. dup facts
    driver.execute_query = AsyncMock(
        side_effect=[
            (dup_records, None, None),
            (stale_records, None, None),
            (orphan_records, None, None),
            (ep_records, None, None),
            (dup_fact_records, None, None),
        ]
    )
    return driver


async def test_consolidate_memory_dry_run_empty():
    """consolidate_memory dry_run with no issues returns zero stats."""
    svc = GraphService(_make_settings(group_id="test-proj"))
    svc._initialized = True

    mock_graphiti = MagicMock()
    mock_graphiti.driver = _mock_driver_for_consolidate()
    svc._graphiti = mock_graphiti

    stats = await svc.consolidate_memory(group_id="test-proj", dry_run=True)

    assert stats["dry_run"] is True
    assert stats["group_id"] == "test-proj"
    assert stats["duplicates_merged"] == 0
    assert stats["stale_facts_found"] == 0
    assert stats["orphans_found"] == 0
    assert stats["episodes_pruned"] == 0
    assert stats["duplicate_facts_removed"] == 0


async def test_consolidate_memory_dry_run_with_issues():
    """consolidate_memory dry_run detects issues but does not delete."""
    svc = GraphService(_make_settings(group_id="proj"))
    svc._initialized = True

    mock_graphiti = MagicMock()
    mock_graphiti.driver = _mock_driver_for_consolidate(
        dup_records=[
            {"name": "EntityA", "cnt": 3, "uuids": ["u1", "u2", "u3"]},
        ],
        stale_records=[{"stale_count": 5}],
        orphan_records=[{"orphan_count": 2}],
        ep_records=[{"old_count": 10}],
        dup_fact_records=[{"dup_fact_groups": 3, "removable": 4}],
    )
    svc._graphiti = mock_graphiti

    stats = await svc.consolidate_memory(group_id="proj", dry_run=True)

    assert stats["duplicates_merged"] == 2  # cnt(3) - 1 = 2
    assert stats["stale_facts_found"] == 5
    assert stats["stale_facts_removed"] == 0  # dry run: no removal
    assert stats["orphans_found"] == 2
    assert stats["episodes_pruned"] == 10
    assert stats["duplicate_facts_removed"] == 4

    # Verify only 5 read queries were executed (no write queries in dry run)
    assert mock_graphiti.driver.execute_query.call_count == 5


async def test_consolidate_memory_execute_mode():
    """consolidate_memory dry_run=False calls write queries."""
    svc = GraphService(_make_settings(group_id="proj"))
    svc._initialized = True

    mock_graphiti = MagicMock()
    driver = AsyncMock()

    # Side effects for all queries (read + write):
    # 1. dup entities (read) — has dups
    # 2. dup entities (write/merge)
    # 3. stale facts (read)
    # 4. stale facts (write/delete)
    # 5. orphans (read)
    # 6. episodes (read) — has old
    # 7. episodes (write/delete)
    # 8. dup facts (read) — has dups
    # 9. dup facts (write/dedup)
    driver.execute_query = AsyncMock(
        side_effect=[
            ([{"name": "X", "cnt": 2, "uuids": ["a", "b"]}], None, None),  # 1
            ([{"merged": 1}], None, None),                                   # 2
            ([{"stale_count": 3}], None, None),                              # 3
            ([{"removed": 3}], None, None),                                  # 4
            ([{"orphan_count": 1}], None, None),                             # 5
            ([{"old_count": 5}], None, None),                                # 6
            ([{"pruned": 5}], None, None),                                   # 7
            ([{"dup_fact_groups": 2, "removable": 3}], None, None),          # 8
            ([{"removed": 3}], None, None),                                  # 9
        ]
    )
    mock_graphiti.driver = driver
    svc._graphiti = mock_graphiti

    stats = await svc.consolidate_memory(group_id="proj", dry_run=False)

    assert stats["dry_run"] is False
    assert stats["duplicates_merged"] == 1
    assert stats["stale_facts_removed"] == 3
    assert stats["orphans_found"] == 1
    assert stats["episodes_pruned"] == 5
    assert stats["duplicate_facts_removed"] == 3
    # 9 total queries: 5 reads + 4 writes
    assert driver.execute_query.call_count == 9


async def test_consolidate_memory_uses_default_gid():
    """consolidate_memory uses settings group_id when no override."""
    svc = GraphService(_make_settings(group_id="default-proj"))
    svc._initialized = True

    mock_graphiti = MagicMock()
    mock_graphiti.driver = _mock_driver_for_consolidate()
    svc._graphiti = mock_graphiti

    stats = await svc.consolidate_memory(dry_run=True)

    assert stats["group_id"] == "default-proj"
