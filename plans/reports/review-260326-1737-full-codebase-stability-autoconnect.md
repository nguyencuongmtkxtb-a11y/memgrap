# Memgrap Full Codebase Review — Stability, Performance & Auto-Connect

**Date:** 2026-03-26
**Scope:** All source files (Python MCP server, dashboard, hooks, config)
**Goal:** Đánh giá ổn định, hiệu suất, và khả năng tự động kết nối cho non-tech users

---

## Tổng quan kiến trúc

```
Claude Code (stdio) → MCP Server (FastMCP) → Graphiti Core → Neo4j (Docker)
                                                    |
                                              OpenAI (gpt-4o-mini + embeddings)

Claude Code hooks → session_save.py / session_recall.py → Neo4j (sync driver)

Dashboard (Next.js 16) → Neo4j (bolt) → Browser (react-force-graph-2d)
```

**Files:** 14 Python, 15 TypeScript, 2 Node.js hooks
**Total LoC:** ~1400 (core) + ~800 (dashboard)

---

## 1. STABILITY — Đánh giá ổn định

### 1.1 Tốt ✅

| Module | Điểm mạnh |
|--------|-----------|
| `graph_service.py` | Lazy init idempotent, property guard, clean close() |
| `entity_types.py` | Ontology Pydantic models rõ ràng, 8 entity types |
| `result_formatters.py` | Simple, safe, truncate episode content at 200 chars |
| `neo4j_ingestor.py` | MERGE cho idempotency, clear-before-reindex |
| `session_save.py` | MERGE idempotent, input validation cho required fields |
| `session_recall.py` | Graceful null return khi không có session |
| Dashboard API routes | Consistent error handling → 503 with detail message |
| Dashboard `lib/neo4j.ts` | Singleton driver, Integer conversion, node property extraction |
| Tests | 6 integration tests hit real Neo4j, cleanup fixtures |

### 1.2 Vấn đề cần sửa ⚠️

#### P1 — Critical

**`mcp_server.py:207-217` — `_cleanup()` dùng deprecated API**
```python
loop = asyncio.get_event_loop()  # deprecated Python 3.10+
if loop.is_running():
    loop.create_task(graph_service.close())  # task có thể không chạy nếu loop đang shutdown
```
→ Nên dùng `try/except RuntimeError` với `asyncio.run()` fallback.

**`config.py:11` — `env_file=".env"` relative path**
- Chỉ hoạt động khi CWD = project root
- `.mcp.json` set `cwd: "D:\\MEMGRAP"` nên hiện tại OK
- Nhưng nếu user chạy từ thư mục khác → load sai/không load .env
→ Nên resolve absolute path từ `__file__`

**`config.py:23` — `openai_api_key: str = ""` empty default**
- Server khởi động thành công dù không có key
- Fail lặng lẽ khi tool call đầu tiên → user confuse
→ Nên validate non-empty tại `initialize()` và raise rõ lỗi

#### P2 — Medium

**`graph_service.py:35` — Side effect toàn cục**
```python
os.environ["SEMAPHORE_LIMIT"] = str(self._settings.semaphore_limit)
```
Ghi đè env var toàn process. Nếu có multi-instance → conflict.

**`session_save.py:15` / `session_recall.py:16` — `sys.path.insert` hack**
```python
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
```
Fragile. Nên dùng package install (`pip install -e .`) đã handle.

**`mcp_server.py:186` — Truy cập internal `graph_service.graphiti.driver`**
```python
indexer = CodeIndexer(graph_service.graphiti.driver)
```
Phá encapsulation. Nếu Graphiti API thay đổi → break.

### 1.3 Thiếu ❌

| Thiếu | Impact |
|-------|--------|
| Không retry khi Neo4j tạm unavailable | Tool call fail nếu Neo4j restart |
| Không timeout cho Graphiti API calls | Hang nếu OpenAI API chậm |
| Không graceful degradation | Nếu Neo4j down → tất cả tools fail, không fallback |
| Không rate limit cho OpenAI API calls | `remember` spam có thể burn API credits |
| Dashboard không health check endpoint riêng | Khó monitor |

