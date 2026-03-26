# Phase 2: Neo4j Client Library + API Routes Foundation

**Context:** [Spec](../../docs/superpowers/specs/2026-03-26-dashboard-ui-design.md)

**Goal:** Create `dashboard/lib/neo4j.ts` singleton and stub all 8 API routes with correct Neo4j Cypher queries.

**Priority:** Critical — all page phases depend on this data layer.

---

### Task 3: Neo4j Client Singleton

**Files:**
- Create: `dashboard/lib/neo4j.ts`
- Test: `dashboard/__tests__/neo4j.test.ts`

- [ ] **Step 1: Write failing test**

```typescript
// dashboard/__tests__/neo4j.test.ts
// NOTE: requires Neo4j running (docker compose up -d from D:/MEMGRAP)
import { getDriver, runQuery } from '@/lib/neo4j'

describe('neo4j client', () => {
  afterAll(async () => {
    const driver = getDriver()
    await driver.close()
  })

  it('connects and runs a simple query', async () => {
    const result = await runQuery('RETURN 1 AS n', {})
    expect(result[0].n).toBe(1)
  })

  it('getDriver returns singleton', () => {
    const a = getDriver()
    const b = getDriver()
    expect(a).toBe(b)
  })
})
```

- [ ] **Step 2: Run test to verify fail**

```bash
cd D:/MEMGRAP/dashboard
npm test -- --testPathPattern=neo4j 2>&1 | tail -10
```

Expected: FAIL — `Cannot find module '@/lib/neo4j'`

- [ ] **Step 3: Implement neo4j.ts**

```typescript
// dashboard/lib/neo4j.ts
/**
 * Neo4j driver singleton for Next.js API routes.
 * Reads credentials from env vars (provided via .env.local or docker env_file).
 * Uses bolt protocol for direct Neo4j connection.
 */
import neo4j, { Driver, QueryResult } from 'neo4j-driver'

let _driver: Driver | null = null

export function getDriver(): Driver {
  if (!_driver) {
    const uri = process.env.NEO4J_URI ?? 'bolt://localhost:7687'
    const user = process.env.NEO4J_USER ?? 'neo4j'
    const password = process.env.NEO4J_PASSWORD ?? 'password'
    _driver = neo4j.driver(uri, neo4j.auth.basic(user, password), {
      connectionTimeout: 5000,
      maxConnectionLifetime: 3600000,
    })
  }
  return _driver
}

/** Run a read query and return plain records (properties extracted). */
export async function runQuery<T = Record<string, unknown>>(
  cypher: string,
  params: Record<string, unknown>
): Promise<T[]> {
  const session = getDriver().session({ defaultAccessMode: neo4j.session.READ })
  try {
    const result: QueryResult = await session.run(cypher, params)
    return result.records.map(r => {
      const obj: Record<string, unknown> = {}
      for (const key of r.keys) {
        const val = r.get(key)
        // Convert Neo4j Integer to JS number
        if (neo4j.isInt(val)) {
          obj[key as string] = val.toNumber()
        } else if (val && typeof val === 'object' && 'properties' in val) {
          // Node — extract properties
          const props: Record<string, unknown> = {}
          for (const [k, v] of Object.entries(val.properties as Record<string, unknown>)) {
            props[k] = neo4j.isInt(v) ? (v as neo4j.Integer).toNumber() : v
          }
          obj[key as string] = { ...props, _id: val.elementId }
        } else {
          obj[key as string] = val
        }
      }
      return obj as T
    })
  } finally {
    await session.close()
  }
}

/** Return GROUP_ID from env — used to scope all graph queries. */
export function getGroupId(): string {
  return process.env.GROUP_ID ?? 'default'
}
```

- [ ] **Step 4: Create `.env.local` for dev**

```bash
# dashboard/.env.local  (gitignored — copy values from D:/MEMGRAP/.env)
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=<same as .env>
GROUP_ID=<same as .env>
```

Note: copy actual values from `D:/MEMGRAP/.env` manually.

- [ ] **Step 5: Run test to verify pass (requires Neo4j up)**

```bash
cd D:/MEMGRAP && docker compose up -d
cd D:/MEMGRAP/dashboard
npm test -- --testPathPattern=neo4j 2>&1 | tail -10
```

