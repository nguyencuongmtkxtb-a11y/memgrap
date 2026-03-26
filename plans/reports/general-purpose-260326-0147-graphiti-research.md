# Graphiti Research Report

**Date:** 2026-03-26
**Repo:** https://github.com/getzep/graphiti
**Version:** 0.28.2 (core) / MCP v1.0.2
**License:** Apache 2.0
**Stars:** 24,206 | **Forks:** 2,396

---

## 1. What Is Graphiti?

Graphiti is an **open-source Python framework for building and querying temporal knowledge graphs** designed for AI agent memory. Built by Zep Software.

### Core Problem Solved
Traditional RAG uses batch processing + static document chunks. Graphiti provides **continuous, incremental knowledge graph construction** where facts evolve over time rather than being treated as static.

### Architecture - Data Model

Four primary elements in a context graph:

| Element | Description |
|---------|-------------|
| **Entities (EntityNode)** | People, products, concepts - nodes with summaries that evolve over time, custom labels, attributes dict |
| **Facts (EntityEdge)** | Relationship triplets (source_node -> fact -> target_node) with **temporal validity windows** (valid_at, invalid_at) |
| **Episodes (EpisodicNode)** | Raw ingested data - every derived fact traces back to source episodes. Types: `message`, `json`, `text` |
| **Communities (CommunityNode)** | Auto-detected clusters of related entities with generated summaries |

Additional structures:
- **SagaNode** - groups episodes into ordered sequences (e.g., a conversation thread)
- **EpisodicEdge** - connects episodes to entities they mention
- **CommunityEdge** - connects entities to their communities
- **HasEpisodeEdge / NextEpisodeEdge** - saga-to-episode and episode ordering

### Temporal Tracking (Key Differentiator)
- Facts have **bi-temporal tracking**: when they became true (`valid_at`) and when superseded (`invalid_at`)
- Old facts are **invalidated, not deleted** - preserves complete historical lineage
- Enables "what was true at time X?" queries

### Processing Pipeline (add_episode)
1. Receive raw text/JSON episode
2. Retrieve previous episodes for context
3. **Extract entities** (nodes) via LLM
4. **Resolve entities** against existing graph (deduplication)
5. **Extract relationships** (edges/facts) via LLM
6. **Resolve edges** - detect contradictions, invalidate old facts
7. **Extract attributes** for nodes
8. Save everything to graph DB
9. Optionally update communities

---

## 2. Key Features

- **Temporal fact management** - validity windows, auto-invalidation of superseded info
- **Hybrid retrieval** - combines semantic embeddings + BM25 keyword search + graph traversal (BFS)
- **Multiple reranking strategies** - RRF, MMR, cross-encoder, node_distance, episode_mentions
- **Episode-based provenance** - full lineage from derived facts to source data
- **Flexible ontology** - prescribed (Pydantic models) or learned (emergent from data)
- **Incremental construction** - no batch recomputation needed
- **Bulk ingestion** - `add_episode_bulk()` for parallel processing of multiple episodes
- **Community detection** - automatic clustering of related entities with summaries
- **Saga support** - ordered episode sequences for conversation threads
- **Graph namespacing** - `group_id` isolates data partitions (multi-tenant)
- **Direct triplet insertion** - `add_triplet()` for pre-structured facts
- **CRUD on nodes/edges** - via `graphiti.nodes` and `graphiti.edges` namespace APIs
- **Token tracking** - built-in LLM token usage monitoring
- **OpenTelemetry tracing** - distributed tracing support
- **MCP server** - Model Context Protocol server for AI assistant integration
- **REST API server** - FastAPI-based HTTP service

---

## 3. Tech Stack

### Language
- **Python 3.10+** (async-first, uses asyncio throughout)

### Core Dependencies
| Package | Purpose |
|---------|---------|
| `pydantic>=2.11.5` | Data models, validation, ontology definitions |
| `neo4j>=5.26.0` | Default graph database driver |
| `openai>=1.91.0` | Default LLM + embeddings |
| `tenacity>=9.0.0` | Retry logic |
| `numpy>=1.0.0` | Embedding operations |
| `python-dotenv>=1.0.1` | Environment config |
| `posthog>=3.0.0` | Anonymous telemetry |

### Graph Database Backends
| Database | Install Extra | Min Version |
|----------|--------------|-------------|
| **Neo4j** | (built-in) | 5.26+ |
| **FalkorDB** | `pip install graphiti-core[falkordb]` | 1.1.2+ |
| **Kuzu** | `pip install graphiti-core[kuzu]` | 0.11.2+ |
| **Amazon Neptune** | `pip install graphiti-core[neptune]` | Database Cluster or Analytics Graph |

