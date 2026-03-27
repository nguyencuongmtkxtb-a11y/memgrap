#!/usr/bin/env bash
set -euo pipefail

echo "============================================"
echo "  Memgrap - One-Click Setup (Linux/macOS)"
echo "============================================"
echo

# Detect project root from this script location
MEMGRAP_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "[1/6] Checking prerequisites..."

if ! command -v python3 &>/dev/null && ! command -v python &>/dev/null; then
    echo "ERROR: Python not found. Install Python 3.10+ from https://python.org"
    exit 1
fi
PYTHON=$(command -v python3 || command -v python)

if ! command -v docker &>/dev/null; then
    echo "ERROR: Docker not found. Install Docker from https://docker.com"
    exit 1
fi
echo "       Python: OK ($($PYTHON --version))"
echo "       Docker: OK ($(docker --version))"
echo

echo "[2/6] Installing Python dependencies..."
cd "$MEMGRAP_DIR"
$PYTHON -m pip install -e . --quiet
echo "       Done."
echo

echo "[3/6] Starting Neo4j container..."
docker compose up -d
echo "       Waiting for Neo4j to be healthy..."
for i in $(seq 1 20); do
    status=$(docker inspect --format='{{.State.Health.Status}}' memgrap-neo4j 2>/dev/null || echo "waiting")
    if [ "$status" = "healthy" ]; then
        echo "       Neo4j: healthy"
        break
    fi
    if [ "$i" -eq 20 ]; then
        echo "WARNING: Neo4j health check timed out. Check: docker compose ps"
    fi
    sleep 3
done
echo

echo "[4/6] Generating .env file..."
if [ ! -f "$MEMGRAP_DIR/.env" ]; then
    cp "$MEMGRAP_DIR/.env.example" "$MEMGRAP_DIR/.env"
    echo
    echo "*** IMPORTANT: Edit .env and add your OPENAI_API_KEY ***"
    echo "    File: $MEMGRAP_DIR/.env"
    echo
    read -rp "Enter OpenAI API key (or press Enter to skip): " OPENAI_KEY
    if [ -n "$OPENAI_KEY" ]; then
        sed -i.bak "s|sk-proj-\.\.\.|$OPENAI_KEY|" "$MEMGRAP_DIR/.env"
        rm -f "$MEMGRAP_DIR/.env.bak"
        echo "       API key saved."
    else
        echo "       Skipped. Edit .env manually later."
    fi
else
    echo "       .env already exists, skipping."
fi
echo

echo "[5/6] Configuring MCP for Claude Code..."
# Write project path to ~/.memgrap for hooks to discover
echo "$MEMGRAP_DIR" > "$HOME/.memgrap"

# Read OPENAI_API_KEY from .env
OPENAI_KEY_VALUE=""
if [ -f "$MEMGRAP_DIR/.env" ]; then
    OPENAI_KEY_VALUE=$(grep '^OPENAI_API_KEY=' "$MEMGRAP_DIR/.env" | cut -d'=' -f2-)
fi

# Write global MCP config (~/.claude/mcp.json) so it works in ALL projects
MCP_DIR="$HOME/.claude"
mkdir -p "$MCP_DIR"
cat > "$MCP_DIR/mcp.json" <<MCPEOF
{
  "mcpServers": {
    "MEMGRAP": {
      "command": "$PYTHON",
      "args": ["-m", "src.mcp_server"],
      "cwd": "$MEMGRAP_DIR",
      "env": {
        "OPENAI_API_KEY": "$OPENAI_KEY_VALUE"
      }
    }
  }
}
MCPEOF
echo "       Global MCP config written: $MCP_DIR/mcp.json"

# Also keep project-level .mcp.json for backward compat
cat > "$MEMGRAP_DIR/.mcp.json" <<MCPEOF
{
  "mcpServers": {
    "MEMGRAP": {
      "command": "$PYTHON",
      "args": ["-m", "src.mcp_server"]
    }
  }
}
MCPEOF
echo "       Project MCP config written."
echo

echo "[6/6] Verifying setup..."
$PYTHON -c "
from src.config import get_settings
s = get_settings()
print(f'  Neo4j: {s.neo4j_uri}')
print(f'  OpenAI key: {\"configured\" if s.openai_api_key else \"MISSING - edit .env\"}')
"
echo

echo "============================================"
echo "  Setup complete!"
echo "  Restart Claude Code to activate Memgrap."
echo "============================================"