Expected: PASS

- [ ] **Step 6: Commit**

```bash
cd D:/MEMGRAP
git add dashboard/lib/neo4j.ts dashboard/__tests__/neo4j.test.ts
git commit -m "feat(dashboard): add Neo4j driver singleton and runQuery helper"
```

---

### Task 4: API Routes — Stats

**Files:**
- Create: `dashboard/app/api/stats/route.ts`

- [ ] **Step 1: Write failing test**

```typescript
// dashboard/__tests__/api-stats.test.ts
// Integration test — hits real Neo4j
import { GET } from '@/app/api/stats/route'
import { NextRequest } from 'next/server'

describe('GET /api/stats', () => {
  it('returns 200 with expected shape', async () => {
    const req = new NextRequest('http://localhost:3000/api/stats')
    const res = await GET(req)
    expect(res.status).toBe(200)
    const data = await res.json()
    expect(typeof data.entityCount).toBe('number')
    expect(typeof data.edgeCount).toBe('number')
    expect(typeof data.sessionCount).toBe('number')
    expect(typeof data.codeFileCount).toBe('number')
    expect(Array.isArray(data.recentEpisodes)).toBe(true)
    expect(data.health).toHaveProperty('neo4j')
    expect(data.health).toHaveProperty('groupId')
  })
})
```

- [ ] **Step 2: Run test to verify fail**

```bash
cd D:/MEMGRAP/dashboard
npm test -- --testPathPattern=api-stats 2>&1 | tail -10
```

- [ ] **Step 3: Implement stats route**

```typescript
// dashboard/app/api/stats/route.ts
import { NextRequest, NextResponse } from 'next/server'
import { runQuery, getGroupId } from '@/lib/neo4j'

export async function GET(_req: NextRequest) {
  const gid = getGroupId()
  try {
    const [entityRes, edgeRes, sessionRes, codeRes, episodeRes] = await Promise.all([
      runQuery<{ count: number }>(
        'MATCH (n:EntityNode {group_id: $gid}) RETURN count(n) AS count',
        { gid }
      ),
      runQuery<{ count: number }>(
        'MATCH (a:EntityNode {group_id: $gid})-[r:RELATES_TO]->() RETURN count(r) AS count',
        { gid }
      ),
      runQuery<{ count: number }>(
        'MATCH (s:SessionEvent) RETURN count(s) AS count',
        {}
      ),
      runQuery<{ count: number }>(
        'MATCH (f:CodeFile) RETURN count(f) AS count',
        {}
      ),
      runQuery<{ episode: Record<string, unknown> }>(
        `MATCH (e:EpisodicNode)
         WHERE e.group_id = $gid
         RETURN e AS episode
         ORDER BY e.created_at DESC
         LIMIT 10`,
        { gid }
      ),
    ])

    return NextResponse.json({
      entityCount: entityRes[0]?.count ?? 0,
      edgeCount: edgeRes[0]?.count ?? 0,
      sessionCount: sessionRes[0]?.count ?? 0,
      codeFileCount: codeRes[0]?.count ?? 0,
      recentEpisodes: episodeRes.map(r => r.episode),
      health: {
        neo4j: 'ok',
        groupId: gid,
        llmModel: process.env.LLM_MODEL ?? 'gpt-4o-mini',
      },
    })
  } catch (err) {
    const message = err instanceof Error ? err.message : 'Unknown error'
    return NextResponse.json(
      { error: 'Neo4j unreachable', detail: message },
      { status: 503 }
    )
  }
}
```

- [ ] **Step 4: Run test to verify pass**

```bash
cd D:/MEMGRAP/dashboard
npm test -- --testPathPattern=api-stats 2>&1 | tail -10
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
cd D:/MEMGRAP
git add dashboard/app/api/stats/
git commit -m "feat(dashboard): add /api/stats route with Neo4j aggregate counts"
```

---

### Task 5: API Routes — Sessions

**Files:**
- Create: `dashboard/app/api/sessions/route.ts`
- Create: `dashboard/app/api/sessions/[id]/route.ts`

- [ ] **Step 1: Write failing test**

