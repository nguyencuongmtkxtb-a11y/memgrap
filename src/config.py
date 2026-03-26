"""Configuration management via pydantic-settings + .env file.

Resolves .env from project root (parent of src/) so it works
regardless of the working directory the process is launched from.
"""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Project root = parent of the `src/` package that contains this file
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_ENV_FILE = _PROJECT_ROOT / ".env"


class Settings(BaseSettings):
    """All configuration loaded from environment variables / .env file."""

    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Neo4j connection
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "password"

    # OpenAI — used for both LLM extraction and embeddings
    openai_api_key: str = ""
    llm_model: str = "gpt-4o-mini"
    llm_small_model: str = "gpt-4o-mini"
    embedding_model: str = "text-embedding-3-small"

    # Graphiti settings
    group_id: str = "default"
    semaphore_limit: int = 5


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Cached singleton — avoids re-parsing .env on every call."""
    return Settings()
