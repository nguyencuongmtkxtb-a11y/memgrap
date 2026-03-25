# System Architecture

## Components

### MCP Server (`src/mcp_server.py`)
- FastMCP with stdio transport
- 7 tools exposed to Claude Code
- Lazy initialization on first tool call
- All logging to stderr (stdout = MCP JSON-RPC)

### Graph Service (`src/graph_service.py`)
- Wraps Graphiti Core API
- Methods: add_memory, recall, search_nodes, search_facts, get_episodes, get_status
- Uses result_formatters for serialization

### Graphiti Factory (`src/graphiti_factory.py`)
- Creates configured Graphiti instance
- OpenAI LLM client (gpt-4o-mini) for extraction
- OpenAI embedder (text-embedding-3-small) for vectors

### Config (`src/config.py`)
- pydantic-settings BaseSettings
- Loads from .env file
- Keys: OPENAI_API_KEY, NEO4J_URI/USER/PASSWORD, LLM_MODEL, GROUP_ID

### Entity Types (`src/entity_types.py`)
- 8 Pydantic models: CodePattern, TechDecision, ProjectContext, Person, Tool, Concept, BugReport, Requirement
- Passed to Graphiti's add_episode for guided extraction

### Result Formatters (`src/result_formatters.py`)
- format_edge, format_node, format_episode
- Serialize Graphiti objects to dicts for MCP responses

## Data Flow
1. Claude Code invokes MCP tool (e.g. `remember`)
2. MCP Server delegates to GraphService
3. GraphService calls Graphiti Core (add_episode / search)
4. Graphiti calls OpenAI for entity extraction + embeddings
5. Results stored in / retrieved from Neo4j

## Infrastructure
- Neo4j 5.26 via Docker Compose (ports 7474/7687)
- 24 range indices + 4 fulltext indices (auto-created by Graphiti)
- Persistent Docker volumes for data/logs