```typescript
// dashboard/__tests__/api-sessions.test.ts
import { GET as listSessions } from '@/app/api/sessions/route'
import { NextRequest } from 'next/server'

describe('GET /api/sessions', () => {
  it('returns 200 with sessions array', async () => {
    const req = new NextRequest('http://localhost:3000/api/sessions')
    const res = await listSessions(req)
    expect(res.status).toBe(200)
    const data = await res.json()
    expect(Array.isArray(data.sessions)).toBe(true)
  })
})
```

- [ ] **Step 2: Run test to verify fail**

```bash
cd D:/MEMGRAP/dashboard
npm test -- --testPathPattern=api-sessions 2>&1 | tail -10
```

- [ ] **Step 3: Implement sessions list route**

```typescript
// dashboard/app/api/sessions/route.ts
import { NextRequest, NextResponse } from 'next/server'
import { runQuery } from '@/lib/neo4j'

export async function GET(_req: NextRequest) {
  try {
    const rows = await runQuery<{ s: Record<string, unknown> }>(
      `MATCH (s:SessionEvent)
       RETURN s
       ORDER BY s.ended_at DESC
       LIMIT 100`,
      {}
    )
    const sessions = rows.map(r => ({
      ...r.s,
      commitCount: Array.isArray(r.s.commits) ? (r.s.commits as unknown[]).length : 0,
      filesCount: Array.isArray(r.s.files_changed) ? (r.s.files_changed as unknown[]).length : 0,
    }))
    return NextResponse.json({ sessions })
  } catch (err) {
    const message = err instanceof Error ? err.message : 'Unknown error'
    return NextResponse.json({ error: 'Neo4j unreachable', detail: message }, { status: 503 })
  }
}
```

- [ ] **Step 4: Implement session detail route**

```typescript
// dashboard/app/api/sessions/[id]/route.ts
import { NextRequest, NextResponse } from 'next/server'
import { runQuery } from '@/lib/neo4j'

export async function GET(
  _req: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params
  try {
    const rows = await runQuery<{ s: Record<string, unknown> }>(
      'MATCH (s:SessionEvent {session_id: $id}) RETURN s',
      { id }
    )
    if (rows.length === 0) {
      return NextResponse.json({ error: 'Not found' }, { status: 404 })
    }
    return NextResponse.json({ session: rows[0].s })
  } catch (err) {
    const message = err instanceof Error ? err.message : 'Unknown error'
    return NextResponse.json({ error: 'Neo4j unreachable', detail: message }, { status: 503 })
  }
}
```

- [ ] **Step 5: Run test to verify pass**

```bash
cd D:/MEMGRAP/dashboard
npm test -- --testPathPattern=api-sessions 2>&1 | tail -10
```

- [ ] **Step 6: Commit**

```bash
cd D:/MEMGRAP
git add dashboard/app/api/sessions/
git commit -m "feat(dashboard): add /api/sessions routes (list + detail)"
```

---

### Task 6: API Routes — Code Index

**Files:**
- Create: `dashboard/app/api/code/files/route.ts`

- [ ] **Step 1: Write failing test**

```typescript
// dashboard/__tests__/api-code.test.ts
import { GET } from '@/app/api/code/files/route'
import { NextRequest } from 'next/server'

describe('GET /api/code/files', () => {
  it('returns 200 with files array', async () => {
    const req = new NextRequest('http://localhost:3000/api/code/files')
    const res = await GET(req)
    expect(res.status).toBe(200)
    const data = await res.json()
    expect(Array.isArray(data.files)).toBe(true)
  })
})
```

- [ ] **Step 2: Run test to verify fail**

```bash
cd D:/MEMGRAP/dashboard
npm test -- --testPathPattern=api-code 2>&1 | tail -10
```

- [ ] **Step 3: Implement code files route**

