"""Tests for session_save.py — writes SessionEvent to Neo4j."""
import json
import subprocess
import sys

import pytest

from src.session.neo4j_connect import get_neo4j_driver

pytestmark = pytest.mark.integration

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


def test_save_creates_session_event():
    """Piping valid JSON creates a SessionEvent node in Neo4j."""
    data = {
        "session_id": "test-save-001",
        "project": "test-project",
        "branch": "main",
        "start_commit": "abc1234",
        "started_at": "2026-03-26T03:00:00Z",
        "ended_at": "2026-03-26T04:00:00Z",
        "commits": ["def5678", "ghi9012"],
        "files_changed": ["src/foo.py", "src/bar.py"],
        "summary": "Worked on foo and bar",
        "transcript_path": "/tmp/transcript.json",
    }
    result = subprocess.run(
        [sys.executable, SAVE_SCRIPT],
        input=json.dumps(data),
        capture_output=True, text=True, timeout=10,
    )
    assert result.returncode == 0, f"stderr: {result.stderr}"

    driver = get_neo4j_driver()
    records, _, _ = driver.execute_query(
        "MATCH (s:SessionEvent {session_id: $sid}) RETURN s",
        sid="test-save-001",
    )
    assert len(records) == 1
    node = records[0]["s"]
    assert node["project"] == "test-project"
    assert node["branch"] == "main"
    assert "def5678" in node["commits"]
    driver.close()


def test_save_is_idempotent():
    """Running save twice with same session_id does MERGE, not duplicate."""
    data = {
        "session_id": "test-save-idem",
        "project": "test-project",
        "branch": "main",
        "start_commit": "abc1234",
        "started_at": "2026-03-26T03:00:00Z",
        "ended_at": "2026-03-26T04:00:00Z",
        "commits": [],
        "files_changed": [],
        "summary": "first run",
    }
    for summary in ["first run", "second run"]:
        data["summary"] = summary
        subprocess.run(
            [sys.executable, SAVE_SCRIPT],
            input=json.dumps(data),
            capture_output=True, text=True, timeout=10,
        )

    driver = get_neo4j_driver()
    records, _, _ = driver.execute_query(
        "MATCH (s:SessionEvent {session_id: $sid}) RETURN s",
        sid="test-save-idem",
    )
    assert len(records) == 1
    assert records[0]["s"]["summary"] == "second run"
    driver.close()