---

## 2. PERFORMANCE — Đánh giá hiệu suất

### 2.1 Tốt ✅

- Lazy init → server start nhanh, chỉ connect Neo4j khi cần
- `lru_cache` cho Settings → không re-parse .env mỗi call
- Batch upsert trong `neo4j_ingestor.py` (UNWIND)
- Dashboard dùng Promise.all cho parallel Neo4j queries
- `ForceGraph2D` dùng canvas (không DOM nodes) → tốt cho render
- ResizeObserver cho responsive graph sizing

### 2.2 Vấn đề ⚠️

| Vấn đề | Severity | Giải pháp |
|--------|----------|-----------|
| Graph viz load tất cả nodes cùng lúc (max 500) | Medium | Implement pagination/infinite scroll |
| `neo4j_ingestor` clear + re-insert per file (N+1 pattern) | Low | Batch multiple files |
| Không cache search results | Low | Add TTL cache cho frequent queries |
| Dashboard API không pagination | Medium | Add cursor-based pagination |
| Tree-sitter language objects init tại module load | Low | Acceptable, ~100ms startup |

### 2.3 Benchmark estimates

| Operation | Est. time | Bottleneck |
|-----------|-----------|------------|
| `remember` (store 1 episode) | 3-8s | OpenAI LLM extraction |
| `recall` (search) | 0.5-2s | Neo4j + OpenAI embedding |
| `index_codebase` (100 files) | 2-5s | Neo4j writes (AST parse = fast) |
| Dashboard graph load (200 nodes) | 0.3-1s | Neo4j read + JSON serialize |
| Session hooks (start/end) | 0.5-2s | Python spawn + Neo4j connect |

---

## 3. AUTO-CONNECT cho NON-TECH USERS — VẤN ĐỀ LỚN NHẤT 🔴

### 3.1 Tình trạng hiện tại

**User phải làm thủ công 6 bước:**
1. Cài Python ≥ 3.10
2. Cài Docker Desktop
3. `pip install -e .`
4. `docker compose up -d`
5. Copy `.env.example` → `.env`, thêm OpenAI key
6. Restart Claude Code

**Hardcoded paths — KHÔNG portable:**
- `.mcp.json` → `"cwd": "D:\\MEMGRAP"` — chỉ chạy trên máy này
- `memgrap-session-start.cjs` → `const MEMGRAP_DIR = "D:/MEMGRAP"` — hardcode
- `memgrap-session-end.cjs` → `const MEMGRAP_DIR = "D:/MEMGRAP"` — hardcode

**Không auto-detect project:** MCP server dùng fixed `group_id=default`, không tự phát hiện project nào đang mở.

### 3.2 Kế hoạch cải thiện — 3 mức độ

#### Level 1: Quick Fixes (không thay đổi kiến trúc)

1. **`setup.bat` / `setup.sh`** — One-click installer:
   - Check Docker installed
   - Start Neo4j container
   - Prompt user cho OpenAI API key
   - Generate `.env`
   - Install Python deps
   - Generate `.mcp.json` với dynamic path
   - Copy hooks với dynamic MEMGRAP_DIR

2. **Dynamic path trong `.mcp.json`:**
   ```json
   {
     "mcpServers": {
       "graphiti-memory": {
         "command": "python",
         "args": ["-m", "src.mcp_server"],
         "env": { "MEMGRAP_DIR": "${workspaceFolder}" }
       }
     }
   }
   ```

3. **Config resolve absolute path:**
   ```python
   # config.py
   _PROJECT_ROOT = Path(__file__).resolve().parent.parent
   env_file = _PROJECT_ROOT / ".env"
   ```

