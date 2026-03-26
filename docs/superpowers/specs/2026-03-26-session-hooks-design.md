# Phase 3: Session Hooks — Auto-Capture Context

## Overview

Auto-capture session context into the knowledge graph when Claude Code starts/ends a session. SessionStart gathers git context, project metadata, and prior session recall. SessionEnd writes a session summary to Neo4j directly.

**Approach**: Pure hook scripts. No MCP server changes. Direct Neo4j writes bypass Graphiti LLM extraction (zero OpenAI cost for session mechanics).

## Architecture

```
Session Start:
  Claude Code launches
    → SessionStart hook fires (JSON input on stdin: {session_id, cwd, ...})
    → memgrap-session-start.cjs:
       1. Parses stdin JSON for session_id + cwd
       2. Gathers git context from cwd (branch, status, recent commits, HEAD hash)
       3. Reads project name from cwd basename
       4. Spawns session-recall.py → queries Neo4j for last session summary
       5. Writes temp session file: <os.tmpdir()>/memgrap-session-<session_id>.json
       6. Outputs systemMessage with formatted context

Session End:
  Claude Code exits
    → SessionEnd hook fires (JSON input: {session_id, cwd, transcript_path, reason})
    → memgrap-session-end.cjs:
       1. Parses stdin JSON for session_id, cwd, transcript_path
       2. Reads temp session file by session_id
       3. Gathers git diff since start commit hash
       4. Pipes session data JSON to session-save.py via stdin
       5. Cleans up temp session file
```

## Hook Input/Output Contract

Hooks receive JSON on stdin from Claude Code and output JSON to stdout.

**SessionStart input**: `{session_id, type, cwd, ...}`
**SessionStart output**: `{systemMessage: "..."}`

**SessionEnd input**: `{session_id, cwd, transcript_path, reason}`
**SessionEnd output**: (none required — fire-and-forget)

## New Files

| File | Location | Purpose |
|------|----------|---------|
| `memgrap-session-start.cjs` | `~/.claude/hooks/` | SessionStart hook — git + metadata + recall |
| `memgrap-session-end.cjs` | `~/.claude/hooks/` | SessionEnd hook — diff + save to Neo4j |
| `session-recall.py` | `src/session/` | Query Neo4j for last session of this project |
| `session-save.py` | `src/session/` | Write SessionEvent node to Neo4j via Cypher |

## Neo4j Schema

New node label: **SessionEvent**

```cypher
CREATE (s:SessionEvent {
  session_id: String,       -- Claude Code session ID (stable across start/end)
  project: String,          -- CWD directory name
  branch: String,           -- git branch at start
  start_commit: String,     -- HEAD commit hash at session start
  started_at: DateTime,
  ended_at: DateTime,
  commits: [String],        -- commit hashes made during session
  files_changed: [String],  -- files modified during session
  summary: String,          -- human-readable session summary
  transcript_path: String   -- path to Claude Code transcript file
})
```

Index: `CREATE INDEX session_project FOR (s:SessionEvent) ON (s.project)`

## SessionStart Hook Detail

### memgrap-session-start.cjs

Runs on `SessionStart` event (startup, resume, clear, compact).

**Steps:**
1. Read stdin (Claude Code sends JSON with `session_id`, `cwd`, etc.)
2. Execute git commands via `child_process.execSync` with `{cwd}`:
   - `git branch --show-current` → branch name
   - `git status --porcelain` → changed files list
   - `git log --oneline -5` → last 5 commits
   - `git rev-parse HEAD` → current commit hash (for diffing at session end)
3. Detect project: `path.basename(cwd)` (from stdin JSON, NOT `process.cwd()`)
4. Spawn `python D:/MEMGRAP/src/session/session-recall.py --project <name>` (absolute path):
   - Connects to Neo4j (reads .env from MEMGRAP dir)
   - Queries: `MATCH (s:SessionEvent {project: $project}) RETURN s ORDER BY s.ended_at DESC LIMIT 1`
   - Returns JSON: `{summary, branch, ended_at, commits, files_changed}` or `null`
