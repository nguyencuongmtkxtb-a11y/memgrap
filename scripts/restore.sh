#!/bin/bash
set -e
DUMP_FILE="$1"
if [ -z "$DUMP_FILE" ]; then echo "Usage: ./scripts/restore.sh <path-to-dump-file>"; exit 1; fi
if [ ! -f "$DUMP_FILE" ]; then echo "Error: File not found: $DUMP_FILE"; exit 1; fi
echo "WARNING: This will overwrite the current Neo4j database!"
read -p "Continue? [y/N] " confirm
if [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then echo "Aborted."; exit 0; fi
ABSOLUTE_PATH=$(realpath "$DUMP_FILE")
DUMP_DIR=$(dirname "$ABSOLUTE_PATH")
echo "Stopping Neo4j..."
docker compose stop neo4j
echo "Restoring..."
docker compose run --rm -v "$DUMP_DIR:/restore" neo4j \
  neo4j-admin database load neo4j --from-path=/restore --overwrite-destination
echo "Restarting Neo4j..."
docker compose start neo4j
echo "Restore complete."