4. **Hooks dùng env var thay vì hardcode:**
   ```javascript
   const MEMGRAP_DIR = process.env.MEMGRAP_DIR || path.resolve(__dirname, "../../MEMGRAP");
   ```

#### Level 2: Auto-Start & Health (trung bình)

5. **Auto-start Docker Neo4j** khi MCP server khởi động:
   ```python
   async def _ensure_neo4j():
       """Check Neo4j container, start if not running."""
       result = subprocess.run(["docker", "inspect", "memgrap-neo4j"], ...)
       if result.returncode != 0:
           subprocess.run(["docker", "compose", "up", "-d"], cwd=MEMGRAP_DIR)
           await _wait_for_neo4j()
   ```

6. **Health check tool có guidance:**
   ```
   get_status → {status: "error", fix: "Run: docker compose up -d"}
   ```

7. **Auto group_id per project:**
   ```python
   # Detect project from CWD passed by Claude Code
   group_id = os.environ.get("CLAUDE_CWD", "default").split("/")[-1]
   ```

#### Level 3: Zero-Config (tham vọng)

8. **NPM/pip global install** → `pip install memgrap` → tự register MCP server
9. **Embedded Neo4j** (SQLite fallback khi Docker unavailable)
10. **Auto-discover projects** từ git repos đang mở
11. **Web installer UI** cho non-tech users

### 3.3 Priority Matrix

| Fix | Effort | Impact cho non-tech | Priority |
|-----|--------|---------------------|----------|
| `setup.bat` one-click | 2h | ★★★★★ | P0 |
| Dynamic path thay hardcode | 1h | ★★★★★ | P0 |
| Config resolve absolute .env | 30m | ★★★★ | P0 |
| Validate OpenAI key on init | 30m | ★★★★ | P1 |
| Auto-start Docker Neo4j | 3h | ★★★★ | P1 |
| Health check with fix guidance | 1h | ★★★ | P1 |
| Auto group_id per project | 1h | ★★★ | P2 |
| Fix `_cleanup()` deprecated API | 30m | ★★ | P2 |
| Pagination cho dashboard | 3h | ★★ | P3 |

---

## 4. CODE QUALITY Summary

| Metric | Score | Notes |
|--------|-------|-------|
| **Modularity** | 9/10 | Tách biệt rõ: config, factory, service, formatters, indexer, session |
| **Error handling** | 7/10 | Có try/catch nhưng thiếu retry, thiếu specific error types |
| **Testing** | 6/10 | 6 integration tests cho session, 0 tests cho MCP tools, 0 cho indexer |
| **Documentation** | 8/10 | Docstrings đầy đủ, README clear |
| **Security** | 7/10 | Dashboard API thiếu auth, Neo4j default password |
| **Portability** | 3/10 | Hardcoded paths everywhere — biggest issue |
| **DX for non-tech** | 2/10 | Cần 6 bước manual setup, no installer |

---

## 5. Khuyến nghị ưu tiên

### Phải làm ngay (P0):
1. Tạo `setup.bat` + `setup.sh` one-click installer
2. Xóa hardcoded paths → dùng dynamic resolution
3. Fix config.py resolve .env absolute path
4. Validate OpenAI key sớm, fail fast với message rõ

### Nên làm sớm (P1):
5. Auto-start Docker container khi MCP server init
6. Health check tool trả guidance cụ thể
7. Thêm retry logic cho Neo4j connection

### Cải thiện dần (P2-P3):
8. Test coverage cho MCP tools + indexer
9. Dashboard pagination
10. Auto group_id per project

---

## Unresolved Questions

1. Có muốn support SQLite fallback khi không có Docker không?
2. Có muốn publish lên PyPI để `pip install memgrap` global không?
3. Dashboard có cần auth không (hiện expose trên port 3001 không có auth)?
4. Có muốn support nhiều OpenAI-compatible providers (Anthropic, local LLM) không?
