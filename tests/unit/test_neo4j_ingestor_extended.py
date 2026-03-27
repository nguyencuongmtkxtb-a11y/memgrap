"""Extended unit tests for src.indexer.neo4j_ingestor — relation ingestion."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.indexer.neo4j_ingestor import CodeIndexer
from src.indexer.relation_extractor import CodeRelation


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_driver() -> MagicMock:
    """Create a mock Neo4jDriver with execute_query as AsyncMock."""
    driver = MagicMock()
    mock_result = MagicMock()
    mock_result.records = [{"cnt": 0}]
    driver.execute_query = AsyncMock(return_value=mock_result)
    return driver


def _make_relation(rel_type: str, source: str = "foo", target: str = "bar",
                   fp: str = "src/main.py", line: int = 10) -> CodeRelation:
    return CodeRelation(
        source_name=source,
        target_name=target,
        relation_type=rel_type,
        file_path=fp,
        line=line,
    )


# ---------------------------------------------------------------------------
# index_relations — empty input
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_index_relations_empty():
    """Empty relations list returns zeroed stats."""
    driver = _make_driver()
    indexer = CodeIndexer(driver)

    result = await indexer.index_relations([])

    assert result == {"calls": 0, "extends": 0, "imports_from": 0}
    driver.execute_query.assert_not_called()


# ---------------------------------------------------------------------------
# index_relations — groups by type
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_index_relations_calls_type():
    """Relations of type 'calls' trigger _upsert_calls."""
    driver = _make_driver()
    mock_result = MagicMock()
    mock_result.records = [{"cnt": 2}]
    driver.execute_query = AsyncMock(return_value=mock_result)
    indexer = CodeIndexer(driver)

    relations = [
        _make_relation("calls", source="funcA", target="funcB"),
        _make_relation("calls", source="funcA", target="funcC"),
    ]
    result = await indexer.index_relations(relations)

    assert result["calls"] == 2
    # Verify CALLS appears in the query
    query = driver.execute_query.call_args[0][0]
    assert "CALLS" in query


# ---------------------------------------------------------------------------
# _upsert_extends — creates placeholder nodes
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_upsert_extends():
    """_upsert_extends uses MERGE with ON CREATE for placeholder parents."""
    driver = _make_driver()
    mock_result = MagicMock()
    mock_result.records = [{"cnt": 1}]
    driver.execute_query = AsyncMock(return_value=mock_result)
    indexer = CodeIndexer(driver, project="testproj")

    extends = [_make_relation("extends", source="Child", target="Parent")]
    count = await indexer._upsert_extends(extends, "2025-01-01T00:00:00")

    assert count == 1
    query = driver.execute_query.call_args[0][0]
    assert "EXTENDS" in query
    assert "MERGE" in query
    assert "ON CREATE SET" in query
    assert "external" in query

    kwargs = driver.execute_query.call_args[1]
    assert kwargs["project"] == "testproj"


# ---------------------------------------------------------------------------
# _upsert_imports_from — resolves imports
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_upsert_imports_from_resolves():
    """_upsert_imports_from calls resolve_import and creates IMPORTS_FROM edges."""
    driver = _make_driver()

    # First call returns indexed file paths, second returns edge count
    indexed_result = MagicMock()
    indexed_result.records = [{"f.path": "src/utils.py"}, {"f.path": "src/main.py"}]
    edge_result = MagicMock()
    edge_result.records = [{"cnt": 1}]
    driver.execute_query = AsyncMock(side_effect=[indexed_result, edge_result])

    indexer = CodeIndexer(driver, project="proj")

    imports = [_make_relation("imports_from", source="src/main.py", target="src.utils", fp="src/main.py")]

    with patch("src.indexer.import_resolver.resolve_import", return_value="src/utils.py"):
        count = await indexer._upsert_imports_from(imports, "2025-01-01T00:00:00")

    assert count == 1


@pytest.mark.asyncio
async def test_upsert_imports_from_no_resolution():
    """_upsert_imports_from returns 0 when no imports resolve."""
    driver = _make_driver()

    indexed_result = MagicMock()
    indexed_result.records = [{"f.path": "src/other.py"}]
    driver.execute_query = AsyncMock(return_value=indexed_result)

    indexer = CodeIndexer(driver)

    imports = [_make_relation("imports_from", source="src/main.py", target="unknown.module")]

    with patch("src.indexer.import_resolver.resolve_import", return_value=None):
        count = await indexer._upsert_imports_from(imports, "2025-01-01T00:00:00")

    assert count == 0


# ---------------------------------------------------------------------------
# _upsert_calls — matches caller in same file
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_upsert_calls():
    """_upsert_calls creates CALLS edges between CodeFunction nodes."""
    driver = _make_driver()
    mock_result = MagicMock()
    mock_result.records = [{"cnt": 3}]
    driver.execute_query = AsyncMock(return_value=mock_result)
    indexer = CodeIndexer(driver, project="myproj")

    calls = [
        _make_relation("calls", source="main", target="helper", fp="src/app.py", line=5),
        _make_relation("calls", source="main", target="process", fp="src/app.py", line=8),
        _make_relation("calls", source="run", target="helper", fp="src/runner.py", line=3),
    ]
    count = await indexer._upsert_calls(calls, "2025-01-01T00:00:00")

    assert count == 3
    query = driver.execute_query.call_args[0][0]
    assert "CALLS" in query
    assert "MERGE" in query

    kwargs = driver.execute_query.call_args[1]
    assert len(kwargs["items"]) == 3
    assert kwargs["items"][0]["caller"] == "main"
    assert kwargs["items"][0]["callee"] == "helper"


# ---------------------------------------------------------------------------
# index_relations — mixed types
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_index_relations_mixed_types():
    """index_relations handles a mix of calls, extends, and imports_from."""
    driver = _make_driver()
    mock_result = MagicMock()
    mock_result.records = [{"cnt": 1}]
    # Multiple calls: extends query, then imports_from (indexed paths + edge)
    indexed_result = MagicMock()
    indexed_result.records = []
    driver.execute_query = AsyncMock(side_effect=[
        mock_result,  # _upsert_calls
        mock_result,  # _upsert_extends
        indexed_result,  # _upsert_imports_from (indexed paths)
    ])

    indexer = CodeIndexer(driver)

    relations = [
        _make_relation("calls"),
        _make_relation("extends"),
        _make_relation("imports_from"),
    ]

    with patch("src.indexer.import_resolver.resolve_import", return_value=None):
        result = await indexer.index_relations(relations)

    assert result["calls"] == 1
    assert result["extends"] == 1
    assert result["imports_from"] == 0


# ---------------------------------------------------------------------------
# CodeIndexer — project property
# ---------------------------------------------------------------------------


def test_code_indexer_project_default():
    """CodeIndexer defaults project to None."""
    driver = _make_driver()
    indexer = CodeIndexer(driver)
    assert indexer._project is None


def test_code_indexer_project_set():
    """CodeIndexer stores project when provided."""
    driver = _make_driver()
    indexer = CodeIndexer(driver, project="my-project")
    assert indexer._project == "my-project"