```typescript
// dashboard/app/api/code/files/route.ts
import { NextRequest, NextResponse } from 'next/server'
import { runQuery } from '@/lib/neo4j'

export async function GET(req: NextRequest) {
  const { searchParams } = req.nextUrl
  const search = searchParams.get('search') ?? ''
  const lang = searchParams.get('lang') ?? ''

  try {
    let cypher = `
      MATCH (f:CodeFile)
      OPTIONAL MATCH (f)-[:CONTAINS|IMPORTS]->(c)
      WHERE ($search = '' OR toLower(f.path) CONTAINS toLower($search))
        AND ($lang = '' OR f.language = $lang)
      RETURN f, collect(c) AS children
      ORDER BY f.path
      LIMIT 200
    `
    const rows = await runQuery<{
      f: Record<string, unknown>
      children: Array<Record<string, unknown>>
    }>(cypher, { search, lang })

    const files = rows.map(r => ({
      ...r.f,
      children: r.children.filter(Boolean),
    }))
    return NextResponse.json({ files })
  } catch (err) {
    const message = err instanceof Error ? err.message : 'Unknown error'
    return NextResponse.json({ error: 'Neo4j unreachable', detail: message }, { status: 503 })
  }
}
```

- [ ] **Step 4: Run test to verify pass**

```bash
cd D:/MEMGRAP/dashboard
npm test -- --testPathPattern=api-code 2>&1 | tail -10
```

- [ ] **Step 5: Commit**

```bash
cd D:/MEMGRAP
git add dashboard/app/api/code/
git commit -m "feat(dashboard): add /api/code/files route for code index"
```

---

### Task 7: API Routes — Graph

**Files:**
- Create: `dashboard/app/api/graph/nodes/route.ts`
- Create: `dashboard/app/api/graph/nodes/[id]/route.ts`
- Create: `dashboard/app/api/graph/edges/route.ts`
- Create: `dashboard/app/api/graph/viz/route.ts`

- [ ] **Step 1: Write failing test**

```typescript
// dashboard/__tests__/api-graph.test.ts
import { GET as getViz } from '@/app/api/graph/viz/route'
import { NextRequest } from 'next/server'

describe('GET /api/graph/viz', () => {
  it('returns 200 with nodes and edges arrays', async () => {
    const req = new NextRequest('http://localhost:3000/api/graph/viz?limit=10')
    const res = await getViz(req)
    expect(res.status).toBe(200)
    const data = await res.json()
    expect(Array.isArray(data.nodes)).toBe(true)
    expect(Array.isArray(data.edges)).toBe(true)
  })
})
```

- [ ] **Step 2: Run test to verify fail**

```bash
cd D:/MEMGRAP/dashboard
npm test -- --testPathPattern=api-graph 2>&1 | tail -10
```

- [ ] **Step 3: Implement graph nodes route**

```typescript
// dashboard/app/api/graph/nodes/route.ts
import { NextRequest, NextResponse } from 'next/server'
import { runQuery, getGroupId } from '@/lib/neo4j'

export async function GET(req: NextRequest) {
  const gid = getGroupId()
  const { searchParams } = req.nextUrl
  const type = searchParams.get('type') ?? ''
  const search = searchParams.get('search') ?? ''
  const limit = Math.min(Number(searchParams.get('limit') ?? '100'), 500)

  try {
    const rows = await runQuery<{ n: Record<string, unknown> }>(
      `MATCH (n:EntityNode)
       WHERE n.group_id = $gid
         AND ($type = '' OR n.entity_type = $type)
         AND ($search = '' OR toLower(n.name) CONTAINS toLower($search))
       RETURN n
       ORDER BY n.created_at DESC
       LIMIT $limit`,
      { gid, type, search, limit }
    )
    return NextResponse.json({ nodes: rows.map(r => r.n) })
  } catch (err) {
    const message = err instanceof Error ? err.message : 'Unknown error'
    return NextResponse.json({ error: 'Neo4j unreachable', detail: message }, { status: 503 })
  }
}
```

- [ ] **Step 4: Implement graph node detail route**