5. Write temp file `<os.tmpdir()>/memgrap-session-<session_id>.json`:
   ```json
   {
     "session_id": "abc123",
     "project": "memgrap",
     "branch": "master",
     "start_commit": "47ee28a",
     "started_at": "2026-03-26T03:45:00Z",
     "cwd": "D:/MEMGRAP"
   }
   ```
6. Output JSON to stdout:
   ```json
   {
     "systemMessage": "## Previous Session\n...\n## Current Context\nBranch: master\n..."
   }
   ```

### session-recall.py

Standalone script. Reads `.env` from `D:/MEMGRAP` (hardcoded MEMGRAP_DIR or env var), connects to Neo4j via `neo4j` Python driver (not Graphiti — no OpenAI needed). Reuses `src/config.py` Settings for Neo4j credentials.

```python
# Args: --project <name>
# Output: JSON to stdout
# Exit 0 on success, non-zero on failure (hook ignores failures)
```

Dependencies: `neo4j` (already installed via graphiti-core), `src.config` (reuse existing).

## SessionEnd Hook Detail

### memgrap-session-end.cjs

Runs on `SessionEnd` event. Fire-and-forget — must complete fast (<2s).

**Steps:**
1. Read stdin JSON for `session_id`, `cwd`, `transcript_path`, `reason`
2. Read temp session file `<os.tmpdir()>/memgrap-session-<session_id>.json`
   - If missing: exit silently (session wasn't tracked)
3. Gather git changes since start commit:
   - `git log --oneline <start_commit>..HEAD` → commits made this session
   - `git diff --name-only <start_commit>..HEAD` → files changed this session
4. Build session summary string:
   - "Session on branch X. Made N commits: [list]. Changed files: [list]."
5. Pipe session data JSON to `python D:/MEMGRAP/src/session/session-save.py` via stdin
   - **Why stdin**: Avoids Windows shell quoting issues with `--data '<json>'`
6. Delete temp session file

### session-save.py

Standalone script. Creates a `SessionEvent` node in Neo4j. Reuses `src/config.py` Settings for Neo4j credentials.

```python
# Input: JSON on stdin
# Writes single MERGE query to Neo4j
# Exit 0 on success
```

Uses MERGE on `session_id` for idempotency.

## Error Handling

| Scenario | Behavior |
|----------|----------|
| Neo4j down | Hook logs error to stderr, exits 0. Session continues. |
| Not a git repo | Skip git context. Capture project name only. |
| SessionEnd interrupted | Temp file remains. Next SessionStart detects orphan, cleans up. |
| No prior session | Start hook shows "No previous session found." |
| Python not available | Hook logs error, exits 0. |
| Stdin parse failure | Hook logs error, exits 0. |

## Settings Configuration

Add to `~/.claude/settings.json` (merge with existing hooks):

```json
{
  "hooks": {
    "SessionStart": [
      {
        "matcher": "startup|resume|clear|compact",
        "hooks": [
          {
            "type": "command",
            "command": "node C:/Users/CUONG/.claude/hooks/memgrap-session-start.cjs"
          }
        ]
      }
    ],
    "SessionEnd": [
      {
        "matcher": "*",
        "hooks": [
          {
            "type": "command",
            "command": "node C:/Users/CUONG/.claude/hooks/memgrap-session-end.cjs"
          }
        ]
      }
    ]
  }
}
```

Note: Use absolute paths for Windows compatibility. These hooks merge with existing hooks in user settings.

## Success Criteria

1. Session start: Claude sees prior session context + current git state in system message
2. Session end: SessionEvent node created in Neo4j with accurate data
3. Both hooks complete in <2 seconds
4. Failure in either hook does not break Claude Code session
5. Works on Windows (D:/ paths, `os.tmpdir()` for temp files)
6. No OpenAI API calls — zero cost per session
7. Git diff is accurate (compares start_commit vs HEAD, not --since timestamp)

## Risks

| Risk | Mitigation |
|------|------------|
| SessionEnd doesn't complete | Keep Python script fast. Single Cypher query. |
| Temp file orphaned | SessionStart detects orphans, cleans up |
| Neo4j connection timeout | Set 2s timeout on Neo4j driver |
| Windows path issues | Absolute paths, `os.tmpdir()`, forward slashes |
| Shell quoting on Windows | Pipe JSON via stdin, not CLI args |
