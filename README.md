# Memgrap

Temporal knowledge graph memory for Claude Code, powered by [Graphiti](https://github.com/getzep/graphiti) + Neo4j.

## Quick Start

```bash
# 1. Install dependencies
pip install -e .

# 2. Configure environment
cp .env.example .env
# Edit .env — add your OPENAI_API_KEY

# 3. Start Neo4j
docker compose up -d

# 4. Verify Neo4j is healthy
docker compose ps
# Browse: http://localhost:7474

# 5. Claude Code auto-loads MCP from .mcp.json on restart
```

## MCP Tools

| Tool | Description |
|------|-------------|
| `remember` | Store info into knowledge graph |
| `recall` | Semantic search for relevant memories |
| `understand_code` | Search code entities (patterns, tools, decisions) |
| `get_history` | Retrieve memory timeline |
| `search_facts` | Find relationships/facts |
| `get_status` | Health check |

## Architecture

```
Claude Code (stdio) --> MCP Server (FastMCP) --> Graphiti Core --> Neo4j (Docker)
                                                      |
                                              OpenAI (gpt-4o-mini + embeddings)
```

## Entity Types

CodePattern, TechDecision, ProjectContext, Person, Tool, Concept, BugReport, Requirement

## Configuration

All config via `.env` file. See `.env.example` for available options.

## License

MIT
