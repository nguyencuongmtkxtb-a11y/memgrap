"""Factory to create configured Graphiti instance with OpenAI LLM + embedder."""

from graphiti_core import Graphiti
from graphiti_core.embedder.openai import OpenAIEmbedder, OpenAIEmbedderConfig
from graphiti_core.llm_client.config import LLMConfig
from graphiti_core.llm_client.openai_client import OpenAIClient

from src.config import Settings


def create_graphiti(settings: Settings) -> Graphiti:
    """Build a Graphiti instance from Settings. Uses OpenAI for both LLM and embeddings."""
    llm_client = OpenAIClient(
        config=LLMConfig(
            api_key=settings.openai_api_key,
            model=settings.llm_model,
            small_model=settings.llm_small_model,
        )
    )

    embedder = OpenAIEmbedder(
        config=OpenAIEmbedderConfig(
            api_key=settings.openai_api_key,
            embedding_model=settings.embedding_model,
        )
    )

    return Graphiti(
        settings.neo4j_uri,
        settings.neo4j_user,
        settings.neo4j_password,
        llm_client=llm_client,
        embedder=embedder,
    )
