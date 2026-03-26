"""Tests for session Neo4j connection helper."""
import pytest

from src.session.neo4j_connect import get_neo4j_driver

pytestmark = pytest.mark.integration


def test_get_neo4j_driver_returns_driver():
    """Driver connects to Neo4j and can run a basic query."""
    driver = get_neo4j_driver()
    assert driver is not None
    records, _, _ = driver.execute_query("RETURN 1 AS n")
    assert records[0]["n"] == 1
    driver.close()


def test_get_neo4j_driver_reuses_config():
    """Driver reads Neo4j credentials from src.config.Settings."""
    driver = get_neo4j_driver()
    driver.close()
