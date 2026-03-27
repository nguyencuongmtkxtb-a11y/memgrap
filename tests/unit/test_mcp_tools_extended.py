"""Extended unit tests for src.mcp_server — project param, code graph tools, full indexing."""

import json
from unittest.mock import AsyncMock, MagicMock, patch


def _parse_json(text: str):
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        raise AssertionError(f"Expected valid JSON, got: {text!r}") from e


# ---------------------------------------------------------------------------
# remember — project param forwarded
# ---------------------------------------------------------------------------


@patch("src.mcp_server._ensure_init", new_callable=AsyncMock)
@patch("src.mcp_server.graph_service")
async def test_remember_project_param(mock_gs, mock_init):
    """remember() passes project as group_id to add_memory."""
    mock_gs.add_memory = AsyncMock(return_value={
        "nodes_count": 1, "edges_count": 0, "nodes": ["X"], "facts": [],
    })

    from src.mcp_server import remember
    await remember(content="test", project="my-project")

    call_kwargs = mock_gs.add_memory.call_args[1]
    assert call_kwargs["group_id"] == "my-project"


@patch("src.mcp_server._ensure_init", new_callable=AsyncMock)
@patch("src.mcp_server.graph_service")
async def test_remember_empty_project_uses_auto_detected(mock_gs, mock_init):
    """remember() with empty project string uses _current_project from CWD."""
    mock_gs.add_memory = AsyncMock(return_value={
        "nodes_count": 0, "edges_count": 0, "nodes": [], "facts": [],
    })

    import src.mcp_server as mod
    original = mod._current_project
    try:
        mod._current_project = "test-project"
        await mod.remember(content="test", project="")
        call_kwargs = mock_gs.add_memory.call_args[1]
        assert call_kwargs["group_id"] == "test-project"
    finally:
        mod._current_project = original


# ---------------------------------------------------------------------------
# recall — project param forwarded
# ---------------------------------------------------------------------------


@patch("src.mcp_server._ensure_init", new_callable=AsyncMock)
@patch("src.mcp_server.graph_service")
async def test_recall_project_param(mock_gs, mock_init):
    """recall() passes project as group_id to graph_service.recall."""
    mock_gs.recall = AsyncMock(return_value=[])

    from src.mcp_server import recall
    await recall(query="test", project="proj-a")

    call_kwargs = mock_gs.recall.call_args[1]
    assert call_kwargs["group_id"] == "proj-a"


@patch("src.mcp_server._ensure_init", new_callable=AsyncMock)
@patch("src.mcp_server.graph_service")
async def test_recall_error_handling(mock_gs, mock_init):
    """recall() returns error string on exception."""
    mock_gs.recall = AsyncMock(side_effect=RuntimeError("neo4j down"))

    from src.mcp_server import recall
    result = await recall(query="test")
    assert result.startswith("Error recalling:")
    assert "neo4j down" in result


# ---------------------------------------------------------------------------
# understand_code — project param forwarded
# ---------------------------------------------------------------------------


@patch("src.mcp_server._ensure_init", new_callable=AsyncMock)
@patch("src.mcp_server.graph_service")
async def test_understand_code_project_param(mock_gs, mock_init):
    """understand_code() passes project as group_id."""
    mock_gs.search_nodes = AsyncMock(return_value=[])

    from src.mcp_server import understand_code
    await understand_code(query="auth", project="proj-b")

    call_kwargs = mock_gs.search_nodes.call_args[1]
    assert call_kwargs["group_id"] == "proj-b"


@patch("src.mcp_server._ensure_init", new_callable=AsyncMock)
@patch("src.mcp_server.graph_service")
async def test_understand_code_error_handling(mock_gs, mock_init):
    """understand_code() returns error string on exception."""
    mock_gs.search_nodes = AsyncMock(side_effect=ValueError("bad query"))

    from src.mcp_server import understand_code
    result = await understand_code(query="test")
    assert result.startswith("Error searching code entities:")


# ---------------------------------------------------------------------------
# get_history — project param forwarded
# ---------------------------------------------------------------------------


@patch("src.mcp_server._ensure_init", new_callable=AsyncMock)
@patch("src.mcp_server.graph_service")
async def test_get_history_project_param(mock_gs, mock_init):
    """get_history() passes project as group_id."""
    mock_gs.get_episodes = AsyncMock(return_value=[])

    from src.mcp_server import get_history
    await get_history(project="proj-c")

    call_kwargs = mock_gs.get_episodes.call_args[1]
    assert call_kwargs["group_id"] == "proj-c"


