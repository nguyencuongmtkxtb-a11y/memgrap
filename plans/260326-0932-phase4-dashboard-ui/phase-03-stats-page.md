# Phase 3: Stats Page (`/stats`)

**Context:** [Spec](../../docs/superpowers/specs/2026-03-26-dashboard-ui-design.md) | [API](phase-02-neo4j-client.md)

**Goal:** Simplest page — validates the data layer end-to-end. Stat cards + recent activity + health check.

---

### Task 8: Stats Components + Page

**Files:**
- Create: `dashboard/components/stat-cards.tsx`
- Create: `dashboard/app/stats/page.tsx`

- [ ] **Step 1: Write failing test for stat-cards component**

```typescript
// dashboard/__tests__/stat-cards.test.tsx
import { render, screen } from '@testing-library/react'
import { StatCards } from '@/components/stat-cards'

const mockStats = {
  entityCount: 42,
  edgeCount: 108,
  sessionCount: 7,
  codeFileCount: 23,
  recentEpisodes: [
    { _id: '1', content: 'Remembered a decision about auth', created_at: '2026-03-26T10:00:00Z' },
  ],
  health: { neo4j: 'ok', groupId: 'test-proj', llmModel: 'gpt-4o-mini' },
}

describe('StatCards', () => {
  it('renders count cards', () => {
    render(<StatCards stats={mockStats} />)
    expect(screen.getByText('42')).toBeInTheDocument()
    expect(screen.getByText('108')).toBeInTheDocument()
    expect(screen.getByText('7')).toBeInTheDocument()
    expect(screen.getByText('23')).toBeInTheDocument()
  })

  it('shows health status', () => {
    render(<StatCards stats={mockStats} />)
    expect(screen.getByText('test-proj')).toBeInTheDocument()
  })
})
```

- [ ] **Step 2: Run test to verify fail**

```bash
cd D:/MEMGRAP/dashboard
npm test -- --testPathPattern=stat-cards 2>&1 | tail -10
```

- [ ] **Step 3: Implement stat-cards.tsx**

```typescript
// dashboard/components/stat-cards.tsx
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Network, Link2, Clock, FileCode2 } from 'lucide-react'

interface StatsData {
  entityCount: number
  edgeCount: number
  sessionCount: number
  codeFileCount: number
  recentEpisodes: Array<{ _id: string; content?: string; created_at?: string }>
  health: { neo4j: string; groupId: string; llmModel: string }
}

const CARDS = [
  { key: 'entityCount' as const, label: 'Entities',    icon: Network },
  { key: 'edgeCount'   as const, label: 'Facts',       icon: Link2 },
  { key: 'sessionCount'as const, label: 'Sessions',    icon: Clock },
  { key: 'codeFileCount'as const,label: 'Code Files',  icon: FileCode2 },
]

export function StatCards({ stats }: { stats: StatsData }) {
  return (
    <div className="space-y-6">
      {/* Count cards */}
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        {CARDS.map(({ key, label, icon: Icon }) => (
          <Card key={key} className="bg-card border-border">
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">{label}</CardTitle>
              <Icon className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats[key].toLocaleString()}</div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Health */}
      <Card className="bg-card border-border">
        <CardHeader>
          <CardTitle className="text-sm font-medium">System Health</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-wrap gap-3 text-sm">
          <span>
            Neo4j:{' '}
            <Badge variant={stats.health.neo4j === 'ok' ? 'default' : 'destructive'}>
              {stats.health.neo4j}
            </Badge>
          </span>
          <span>
            Group: <code className="text-xs bg-muted px-1 rounded">{stats.health.groupId}</code>
          </span>
          <span>
            LLM: <code className="text-xs bg-muted px-1 rounded">{stats.health.llmModel}</code>
          </span>
        </CardContent>
      </Card>

      {/* Recent episodes */}
      <Card className="bg-card border-border">
        <CardHeader>
          <CardTitle className="text-sm font-medium">Recent Activity</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          {stats.recentEpisodes.length === 0 && (
            <p className="text-sm text-muted-foreground">No recent activity.</p>
          )}
          {stats.recentEpisodes.map(ep => (
            <div key={ep._id} className="text-sm border-b border-border pb-2 last:border-0">
              <p className="truncate text-foreground">{ep.content ?? '(no content)'}</p>
              {ep.created_at && (
                <p className="text-xs text-muted-foreground mt-0.5">
                  {new Date(ep.created_at).toLocaleString()}
                </p>
              )}
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  )
}
```

- [ ] **Step 4: Implement stats page**

```typescript
// dashboard/app/stats/page.tsx
import { StatCards } from '@/components/stat-cards'

async function fetchStats() {
  // Server component — direct fetch to own API route
  const res = await fetch('http://localhost:3000/api/stats', { cache: 'no-store' })
  if (!res.ok) return null
  return res.json()
}

export default async function StatsPage() {
  const stats = await fetchStats()

  if (!stats || stats.error) {
    return (
      <div className="p-8">
        <div className="rounded-md bg-destructive/10 border border-destructive/20 px-4 py-3 text-sm text-destructive">
          Neo4j unreachable — ensure <code>docker compose up -d</code> is running.
        </div>
      </div>
    )
  }

  return (
    <div className="p-8 max-w-5xl">
      <h1 className="text-xl font-semibold mb-6">Stats</h1>
      <StatCards stats={stats} />
    </div>
  )
}
```

- [ ] **Step 5: Run component test to verify pass**

```bash
cd D:/MEMGRAP/dashboard
npm test -- --testPathPattern=stat-cards 2>&1 | tail -10
```

- [ ] **Step 6: Manual smoke test**

```bash
cd D:/MEMGRAP/dashboard
npm run dev &
sleep 3
curl -s http://localhost:3000/api/stats | python -m json.tool | head -20
kill %1
```

Expected: JSON with entityCount, edgeCount, etc.

- [ ] **Step 7: Commit**

```bash
cd D:/MEMGRAP
git add dashboard/components/stat-cards.tsx dashboard/app/stats/
git commit -m "feat(dashboard): add /stats page with stat cards and health check"
```
