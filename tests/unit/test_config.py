"""Unit tests for src.config — Settings defaults, env overrides, caching."""

from src.config import Settings, get_settings

# ---------------------------------------------------------------------------
# Default values
# ---------------------------------------------------------------------------


def test_default_settings_values(monkeypatch):
    """Verify all default values when no env vars are set."""
    # Clear env vars that could leak from the host or .env file
    env_keys = [
        "NEO4J_URI", "NEO4J_USER", "NEO4J_PASSWORD",
        "OPENAI_API_KEY", "LLM_MODEL", "LLM_SMALL_MODEL",
        "EMBEDDING_MODEL", "GROUP_ID", "SEMAPHORE_LIMIT",
    ]
    for key in env_keys:
        monkeypatch.delenv(key, raising=False)

    s = Settings(_env_file=None)  # skip .env file
    assert s.neo4j_uri == "bolt://localhost:7687"
    assert s.neo4j_user == "neo4j"
    assert s.neo4j_password == "password"
    assert s.openai_api_key == ""
    assert s.llm_model == "gpt-4o-mini"
    assert s.llm_small_model == "gpt-4o-mini"
    assert s.embedding_model == "text-embedding-3-small"
    assert s.group_id == "default"
    assert s.semaphore_limit == 5


# ---------------------------------------------------------------------------
# Environment override
# ---------------------------------------------------------------------------


def test_env_override(monkeypatch):
    """Env vars should override defaults when constructing Settings directly."""
    monkeypatch.setenv("NEO4J_URI", "bolt://custom:7688")
    monkeypatch.setenv("NEO4J_USER", "admin")
    monkeypatch.setenv("NEO4J_PASSWORD", "s3cret")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")
    monkeypatch.setenv("GROUP_ID", "project-x")
    monkeypatch.setenv("SEMAPHORE_LIMIT", "10")

    s = Settings(_env_file=None)
    assert s.neo4j_uri == "bolt://custom:7688"
    assert s.neo4j_user == "admin"
    assert s.neo4j_password == "s3cret"
    assert s.openai_api_key == "sk-test-key"
    assert s.group_id == "project-x"
    assert s.semaphore_limit == 10


# ---------------------------------------------------------------------------
# Caching
# ---------------------------------------------------------------------------


def test_get_settings_cached():
    """get_settings() uses lru_cache so two calls return the same object."""
    a = get_settings()
    b = get_settings()
    assert a is b