@patch("src.mcp_server._ensure_init", new_callable=AsyncMock)
@patch("src.mcp_server.graph_service")
async def test_get_history_error_handling(mock_gs, mock_init):
    """get_history() returns error string on exception."""
    mock_gs.get_episodes = AsyncMock(side_effect=ConnectionError("timeout"))

    from src.mcp_server import get_history
    result = await get_history()
    assert result.startswith("Error retrieving history:")


# ---------------------------------------------------------------------------
# search_facts — project param forwarded
# ---------------------------------------------------------------------------


@patch("src.mcp_server._ensure_init", new_callable=AsyncMock)
@patch("src.mcp_server.graph_service")
async def test_search_facts_project_param(mock_gs, mock_init):
    """search_facts() passes project as group_id."""
    mock_gs.search_facts = AsyncMock(return_value=[])

    from src.mcp_server import search_facts
    await search_facts(query="db", project="proj-d")

    call_kwargs = mock_gs.search_facts.call_args[1]
    assert call_kwargs["group_id"] == "proj-d"


@patch("src.mcp_server._ensure_init", new_callable=AsyncMock)
@patch("src.mcp_server.graph_service")
async def test_search_facts_error_handling(mock_gs, mock_init):
    """search_facts() returns error string on exception."""
    mock_gs.search_facts = AsyncMock(side_effect=RuntimeError("fail"))

    from src.mcp_server import search_facts
    result = await search_facts(query="test")
    assert result.startswith("Error searching facts:")


# ---------------------------------------------------------------------------
# Code graph MCP tools — find_callers
# ---------------------------------------------------------------------------


@patch("src.mcp_server.code_graph")
async def test_find_callers_tool_success(mock_cg):
    """find_callers MCP tool returns formatted JSON."""
    mock_cg.find_callers = AsyncMock(return_value=[
        {"caller": "main", "caller_file": "src/main.py"},
    ])

    from src.mcp_server import find_callers
    result = await find_callers(function_name="helper")

    parsed = _parse_json(result)
    assert len(parsed) == 1
    assert parsed[0]["caller"] == "main"


@patch("src.mcp_server.code_graph")
async def test_find_callers_tool_empty(mock_cg):
    """find_callers MCP tool returns message when no callers."""
    mock_cg.find_callers = AsyncMock(return_value=[])

    from src.mcp_server import find_callers
    result = await find_callers(function_name="orphan")

    assert "No callers found" in result


@patch("src.mcp_server.code_graph")
async def test_find_callers_tool_error(mock_cg):
    """find_callers MCP tool returns error message on exception."""
    mock_cg.find_callers = AsyncMock(side_effect=RuntimeError("boom"))

    from src.mcp_server import find_callers
    result = await find_callers(function_name="test")

    assert result.startswith("Error:")


# ---------------------------------------------------------------------------
# Code graph MCP tools — find_callees
# ---------------------------------------------------------------------------


@patch("src.mcp_server.code_graph")
async def test_find_callees_tool_empty(mock_cg):
    """find_callees MCP tool returns message when no callees."""
    mock_cg.find_callees = AsyncMock(return_value=[])

    from src.mcp_server import find_callees
    result = await find_callees(function_name="leaf")

    assert "No callees found" in result


# ---------------------------------------------------------------------------
# Code graph MCP tools — find_class_hierarchy
# ---------------------------------------------------------------------------


@patch("src.mcp_server.code_graph")
async def test_find_class_hierarchy_tool_empty(mock_cg):
    """find_class_hierarchy MCP tool returns message when no hierarchy."""
    mock_cg.find_class_hierarchy = AsyncMock(return_value=[])

    from src.mcp_server import find_class_hierarchy
    result = await find_class_hierarchy(class_name="Orphan")

    assert "No hierarchy found" in result


# ---------------------------------------------------------------------------
# Code graph MCP tools — find_file_imports
# ---------------------------------------------------------------------------


@patch("src.mcp_server.code_graph")
async def test_find_file_imports_tool_empty(mock_cg):
    """find_file_imports MCP tool returns message when no imports."""
    mock_cg.find_file_imports = AsyncMock(return_value=[])

    from src.mcp_server import find_file_imports
    result = await find_file_imports(file_path="unknown.py")

    assert "No import relationships found" in result


# ---------------------------------------------------------------------------
# Code graph MCP tools — search_code
# ---------------------------------------------------------------------------


@patch("src.mcp_server.code_graph")
async def test_search_code_tool_success(mock_cg):
    """search_code MCP tool returns formatted JSON."""
    mock_cg.search_code = AsyncMock(return_value=[
        {"type": "function", "name": "parse_file"},
    ])

    from src.mcp_server import search_code
    result = await search_code(query="parse")

    parsed = _parse_json(result)
    assert parsed[0]["name"] == "parse_file"


