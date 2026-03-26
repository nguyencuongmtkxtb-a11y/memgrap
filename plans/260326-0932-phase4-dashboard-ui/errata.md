# Dashboard Plan Errata — Schema Mismatches & Review Fixes

**Date:** 2026-03-26 | **Source:** Neo4j schema verification + code review

---

## Schema Mismatches (discovered via `db.schema.nodeTypeProperties()`)

### E1 — Node label: `Entity` not `EntityNode`
- **Plan says:** `MATCH (n:EntityNode {group_id: $gid})`
- **Reality:** Label is `Entity` with sublabels `Concept`, `Tool`
- **All affected phases:** 2 (stats, graph routes), 6 (graph page)
- **Fix:** Replace `EntityNode` → `Entity` in all Cypher queries

### E2 — Node label: `Episodic` not `EpisodicNode`
- **Plan says:** `MATCH (e:EpisodicNode)`
- **Reality:** Label is `Episodic`
- **Affected:** phase-02 stats route
- **Fix:** Replace `EpisodicNode` → `Episodic`

### E3 — Entity type stored as dual labels, not `entity_type` property
- **Plan says:** `n.entity_type = $type` filter
- **Reality:** Types are labels (e.g., `:Concept:Entity`, `:Tool:Entity`). Property `labels` (StringArray) also exists.
- **Fix:** Use `labels(n)` or the `labels` property for filtering. E.g.:
  ```cypher
  MATCH (n:Entity) WHERE n.group_id = $gid
    AND ($type = '' OR $type IN labels(n))
  ```

### E4 — Code child property: `line` not `line_start`
- **Plan says:** `child.line_start`
- **Reality:** Property is `line` (Long)
- **Fix:** Use `line` in CodeTree component

### E5 — SessionEvent has `project` property, no `group_id`
- **Plan says:** No GROUP_ID filter on sessions (review S3 noted this)
- **Reality:** `SessionEvent` has `project` property
- **Fix:** Filter sessions by `project` matching GROUP_ID/project context

### E6 — Episodic has `content` property (confirmed)
- **Plan assumed:** `content` or other — verified `content` is correct

### E7 — Episodic timestamp: `created_at` is DateTime (confirmed)
- **Plan assumed:** `created_at` — verified correct

### E8 — Entity node `entity_type` not a property
- For viz route node coloring: derive type from `labels(n)` excluding "Entity"
- GraphViewer color map keys match sublabel names: `Concept`, `Tool`, etc.
- Current known sublabels: `Concept`, `Tool`
- Other entity types from spec (CodePattern, TechDecision, etc.) not yet in DB but may appear

---

## Review Fixes (from plan-review report)

### C1 — Jest config typo
`setupFilesAfterFramework` → `setupFilesAfterEnv`

### C2 — Server Component fetch localhost
Replace `fetch('http://localhost:3000/api/...')` with direct handler import in Server Components (stats, sessions pages)

### I1 — Missing userEvent import
Add `import userEvent from '@testing-library/user-event'` in node-detail test

### I3 — Cypher WHERE placement
Move WHERE before OPTIONAL MATCH in code files route

### I4 — neo4j.Integer import
Use named import `Integer` from neo4j-driver

### I5 — @types/react-force-graph-2d doesn't exist
Remove install step — types are bundled

### S1 — GraphViewer sizing
Use ResizeObserver or container dimensions instead of `width={undefined}`
