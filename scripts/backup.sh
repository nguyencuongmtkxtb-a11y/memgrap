#!/bin/bash
set -e
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
BACKUP_DIR="./backups"
mkdir -p "$BACKUP_DIR"
echo "Stopping Neo4j..."
docker compose stop neo4j
echo "Creating backup..."
docker compose run --rm -v "$(pwd)/backups:/backups" neo4j \
  neo4j-admin database dump neo4j --to-path=/backups --overwrite-destination
mv "$BACKUP_DIR/neo4j.dump" "$BACKUP_DIR/memgrap-${TIMESTAMP}.dump" 2>/dev/null || true
echo "Restarting Neo4j..."
docker compose start neo4j
echo "Backup complete: $BACKUP_DIR/memgrap-${TIMESTAMP}.dump"