```typescript
// dashboard/app/api/graph/nodes/[id]/route.ts
import { NextRequest, NextResponse } from 'next/server'
import { runQuery } from '@/lib/neo4j'

export async function GET(
  _req: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params
  try {
    const rows = await runQuery<{
      n: Record<string, unknown>
      r: Record<string, unknown>
      m: Record<string, unknown>
    }>(
      `MATCH (n:EntityNode)-[r]-(m)
       WHERE elementId(n) = $id
       RETURN n, r, m
       LIMIT 50`,
      { id }
    )
    if (rows.length === 0) {
      // Try fetching node alone (may have no edges)
      const solo = await runQuery<{ n: Record<string, unknown> }>(
        'MATCH (n:EntityNode) WHERE elementId(n) = $id RETURN n',
        { id }
      )
      if (solo.length === 0) return NextResponse.json({ error: 'Not found' }, { status: 404 })
      return NextResponse.json({ node: solo[0].n, connections: [] })
    }
    const node = rows[0].n
    const connections = rows.map(r => ({ rel: r.r, neighbor: r.m }))
    return NextResponse.json({ node, connections })
  } catch (err) {
    const message = err instanceof Error ? err.message : 'Unknown error'
    return NextResponse.json({ error: 'Neo4j unreachable', detail: message }, { status: 503 })
  }
}
```

- [ ] **Step 5: Implement graph edges route**

```typescript
// dashboard/app/api/graph/edges/route.ts
import { NextRequest, NextResponse } from 'next/server'
import { runQuery, getGroupId } from '@/lib/neo4j'

export async function GET(req: NextRequest) {
  const gid = getGroupId()
  const limit = Math.min(Number(req.nextUrl.searchParams.get('limit') ?? '200'), 500)
  try {
    const rows = await runQuery<{
      sourceId: string; targetId: string; label: string; fact: string
    }>(
      `MATCH (a:EntityNode)-[r:RELATES_TO]->(b:EntityNode)
       WHERE a.group_id = $gid
       RETURN elementId(a) AS sourceId, elementId(b) AS targetId,
              type(r) AS label, r.fact AS fact
       LIMIT $limit`,
      { gid, limit }
    )
    return NextResponse.json({ edges: rows })
  } catch (err) {
    const message = err instanceof Error ? err.message : 'Unknown error'
    return NextResponse.json({ error: 'Neo4j unreachable', detail: message }, { status: 503 })
  }
}
```

- [ ] **Step 6: Implement graph viz route (force-graph data)**

```typescript
// dashboard/app/api/graph/viz/route.ts
import { NextRequest, NextResponse } from 'next/server'
import { runQuery, getGroupId } from '@/lib/neo4j'

/** Returns nodes + edges shaped for react-force-graph-2d. */
export async function GET(req: NextRequest) {
  const gid = getGroupId()
  const limit = Math.min(Number(req.nextUrl.searchParams.get('limit') ?? '200'), 500)
  const type = req.nextUrl.searchParams.get('type') ?? ''

  try {
    const [nodeRows, edgeRows] = await Promise.all([
      runQuery<{ n: Record<string, unknown> }>(
        `MATCH (n:EntityNode)
         WHERE n.group_id = $gid
           AND ($type = '' OR n.entity_type = $type)
         RETURN n
         LIMIT $limit`,
        { gid, limit, type }
      ),
      runQuery<{ sid: string; tid: string; label: string; fact: string }>(
        `MATCH (a:EntityNode)-[r:RELATES_TO]->(b:EntityNode)
         WHERE a.group_id = $gid
           AND ($type = '' OR a.entity_type = $type)
         RETURN elementId(a) AS sid, elementId(b) AS tid,
                type(r) AS label, r.fact AS fact
         LIMIT $limit`,
        { gid, limit, type }
      ),
    ])

    const nodes = nodeRows.map(r => ({
      id: r.n._id as string,
      name: r.n.name as string,
      entityType: r.n.entity_type as string,
      ...r.n,
    }))
    const edges = edgeRows.map(r => ({
      source: r.sid,
      target: r.tid,
      label: r.label,
      fact: r.fact,
    }))

    return NextResponse.json({ nodes, edges })
  } catch (err) {
    const message = err instanceof Error ? err.message : 'Unknown error'
    return NextResponse.json({ error: 'Neo4j unreachable', detail: message }, { status: 503 })
  }
}
```

- [ ] **Step 7: Run test to verify pass**

```bash
cd D:/MEMGRAP/dashboard
npm test -- --testPathPattern=api-graph 2>&1 | tail -10
```

- [ ] **Step 8: Commit**

```bash
cd D:/MEMGRAP
git add dashboard/app/api/graph/
git commit -m "feat(dashboard): add /api/graph/* routes (nodes, edges, viz, detail)"
```
