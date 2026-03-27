"""Write parsed CodeSymbols and CodeRelations directly to Neo4j via Cypher.

Bypasses Graphiti LLM extraction — AST data is already structured.
Uses MERGE for idempotent upserts (re-indexing same file won't duplicate).

Relationship types:
- CONTAINS: CodeFile -> CodeFunction/CodeClass
- IMPORTS: CodeFile -> CodeImport
- CALLS: CodeFunction -> CodeFunction (cross-file function calls)
- EXTENDS: CodeClass -> CodeClass (inheritance/implementation)
- IMPORTS_FROM: CodeFile -> CodeFile (resolved import source)
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

    async def index_relations(self, relations: list) -> dict:
        """Ingest CodeRelation objects as Neo4j edges.

        Creates CALLS, EXTENDS, and IMPORTS_FROM relationships between
        existing nodes. Skips relations where target nodes don't exist.

        Returns stats: {calls, extends, imports_from}.
        """
        if not relations:
            return {"calls": 0, "extends": 0, "imports_from": 0}

        stats = {"calls": 0, "extends": 0, "imports_from": 0}
        now = datetime.now(timezone.utc).isoformat()

        # Group by type for batch processing
        calls = [r for r in relations if r.relation_type == "calls"]
        extends = [r for r in relations if r.relation_type == "extends"]
        imports_from = [r for r in relations if r.relation_type == "imports_from"]

        if calls:
            cnt = await self._upsert_calls(calls, now)
            stats["calls"] = cnt

        if extends:
            cnt = await self._upsert_extends(extends, now)
            stats["extends"] = cnt

        if imports_from:
            cnt = await self._upsert_imports_from(imports_from, now)
            stats["imports_from"] = cnt

        logger.info(
            "Indexed relations: %d calls, %d extends, %d imports_from",
            stats["calls"], stats["extends"], stats["imports_from"],
        )
        return stats

    async def _upsert_calls(self, calls: list, now: str) -> int:
        """Create CALLS edges between CodeFunction nodes."""
        data = [
            {
                "caller": r.source_name,
                "callee": r.target_name,
                "fp": r.file_path,
                "line": r.line,
            }
            for r in calls
        ]
        # Match caller function in the same file, callee in any file within project
        result = await self._driver.execute_query(
            "UNWIND $items AS item "
            "MATCH (caller:CodeFunction {name: item.caller, file_path: item.fp}) "
            "MATCH (callee:CodeFunction {name: item.callee}) "
            "WHERE callee.project = $project "
            "MERGE (caller)-[r:CALLS]->(callee) "
            "SET r.line = item.line, r.updated_at = $now "
            "RETURN count(r) AS cnt",
            items=data, now=now, project=self._project or "",
        )
        return result.records[0]["cnt"] if result.records else 0

    async def _upsert_extends(self, extends: list, now: str) -> int:
        """Create EXTENDS edges between CodeClass nodes.

        Creates placeholder CodeClass nodes (external=true) for parent classes
        not found in the project, so inheritance queries always return results.
        """
        data = [
            {
                "child": r.source_name,
                "parent": r.target_name,
                "fp": r.file_path,
                "line": r.line,
            }
            for r in extends
        ]
        result = await self._driver.execute_query(
            "UNWIND $items AS item "
            "MATCH (child:CodeClass {name: item.child, file_path: item.fp}) "
            "MERGE (parent:CodeClass {name: item.parent, project: $project}) "
            "ON CREATE SET parent.external = true, parent.indexed_at = $now "
            "MERGE (child)-[r:EXTENDS]->(parent) "
            "SET r.line = item.line, r.updated_at = $now "
            "RETURN count(r) AS cnt",
            items=data, now=now, project=self._project or "",
        )
        return result.records[0]["cnt"] if result.records else 0

    async def _upsert_imports_from(self, imports_from: list, now: str) -> int:
        """Create IMPORTS_FROM edges between CodeFile nodes."""
        from src.indexer.import_resolver import resolve_import

        # Fetch indexed file paths for resolution
        result = await self._driver.execute_query(
            "MATCH (f:CodeFile) WHERE f.project = $project RETURN f.path",
            project=self._project or "",
        )
        indexed_paths = {rec["f.path"] for rec in result.records}

        # Resolve import sources to actual file paths
        data = []
        for r in imports_from:
            resolved = resolve_import(r.target_name, r.file_path, indexed_paths)
            if resolved:
                data.append({
                    "source_fp": r.file_path,
                    "target_fp": resolved,
                    "line": r.line,
                })

        if not data:
            return 0

        result = await self._driver.execute_query(
            "UNWIND $items AS item "
            "MATCH (src:CodeFile {path: item.source_fp}) "
            "MATCH (tgt:CodeFile {path: item.target_fp}) "
            "MERGE (src)-[r:IMPORTS_FROM]->(tgt) "
            "SET r.line = item.line, r.updated_at = $now "
            "RETURN count(r) AS cnt",
            items=data, now=now, project=self._project or "",
        )
        return result.records[0]["cnt"] if result.records else 0