### LLM Providers
| Provider | Install Extra | Client Class |
|----------|--------------|-------------|
| **OpenAI** | (built-in) | `OpenAIClient` |
| **Azure OpenAI** | (built-in) | `AzureOpenAILLMClient` |
| **Anthropic** | `[anthropic]` | `AnthropicClient` |
| **Groq** | `[groq]` | `GroqClient` |
| **Google Gemini** | `[google-genai]` | `GeminiClient` |
| **Ollama / OpenAI-compatible** | (built-in) | `OpenAIGenericClient` |
| **GLiNER 2** | `[gliner2]` | `Gliner2Client` (Python 3.11+) |

### Embedder Providers
| Provider | Client Class |
|----------|-------------|
| **OpenAI** | `OpenAIEmbedder` (default) |
| **Azure OpenAI** | `AzureOpenAIEmbedder` |
| **Google Gemini** | `GeminiEmbedder` |
| **Voyage AI** | `VoyageEmbedder` |

### Cross-Encoder / Reranker Providers
| Provider | Client Class |
|----------|-------------|
| **OpenAI** | `OpenAIRerankerClient` (default) |
| **Google Gemini** | `GeminiRerankerClient` |
| **BGE Reranker** | `BGERerankerClient` (sentence-transformers) |

### Build System
- `hatchling` build backend
- `ruff` for linting/formatting
- `pyright` for type checking
- `pytest` + `pytest-asyncio` for testing

---

## 4. API/SDK

### Installation
```bash
pip install graphiti-core
# With extras:
pip install graphiti-core[falkordb,anthropic,groq,google-genai]
```

### Initialization
```python
from graphiti_core import Graphiti
from graphiti_core.nodes import EpisodeType

# Simple (Neo4j + OpenAI defaults)
graphiti = Graphiti("bolt://localhost:7687", "neo4j", "password")

# Custom driver
from graphiti_core.driver.neo4j_driver import Neo4jDriver
driver = Neo4jDriver(uri="bolt://localhost:7687", user="neo4j", password="pw", database="mydb")
graphiti = Graphiti(graph_driver=driver)

# Custom LLM + embedder
from graphiti_core.llm_client.anthropic_client import AnthropicClient
graphiti = Graphiti("bolt://...", "neo4j", "pw",
    llm_client=AnthropicClient(config=LLMConfig(model="claude-sonnet-4-20250514")),
    embedder=OpenAIEmbedder())

# Setup indices (run once)
await graphiti.build_indices_and_constraints()
```

### Core Public API Methods

#### `add_episode()` - Ingest data
```python
result = await graphiti.add_episode(
    name="conversation-1",
    episode_body="Alice told Bob she moved to NYC in January.",
    source_description="chat message",
    reference_time=datetime.now(timezone.utc),
    source=EpisodeType.message,
    group_id="user-123",                    # namespace/tenant isolation
    entity_types={"Person": PersonModel},   # custom ontology (Pydantic)
    edge_types={"WORKS_AT": WorksAtModel},  # custom relationship types
    update_communities=True,                # rebuild community summaries
    saga="conversation-thread-1",           # group into ordered saga
)
# Returns: AddEpisodeResults(episode, episodic_edges, nodes, edges, communities, community_edges)
```

#### `add_episode_bulk()` - Parallel ingestion
```python
from graphiti_core.utils.bulk_utils import RawEpisode
episodes = [RawEpisode(name=..., body=..., source=..., ...)]
result = await graphiti.add_episode_bulk(episodes, group_id="user-123")
```

#### `search()` - Basic hybrid search (returns edges/facts)
```python
edges = await graphiti.search(
    query="Who is the California Attorney General?",
    group_ids=["user-123"],
    num_results=10,
    center_node_uuid="...",      # rerank by graph proximity
    search_filter=SearchFilters(
        edge_types=["WORKS_AT"],
        node_labels=["Person"],
        valid_at=[[DateFilter(date=some_date, comparison_operator=ComparisonOperator.less_than)]],
    ),
)
```

#### `search_()` - Advanced search (returns nodes + edges + communities)
```python
from graphiti_core.search.search_config_recipes import COMBINED_HYBRID_SEARCH_CROSS_ENCODER
results = await graphiti.search_(
    query="California politics",
    config=COMBINED_HYBRID_SEARCH_CROSS_ENCODER,
    group_ids=["user-123"],
    center_node_uuid="...",
    bfs_origin_node_uuids=["..."],
)
# Returns: SearchResults(edges, nodes, episodes, communities)
```

