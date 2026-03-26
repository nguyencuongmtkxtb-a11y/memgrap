#!/usr/bin/env python3
"""Write a SessionEvent node to Neo4j from JSON on stdin.

Usage: echo '{"session_id": "...", ...}' | python src/session/session_save.py

Designed to be called from Claude Code SessionEnd hook.
Must complete fast (<2s). Uses MERGE for idempotency.
.env is resolved from D:/MEMGRAP (CWD set by calling hook).
"""

import json
import sys
from pathlib import Path

# Ensure project root is on sys.path for `src.*` imports
_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent.parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

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

        # Notify dashboard SSE about new session
        try:
            import urllib.request
            from src.config import get_settings
            dashboard_url = get_settings().dashboard_url
            url = f"{dashboard_url}/api/notify"
            payload = json.dumps({
                "event": "session:created",
                "project": data["project"],
            }).encode()
            req = urllib.request.Request(
                url, data=payload,
                headers={"Content-Type": "application/json"},
            )
            urllib.request.urlopen(req, timeout=2)
        except Exception:
            pass  # Dashboard may not be running
    finally:
        driver.close()


if __name__ == "__main__":
    main()
