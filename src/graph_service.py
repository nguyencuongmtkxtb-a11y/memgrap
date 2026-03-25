"""Graphiti wrapper service — init, add memory, search, status."""

import logging
import os
from datetime import datetime, timezone

from graphiti_core import Graphiti
from graphiti_core.nodes import EpisodeType
from graphiti_core.search.search_config_recipes import (
    EDGE_HYBRID_SEARCH_RRF,
    NODE_HYBRID_SEARCH_RRF,
)
from graphiti_core.search.search_config import SearchResults

from src.config import Settings
from src.entity_types import ENTITY_TYPES
from src.graphiti_factory import create_graphiti
from src.result_formatters import format_edge, format_node, format_episode

logger = logging.getLogger(__name__)


class GraphService:
    """Wraps Graphiti Core with lazy initialization and developer-memory defaults."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._graphiti: Graphiti | None = None
        self._initialized = False

    async def initialize(self) -> None:
        """Connect to Neo4j, create Graphiti instance, build indices. Idempotent."""
        if self._initialized:
            return
        os.environ["SEMAPHORE_LIMIT"] = str(self._settings.semaphore_limit)
        self._graphiti = create_graphiti(self._settings)
        await self._graphiti.build_indices_and_constraints()
        self._initialized = True
        logger.info("GraphService initialized — Neo4j connected, indices built.")

    @property
    def graphiti(self) -> Graphiti:
        if self._graphiti is None:
            raise RuntimeError("GraphService not initialized. Call initialize() first.")
        return self._graphiti

    async def add_memory(self, content: str, source: str = "claude_code", name: str | None = None) -> dict:
        """Ingest text into the knowledge graph. Returns extracted entity/fact summary."""
        episode_name = name or f"memory-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}"
        result = await self.graphiti.add_episode(
            name=episode_name,
            episode_body=content,
            source=EpisodeType.text,
            source_description=source,
            reference_time=datetime.now(timezone.utc),
            group_id=self._settings.group_id,
            entity_types=ENTITY_TYPES,
        )
        return {
            "episode": episode_name,
            "nodes_count": len(result.nodes) if result.nodes else 0,
            "edges_count": len(result.edges) if result.edges else 0,
            "nodes": [n.name for n in (result.nodes or [])],
            "facts": [e.fact for e in (result.edges or [])],
        }

    async def recall(self, query: str, num_results: int = 10) -> list[dict]:
        """Hybrid search for facts (edges). Returns temporal fact list."""
        edges = await self.graphiti.search(
            query=query, group_ids=[self._settings.group_id], num_results=num_results,
        )
        return [format_edge(e) for e in edges]

    async def search_nodes(self, query: str, num_results: int = 10) -> list[dict]:
        """Search entity nodes via NODE_HYBRID_SEARCH_RRF recipe (public API)."""
        config = NODE_HYBRID_SEARCH_RRF.model_copy(deep=True)
        config.limit = num_results
        results: SearchResults = await self.graphiti.search_(
            query=query, config=config, group_ids=[self._settings.group_id],
        )
        return [format_node(n) for n in (results.nodes or [])]

    async def search_facts(self, query: str, num_results: int = 10) -> list[dict]:
        """Search relationship edges via EDGE_HYBRID_SEARCH_RRF recipe (public API)."""
        config = EDGE_HYBRID_SEARCH_RRF.model_copy(deep=True)
        config.limit = num_results
        results: SearchResults = await self.graphiti.search_(
            query=query, config=config, group_ids=[self._settings.group_id],
        )
        return [format_edge(e) for e in (results.edges or [])]

    async def get_episodes(self, last_n: int = 10) -> list[dict]:
        """Retrieve recent episodes (raw ingested data)."""
        episodes = await self.graphiti.retrieve_episodes(
            reference_time=datetime.now(timezone.utc),
            group_ids=[self._settings.group_id], last_n=last_n,
        )
        return [format_episode(ep) for ep in episodes]

    async def get_status(self) -> dict:
        """Health check — verify Neo4j connection and return basic stats."""
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
            return {"status": "error", "error": str(e), "initialized": self._initialized}

    async def close(self) -> None:
        """Close Graphiti and Neo4j connection."""
        if self._graphiti:
            await self._graphiti.close()
            self._initialized = False
            logger.info("GraphService closed.")
