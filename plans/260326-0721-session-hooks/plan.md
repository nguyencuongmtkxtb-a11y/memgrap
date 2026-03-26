# Phase 3: Session Hooks Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Auto-capture session context into Neo4j knowledge graph when Claude Code starts/ends a session.

**Architecture:** Two Claude Code hook scripts (Node.js .cjs) fire on SessionStart and SessionEnd. They gather git context and spawn lightweight Python scripts that read/write SessionEvent nodes directly to Neo4j via Cypher. No MCP server changes. No OpenAI cost.

**Tech Stack:** Node.js (hooks), Python (Neo4j scripts), neo4j Python driver, Cypher queries

**Spec:** `docs/superpowers/specs/2026-03-26-session-hooks-design.md`

**Environment:** Windows 10, D:\MEMGRAP, Python venv, Neo4j in Docker (bolt://localhost:7687)

---

## File Structure

| File | Action | Responsibility |
|------|--------|---------------|
| `src/session/__init__.py` | Create | Package marker |
| `src/session/session_recall.py` | Create | Query Neo4j for last session of a project |
| `src/session/session_save.py` | Create | Write SessionEvent node to Neo4j via Cypher |
| `src/session/neo4j_connect.py` | Create | Shared Neo4j connection helper (reuses src/config.py) |
| `~/.claude/hooks/memgrap-session-start.cjs` | Create | SessionStart hook — git context + recall |
| `~/.claude/hooks/memgrap-session-end.cjs` | Create | SessionEnd hook — diff + save |
| `~/.claude/settings.json` | Modify | Register new hooks (merge with existing) |
| `tests/test_session_recall.py` | Create | Tests for session-recall.py |
| `tests/test_session_save.py` | Create | Tests for session-save.py |

---

### Task 1: Neo4j Connection Helper

Shared module so both session-recall.py and session-save.py reuse the same connection logic.

**Files:**
- Create: `src/session/__init__.py`
- Create: `src/session/neo4j_connect.py`
- Test: `tests/test_neo4j_connect.py`

**Note:** Python files in `src/session/` use underscores (not kebab-case) because they must be importable as Python modules. Kebab-case filenames cause `SyntaxError` on import.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_neo4j_connect.py
"""Tests for session Neo4j connection helper."""
from src.session.neo4j_connect import get_neo4j_driver


def test_get_neo4j_driver_returns_driver():
    """Driver connects to Neo4j and can run a basic query."""
    driver = get_neo4j_driver()
    assert driver is not None
    records, _, _ = driver.execute_query("RETURN 1 AS n")
    assert records[0]["n"] == 1
    driver.close()


def test_get_neo4j_driver_reuses_config():
    """Driver reads Neo4j credentials from src.config.Settings."""
    driver = get_neo4j_driver()
    # Should not raise — proves config loading works
    driver.close()
```

- [ ] **Step 1b: Ensure pytest config has pythonpath**

Check `pyproject.toml` has `[tool.pytest.ini_options]` with `pythonpath = ["."]`. If not, add it. This is required for `from src.session...` imports to work in tests.

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_neo4j_connect.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'src.session'"

- [ ] **Step 3: Create package and implement**

```python
# src/session/__init__.py
```

```python
# src/session/neo4j_connect.py
"""Shared Neo4j connection helper for session scripts.

Reads credentials from src.config.Settings (same .env as MCP server).
Uses the synchronous neo4j Python driver — no asyncio needed for scripts.
"""

from neo4j import GraphDatabase

from src.config import get_settings


def get_neo4j_driver():
    """Create a Neo4j driver using settings from .env."""
    settings = get_settings()
    return GraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_user, settings.neo4j_password),
        connection_timeout=2,  # fast fail if Neo4j is down
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_neo4j_connect.py -v`
Expected: PASS (requires Neo4j running via `docker compose up -d`)

- [ ] **Step 5: Commit**

```bash
git add src/session/__init__.py src/session/neo4j_connect.py tests/test_neo4j_connect.py
git commit -m "feat(session): add shared Neo4j connection helper for session scripts"
```

---

### Task 2: Session Save Script

Writes a SessionEvent node to Neo4j. Receives JSON on stdin.

**Files:**
- Create: `src/session/session_save.py`
- Test: `tests/test_session_save.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_session_save.py
"""Tests for session-save.py — writes SessionEvent to Neo4j."""
import json
import subprocess
import sys