@patch("src.mcp_server.code_graph")
async def test_search_code_tool_empty(mock_cg):
    """search_code MCP tool returns message when no matches."""
    mock_cg.search_code = AsyncMock(return_value=[])

    from src.mcp_server import search_code
    result = await search_code(query="zzz")

    assert "No code symbols matching" in result


# ---------------------------------------------------------------------------
# index_codebase — full mode with relations
# ---------------------------------------------------------------------------


@patch("src.mcp_server._ensure_init", new_callable=AsyncMock)
@patch("src.mcp_server.graph_service")
async def test_index_codebase_full_with_relations(mock_gs, mock_init):
    """Full index extracts relations and includes stats."""
    mock_indexer = AsyncMock()
    mock_indexer.index_symbols = AsyncMock(return_value={
        "files": 2, "functions": 5, "classes": 1, "imports": 3,
    })
    mock_indexer.index_relations = AsyncMock(return_value={
        "calls": 3, "extends": 1, "imports_from": 2,
    })

    mock_symbol = MagicMock()
    mock_symbol.file_path = "src/main.py"

    with patch("src.indexer.ast_parser.parse_directory", return_value=[mock_symbol]):
        with patch("src.indexer.neo4j_ingestor.CodeIndexer", return_value=mock_indexer):
            with patch("src.indexer.relation_extractor.extract_relations", return_value=[MagicMock()]):
                mock_gs.graphiti = MagicMock()
                mock_gs.graphiti.driver = MagicMock()

                from src.mcp_server import index_codebase
                result = await index_codebase(path="/tmp/project", full=True)

    parsed = _parse_json(result)
    assert parsed["status"] == "indexed_full"
    assert parsed["relations"]["calls"] == 3
    assert parsed["relations"]["extends"] == 1


@patch("src.mcp_server._ensure_init", new_callable=AsyncMock)
@patch("src.mcp_server.graph_service")
async def test_index_codebase_error_handling(mock_gs, mock_init):
    """index_codebase returns error string on exception."""
    with patch(
        "src.indexer.incremental_indexer.run_incremental_index",
        new_callable=AsyncMock,
        side_effect=RuntimeError("disk full"),
    ):
        from src.mcp_server import index_codebase
        result = await index_codebase(path="/tmp/fail")

    assert result.startswith("Error indexing codebase:")
    assert "disk full" in result


# ---------------------------------------------------------------------------
# Auto-detect project from CWD
# ---------------------------------------------------------------------------


async def test_current_project_is_cwd_name():
    """_current_project is set to Path.cwd().name at module load."""
    from pathlib import Path

    import src.mcp_server as mod
    assert mod._current_project == Path.cwd().name


@patch("src.mcp_server._ensure_init", new_callable=AsyncMock)
@patch("src.mcp_server.graph_service")
async def test_get_status_includes_current_project(mock_gs, mock_init):
    """get_status() response includes current_project field."""
    mock_gs.get_status = AsyncMock(return_value={
        "status": "healthy", "initialized": True,
    })

    import src.mcp_server as mod
    original = mod._current_project
    try:
        mod._current_project = "my-proj"
        result = await mod.get_status()
        parsed = _parse_json(result)
        assert parsed["current_project"] == "my-proj"
    finally:
        mod._current_project = original


@patch("src.mcp_server.code_graph")
async def test_code_graph_tools_use_auto_detected_project(mock_cg):
    """Code graph tools pass _current_project when project param is empty."""
    mock_cg.find_callers = AsyncMock(return_value=[])

    import src.mcp_server as mod
    original = mod._current_project
    try:
        mod._current_project = "auto-proj"
        await mod.find_callers(function_name="foo")
        mock_cg.find_callers.assert_awaited_once_with("foo", "auto-proj")
    finally:
        mod._current_project = original


@patch("src.mcp_server.code_graph")
async def test_code_graph_tools_explicit_project_overrides(mock_cg):
    """Code graph tools use explicit project over _current_project."""
    mock_cg.search_code = AsyncMock(return_value=[])

    import src.mcp_server as mod
    original = mod._current_project
    try:
        mod._current_project = "auto-proj"
        await mod.search_code(query="test", project="explicit-proj")
        mock_cg.search_code.assert_awaited_once_with("test", "explicit-proj", 20)
    finally:
        mod._current_project = original


# ---------------------------------------------------------------------------
# consolidate_memory MCP tool
# ---------------------------------------------------------------------------


