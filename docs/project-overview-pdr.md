# Memgrap — Project Overview

## What
Temporal knowledge graph memory system for Claude Code, powered by Graphiti + Neo4j.

## Why
Claude Code loses context between sessions. Flat file memory (CLAUDE.md, MEMORY.md) lacks structure, relationships, and temporal tracking. Memgrap provides:
- Structured entity/relationship extraction from conversations
- Temporal fact tracking (valid_at/invalid_at)
- Hybrid semantic search (BM25 + cosine + graph traversal)
- MCP integration for seamless Claude Code access

## Architecture
```
Claude Code (stdio) --> MCP Server (FastMCP) --> Graphiti Core --> Neo4j (Docker)
                                                      |
                                              OpenAI API (LLM + embeddings)
```

## Tech Stack
- **Python 3.10+** (async)
- **Graphiti Core 0.28.2** — temporal knowledge graph engine
- **Neo4j 5.26** — graph database (Docker)
- **OpenAI gpt-4o-mini** — entity/relationship extraction
- **OpenAI text-embedding-3-small** — vector embeddings
- **FastMCP** — MCP server framework (stdio transport)
- **pydantic-settings** — config from .env

## MCP Tools (7)
| Tool | Purpose |
|------|---------|
| `remember` | Store info into knowledge graph |
| `recall` | Semantic search for relevant memories |
| `understand_code` | Search code entities |
| `get_history` | Memory timeline |
| `search_nodes` | Find entities |
| `search_facts` | Find relationships |
| `get_status` | Health check |

## Entity Types (8)
CodePattern, TechDecision, ProjectContext, Person, Tool, Concept, BugReport, Requirement
