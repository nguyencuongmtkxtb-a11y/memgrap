"""Shared Neo4j connection helper for session scripts.

Reads credentials from src.config.Settings (same .env as MCP server).
Uses the synchronous neo4j Python driver — no asyncio needed for scripts.
"""

from neo4j import GraphDatabase

from src.config import get_settings


def get_neo4j_driver():
    """Create a Neo4j driver using settings from .env."""
    settings = get_settings()
    return GraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_user, settings.neo4j_password),
        connection_timeout=2,
    )
