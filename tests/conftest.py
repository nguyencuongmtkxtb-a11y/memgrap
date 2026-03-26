"""Shared test fixtures and marker registration."""

import pytest


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line("markers", "integration: requires running Neo4j instance")


@pytest.fixture(autouse=True)
def _clear_settings_cache():
    """Clear lru_cache on get_settings between tests for isolation."""
    yield
    from src.config import get_settings
    get_settings.cache_clear()
