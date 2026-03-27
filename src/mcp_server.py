"""FastMCP server exposing Graphiti knowledge graph as tools for Claude Code.

Transport: stdio (local process spawned by Claude Code).
All logging goes to stderr — stdout is reserved for MCP JSON-RPC messages.
"""

import asyncio
import atexit
import json
import logging
import os
import sys
import urllib.request
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from src.code_graph_service import CodeGraphService
from src.config import get_settings
from src.graph_service import GraphService

# Logging to stderr only — stdout is MCP protocol
logging.basicConfig(
    level=logging.INFO,
    stream=sys.stderr,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("memgrap")

# --- Auto-detect project from CWD ---
# NOTE: When running as MCP subprocess, CWD is always MEMGRAP (fixed in config).
# The real project is passed by Claude via the `project` parameter on each tool call.
# This fallback is only used when `project` param is empty AND no env override.
_current_project: str = os.environ.get("MEMGRAP_PROJECT", "") or Path.cwd().name

# --- Server & service setup ---

mcp = FastMCP(
    "Graphiti Memory",
    instructions=(
        "Persistent memory for Claude Code backed by a temporal knowledge graph. "
        "Use 'remember' to store decisions, patterns, context. "
        "Use 'recall' to retrieve relevant memories via semantic search. "
        "Facts track temporal validity — the graph knows when things changed.\n\n"
        "IMPORTANT: Always pass the `project` parameter with the current project's "
        "folder name (e.g. 'goclaw', 'QuanNet'). The MCP server runs in a fixed "
        "directory and cannot auto-detect which project you are working on."
    ),
)

settings = get_settings()
graph_service = GraphService(settings)
code_graph = CodeGraphService(settings)


_consolidation_done = False
_registered_projects: set[str] = set()


async def _register_project(project: str) -> None:
    """Register a project in Neo4j if seen for the first time.

    Creates a lightweight marker node so the project is discoverable
    via dashboard queries even before any memories are stored.
    """
    if not project or project in _registered_projects:
        return
    _registered_projects.add(project)
    try:
        driver = graph_service.graphiti.driver
        async with driver.session() as session:
            await session.run(
                "MERGE (p:Project {name: $name}) "
                "ON CREATE SET p.created_at = datetime(), p.source = 'auto_register'",
                name=project,
            )
        logger.info("Auto-registered project: %s", project)
    except Exception as e:
        logger.warning("Failed to register project '%s': %s", project, e)


async def _ensure_init() -> None:
    """Lazy init: connect to Neo4j + build indices on first tool call.

    Validates OpenAI API key before attempting Graphiti init so the user
    gets a clear error instead of a cryptic downstream failure.
    Auto-runs consolidate_memory (phases 1-5, zero OpenAI cost) on first init.
    """
    global _consolidation_done

    if not settings.openai_api_key:
        raise RuntimeError(
            "OPENAI_API_KEY is not set. "
            "Add it to your .env file or set the environment variable. "
            "See .env.example for reference."
        )
    # Set auto-detected project as default group_id for Graphiti
    if _current_project:
        graph_service._settings.group_id = _current_project
    await graph_service.initialize()
    # Auto-register default project
    if _current_project:
        await _register_project(_current_project)

    # Auto-consolidate on first init (phases 1-5 only, zero OpenAI cost)
    if not _consolidation_done:
        _consolidation_done = True
        try:
            stats = await graph_service.consolidate_memory(
                dry_run=False, use_ai=False,
            )
            cleaned = (
                stats["duplicates_merged"] + stats["stale_facts_removed"]
                + stats["episodes_pruned"] + stats["duplicate_facts_removed"]
            )
            if cleaned > 0:
                logger.info("Auto-consolidation cleaned %d items: %s", cleaned, stats)
        except Exception as e:
            logger.warning("Auto-consolidation skipped: %s", e)


def _fmt(data: object) -> str:
    """Format dict/list as readable JSON string for MCP response."""
    return json.dumps(data, indent=2, ensure_ascii=False, default=str)


def _notify_dashboard(event: str, project: str | None = None) -> None:
    """Fire-and-forget notification to dashboard SSE."""
    try:
        url = f"{settings.dashboard_url}/api/notify"
        payload = json.dumps({"event": event, "project": project}).encode()
        req = urllib.request.Request(
            url, data=payload, headers={"Content-Type": "application/json"},
        )
        urllib.request.urlopen(req, timeout=2)
    except Exception:
        pass  # Dashboard may not be running


# --- MCP Tools ---


@mcp.tool()
async def remember(
    content: str,
    source: str = "claude_code",
    name: str | None = None,
    project: str = "",
) -> str:
    """Store information into the knowledge graph.

    Automatically extracts entities, relationships, and facts.
    Use for: decisions, code patterns, project context, user preferences, bug reports.

    Args:
        content: The text to remember (e.g. "We chose PostgreSQL because...")
        source: Source label (default: claude_code)
        name: Optional episode name
        project: Optional project name to isolate memories per project
    """
    await _ensure_init()
    try:
        gid = project or _current_project or None
        await _register_project(gid)
        result = await graph_service.add_memory(content=content, source=source, name=name, group_id=gid)
        _notify_dashboard("entity:created")
        return (
            f"Stored. Extracted {result['nodes_count']} entities, "
            f"{result['edges_count']} facts.\n"
            f"Entities: {result['nodes']}\nFacts: {result['facts']}"
        )
    except Exception as e:
        logger.error("remember failed: %s", e)
        return f"Error storing memory: {e}"


@mcp.tool()
async def recall(query: str, num_results: int = 10, project: str = "") -> str:
    """Search the knowledge graph for relevant memories.

    Returns facts (relationships between entities) ranked by relevance.
    Facts include temporal validity — when they became true and if superseded.

    Args:
        query: Natural language query (e.g. "What auth approach did we choose?")
        num_results: Max results to return (default: 10)
        project: Optional project filter
    """
    await _ensure_init()
    try:
        gid = project or _current_project or None
        results = await graph_service.recall(query=query, num_results=num_results, group_id=gid)
        if not results:
            return "No relevant memories found."
        return _fmt(results)
    except Exception as e:
        logger.error("recall failed: %s", e)
        return f"Error recalling: {e}"


@mcp.tool()
async def understand_code(query: str, num_results: int = 10, project: str = "") -> str:
    """Search for code-related entities: patterns, tools, libraries, decisions.

    Returns entity nodes with names, summaries, and labels.

    Args:
        query: What to search for (e.g. "authentication patterns")
        num_results: Max results (default: 10)
        project: Optional project filter
    """
    await _ensure_init()
    try:
        gid = project or _current_project or None
        results = await graph_service.search_nodes(query=query, num_results=num_results, group_id=gid)
        if not results:
            return "No code entities found."
        return _fmt(results)
    except Exception as e:
        logger.error("understand_code failed: %s", e)
        return f"Error searching code entities: {e}"


@mcp.tool()
async def get_history(last_n: int = 10, project: str = "") -> str:
    """Get the timeline of recently stored memories (episodes).

    Shows what information was stored and when. Useful for session review.

    Args:
        last_n: Number of recent episodes to retrieve (default: 10)
        project: Optional project filter
    """
    await _ensure_init()
    try:
        gid = project or _current_project or None
        episodes = await graph_service.get_episodes(last_n=last_n, group_id=gid)
        if not episodes:
            return "No memory history found."
        return _fmt(episodes)
    except Exception as e:
        logger.error("get_history failed: %s", e)
        return f"Error retrieving history: {e}"


@mcp.tool()
async def search_facts(query: str, num_results: int = 10, project: str = "") -> str:
    """Find facts (relationships between entities) in the knowledge graph.

    Facts are temporal — they track when something became true and when superseded.
    Useful for understanding how decisions or context evolved over time.

    Args:
        query: Natural language query
        num_results: Max results (default: 10)
        project: Optional project filter
    """
    await _ensure_init()
    try:
        gid = project or _current_project or None
        results = await graph_service.search_facts(query=query, num_results=num_results, group_id=gid)
        if not results:
            return "No facts found."
        return _fmt(results)
    except Exception as e:
        logger.error("search_facts failed: %s", e)
        return f"Error searching facts: {e}"


@mcp.tool()
async def index_codebase(
    path: str,
    extensions: str | None = None,
    full: bool = False,
) -> str:
    """Index a codebase directory into the knowledge graph.

    Parses source files with tree-sitter, extracts functions/classes/imports,
    and writes them directly to Neo4j for code intelligence queries.

    By default uses incremental mode (only new/changed files). Set full=True
    to force a complete re-index of all files.

    Args:
        path: Directory path to index (e.g. "D:/myproject/src")
        extensions: Comma-separated extensions (default: all supported)
            Supported: .py,.js,.ts,.tsx,.jsx,.go,.rs,.java,.c,.cpp,.cs,.rb,.php,.kt,.swift
        full: Force full re-index instead of incremental (default: False)
    """
    await _ensure_init()
    try:
        ext_set = None
        if extensions:
            ext_set = {e.strip() if e.startswith(".") else f".{e.strip()}" for e in extensions.split(",")}

        from pathlib import Path as _Path
        project_name = _Path(path).name

        if not full:
            # Incremental mode — only index new/changed files
            from src.indexer.incremental_indexer import run_incremental_index
            stats = await run_incremental_index(path, extensions=ext_set, project=project_name)
            _notify_dashboard("code:indexed", project_name)
            return _fmt({"status": "indexed_incremental", "path": path, **stats})

        # Full mode — re-index everything
        from src.indexer.ast_parser import parse_directory
        from src.indexer.neo4j_ingestor import CodeIndexer
        from src.indexer.relation_extractor import extract_relations

        symbols = parse_directory(path, extensions=ext_set)
        indexer = CodeIndexer(graph_service.graphiti.driver, project=project_name)
        stats = await indexer.index_symbols(symbols)

        # Phase 2: Extract and ingest code relationships (calls, extends, imports_from)
        unique_files = {s.file_path for s in symbols}
        all_relations = []
        for fp in unique_files:
            all_relations.extend(extract_relations(fp))
        rel_stats = {}
        if all_relations:
            rel_stats = await indexer.index_relations(all_relations)
        stats["relations"] = rel_stats

        _notify_dashboard("code:indexed", project_name)
        return _fmt({"status": "indexed_full", "path": path, "symbols": len(symbols), **stats})
    except Exception as e:
        logger.error("index_codebase failed: %s", e)
        return f"Error indexing codebase: {e}"


@mcp.tool()
async def get_status() -> str:
    """Check health of the memory system.

    Returns: Neo4j connection status, config info, initialization state.
    """
    await _ensure_init()
    status = await graph_service.get_status()
    status["current_project"] = _current_project
    return _fmt(status)


@mcp.tool()
async def consolidate_memory(
    max_age_days: int = 30,
    dry_run: bool = True,
    use_ai: bool = False,
    project: str = "",
) -> str:
    """Consolidate and clean up the knowledge graph memory.

    Reviews all stored memories, removes stale/duplicate data,
    merges related insights, and updates temporal validity.
    Phases 1-5 use direct Cypher queries (zero OpenAI cost).
    Phase 6 (opt-in) uses OpenAI LLM for semantic dedup, conflict resolution,
    and fact summarization.

    Args:
        max_age_days: Remove episodes older than this (default: 30)
        dry_run: If true, only report what would be cleaned (default: true)
        use_ai: If true, use OpenAI LLM for semantic analysis (costs API tokens)
        project: Optional project filter
    """
    await _ensure_init()
    try:
        gid = project or _current_project or None
        stats = await graph_service.consolidate_memory(
            group_id=gid,
            max_age_days=max_age_days,
            dry_run=dry_run,
            use_ai=use_ai,
        )
        if not dry_run:
            _notify_dashboard("memory:consolidated", gid)

        mode = "DRY RUN" if dry_run else "EXECUTED"
        lines = [
            f"Memory consolidation ({mode}):",
            f"  Duplicate entities merged: {stats['duplicates_merged']}",
            f"  Stale facts (superseded): {stats['stale_facts_found']}",
            f"  Stale facts removed: {stats['stale_facts_removed']}",
            f"  Orphan entities (no relations): {stats['orphans_found']}",
            f"  Old episodes pruned (>{max_age_days}d): {stats['episodes_pruned']}",
            f"  Duplicate facts consolidated: {stats['duplicate_facts_removed']}",
        ]
        # Append AI stats if AI analysis was used
        if use_ai:
            lines.append("  --- AI Semantic Analysis ---")
            lines.append(f"  AI semantic merges: {stats.get('ai_semantic_merges', 0)}")
            lines.append(f"  AI conflicts resolved: {stats.get('ai_conflicts_resolved', 0)}")
            lines.append(f"  AI facts summarized: {stats.get('ai_facts_summarized', 0)}")
        return "\n".join(lines)
    except Exception as e:
        logger.error("consolidate_memory failed: %s", e)
        return f"Error consolidating memory: {e}"


@mcp.tool()
async def delete_project(project: str, confirm: bool = False) -> str:
    """Delete ALL data for a project from the knowledge graph.

    Removes entities, episodes, facts, code index, sessions, and project marker.
    This is IRREVERSIBLE. Set confirm=True to execute.

    Args:
        project: Project name to delete (required, cannot be empty)
        confirm: Safety flag — must be True to actually delete (default: False)
    """
    await _ensure_init()
    if not project:
        return "Error: project name is required. Cannot delete without specifying which project."
    if not confirm:
        return (
            f"⚠ DRY RUN: This would delete ALL data for project '{project}' "
            f"(entities, episodes, facts, code index, sessions). "
            f"To execute, call again with confirm=True."
        )
    try:
        stats = await graph_service.delete_project(group_id=project)
        _registered_projects.discard(project)
        _notify_dashboard("project:deleted", project)
        lines = [
            f"Project '{project}' deleted:",
            f"  Entities: {stats['entities_deleted']}",
            f"  Episodes: {stats['episodes_deleted']}",
            f"  Facts: {stats['facts_deleted']}",
            f"  Code files: {stats['code_files_deleted']}",
            f"  Code functions: {stats['code_functions_deleted']}",
            f"  Code classes: {stats['code_classes_deleted']}",
            f"  Code imports: {stats['code_imports_deleted']}",
            f"  Sessions: {stats['sessions_deleted']}",
            f"  Project node: {stats['project_node_deleted']}",
            f"  Total: {stats['total_deleted']} items",
        ]
        return "\n".join(lines)
    except Exception as e:
        logger.error("delete_project failed: %s", e)
        return f"Error deleting project: {e}"


# --- Code Graph Tools (zero OpenAI cost — direct Neo4j queries) ---


@mcp.tool()
async def find_callers(function_name: str, project: str = "") -> str:
    """Find all functions that call a given function.

    Use for impact analysis: before modifying a function, check who calls it.

    Args:
        function_name: Name of the function to find callers for
        project: Optional project filter
    """
    try:
        results = await code_graph.find_callers(function_name, project or _current_project)
        if not results:
            return f"No callers found for '{function_name}'."
        return _fmt(results)
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
async def find_callees(function_name: str, project: str = "") -> str:
    """Find all functions that a given function calls.

    Use for understanding execution flow and dependencies.

    Args:
        function_name: Name of the function to analyze
        project: Optional project filter
    """
    try:
        results = await code_graph.find_callees(function_name, project or _current_project)
        if not results:
            return f"No callees found for '{function_name}'."
        return _fmt(results)
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
async def find_class_hierarchy(class_name: str, project: str = "") -> str:
    """Find parent and child classes for a given class.

    Shows inheritance relationships: what a class extends and what extends it.

    Args:
        class_name: Name of the class to analyze
        project: Optional project filter
    """
    try:
        results = await code_graph.find_class_hierarchy(class_name, project or _current_project)
        if not results:
            return f"No hierarchy found for '{class_name}'."
        return _fmt(results)
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
async def find_file_imports(file_path: str, project: str = "") -> str:
    """Find import relationships for a file.

    Shows what files this file imports and what files import this file.
    Useful for tracing data flow and understanding module dependencies.

    Args:
        file_path: File path (or suffix like 'server.py')
        project: Optional project filter
    """
    try:
        results = await code_graph.find_file_imports(file_path, project or _current_project)
        if not results:
            return f"No import relationships found for '{file_path}'."
        return _fmt(results)
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
async def search_code(query: str, project: str = "", limit: int = 20) -> str:
    """Search indexed code symbols by name.

    Searches functions, classes, and files. Use for discovering code structure.

    Args:
        query: Search term (case-insensitive substring match)
        project: Optional project filter
        limit: Max results (default: 20)
    """
    try:
        results = await code_graph.search_code(query, project or _current_project, limit)
        if not results:
            return f"No code symbols matching '{query}'."
        return _fmt(results)
    except Exception as e:
        return f"Error: {e}"


# --- Lifecycle ---

def _cleanup() -> None:
    """Close Neo4j connection on process exit.

    Uses asyncio.run() which is safe in atexit handlers (Python 3.10+).
    Falls back silently if the event loop is already closed.
    """
    try:
        asyncio.run(graph_service.close())
    except (RuntimeError, Exception):
        pass
    try:
        asyncio.run(code_graph.close())
    except (RuntimeError, Exception):
        pass

atexit.register(_cleanup)

if __name__ == "__main__":
    mcp.run(transport="stdio")
