"""FastMCP server exposing Graphiti knowledge graph as tools for Claude Code.

Transport: stdio (local process spawned by Claude Code).
All logging goes to stderr — stdout is reserved for MCP JSON-RPC messages.
"""

import json
import logging
import sys

from mcp.server.fastmcp import FastMCP

from src.config import get_settings
from src.graph_service import GraphService

# Logging to stderr only — stdout is MCP protocol
logging.basicConfig(
    level=logging.INFO,
    stream=sys.stderr,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("memgrap")

# --- Server & service setup ---

mcp = FastMCP(
    "Graphiti Memory",
    instructions=(
        "Persistent memory for Claude Code backed by a temporal knowledge graph. "
        "Use 'remember' to store decisions, patterns, context. "
        "Use 'recall' to retrieve relevant memories via semantic search. "
        "Facts track temporal validity — the graph knows when things changed."
    ),
)

settings = get_settings()
graph_service = GraphService(settings)


async def _ensure_init() -> None:
    """Lazy init: connect to Neo4j + build indices on first tool call."""
    await graph_service.initialize()


def _fmt(data: object) -> str:
    """Format dict/list as readable JSON string for MCP response."""
    return json.dumps(data, indent=2, ensure_ascii=False, default=str)


# --- MCP Tools ---


@mcp.tool()
async def remember(
    content: str,
    source: str = "claude_code",
    name: str | None = None,
) -> str:
    """Store information into the knowledge graph.

    Automatically extracts entities, relationships, and facts.
    Use for: decisions, code patterns, project context, user preferences, bug reports.

    Args:
        content: The text to remember (e.g. "We chose PostgreSQL because...")
        source: Source label (default: claude_code)
        name: Optional episode name
    """
    await _ensure_init()
    try:
        result = await graph_service.add_memory(content=content, source=source, name=name)
        return f"Stored. Extracted {result['nodes_count']} entities, {result['edges_count']} facts.\nEntities: {result['nodes']}\nFacts: {result['facts']}"
    except Exception as e:
        logger.error("remember failed: %s", e)
        return f"Error storing memory: {e}"


@mcp.tool()
async def recall(query: str, num_results: int = 10) -> str:
    """Search the knowledge graph for relevant memories.

    Returns facts (relationships between entities) ranked by relevance.
    Facts include temporal validity — when they became true and if superseded.

    Args:
        query: Natural language query (e.g. "What auth approach did we choose?")
        num_results: Max results to return (default: 10)
    """
    await _ensure_init()
    try:
        results = await graph_service.recall(query=query, num_results=num_results)
        if not results:
            return "No relevant memories found."
        return _fmt(results)
    except Exception as e:
        logger.error("recall failed: %s", e)
        return f"Error recalling: {e}"


@mcp.tool()
async def understand_code(query: str, num_results: int = 10) -> str:
    """Search for code-related entities: patterns, tools, libraries, decisions.

    Returns entity nodes with names, summaries, and labels.

    Args:
        query: What to search for (e.g. "authentication patterns")
        num_results: Max results (default: 10)
    """
    await _ensure_init()
    try:
        results = await graph_service.search_nodes(query=query, num_results=num_results)
        if not results:
            return "No code entities found."
        return _fmt(results)
    except Exception as e:
        logger.error("understand_code failed: %s", e)
        return f"Error searching code entities: {e}"


@mcp.tool()
async def get_history(last_n: int = 10) -> str:
    """Get the timeline of recently stored memories (episodes).

    Shows what information was stored and when. Useful for session review.

    Args:
        last_n: Number of recent episodes to retrieve (default: 10)
    """
    await _ensure_init()
    try:
        episodes = await graph_service.get_episodes(last_n=last_n)
        if not episodes:
            return "No memory history found."
        return _fmt(episodes)
    except Exception as e:
        logger.error("get_history failed: %s", e)
        return f"Error retrieving history: {e}"


@mcp.tool()
async def search_nodes(query: str, num_results: int = 10) -> str:
    """Find specific entities (people, tools, concepts, decisions) in the graph.

    Returns entities with names, types/labels, and summaries.

    Args:
        query: Natural language query
        num_results: Max results (default: 10)
    """
    await _ensure_init()
    try:
        results = await graph_service.search_nodes(query=query, num_results=num_results)
        if not results:
            return "No entities found."
        return _fmt(results)
    except Exception as e:
        logger.error("search_nodes failed: %s", e)
        return f"Error searching nodes: {e}"


@mcp.tool()
async def search_facts(query: str, num_results: int = 10) -> str:
    """Find facts (relationships between entities) in the knowledge graph.

    Facts are temporal — they track when something became true and when superseded.
    Useful for understanding how decisions or context evolved over time.

    Args:
        query: Natural language query
        num_results: Max results (default: 10)
    """
    await _ensure_init()
    try:
        results = await graph_service.search_facts(query=query, num_results=num_results)
        if not results:
            return "No facts found."
        return _fmt(results)
    except Exception as e:
        logger.error("search_facts failed: %s", e)
        return f"Error searching facts: {e}"


@mcp.tool()
async def get_status() -> str:
    """Check health of the memory system.

    Returns: Neo4j connection status, config info, initialization state.
    """
    await _ensure_init()
    status = await graph_service.get_status()
    return _fmt(status)


# --- Entry point ---

if __name__ == "__main__":
    mcp.run(transport="stdio")
