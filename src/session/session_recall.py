#!/usr/bin/env python3
"""Query Neo4j for the most recent SessionEvent of a project.

Usage: python src/session/session_recall.py --project <name>
Output: JSON to stdout (session object or null)

Designed to be called from Claude Code SessionStart hook.
.env is resolved from D:/MEMGRAP (CWD set by calling hook).
"""

import argparse
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.session.neo4j_connect import get_neo4j_driver


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", required=True, help="Project name to recall")
    args = parser.parse_args()

    driver = get_neo4j_driver()
    try:
        records, _, _ = driver.execute_query(
            """
            MATCH (s:SessionEvent {project: $project})
            RETURN s
            ORDER BY s.ended_at DESC
            LIMIT 1
            """,
            project=args.project,
        )
        if not records:
            print(json.dumps(None))
            return

        node = records[0]["s"]
        result = {
            "session_id": node.get("session_id"),
            "project": node.get("project"),
            "branch": node.get("branch"),
            "started_at": node.get("started_at"),
            "ended_at": node.get("ended_at"),
            "commits": list(node.get("commits", [])),
            "files_changed": list(node.get("files_changed", [])),
            "summary": node.get("summary", ""),
        }
        print(json.dumps(result, ensure_ascii=False))
    finally:
        driver.close()


if __name__ == "__main__":
    main()