#### `add_triplet()` - Direct fact insertion
```python
result = await graphiti.add_triplet(
    source_node=EntityNode(name="Alice", group_id="g1", ...),
    edge=EntityEdge(name="LIVES_IN", fact="Alice lives in NYC", group_id="g1", ...),
    target_node=EntityNode(name="NYC", group_id="g1", ...),
)
```

#### CRUD via Namespaces
```python
# Nodes
node = await graphiti.nodes.entity.get(uuid="...")
await graphiti.nodes.entity.save(node)
await graphiti.nodes.entity.delete(uuid="...")

# Edges
edge = await graphiti.edges.entity.get(uuid="...")
await graphiti.edges.entity.save(edge)
```

#### Other Methods
- `build_indices_and_constraints()` - DB schema setup
- `build_communities()` - rebuild all community nodes
- `remove_episode(uuid)` - delete episode and its data
- `retrieve_episodes()` - get episodes by time range
- `get_nodes_and_edges_by_episode(uuids)` - get graph data linked to episodes
- `close()` - close DB connection

### Search Configuration Recipes (Pre-built)
| Recipe | Description |
|--------|-------------|
| `COMBINED_HYBRID_SEARCH_RRF` | Hybrid over edges+nodes+communities, RRF reranking |
| `COMBINED_HYBRID_SEARCH_MMR` | Same but MMR reranking |
| `COMBINED_HYBRID_SEARCH_CROSS_ENCODER` | BM25+cosine+BFS, cross-encoder reranking (best quality) |
| `EDGE_HYBRID_SEARCH_RRF` | Edge-only, RRF |
| `EDGE_HYBRID_SEARCH_NODE_DISTANCE` | Edge-only, rerank by graph distance to center node |
| `EDGE_HYBRID_SEARCH_EPISODE_MENTIONS` | Edge-only, rerank by episode mention frequency |
| `EDGE_HYBRID_SEARCH_CROSS_ENCODER` | Edge-only, cross-encoder |
| `NODE_HYBRID_SEARCH_*` | Node-focused variants (RRF, MMR, cross-encoder, etc.) |
| `COMMUNITY_HYBRID_SEARCH_*` | Community-focused variants |

### Search Filters
- `node_labels` - filter by entity type labels
- `edge_types` - filter by relationship type names
- `valid_at` / `invalid_at` / `created_at` / `expired_at` - temporal filters with comparison operators (=, <>, >, <, >=, <=, IS NULL, IS NOT NULL)
- `edge_uuids` - filter to specific edges
- `property_filters` - generic property name/value/operator filters

---

## 5. Extension Points

### Custom Ontology (Entity & Edge Types)
```python
from pydantic import BaseModel

class Person(BaseModel):
    occupation: str | None = None
    nationality: str | None = None

class WorksAt(BaseModel):
    role: str | None = None
    start_date: str | None = None

await graphiti.add_episode(
    ...,
    entity_types={"Person": Person, "Organization": Organization},
    edge_types={"WORKS_AT": WorksAt},
    edge_type_map={("Person", "Organization"): ["WORKS_AT"]},
)
```

### Pluggable Graph Backends
Implement `GraphDriver` abstract class. Current: Neo4j, FalkorDB, Kuzu, Neptune.
Contributing guide covers "Adding a graph driver."

### Pluggable LLM Providers
Implement `LLMClient` abstract class. Any OpenAI-compatible endpoint works via `OpenAIGenericClient`.

### Pluggable Embedders
Implement `EmbedderClient` abstract class.

### Pluggable Cross-Encoders / Rerankers
Implement `CrossEncoderClient` abstract class.

### Custom Search Configurations
Build custom `SearchConfig` objects mixing search methods (BM25, cosine, BFS) with rerankers (RRF, MMR, cross-encoder, node_distance, episode_mentions).

### Custom Extraction Instructions
Pass `custom_extraction_instructions` string to `add_episode()` to guide the LLM entity/edge extraction prompts.

### Excluded Entity Types
Pass `excluded_entity_types` to filter out unwanted entity categories during extraction.

### MCP Server
Full MCP protocol integration for AI assistants. Located in `mcp_server/` directory. Provides episode management, entity handling, search, group management, graph maintenance tools.

### REST API Server
FastAPI-based HTTP server in `server/` directory. Can be deployed independently.

### Concurrency Tuning
- `SEMAPHORE_LIMIT` env var (default: 10) controls parallel LLM calls
- `max_coroutines` constructor param overrides it

### OpenTelemetry Integration
Pass a `Tracer` instance to constructor for distributed tracing.

---

## 6. Use Cases

