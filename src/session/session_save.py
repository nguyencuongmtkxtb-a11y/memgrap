#!/usr/bin/env python3
"""Write a SessionEvent node to Neo4j from JSON on stdin.

Usage: echo '{"session_id": "...", ...}' | python src/session/session_save.py

Designed to be called from Claude Code SessionEnd hook.
Must complete fast (<2s). Uses MERGE for idempotency.
.env is resolved from D:/MEMGRAP (CWD set by calling hook).
"""

import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.session.neo4j_connect import get_neo4j_driver


def main():
    try:
        data = json.loads(sys.stdin.read())
    except (json.JSONDecodeError, Exception) as e:
        print(f"Error parsing stdin JSON: {e}", file=sys.stderr)
        sys.exit(1)

    required = ["session_id", "project", "branch", "started_at", "ended_at"]
    for field in required:
        if field not in data:
            print(f"Missing required field: {field}", file=sys.stderr)
            sys.exit(1)

    driver = get_neo4j_driver()
    try:
        driver.execute_query(
            """
            MERGE (s:SessionEvent {session_id: $session_id})
            SET s.project = $project,
                s.branch = $branch,
                s.start_commit = $start_commit,
                s.started_at = $started_at,
                s.ended_at = $ended_at,
                s.commits = $commits,
                s.files_changed = $files_changed,
                s.summary = $summary,
                s.transcript_path = $transcript_path
            """,
            session_id=data["session_id"],
            project=data["project"],
            branch=data["branch"],
            start_commit=data.get("start_commit", ""),
            started_at=data["started_at"],
            ended_at=data["ended_at"],
            commits=data.get("commits", []),
            files_changed=data.get("files_changed", []),
            summary=data.get("summary", ""),
            transcript_path=data.get("transcript_path", ""),
        )
    finally:
        driver.close()


if __name__ == "__main__":
    main()
