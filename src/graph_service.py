"""Graphiti wrapper service — init, add memory, search, status.

Includes auto-start for Docker Neo4j container and connection retry with backoff.
"""

import asyncio
import logging
import os
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from graphiti_core import Graphiti
from graphiti_core.nodes import EpisodeType
from graphiti_core.search.search_config import SearchResults
from graphiti_core.search.search_config_recipes import (
    EDGE_HYBRID_SEARCH_RRF,
    NODE_HYBRID_SEARCH_RRF,
)

from src.config import Settings
from src.entity_types import ENTITY_TYPES
from src.graphiti_factory import create_graphiti
from src.result_formatters import format_edge, format_episode, format_node

logger = logging.getLogger(__name__)

# Project root for docker-compose.yml discovery
_PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Retry config for Neo4j connection
_MAX_RETRIES = 3
_RETRY_DELAY_SECONDS = 2


def _ensure_neo4j_container() -> None:
    """Start Neo4j Docker container if not running. Skips if Docker unavailable."""
    if not shutil.which("docker"):
        logger.warning("Docker not found on PATH — skipping auto-start.")
        return

    compose_file = _PROJECT_ROOT / "docker-compose.yml"
    if not compose_file.exists():
        logger.warning("docker-compose.yml not found at %s — skipping auto-start.", _PROJECT_ROOT)
        return

    try:
        result = subprocess.run(
            ["docker", "inspect", "--format", "{{.State.Status}}", "memgrap-neo4j"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0 and "running" in result.stdout:
            return  # Already running
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    logger.info("Neo4j container not running — starting via docker compose...")
    try:
        subprocess.run(
            ["docker", "compose", "up", "-d"],
            cwd=str(_PROJECT_ROOT), capture_output=True, text=True, timeout=30,
        )
        logger.info("Docker compose started. Waiting for Neo4j health...")
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        logger.warning("Failed to start Neo4j container: %s", e)


class GraphService:
    """Wraps Graphiti Core with lazy initialization and developer-memory defaults."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._graphiti: Graphiti | None = None
        self._initialized = False

    async def initialize(self) -> None:
        """Connect to Neo4j, create Graphiti instance, build indices.

        Idempotent. Auto-starts Neo4j container if Docker is available.
        Retries connection up to 3 times with backoff.
        """
        if self._initialized:
            return

        # Try to auto-start Neo4j container
        _ensure_neo4j_container()

        os.environ["SEMAPHORE_LIMIT"] = str(self._settings.semaphore_limit)
        self._graphiti = create_graphiti(self._settings)

        # Retry loop for Neo4j connection (container may still be starting)
        last_error: Exception | None = None
        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                await self._graphiti.build_indices_and_constraints()
                self._initialized = True
                logger.info("GraphService initialized — Neo4j connected, indices built.")
                return
            except Exception as e:
                last_error = e
                if attempt < _MAX_RETRIES:
                    logger.warning(
                        "Neo4j connection attempt %d/%d failed: %s. Retrying in %ds...",
                        attempt, _MAX_RETRIES, e, _RETRY_DELAY_SECONDS * attempt,
                    )
                    await asyncio.sleep(_RETRY_DELAY_SECONDS * attempt)

        raise RuntimeError(
            f"Failed to connect to Neo4j after {_MAX_RETRIES} attempts. "
            f"Last error: {last_error}. "
            f"Check that Neo4j is running: docker compose ps"
        )

    @property
    def graphiti(self) -> Graphiti:
        if self._graphiti is None:
            raise RuntimeError("GraphService not initialized. Call initialize() first.")
        return self._graphiti

    def _gid(self, group_id: str | None = None) -> str:
        """Resolve effective group_id: explicit param > settings default."""
        return group_id or self._settings.group_id

    async def add_memory(self, content: str, source: str = "claude_code", name: str | None = None, group_id: str | None = None) -> dict:
        """Ingest text into the knowledge graph. Returns extracted entity/fact summary."""
        episode_name = name or f"memory-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}"
        result = await self.graphiti.add_episode(
            name=episode_name,
            episode_body=content,
            source=EpisodeType.text,
            source_description=source,
            reference_time=datetime.now(timezone.utc),
            group_id=self._gid(group_id),
            entity_types=ENTITY_TYPES,
        )
        return {
            "episode": episode_name,
            "nodes_count": len(result.nodes) if result.nodes else 0,
            "edges_count": len(result.edges) if result.edges else 0,
            "nodes": [n.name for n in (result.nodes or [])],
            "facts": [e.fact for e in (result.edges or [])],
        }

    async def recall(self, query: str, num_results: int = 10, group_id: str | None = None) -> list[dict]:
        """Hybrid search for facts (edges). Returns temporal fact list."""
        edges = await self.graphiti.search(
            query=query, group_ids=[self._gid(group_id)], num_results=num_results,
        )
        return [format_edge(e) for e in edges]

    async def search_nodes(self, query: str, num_results: int = 10, group_id: str | None = None) -> list[dict]:
        """Search entity nodes via NODE_HYBRID_SEARCH_RRF recipe (public API)."""
        config = NODE_HYBRID_SEARCH_RRF.model_copy(deep=True)
        config.limit = num_results
        results: SearchResults = await self.graphiti.search_(
            query=query, config=config, group_ids=[self._gid(group_id)],
        )
        return [format_node(n) for n in (results.nodes or [])]

    async def search_facts(self, query: str, num_results: int = 10, group_id: str | None = None) -> list[dict]:
        """Search relationship edges via EDGE_HYBRID_SEARCH_RRF recipe (public API)."""
        config = EDGE_HYBRID_SEARCH_RRF.model_copy(deep=True)
        config.limit = num_results
        results: SearchResults = await self.graphiti.search_(
            query=query, config=config, group_ids=[self._gid(group_id)],
        )
        return [format_edge(e) for e in (results.edges or [])]

    async def get_episodes(self, last_n: int = 10, group_id: str | None = None) -> list[dict]:
        """Retrieve recent episodes (raw ingested data)."""
        episodes = await self.graphiti.retrieve_episodes(
            reference_time=datetime.now(timezone.utc),
            group_ids=[self._gid(group_id)], last_n=last_n,
        )
        return [format_episode(ep) for ep in episodes]

    async def get_status(self) -> dict:
        """Health check — verify Neo4j connection and return basic stats with fix guidance."""
        try:
            await self.graphiti.retrieve_episodes(
                reference_time=datetime.now(timezone.utc),
                group_ids=[self._settings.group_id], last_n=1,
            )
            return {
                "status": "healthy",
                "neo4j_uri": self._settings.neo4j_uri,
                "group_id": self._settings.group_id,
                "llm_model": self._settings.llm_model,
                "embedding_model": self._settings.embedding_model,
                "initialized": self._initialized,
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "initialized": self._initialized,
                "fix": "Run: docker compose up -d (in the Memgrap project directory)",
            }

    async def consolidate_memory(
        self,
        group_id: str | None = None,
        max_age_days: int = 30,
        dry_run: bool = True,
    ) -> dict:
        """Review and clean up knowledge graph: dedup, prune stale, find orphans.

        All operations use direct Cypher queries — zero OpenAI/LLM cost.

        Args:
            group_id: Scope cleanup to this group (project). None = settings default.
            max_age_days: Remove episodes older than this many days.
            dry_run: If True, only report stats without modifying data.

        Returns:
            Dict with cleanup stats.
        """
        gid = self._gid(group_id)
        driver = self.graphiti.driver

        stats: dict = {
            "group_id": gid,
            "dry_run": dry_run,
            "duplicates_merged": 0,
            "stale_facts_found": 0,
            "stale_facts_removed": 0,
            "orphans_found": 0,
            "episodes_pruned": 0,
            "duplicate_facts_removed": 0,
        }

        # 1. Find duplicate entities: same name + same group_id
        dup_query = """
        MATCH (n:Entity)
        WHERE n.group_id = $gid
        WITH n.name AS name, collect(n) AS nodes, count(*) AS cnt
        WHERE cnt > 1
        RETURN name, cnt, [x IN nodes | x.uuid] AS uuids
        """
        dup_records, _, _ = await driver.execute_query(dup_query, gid=gid)
        total_dups = sum(r["cnt"] - 1 for r in dup_records)
        stats["duplicates_merged"] = total_dups

        if not dry_run and dup_records:
            # For each set of duplicates, keep the first (most recently created),
            # transfer relationships from others, then delete others.
            merge_query = """
            MATCH (n:Entity)
            WHERE n.group_id = $gid
            WITH n.name AS name, collect(n) AS nodes, count(*) AS cnt
            WHERE cnt > 1
            WITH name, head(nodes) AS keep, tail(nodes) AS remove
            UNWIND remove AS dup
            OPTIONAL MATCH (dup)-[r_out]->()
            DELETE r_out
            WITH keep, dup
            OPTIONAL MATCH (dup)<-[r_in]-()
            DELETE r_in
            WITH keep, dup
            DETACH DELETE dup
            RETURN count(dup) AS merged
            """
            merge_records, _, _ = await driver.execute_query(merge_query, gid=gid)
            if merge_records:
                stats["duplicates_merged"] = merge_records[0]["merged"]

        # 2. Find superseded/stale facts (invalid_at IS NOT NULL)
        stale_query = """
        MATCH ()-[e:RELATES_TO]->()
        WHERE e.group_id = $gid AND e.invalid_at IS NOT NULL
        RETURN count(e) AS stale_count
        """
        stale_records, _, _ = await driver.execute_query(stale_query, gid=gid)
        stale_count = stale_records[0]["stale_count"] if stale_records else 0
        stats["stale_facts_found"] = stale_count

        if not dry_run and stale_count > 0:
            del_stale_query = """
            MATCH ()-[e:RELATES_TO]->()
            WHERE e.group_id = $gid AND e.invalid_at IS NOT NULL
            DELETE e
            RETURN count(e) AS removed
            """
            del_records, _, _ = await driver.execute_query(del_stale_query, gid=gid)
            stats["stale_facts_removed"] = del_records[0]["removed"] if del_records else 0

        # 3. Find orphan entities (no relationships at all)
        orphan_query = """
        MATCH (n:Entity)
        WHERE n.group_id = $gid
          AND NOT (n)-[]-()
        RETURN count(n) AS orphan_count
        """
        orphan_records, _, _ = await driver.execute_query(orphan_query, gid=gid)
        stats["orphans_found"] = orphan_records[0]["orphan_count"] if orphan_records else 0

        # 4. Delete old episodes (older than max_age_days)
        episode_query = """
        MATCH (ep:Episodic)
        WHERE ep.group_id = $gid
          AND ep.created_at < datetime() - duration({days: $max_age})
        RETURN count(ep) AS old_count
        """
        ep_records, _, _ = await driver.execute_query(
            episode_query, gid=gid, max_age=max_age_days,
        )
        old_ep_count = ep_records[0]["old_count"] if ep_records else 0
        stats["episodes_pruned"] = old_ep_count

        if not dry_run and old_ep_count > 0:
            del_ep_query = """
            MATCH (ep:Episodic)
            WHERE ep.group_id = $gid
              AND ep.created_at < datetime() - duration({days: $max_age})
            DETACH DELETE ep
            RETURN count(ep) AS pruned
            """
            del_ep_records, _, _ = await driver.execute_query(
                del_ep_query, gid=gid, max_age=max_age_days,
            )
            stats["episodes_pruned"] = del_ep_records[0]["pruned"] if del_ep_records else 0

        # 5. Consolidate duplicate facts: same source+target+relation_type, keep latest
        dup_fact_query = """
        MATCH (a:Entity)-[e:RELATES_TO]->(b:Entity)
        WHERE e.group_id = $gid AND e.invalid_at IS NULL
        WITH a, b, e.name AS rel_name, collect(e) AS edges, count(*) AS cnt
        WHERE cnt > 1
        RETURN count(*) AS dup_fact_groups,
               sum(cnt - 1) AS removable
        """
        df_records, _, _ = await driver.execute_query(dup_fact_query, gid=gid)
        removable = df_records[0]["removable"] if df_records else 0
        stats["duplicate_facts_removed"] = removable

        if not dry_run and removable > 0:
            # Keep the edge with the latest created_at, delete the rest
            dedup_fact_query = """
            MATCH (a:Entity)-[e:RELATES_TO]->(b:Entity)
            WHERE e.group_id = $gid AND e.invalid_at IS NULL
            WITH a, b, e.name AS rel_name, collect(e) AS edges, count(*) AS cnt
            WHERE cnt > 1
            WITH edges[0] AS keep, edges[1..] AS remove
            UNWIND remove AS dup_edge
            DELETE dup_edge
            RETURN count(dup_edge) AS removed
            """
            dedup_records, _, _ = await driver.execute_query(dedup_fact_query, gid=gid)
            stats["duplicate_facts_removed"] = dedup_records[0]["removed"] if dedup_records else 0

        return stats

    async def close(self) -> None:
        """Close Graphiti and Neo4j connection."""
        if self._graphiti:
            await self._graphiti.close()
            self._initialized = False
            logger.info("GraphService closed.")