1. **AI Agent Memory** - persistent, evolving memory for conversational agents that tracks user preferences, decisions, context across sessions
2. **Multi-User Agent Systems** - `group_id` namespacing enables per-user knowledge graphs
3. **Real-Time Data Integration** - continuous ingestion of structured/unstructured data into queryable graph
4. **Temporal Analysis** - "What was true at time X?" queries for compliance, audit trails, historical analysis
5. **Enterprise Knowledge Management** - ingest documents, communications, metadata into connected graph
6. **Customer Support** - track customer interactions, preferences, issues across time
7. **Research & Intelligence** - build knowledge graphs from podcasts, articles, reports (see examples: podcast, wizard_of_oz, ecommerce)
8. **LangGraph Integration** - plug into LangGraph agent workflows for tool-augmented agents
9. **RAG Enhancement** - replace flat document chunks with structured, temporal graph context

---

## 7. Limitations & Constraints

### LLM Requirements
- **Structured Output support essential** - providers without it may produce incorrect schemas and ingestion failures
- **LLM dependency for ingestion** - every `add_episode` call makes multiple LLM calls (extraction, deduplication, resolution); costs add up
- **OpenAI API key required by default** - even if using alternative LLM, embedder defaults to OpenAI

### Performance
- **Sequential episode processing recommended** - docs say "each episode is added sequentially and awaited before adding the next one" for single-group consistency
- **Default SEMAPHORE_LIMIT=10** conservative; may feel slow without tuning
- **Latency depends on LLM response time** - ingestion is LLM-bound, not graph-DB-bound
- **Large graphs** - community building can be expensive as graph grows

### Self-Hosted Only
- No managed cloud offering (Zep is the managed version but separate product)
- Must manage Neo4j/FalkorDB/Kuzu infrastructure yourself
- No built-in user management, auth, or dashboard

### Data Model
- **No image/file storage** - text/JSON only for episodes
- **English-centric** - prompts and extraction are in English; multilingual support unclear
- **Ontology changes** - changing entity/edge types after data exists requires careful migration

### Operational
- **Telemetry opt-out required** - collects anonymous usage data by default
- **Security** - recent cypher injection vulnerability (fixed in 0.28.2 / MCP v1.0.2)
- **No built-in backup/restore** - relies on graph DB's native mechanisms
- **Python-only SDK** - no official clients for other languages

### Scale
- Graph size bounded by underlying graph DB capacity
- Embedding storage grows with every entity and edge
- No built-in sharding or horizontal scaling (depends on DB backend)

---

## Comparison: Graphiti vs GraphRAG

| Aspect | Graphiti | GraphRAG (Microsoft) |
|--------|----------|---------------------|
| Processing | Continuous, incremental | Batch-oriented |
| Temporal | Bi-temporal with auto-invalidation | Basic timestamps |
| Structure | Temporal context graph | Entity clusters + community summaries |
| Retrieval | Hybrid semantic/keyword/graph | Sequential LLM summarization |
| Latency | Sub-second queries | Seconds to tens of seconds |
| Custom Types | Yes (Pydantic) | No |
| Use Case | Dynamic agent context | Static document summarization |

---

## Key Files & Structure

```
graphiti_core/
  graphiti.py          # Main Graphiti class - all public API methods
  nodes.py             # Node models (EntityNode, EpisodicNode, CommunityNode, SagaNode)
  edges.py             # Edge models (EntityEdge, EpisodicEdge, CommunityEdge, etc.)
  search/              # Search engine (config, recipes, filters, utils)
  llm_client/          # LLM provider implementations
  embedder/            # Embedding provider implementations
  cross_encoder/       # Reranker implementations
  driver/              # Graph DB driver implementations (neo4j, falkordb, kuzu, neptune)
  prompts/             # LLM prompt templates for extraction/deduplication
  namespaces/          # CRUD namespace APIs (nodes.entity, edges.entity)
  utils/               # Bulk operations, community ops, maintenance
  models/              # DB query builders
  migrations/          # Schema migration scripts
server/                # FastAPI REST API server
mcp_server/            # MCP protocol server for AI assistants
examples/              # Quickstart, LangGraph, podcast, ecommerce examples
```

---

## Unresolved Questions

1. **Multilingual support** - No documentation found on non-English language handling; likely depends on LLM capabilities but prompts are English-only
2. **Max graph size tested** - No published benchmarks on maximum entities/edges before degradation
3. **Concurrent write safety** - Sequential processing recommended per group; unclear behavior with concurrent writes across groups
4. **Community detection algorithm** - Specific algorithm not documented in public API; lives in `utils/maintenance/community_operations.py`
5. **Migration path** - How to handle ontology schema changes on existing populated graphs