import pytest

from src.session.neo4j_connect import get_neo4j_driver

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

    # Verify node exists in Neo4j
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_session_save.py -v`
Expected: FAIL — script doesn't exist

- [ ] **Step 3: Implement session-save.py**

```python
#!/usr/bin/env python3
"""Write a SessionEvent node to Neo4j from JSON on stdin.

Usage: echo '{"session_id": "...", ...}' | python src/session/session_save.py

Designed to be called from Claude Code SessionEnd hook.
Must complete fast (<2s). Uses MERGE for idempotency.
"""

import json
import sys
import os

# Add project root to path so src.config is importable
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_session_save.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/session/session_save.py tests/test_session_save.py
git commit -m "feat(session): add session-save script — writes SessionEvent to Neo4j"
```

---

### Task 3: Session Recall Script

Queries Neo4j for the most recent SessionEvent for a given project.

**Files:**
- Create: `src/session/session_recall.py`
- Test: `tests/test_session_recall.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_session_recall.py
"""Tests for session-recall.py — queries last session from Neo4j."""
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
    """Helper: pipe data to session-save.py."""
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_session_recall.py -v`
Expected: FAIL — script doesn't exist

- [ ] **Step 3: Implement session-recall.py**

```python
#!/usr/bin/env python3
"""Query Neo4j for the most recent SessionEvent of a project.

Usage: python src/session/session_recall.py --project <name>
Output: JSON to stdout (session object or null)

Designed to be called from Claude Code SessionStart hook.
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_session_recall.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/session/session_recall.py tests/test_session_recall.py
git commit -m "feat(session): add session-recall script — queries last session from Neo4j"
```

---

### Task 4: SessionStart Hook (Node.js)

Gathers git context, spawns session-recall.py, writes temp file, outputs systemMessage.

**Files:**
- Create: `~/.claude/hooks/memgrap-session-start.cjs`

- [ ] **Step 1: Implement memgrap-session-start.cjs**

```javascript
// memgrap-session-start.cjs
// Claude Code SessionStart hook for Memgrap.
// Gathers git context + prior session from Neo4j, injects systemMessage.

const { execSync, spawnSync } = require("child_process");
const fs = require("fs");
const os = require("os");
const path = require("path");

// Memgrap project root (absolute path for Python scripts)
const MEMGRAP_DIR = "D:/MEMGRAP";
const PYTHON = "python";

/**
 * Read all stdin synchronously (Claude Code sends JSON input).
 */
function readStdin() {
  try {
    return JSON.parse(fs.readFileSync(0, "utf-8"));
  } catch {
    return {};
  }
}

/**
 * Run a git command in the given cwd. Returns trimmed stdout or empty string.
 */
function git(cmd, cwd) {
  try {
    return execSync(`git ${cmd}`, { cwd, encoding: "utf-8", timeout: 5000 }).trim();
  } catch {
    return "";
  }
}

/**
 * Check if cwd is inside a git repo.
 */
function isGitRepo(cwd) {
  return git("rev-parse --is-inside-work-tree", cwd) === "true";
}

/**
 * Spawn session-recall.py and return parsed JSON (or null).
 */
function recallLastSession(project) {
  try {
    const result = spawnSync(
      PYTHON,
      [path.join(MEMGRAP_DIR, "src/session/session_recall.py"), "--project", project],
      { encoding: "utf-8", timeout: 5000, cwd: MEMGRAP_DIR }
    );
    if (result.status === 0 && result.stdout) {
      return JSON.parse(result.stdout);
    }
  } catch (e) {
    process.stderr.write(`[memgrap] recall failed: ${e.message}\n`);
  }
  return null;
}

function main() {
  const input = readStdin();
  const cwd = input.cwd || process.cwd();
  const sessionId = input.session_id || `fallback-${Date.now()}`;
  const project = path.basename(cwd);

  // --- Git context ---
  let gitContext = null;
  if (isGitRepo(cwd)) {
    gitContext = {
      branch: git("branch --show-current", cwd),
      status: git("status --porcelain", cwd),
      recentCommits: git("log --oneline -5", cwd),
      headCommit: git("rev-parse HEAD", cwd),
    };
  }

  // --- Prior session recall ---
  const lastSession = recallLastSession(project);

  // --- Write temp session file for SessionEnd ---
  const tempFile = path.join(os.tmpdir(), `memgrap-session-${sessionId}.json`);
  const sessionData = {
    session_id: sessionId,
    project,
    branch: gitContext?.branch || "unknown",
    start_commit: gitContext?.headCommit || "",
    started_at: new Date().toISOString(),
    cwd,
  };
  try {
    fs.writeFileSync(tempFile, JSON.stringify(sessionData));
  } catch (e) {
    process.stderr.write(`[memgrap] temp file write failed: ${e.message}\n`);
  }

  // --- Clean up orphaned temp files (older than 24h) ---
  try {
    const tmpDir = os.tmpdir();
    const files = fs.readdirSync(tmpDir).filter(f => f.startsWith("memgrap-session-"));
    const cutoff = Date.now() - 24 * 60 * 60 * 1000;
    for (const f of files) {
      const fp = path.join(tmpDir, f);
      if (f !== path.basename(tempFile)) {
        try {
          const stat = fs.statSync(fp);
          if (stat.mtimeMs < cutoff) fs.unlinkSync(fp);
        } catch { /* ignore */ }
      }
    }
  } catch { /* ignore orphan cleanup errors */ }

  // --- Build systemMessage ---
  const parts = ["## Memgrap Session Context"];

  if (lastSession) {
    parts.push("\n### Previous Session");
    parts.push(`- **Branch:** ${lastSession.branch}`);
    parts.push(`- **Ended:** ${lastSession.ended_at}`);
    if (lastSession.summary) parts.push(`- **Summary:** ${lastSession.summary}`);
    if (lastSession.commits?.length) {
      parts.push(`- **Commits:** ${lastSession.commits.join(", ")}`);
    }
    if (lastSession.files_changed?.length) {
      parts.push(`- **Files changed:** ${lastSession.files_changed.join(", ")}`);
    }
  } else {
    parts.push("\n*No previous session found for this project.*");
  }

  if (gitContext) {
    parts.push("\n### Current Git State");
    parts.push(`- **Branch:** ${gitContext.branch}`);
    parts.push(`- **HEAD:** ${gitContext.headCommit}`);
    if (gitContext.status) {
      const changedCount = gitContext.status.split("\n").filter(Boolean).length;
      parts.push(`- **Uncommitted changes:** ${changedCount} file(s)`);
    } else {
      parts.push("- **Working tree:** clean");
    }
    if (gitContext.recentCommits) {
      parts.push("\n**Recent commits:**");
      parts.push("```");
      parts.push(gitContext.recentCommits);
      parts.push("```");
    }
  } else {
    parts.push("\n*Not a git repository.*");
  }

  // Output for Claude Code
  const output = { systemMessage: parts.join("\n") };
  process.stdout.write(JSON.stringify(output));
}

main();
```

- [ ] **Step 2: Manual test — run the script with mock stdin**

Run from D:\MEMGRAP:
```bash
echo '{"session_id":"test-manual","cwd":"D:/MEMGRAP"}' | node ~/.claude/hooks/memgrap-session-start.cjs
```
Expected: JSON output with `systemMessage` containing git context. Check that temp file exists in `os.tmpdir()`.

- [ ] **Step 3: Commit**

```bash
git add ~/.claude/hooks/memgrap-session-start.cjs
git commit -m "feat(session): add SessionStart hook — git context + prior session recall"
```

---

### Task 5: SessionEnd Hook (Node.js)

Reads temp file, gathers git diff, pipes to session-save.py.

**Files:**
- Create: `~/.claude/hooks/memgrap-session-end.cjs`

- [ ] **Step 1: Implement memgrap-session-end.cjs**

```javascript
// memgrap-session-end.cjs
// Claude Code SessionEnd hook for Memgrap.
// Gathers git changes since session start, writes SessionEvent to Neo4j.

const { execSync, spawnSync } = require("child_process");
const fs = require("fs");
const os = require("os");
const path = require("path");

const MEMGRAP_DIR = "D:/MEMGRAP";
const PYTHON = "python";

function readStdin() {
  try {
    return JSON.parse(fs.readFileSync(0, "utf-8"));
  } catch {
    return {};
  }
}

function git(cmd, cwd) {
  try {
    return execSync(`git ${cmd}`, { cwd, encoding: "utf-8", timeout: 5000 }).trim();
  } catch {
    return "";
  }
}

function main() {
  const input = readStdin();
  const sessionId = input.session_id;
  const cwd = input.cwd || process.cwd();
  const transcriptPath = input.transcript_path || "";

  if (!sessionId) {
    process.stderr.write("[memgrap] SessionEnd: no session_id in input, skipping.\n");
    return;
  }

  // Read temp session file
  const tempFile = path.join(os.tmpdir(), `memgrap-session-${sessionId}.json`);
  let sessionData;
  try {
    sessionData = JSON.parse(fs.readFileSync(tempFile, "utf-8"));
  } catch {
    process.stderr.write("[memgrap] SessionEnd: no temp file found, skipping.\n");
    return;
  }

  // Gather git changes since start commit
  const startCommit = sessionData.start_commit;
  let commits = [];
  let filesChanged = [];

  if (startCommit) {
    const commitLog = git(`log --oneline ${startCommit}..HEAD`, cwd);
    if (commitLog) {
      commits = commitLog.split("\n").filter(Boolean).map(l => l.split(" ")[0]);
    }
    const diffFiles = git(`diff --name-only ${startCommit}..HEAD`, cwd);
    if (diffFiles) {
      filesChanged = diffFiles.split("\n").filter(Boolean);
    }
  }

  // Build summary
  const commitCount = commits.length;
  const fileCount = filesChanged.length;
  let summary = `Session on branch ${sessionData.branch}.`;
  if (commitCount > 0) {
    summary += ` Made ${commitCount} commit(s): ${commits.join(", ")}.`;
  } else {
    summary += " No commits made.";
  }
  if (fileCount > 0) {
    summary += ` Changed ${fileCount} file(s): ${filesChanged.slice(0, 10).join(", ")}`;
    if (fileCount > 10) summary += ` (+${fileCount - 10} more)`;
    summary += ".";
  }

  // Pipe to session-save.py
  const saveData = {
    session_id: sessionData.session_id,
    project: sessionData.project,
    branch: sessionData.branch,
    start_commit: startCommit,
    started_at: sessionData.started_at,
    ended_at: new Date().toISOString(),
    commits,
    files_changed: filesChanged,
    summary,
    transcript_path: transcriptPath,
  };

  const result = spawnSync(
    PYTHON,
    [path.join(MEMGRAP_DIR, "src/session/session_save.py")],
    {
      input: JSON.stringify(saveData),
      encoding: "utf-8",
      timeout: 5000,
      cwd: MEMGRAP_DIR,
    }
  );

  if (result.status !== 0) {
    process.stderr.write(`[memgrap] session-save failed: ${result.stderr}\n`);
  }

  // Clean up temp file
  try {
    fs.unlinkSync(tempFile);
  } catch { /* ignore */ }
}

main();
```

- [ ] **Step 2: Manual test — simulate a session lifecycle**

```bash
# 1. Simulate SessionStart
echo '{"session_id":"test-e2e","cwd":"D:/MEMGRAP"}' | node ~/.claude/hooks/memgrap-session-start.cjs

# 2. Verify temp file exists
cat $(python -c "import os,tempfile; print(os.path.join(tempfile.gettempdir(), 'memgrap-session-test-e2e.json'))")

# 3. Simulate SessionEnd
echo '{"session_id":"test-e2e","cwd":"D:/MEMGRAP","transcript_path":"/tmp/transcript.json"}' | node ~/.claude/hooks/memgrap-session-end.cjs

# 4. Verify SessionEvent in Neo4j
python -c "
from src.session.neo4j_connect import get_neo4j_driver
d = get_neo4j_driver()
r, _, _ = d.execute_query('MATCH (s:SessionEvent {session_id: \"test-e2e\"}) RETURN s')
print(dict(r[0]['s']) if r else 'NOT FOUND')
d.close()
"
```

- [ ] **Step 3: Clean up test data**

```bash
python -c "
from src.session.neo4j_connect import get_neo4j_driver
d = get_neo4j_driver()
d.execute_query('MATCH (s:SessionEvent {session_id: \"test-e2e\"}) DETACH DELETE s')
d.close()
print('cleaned up')
"
```

- [ ] **Step 4: Commit**

```bash
git add ~/.claude/hooks/memgrap-session-end.cjs
git commit -m "feat(session): add SessionEnd hook — saves session summary to Neo4j"
```

---

### Task 6: Neo4j Index + Register Hooks in Settings

Create the index for fast session queries and wire hooks into Claude Code settings.

**Files:**
- Modify: `~/.claude/settings.json` (merge hooks into existing config)

- [ ] **Step 1: Create Neo4j index for SessionEvent**

```bash
python -c "
from src.session.neo4j_connect import get_neo4j_driver
d = get_neo4j_driver()
d.execute_query('CREATE INDEX session_project IF NOT EXISTS FOR (s:SessionEvent) ON (s.project)')
print('Index created')
d.close()
"
```

- [ ] **Step 2: Register hooks in ~/.claude/settings.json**

Read current settings, add SessionStart and SessionEnd hook entries. Merge with existing hooks — do NOT overwrite.

Add to `hooks.SessionStart` array:
```json
{
  "matcher": "startup|resume|clear|compact",
  "hooks": [
    {
      "type": "command",
      "command": "node C:/Users/CUONG/.claude/hooks/memgrap-session-start.cjs"
    }
  ]
}
```

Add new `hooks.SessionEnd` array:
```json
{
  "matcher": "*",
  "hooks": [
    {
      "type": "command",
      "command": "node C:/Users/CUONG/.claude/hooks/memgrap-session-end.cjs"
    }
  ]
}
```

- [ ] **Step 3: Commit project files**

```bash
git add src/session/ tests/test_session_*.py tests/test_neo4j_connect.py
git commit -m "feat(session): Phase 3 session hooks — auto-capture context on start/end"
```

---

### Task 7: End-to-End Verification

Verify the full lifecycle works by restarting Claude Code.

- [ ] **Step 1: Ensure Neo4j is running**

```bash
docker compose ps
```

- [ ] **Step 2: Restart Claude Code session**

Exit and restart Claude Code. Observe:
- SessionStart hook fires
- systemMessage appears with git context
- If prior sessions exist, they show up

- [ ] **Step 3: Work in session, then exit**

Make a small change (e.g. edit a comment), commit it, then exit Claude Code. Verify:
- SessionEnd hook fires
- SessionEvent node created in Neo4j

```bash
python -c "
from src.session.neo4j_connect import get_neo4j_driver
d = get_neo4j_driver()
r, _, _ = d.execute_query('MATCH (s:SessionEvent) RETURN s ORDER BY s.ended_at DESC LIMIT 1')
if r:
    print(dict(r[0]['s']))
else:
    print('No sessions found')
d.close()
"
```

- [ ] **Step 4: Restart again — verify recall works**

Restart Claude Code. The SessionStart hook should now show the previous session's summary in the system message.

- [ ] **Step 5: Update memory**

Update project memory file to reflect Phase 3 completion.
