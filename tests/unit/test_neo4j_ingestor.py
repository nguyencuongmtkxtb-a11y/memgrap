"""Unit tests for src.indexer.neo4j_ingestor — CodeIndexer Neo4j writes."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.indexer.ast_parser import CodeSymbol
from src.indexer.neo4j_ingestor import CodeIndexer

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_symbol(name: str, kind: str, file_path: str, line: int = 1, parent: str | None = None) -> CodeSymbol:
    return CodeSymbol(name=name, kind=kind, line=line, file_path=file_path, parent=parent)


def _make_driver() -> MagicMock:
    """Create a mock Neo4jDriver with execute_query as AsyncMock."""
    driver = MagicMock()
    mock_result = MagicMock()
    mock_result.records = [{"cnt": 0}]
    driver.execute_query = AsyncMock(return_value=mock_result)
    return driver


# ---------------------------------------------------------------------------
# index_symbols — empty input
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_index_symbols_empty():
    """Empty symbol list returns zeroed stats, no queries executed."""
    driver = _make_driver()
    indexer = CodeIndexer(driver)

    result = await indexer.index_symbols([])

    assert result == {"files": 0, "functions": 0, "classes": 0, "imports": 0}
    driver.execute_query.assert_not_called()


# ---------------------------------------------------------------------------
# index_symbols — groups by file
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_index_symbols_groups_by_file():
    """Symbols from 2 files produce 2 clear_file calls (one per file)."""
    driver = _make_driver()
    indexer = CodeIndexer(driver)

    symbols = [
        _make_symbol("func_a", "function", "src/a.py"),
        _make_symbol("func_b", "function", "src/b.py"),
    ]
    await indexer.index_symbols(symbols)

    # Collect all queries that contain DETACH DELETE (clear_file calls)
    clear_calls = [
        call for call in driver.execute_query.call_args_list
        if "DETACH DELETE" in str(call)
    ]
    assert len(clear_calls) == 2


# ---------------------------------------------------------------------------
# clear_file — DETACH DELETE query
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_clear_file_query():
    """clear_file should execute DETACH DELETE query for given file path."""
    driver = _make_driver()
    indexer = CodeIndexer(driver)

    await indexer.clear_file("src/target.py")

    driver.execute_query.assert_called_once()
    query = driver.execute_query.call_args[0][0]
    assert "DETACH DELETE" in query
    assert driver.execute_query.call_args[1]["fp"] == "src/target.py"


# ---------------------------------------------------------------------------
# _upsert_functions — UNWIND batch query
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_upsert_functions_batch():
    """_upsert_functions uses UNWIND and passes correct items data."""
    driver = _make_driver()
    indexer = CodeIndexer(driver)

    funcs = [
        _make_symbol("parse", "function", "src/parser.py", line=10, parent="Parser"),
        _make_symbol("lex", "function", "src/parser.py", line=20),
    ]

    await indexer._upsert_functions("src/parser.py", funcs, "2025-01-01T00:00:00")

    driver.execute_query.assert_called_once()
    query = driver.execute_query.call_args[0][0]
    assert "UNWIND" in query
    assert "CodeFunction" in query

    kwargs = driver.execute_query.call_args[1]
    items = kwargs["items"]
    assert len(items) == 2
    assert items[0]["name"] == "parse"
    assert items[0]["parent"] == "Parser"
    assert items[1]["name"] == "lex"
    assert items[1]["parent"] is None


# ---------------------------------------------------------------------------
# _upsert_classes — MERGE CodeClass
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_upsert_classes_batch():
    """_upsert_classes uses MERGE CodeClass in the query."""
    driver = _make_driver()
    indexer = CodeIndexer(driver)

    classes = [
        _make_symbol("UserModel", "class", "src/models.py", line=5),
    ]

    await indexer._upsert_classes("src/models.py", classes, "2025-01-01T00:00:00")

    query = driver.execute_query.call_args[0][0]
    assert "MERGE" in query
    assert "CodeClass" in query

    kwargs = driver.execute_query.call_args[1]
    assert kwargs["items"][0]["name"] == "UserModel"


# ---------------------------------------------------------------------------
# _upsert_imports — MERGE CodeImport
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_upsert_imports_batch():
    """_upsert_imports uses MERGE CodeImport in the query."""
    driver = _make_driver()
    indexer = CodeIndexer(driver)

    imports = [
        _make_symbol("import os", "import", "src/utils.py", line=1),
    ]

    await indexer._upsert_imports("src/utils.py", imports, "2025-01-01T00:00:00")

    query = driver.execute_query.call_args[0][0]
    assert "MERGE" in query
    assert "CodeImport" in query
    assert "IMPORTS" in query

    kwargs = driver.execute_query.call_args[1]
    assert kwargs["items"][0]["name"] == "import os"
