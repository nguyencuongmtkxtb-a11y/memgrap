"""Unit tests for src.indexer.incremental_indexer — incremental file indexing."""

import time
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.indexer.incremental_indexer import (
    _collect_files,
    _needs_reindex,
    run_incremental_index,
)

# ---------------------------------------------------------------------------
# _collect_files — finds matching extensions
# ---------------------------------------------------------------------------


def test_collect_files_finds_matching(tmp_path):
    """Create .py files in tmp_path, verify they appear in result."""
    (tmp_path / "app.py").write_text("x = 1\n")
    (tmp_path / "utils.py").write_text("y = 2\n")
    (tmp_path / "readme.md").write_text("# hi\n")

    result = _collect_files(str(tmp_path), extensions={".py"})

    paths = list(result.keys())
    assert len(paths) == 2
    assert all(p.endswith(".py") for p in paths)
    # Paths should use forward slashes
    assert all("/" in p for p in paths)
    # Each value is a float mtime
    assert all(isinstance(v, float) for v in result.values())


# ---------------------------------------------------------------------------
# _collect_files — skips ignored directories
# ---------------------------------------------------------------------------


def test_collect_files_skips_ignored_dirs(tmp_path):
    """node_modules/ subdir should not be traversed."""
    (tmp_path / "main.py").write_text("def main(): pass\n")

    nm = tmp_path / "node_modules"
    nm.mkdir()
    (nm / "pkg.py").write_text("def hidden(): pass\n")

    result = _collect_files(str(tmp_path), extensions={".py"})

    paths = list(result.keys())
    assert len(paths) == 1
    assert any("main.py" in p for p in paths)
    assert not any("node_modules" in p for p in paths)


# ---------------------------------------------------------------------------
# _needs_reindex — new file (no indexed_at)
# ---------------------------------------------------------------------------


def test_needs_reindex_new_file():
    """File with indexed_at=None is always considered new -> needs reindex."""
    assert _needs_reindex(mtime=time.time(), indexed_at_iso=None) is True


# ---------------------------------------------------------------------------
# _needs_reindex — modified file
# ---------------------------------------------------------------------------


def test_needs_reindex_modified():
    """File mtime after indexed_at -> needs reindex."""
    old_time = "2024-01-01T00:00:00+00:00"
    recent_mtime = datetime(2025, 6, 1, tzinfo=timezone.utc).timestamp()
    assert _needs_reindex(mtime=recent_mtime, indexed_at_iso=old_time) is True


# ---------------------------------------------------------------------------
# _needs_reindex — unchanged file
# ---------------------------------------------------------------------------


def test_needs_reindex_unchanged():
    """File mtime before indexed_at -> no reindex needed."""
    recent_time = "2025-06-01T00:00:00+00:00"
    old_mtime = datetime(2024, 1, 1, tzinfo=timezone.utc).timestamp()
    assert _needs_reindex(mtime=old_mtime, indexed_at_iso=recent_time) is False


# ---------------------------------------------------------------------------
# run_incremental_index — no changes needed
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_run_incremental_no_changes(tmp_path):
    """All files up to date -> stats show 0 new, 0 updated."""
    # Create a file on disk
    py_file = tmp_path / "stable.py"
    py_file.write_text("x = 1\n")
    # indexed_at is well after file mtime
    future_ts = datetime(2099, 1, 1, tzinfo=timezone.utc).isoformat()
    normalized_path = str(py_file).replace("\\", "/")

    # Mock Neo4j driver returning this file as already indexed
    mock_driver_instance = MagicMock()
    mock_record = {"path": normalized_path, "indexed_at": future_ts}
    mock_result = MagicMock()
    mock_result.records = [mock_record]
    mock_driver_instance.execute_query = AsyncMock(return_value=mock_result)
    mock_driver_instance.close = AsyncMock()

    mock_settings = MagicMock()
    mock_settings.neo4j_uri = "bolt://localhost:7687"
    mock_settings.neo4j_user = "neo4j"
    mock_settings.neo4j_password = "password"

    with (
        patch("graphiti_core.driver.neo4j_driver.Neo4jDriver", return_value=mock_driver_instance),
        patch("src.config.get_settings", return_value=mock_settings),
    ):
        stats = await run_incremental_index(str(tmp_path), extensions={".py"})

    assert stats["new"] == 0
    assert stats["updated"] == 0
    assert stats["skipped"] >= 1
    assert stats["errors"] == 0


# ---------------------------------------------------------------------------
# run_incremental_index — indexes changed files
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_run_incremental_indexes_changed(tmp_path):
    """Modified file triggers parse_file + CodeIndexer.index_symbols."""
    # Create a Python file with extractable symbols
    py_file = tmp_path / "changed.py"
    py_file.write_text("def hello(): pass\n")

    normalized_path = str(py_file).replace("\\", "/")

    # indexed_at is old -> file needs reindex
    old_ts = "2020-01-01T00:00:00+00:00"

    # Mock driver: _get_indexed_files returns old timestamp for this file
    mock_driver_instance = MagicMock()
    mock_record = {"path": normalized_path, "indexed_at": old_ts}
    mock_result = MagicMock()
    mock_result.records = [mock_record]
    mock_driver_instance.execute_query = AsyncMock(return_value=mock_result)
    mock_driver_instance.close = AsyncMock()

    mock_settings = MagicMock()
    mock_settings.neo4j_uri = "bolt://localhost:7687"
    mock_settings.neo4j_user = "neo4j"
    mock_settings.neo4j_password = "password"

    mock_indexer_instance = MagicMock()
    mock_indexer_instance.index_symbols = AsyncMock(
        return_value={"files": 1, "functions": 1, "classes": 0, "imports": 0}
    )

    with (
        patch("graphiti_core.driver.neo4j_driver.Neo4jDriver", return_value=mock_driver_instance),
        patch("src.config.get_settings", return_value=mock_settings),
        patch("src.indexer.neo4j_ingestor.CodeIndexer", return_value=mock_indexer_instance),
    ):
        stats = await run_incremental_index(str(tmp_path), extensions={".py"})

    assert stats["updated"] >= 1
    assert stats["errors"] == 0
    mock_indexer_instance.index_symbols.assert_called_once()
    # Verify symbols were passed to index_symbols
    call_args = mock_indexer_instance.index_symbols.call_args[0][0]
    assert len(call_args) >= 1
    assert any(s.name == "hello" for s in call_args)
