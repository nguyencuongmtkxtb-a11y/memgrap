"""Write parsed CodeSymbols directly to Neo4j via Cypher.

Bypasses Graphiti LLM extraction — AST data is already structured.
Uses MERGE for idempotent upserts (re-indexing same file won't duplicate).
"""

import logging
from datetime import datetime, timezone

from graphiti_core.driver.neo4j_driver import Neo4jDriver

logger = logging.getLogger(__name__)


class CodeIndexer:
    """Writes code symbols to Neo4j as CodeFile/Function/Class/Import nodes."""

    def __init__(self, driver: Neo4jDriver, project: str | None = None) -> None:
        self._driver = driver
        self._project = project

    async def clear_file(self, file_path: str) -> int:
        """Remove all code index nodes for a file. Returns count deleted."""
        result = await self._driver.execute_query(
            "MATCH (n) WHERE n.file_path = $fp AND "
            "(n:CodeFile OR n:CodeFunction OR n:CodeClass OR n:CodeImport) "
            "DETACH DELETE n RETURN count(n) AS cnt",
            fp=file_path,
        )
        return result.records[0]["cnt"] if result.records else 0

    async def ensure_fulltext_indexes(self) -> None:
        """Create fulltext indexes for search if they don't exist."""
        indexes = [
            "CREATE FULLTEXT INDEX session_search IF NOT EXISTS "
            "FOR (s:SessionEvent) ON EACH [s.branch, s.summary]",
            "CREATE FULLTEXT INDEX code_file_search IF NOT EXISTS "
            "FOR (c:CodeFile) ON EACH [c.path]",
            "CREATE FULLTEXT INDEX code_function_search IF NOT EXISTS "
            "FOR (f:CodeFunction) ON EACH [f.name]",
        ]
        for idx in indexes:
            try:
                await self._driver.execute_query(idx)
            except Exception as e:
                logger.warning("Index creation skipped: %s", e)

    async def index_symbols(self, symbols: list) -> dict:
        """Ingest a list of CodeSymbol objects into Neo4j.

        Groups symbols by file, clears old data per file, then batch upserts.
        Returns stats: {files, functions, classes, imports}.
        """
        if not symbols:
            return {"files": 0, "functions": 0, "classes": 0, "imports": 0}

        await self.ensure_fulltext_indexes()

        # Group by file
        by_file: dict[str, list] = {}
        for sym in symbols:
            by_file.setdefault(sym.file_path, []).append(sym)

        stats = {"files": 0, "functions": 0, "classes": 0, "imports": 0}
        now = datetime.now(timezone.utc).isoformat()

        for file_path, file_symbols in by_file.items():
            # Clear old data for this file
            await self.clear_file(file_path)

            # Detect language from extension
            lang = file_path.rsplit(".", 1)[-1] if "." in file_path else "unknown"

            # Upsert CodeFile node
            await self._driver.execute_query(
                "MERGE (f:CodeFile {path: $path}) "
                "SET f.language = $lang, f.indexed_at = $now, f.project = $project",
                path=file_path, lang=lang, now=now, project=self._project or "",
            )
            stats["files"] += 1

            # Batch upsert symbols by kind
            funcs = [s for s in file_symbols if s.kind == "function"]
            classes = [s for s in file_symbols if s.kind == "class"]
            imports = [s for s in file_symbols if s.kind == "import"]

            if funcs:
                await self._upsert_functions(file_path, funcs, now)
                stats["functions"] += len(funcs)

            if classes:
                await self._upsert_classes(file_path, classes, now)
                stats["classes"] += len(classes)

            if imports:
                await self._upsert_imports(file_path, imports, now)
                stats["imports"] += len(imports)

        logger.info(
            "Indexed %d files: %d functions, %d classes, %d imports",
            stats["files"], stats["functions"], stats["classes"], stats["imports"],
        )
        return stats

    async def _upsert_functions(self, file_path: str, funcs: list, now: str) -> None:
        """Batch upsert Function nodes with CONTAINS relationship."""
        data = [
            {"name": f.name, "line": f.line, "parent": f.parent, "fp": f.file_path}
            for f in funcs
        ]
        await self._driver.execute_query(
            "UNWIND $items AS item "
            "MATCH (f:CodeFile {path: $fp}) "
            "MERGE (fn:CodeFunction {name: item.name, file_path: item.fp}) "
            "SET fn.line = item.line, fn.parent_scope = item.parent, fn.indexed_at = $now, fn.project = $project "
            "MERGE (f)-[:CONTAINS]->(fn)",
            items=data, fp=file_path, now=now, project=self._project or "",
        )

    async def _upsert_classes(self, file_path: str, classes: list, now: str) -> None:
        """Batch upsert Class nodes with CONTAINS relationship."""
        data = [
            {"name": c.name, "line": c.line, "parent": c.parent, "fp": c.file_path}
            for c in classes
        ]
        await self._driver.execute_query(
            "UNWIND $items AS item "
            "MATCH (f:CodeFile {path: $fp}) "
            "MERGE (cls:CodeClass {name: item.name, file_path: item.fp}) "
            "SET cls.line = item.line, cls.parent_scope = item.parent, cls.indexed_at = $now, cls.project = $project "
            "MERGE (f)-[:CONTAINS]->(cls)",
            items=data, fp=file_path, now=now, project=self._project or "",
        )

    async def _upsert_imports(self, file_path: str, imports: list, now: str) -> None:
        """Batch upsert Import nodes with IMPORTS relationship."""
        data = [
            {"name": i.name, "line": i.line, "fp": i.file_path}
            for i in imports
        ]
        await self._driver.execute_query(
            "UNWIND $items AS item "
            "MATCH (f:CodeFile {path: $fp}) "
            "MERGE (imp:CodeImport {name: item.name, file_path: item.fp}) "
            "SET imp.line = item.line, imp.indexed_at = $now, imp.project = $project "
            "MERGE (f)-[:IMPORTS]->(imp)",
            items=data, fp=file_path, now=now, project=self._project or "",
        )
