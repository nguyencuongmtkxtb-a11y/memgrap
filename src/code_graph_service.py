"""Direct Neo4j queries for code graph data — no OpenAI needed.

Provides code intelligence: callers, callees, class hierarchy, imports, search.
Uses neo4j async driver directly for zero-cost queries.
"""

import logging

from neo4j import AsyncGraphDatabase

from src.config import Settings

logger = logging.getLogger(__name__)


class CodeGraphService:
    """Query code graph nodes and relationships in Neo4j."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._driver = None

    async def _ensure_driver(self):
        if self._driver is None:
            self._driver = AsyncGraphDatabase.driver(
                self._settings.neo4j_uri,
                auth=(self._settings.neo4j_user, self._settings.neo4j_password),
            )

    async def close(self):
        if self._driver:
            await self._driver.close()
            self._driver = None

    async def _run(self, query: str, **params) -> list[dict]:
        await self._ensure_driver()
        async with self._driver.session() as session:
            result = await session.run(query, params)
            return [dict(r) for r in await result.data()]

    async def find_callers(self, function_name: str, project: str = "") -> list[dict]:
        """Find all functions that CALL a given function."""
        return await self._run(
            """
            MATCH (caller:CodeFunction)-[r:CALLS]->(callee:CodeFunction)
            WHERE callee.name = $name
              AND ($project = '' OR callee.project = $project)
            RETURN caller.name AS caller, caller.file_path AS caller_file,
                   caller.line AS caller_line, r.line AS call_line,
                   callee.file_path AS callee_file
            ORDER BY caller.file_path, r.line
            """,
            name=function_name, project=project,
        )

    async def find_callees(self, function_name: str, project: str = "") -> list[dict]:
        """Find all functions that a given function CALLS."""
        return await self._run(
            """
            MATCH (caller:CodeFunction)-[r:CALLS]->(callee:CodeFunction)
            WHERE caller.name = $name
              AND ($project = '' OR caller.project = $project)
            RETURN callee.name AS callee, callee.file_path AS callee_file,
                   callee.line AS callee_line, r.line AS call_line,
                   caller.file_path AS caller_file
            ORDER BY caller.file_path, r.line
            """,
            name=function_name, project=project,
        )

    async def find_class_hierarchy(self, class_name: str, project: str = "") -> list[dict]:
        """Find parent and child classes via EXTENDS relationships."""
        return await self._run(
            """
            OPTIONAL MATCH (child:CodeClass)-[r1:EXTENDS]->(target:CodeClass)
            WHERE target.name = $name
              AND ($project = '' OR target.project = $project)
            WITH collect({child: child.name, child_file: child.file_path,
                          child_line: child.line}) AS children, $name AS name, $project AS project
            OPTIONAL MATCH (target2:CodeClass)-[r2:EXTENDS]->(parent:CodeClass)
            WHERE target2.name = name
              AND ($project = '' OR target2.project = project)
            RETURN children,
                   collect({parent: parent.name, parent_file: parent.file_path,
                            parent_line: parent.line}) AS parents
            """,
            name=class_name, project=project,
        )

    async def find_file_imports(self, file_path: str, project: str = "") -> list[dict]:
        """Find files imported by a given file and files that import it."""
        return await self._run(
            """
            OPTIONAL MATCH (src:CodeFile)-[r1:IMPORTS_FROM]->(tgt:CodeFile)
            WHERE src.path ENDS WITH $path
              AND ($project = '' OR src.project = $project)
            WITH collect({imports: tgt.path, line: r1.line}) AS outgoing,
                 $path AS path, $project AS project
            OPTIONAL MATCH (src2:CodeFile)-[r2:IMPORTS_FROM]->(tgt2:CodeFile)
            WHERE tgt2.path ENDS WITH path
              AND ($project = '' OR tgt2.project = $project)
            RETURN outgoing AS imports,
                   collect({imported_by: src2.path, line: r2.line}) AS imported_by
            """,
            path=file_path, project=project,
        )

    async def search_code(self, query: str, project: str = "", limit: int = 20) -> list[dict]:
        """Search code symbols (functions, classes, files) by name."""
        return await self._run(
            """
            MATCH (n)
            WHERE (n:CodeFunction OR n:CodeClass OR n:CodeFile)
              AND ($project = '' OR n.project = $project)
              AND (
                (n:CodeFile AND toLower(n.path) CONTAINS toLower($q))
                OR ((n:CodeFunction OR n:CodeClass) AND toLower(n.name) CONTAINS toLower($q))
              )
            RETURN
              CASE
                WHEN n:CodeFunction THEN 'function'
                WHEN n:CodeClass THEN 'class'
                ELSE 'file'
              END AS type,
              COALESCE(n.name, n.path) AS name,
              COALESCE(n.file_path, n.path) AS file_path,
              n.line AS line,
              n.language AS language,
              n.project AS project
            ORDER BY type, name
            LIMIT $limit
            """,
            q=query, project=project, limit=limit,
        )

    async def list_code_files(self, project: str = "", limit: int = 50) -> list[dict]:
        """List indexed code files with symbol counts."""
        return await self._run(
            """
            MATCH (f:CodeFile)
            WHERE $project = '' OR f.project = $project
            OPTIONAL MATCH (f)-[:CONTAINS]->(fn:CodeFunction)
            OPTIONAL MATCH (f)-[:CONTAINS]->(cls:CodeClass)
            RETURN f.path AS path, f.language AS language, f.project AS project,
                   count(DISTINCT fn) AS functions, count(DISTINCT cls) AS classes
            ORDER BY f.path
            LIMIT $limit
            """,
            project=project, limit=limit,
        )