@patch("src.mcp_server._ensure_init", new_callable=AsyncMock)
@patch("src.mcp_server.graph_service")
async def test_consolidate_memory_dry_run(mock_gs, mock_init):
    """consolidate_memory() dry_run returns stats without modifying."""
    mock_gs.consolidate_memory = AsyncMock(return_value={
        "group_id": "test",
        "dry_run": True,
        "duplicates_merged": 2,
        "stale_facts_found": 3,
        "stale_facts_removed": 0,
        "orphans_found": 1,
        "episodes_pruned": 5,
        "duplicate_facts_removed": 4,
    })

    from src.mcp_server import consolidate_memory
    result = await consolidate_memory(dry_run=True)

    assert "DRY RUN" in result
    assert "Duplicate entities merged: 2" in result
    assert "Stale facts (superseded): 3" in result
    assert "Stale facts removed: 0" in result
    assert "Orphan entities (no relations): 1" in result
    assert "Old episodes pruned (>30d): 5" in result
    assert "Duplicate facts consolidated: 4" in result


@patch("src.mcp_server._ensure_init", new_callable=AsyncMock)
@patch("src.mcp_server.graph_service")
async def test_consolidate_memory_execute(mock_gs, mock_init):
    """consolidate_memory() with dry_run=False reports EXECUTED."""
    mock_gs.consolidate_memory = AsyncMock(return_value={
        "group_id": "proj",
        "dry_run": False,
        "duplicates_merged": 1,
        "stale_facts_found": 2,
        "stale_facts_removed": 2,
        "orphans_found": 0,
        "episodes_pruned": 3,
        "duplicate_facts_removed": 1,
    })

    from src.mcp_server import consolidate_memory
    result = await consolidate_memory(dry_run=False)

    assert "EXECUTED" in result
    assert "Stale facts removed: 2" in result


@patch("src.mcp_server._ensure_init", new_callable=AsyncMock)
@patch("src.mcp_server.graph_service")
async def test_consolidate_memory_project_forwarded(mock_gs, mock_init):
    """consolidate_memory() passes project param as group_id."""
    mock_gs.consolidate_memory = AsyncMock(return_value={
        "group_id": "my-proj",
        "dry_run": True,
        "duplicates_merged": 0,
        "stale_facts_found": 0,
        "stale_facts_removed": 0,
        "orphans_found": 0,
        "episodes_pruned": 0,
        "duplicate_facts_removed": 0,
    })

    from src.mcp_server import consolidate_memory
    await consolidate_memory(project="my-proj")

    call_kwargs = mock_gs.consolidate_memory.call_args[1]
    assert call_kwargs["group_id"] == "my-proj"


@patch("src.mcp_server._ensure_init", new_callable=AsyncMock)
@patch("src.mcp_server.graph_service")
async def test_consolidate_memory_max_age_forwarded(mock_gs, mock_init):
    """consolidate_memory() passes max_age_days param."""
    mock_gs.consolidate_memory = AsyncMock(return_value={
        "group_id": "x",
        "dry_run": True,
        "duplicates_merged": 0,
        "stale_facts_found": 0,
        "stale_facts_removed": 0,
        "orphans_found": 0,
        "episodes_pruned": 0,
        "duplicate_facts_removed": 0,
    })

    from src.mcp_server import consolidate_memory
    await consolidate_memory(max_age_days=7)

    call_kwargs = mock_gs.consolidate_memory.call_args[1]
    assert call_kwargs["max_age_days"] == 7


@patch("src.mcp_server._ensure_init", new_callable=AsyncMock)
@patch("src.mcp_server.graph_service")
async def test_consolidate_memory_error_handling(mock_gs, mock_init):
    """consolidate_memory() returns error string on exception."""
    mock_gs.consolidate_memory = AsyncMock(side_effect=RuntimeError("neo4j boom"))

    from src.mcp_server import consolidate_memory
    result = await consolidate_memory()

    assert result.startswith("Error consolidating memory:")
    assert "neo4j boom" in result


@patch("src.mcp_server._ensure_init", new_callable=AsyncMock)
@patch("src.mcp_server.graph_service")
async def test_consolidate_memory_uses_auto_project(mock_gs, mock_init):
    """consolidate_memory() uses _current_project when project is empty."""
    mock_gs.consolidate_memory = AsyncMock(return_value={
        "group_id": "auto-proj",
        "dry_run": True,
        "duplicates_merged": 0,
        "stale_facts_found": 0,
        "stale_facts_removed": 0,
        "orphans_found": 0,
        "episodes_pruned": 0,
        "duplicate_facts_removed": 0,
    })

    import src.mcp_server as mod
    original = mod._current_project
    try:
        mod._current_project = "auto-proj"
        await mod.consolidate_memory(project="")
        call_kwargs = mock_gs.consolidate_memory.call_args[1]
        assert call_kwargs["group_id"] == "auto-proj"
    finally:
        mod._current_project = original
