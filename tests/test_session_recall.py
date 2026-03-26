"""Tests for session_recall.py — queries last session from Neo4j."""
import json
import subprocess
import sys

import pytest

from src.session.neo4j_connect import get_neo4j_driver

RECALL_SCRIPT = "src/session/session_recall.py"
SAVE_SCRIPT = "src/session/session_save.py"


@pytest.fixture(autouse=True)
def cleanup_test_sessions():
    """Remove test SessionEvent nodes after each test."""
    yield
    driver = get_neo4j_driver()
    driver.execute_query(
        "MATCH (s:SessionEvent) WHERE s.session_id STARTS WITH 'test-' DETACH DELETE s"
    )
    driver.close()


def _save_session(data: dict):
    """Helper: pipe data to session_save.py."""
    subprocess.run(
        [sys.executable, SAVE_SCRIPT],
        input=json.dumps(data),
        capture_output=True, text=True, timeout=10,
    )


def test_recall_returns_last_session():
    """Recall returns the most recent session for the project."""
    _save_session({
        "session_id": "test-recall-old",
        "project": "test-recall-proj",
        "branch": "main",
        "start_commit": "aaa",
        "started_at": "2026-03-25T01:00:00Z",
        "ended_at": "2026-03-25T02:00:00Z",
        "commits": [],
        "files_changed": [],
        "summary": "old session",
    })
    _save_session({
        "session_id": "test-recall-new",
        "project": "test-recall-proj",
        "branch": "feat/x",
        "start_commit": "bbb",
        "started_at": "2026-03-26T01:00:00Z",
        "ended_at": "2026-03-26T02:00:00Z",
        "commits": ["ccc"],
        "files_changed": ["src/x.py"],
        "summary": "new session",
    })

    result = subprocess.run(
        [sys.executable, RECALL_SCRIPT, "--project", "test-recall-proj"],
        capture_output=True, text=True, timeout=10,
    )
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert data["session_id"] == "test-recall-new"
    assert data["summary"] == "new session"


def test_recall_no_sessions_returns_null():
    """Recall returns null JSON when no sessions exist for project."""
    result = subprocess.run(
        [sys.executable, RECALL_SCRIPT, "--project", "nonexistent-project-xyz"],
        capture_output=True, text=True, timeout=10,
    )
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert data is None
