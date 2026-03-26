"""Incremental codebase indexer — only re-indexes new or modified files.

Compares file modification times against Neo4j CodeFile.indexed_at timestamps.
Can be run standalone via: python -m src.indexer.incremental_indexer --path <dir>

Used by the SessionStart hook to keep the code index fresh without full re-scans.
"""

import argparse
import asyncio
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from src.indexer.ast_parser import DEFAULT_IGNORE_DIRS, parse_file

logger = logging.getLogger(__name__)

# Default extensions to index
DEFAULT_EXTENSIONS = {".py", ".js", ".ts", ".tsx", ".jsx"}


def _collect_files(
    root: str,
    extensions: set[str],
    ignore_dirs: set[str] | None = None,
) -> dict[str, float]:
    """Walk directory and return {normalized_path: mtime} for matching files."""
    if ignore_dirs is None:
        ignore_dirs = DEFAULT_IGNORE_DIRS

    files: dict[str, float] = {}
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in ignore_dirs]
        for fname in filenames:
            ext = Path(fname).suffix.lower()
            if ext in extensions:
                full_path = os.path.join(dirpath, fname).replace("\\", "/")
                try:
                    files[full_path] = os.path.getmtime(
                        os.path.join(dirpath, fname)
                    )
                except OSError:
                    pass
    return files


async def _get_indexed_files(driver) -> dict[str, str]:
    """Query Neo4j for existing CodeFile nodes. Returns {path: indexed_at_iso}."""
    result = await driver.execute_query(
        "MATCH (f:CodeFile) RETURN f.path AS path, f.indexed_at AS indexed_at"
    )
    indexed: dict[str, str] = {}
    for record in result.records:
        path = record["path"]
        ts = record["indexed_at"]
        if path and ts:
            indexed[path] = ts
    return indexed


def _needs_reindex(mtime: float, indexed_at_iso: str | None) -> bool:
    """Return True if file is new or modified after last index."""
    if indexed_at_iso is None:
        return True
    try:
        indexed_dt = datetime.fromisoformat(indexed_at_iso)
        if indexed_dt.tzinfo is None:
            indexed_dt = indexed_dt.replace(tzinfo=timezone.utc)
        file_dt = datetime.fromtimestamp(mtime, tz=timezone.utc)
        return file_dt > indexed_dt
    except (ValueError, OSError):
        return True


async def run_incremental_index(
    path: str,
    extensions: set[str] | None = None,
    project: str | None = None,
) -> dict:
    """Run incremental index: only parse+ingest new/changed files.

    Returns stats dict: {new, updated, skipped, errors}.
    """
    from graphiti_core.driver.neo4j_driver import Neo4jDriver

    from src.config import get_settings
    from src.indexer.neo4j_ingestor import CodeIndexer

    if extensions is None:
        extensions = DEFAULT_EXTENSIONS

    settings = get_settings()

    # Connect to Neo4j directly (no Graphiti/OpenAI needed)
    driver = Neo4jDriver(
        uri=settings.neo4j_uri,
        user=settings.neo4j_user,
        password=settings.neo4j_password,
    )

    try:
        # Get current index state from Neo4j
        indexed_files = await _get_indexed_files(driver)
    except Exception as e:
        logger.warning("Cannot connect to Neo4j: %s — skipping incremental index", e)
        return {"new": 0, "updated": 0, "skipped": 0, "errors": 1, "error": str(e)}

    # Collect files from disk
    disk_files = _collect_files(path, extensions)

    # Classify files
    new_files: list[str] = []
    updated_files: list[str] = []
    skipped = 0

    for file_path, mtime in disk_files.items():
        indexed_at = indexed_files.get(file_path)
        if indexed_at is None:
            new_files.append(file_path)
        elif _needs_reindex(mtime, indexed_at):
            updated_files.append(file_path)
        else:
            skipped += 1

    files_to_index = new_files + updated_files

    if not files_to_index:
        await driver.close()
        return {
            "new": 0,
            "updated": 0,
            "skipped": skipped,
            "errors": 0,
        }

    # Parse and ingest only changed files
    indexer = CodeIndexer(driver, project=project)
    all_symbols = []
    actually_new = 0
    actually_updated = 0
    new_set = set(new_files)
    for fp in files_to_index:
        symbols = parse_file(fp)
        if not symbols:
            # File has no extractable symbols (e.g. empty __init__.py) — skip
            skipped += 1
            continue
        all_symbols.extend(symbols)
        if fp in new_set:
            actually_new += 1
        else:
            actually_updated += 1

    try:
        if all_symbols:
            await indexer.index_symbols(all_symbols)
    except Exception as e:
        logger.error("Ingestion error: %s", e)
        await driver.close()
        return {
            "new": actually_new,
            "updated": actually_updated,
            "skipped": skipped,
            "errors": 1,
            "error": str(e),
        }

    await driver.close()
    return {
        "new": actually_new,
        "updated": actually_updated,
        "skipped": skipped,
        "errors": 0,
    }


def main() -> None:
    """CLI entry point for incremental indexing."""
    parser = argparse.ArgumentParser(
        description="Incremental codebase indexer — only re-indexes new/changed files"
    )
    parser.add_argument(
        "--path", default=os.getcwd(), help="Directory to index (default: CWD)"
    )
    parser.add_argument(
        "--extensions",
        default=".py,.js,.ts,.tsx,.jsx",
        help="Comma-separated file extensions (default: .py,.js,.ts,.tsx,.jsx)",
    )
    args = parser.parse_args()

    ext_set = {
        e.strip() if e.startswith(".") else f".{e.strip()}"
        for e in args.extensions.split(",")
    }

    logging.basicConfig(
        level=logging.INFO,
        stream=sys.stderr,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    try:
        stats = asyncio.run(run_incremental_index(args.path, ext_set))
    except Exception as e:
        print(f"[memgrap-index] Error: {e}", file=sys.stderr)
        sys.exit(0)  # Exit cleanly — don't crash session start

    print(
        f"[memgrap-index] Indexed {stats['new']} new, "
        f"{stats['updated']} updated, "
        f"{stats['skipped']} skipped (unchanged)"
        + (f", {stats['errors']} errors" if stats.get("errors") else ""),
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
