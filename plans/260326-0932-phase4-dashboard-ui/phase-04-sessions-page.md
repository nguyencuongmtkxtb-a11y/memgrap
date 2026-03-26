# Phase 4: Sessions Page (`/sessions`)

**Context:** [Spec](../../docs/superpowers/specs/2026-03-26-dashboard-ui-design.md)

**Goal:** List SessionEvent nodes sorted by date, click to see detail — commits, files changed, summary.

---

### Task 9: Session Components + Page

**Files:**
- Create: `dashboard/components/session-list.tsx`
- Create: `dashboard/app/sessions/page.tsx`
- Create: `dashboard/app/sessions/[id]/page.tsx`

- [ ] **Step 1: Write failing test**

```typescript
// dashboard/__tests__/session-list.test.tsx
import { render, screen } from '@testing-library/react'
import { SessionList } from '@/components/session-list'

const mockSessions = [
  {
    session_id: 'abc123',
    branch: 'feat/auth',
    ended_at: '2026-03-26T10:00:00Z',
    commitCount: 3,
    filesCount: 7,
    summary: 'Implemented auth flow',
  },
]

describe('SessionList', () => {
  it('renders session row with branch and counts', () => {
    render(<SessionList sessions={mockSessions} />)
    expect(screen.getByText('feat/auth')).toBeInTheDocument()
    expect(screen.getByText('3 commits')).toBeInTheDocument()
    expect(screen.getByText('7 files')).toBeInTheDocument()
  })

  it('shows empty state when no sessions', () => {
    render(<SessionList sessions={[]} />)
    expect(screen.getByText(/no sessions/i)).toBeInTheDocument()
  })
})
```

- [ ] **Step 2: Run test to verify fail**

```bash
cd D:/MEMGRAP/dashboard
npm test -- --testPathPattern=session-list 2>&1 | tail -10
```

- [ ] **Step 3: Implement session-list.tsx**

```typescript
// dashboard/components/session-list.tsx
'use client'

import Link from 'next/link'
import { Badge } from '@/components/ui/badge'
import { GitBranch, GitCommit, FileCode2, Clock } from 'lucide-react'

interface SessionRow {
  session_id: string
  branch: string
  ended_at: string
  commitCount: number
  filesCount: number
  summary?: string
  project?: string
}

export function SessionList({ sessions }: { sessions: SessionRow[] }) {
  if (sessions.length === 0) {
    return <p className="text-sm text-muted-foreground py-4">No sessions recorded yet.</p>
  }

  return (
    <div className="divide-y divide-border rounded-lg border border-border overflow-hidden">
      {sessions.map(s => (
        <Link
          key={s.session_id}
          href={`/sessions/${s.session_id}`}
          className="flex items-center gap-4 px-4 py-3 hover:bg-accent transition-colors"
        >
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-0.5">
              <GitBranch className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
              <span className="text-sm font-medium truncate">{s.branch}</span>
              {s.project && (
                <Badge variant="outline" className="text-xs">{s.project}</Badge>
              )}
            </div>
            {s.summary && (
              <p className="text-xs text-muted-foreground truncate">{s.summary}</p>
            )}
          </div>
          <div className="flex items-center gap-4 text-xs text-muted-foreground shrink-0">
            <span className="flex items-center gap-1">
              <GitCommit className="h-3.5 w-3.5" />{s.commitCount} commits
            </span>
            <span className="flex items-center gap-1">
              <FileCode2 className="h-3.5 w-3.5" />{s.filesCount} files
            </span>
            <span className="flex items-center gap-1">
              <Clock className="h-3.5 w-3.5" />
              {new Date(s.ended_at).toLocaleDateString()}
            </span>
          </div>
        </Link>
      ))}
    </div>
  )
}
```

- [ ] **Step 4: Implement sessions list page**

```typescript
// dashboard/app/sessions/page.tsx
import { SessionList } from '@/components/session-list'

async function fetchSessions() {
  const res = await fetch('http://localhost:3000/api/sessions', { cache: 'no-store' })
  if (!res.ok) return null
  return res.json()
}

export default async function SessionsPage() {
  const data = await fetchSessions()
  if (!data || data.error) {
    return (
      <div className="p-8">
        <div className="rounded-md bg-destructive/10 border border-destructive/20 px-4 py-3 text-sm text-destructive">
          Neo4j unreachable.
        </div>
      </div>
    )
  }
  return (
    <div className="p-8 max-w-4xl">
      <h1 className="text-xl font-semibold mb-6">Sessions</h1>
      <SessionList sessions={data.sessions} />
    </div>
  )
}
```

- [ ] **Step 5: Implement session detail page**

```typescript
// dashboard/app/sessions/[id]/page.tsx
import { Badge } from '@/components/ui/badge'
import { notFound } from 'next/navigation'

async function fetchSession(id: string) {
  const res = await fetch(`http://localhost:3000/api/sessions/${encodeURIComponent(id)}`, {
    cache: 'no-store',
  })
  if (res.status === 404) return null
  if (!res.ok) return null
  return res.json()
}

export default async function SessionDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params
  const data = await fetchSession(id)
  if (!data) notFound()
  const s = data.session

  const commits: string[] = Array.isArray(s.commits) ? s.commits : []
  const files: string[] = Array.isArray(s.files_changed) ? s.files_changed : []

  return (
    <div className="p-8 max-w-3xl space-y-6">
      <div>
        <h1 className="text-xl font-semibold">Session Detail</h1>
        <p className="text-sm text-muted-foreground mt-1 font-mono">{s.session_id}</p>
      </div>

      <div className="flex flex-wrap gap-3 text-sm">
        <Badge variant="outline">{s.branch}</Badge>
        {s.project && <Badge variant="secondary">{s.project}</Badge>}
        <span className="text-muted-foreground">
          {s.started_at ? new Date(s.started_at).toLocaleString() : ''}
          {' → '}
          {s.ended_at ? new Date(s.ended_at).toLocaleString() : ''}
        </span>
      </div>

      {s.summary && (
        <div>
          <h2 className="text-sm font-medium mb-1">Summary</h2>
          <p className="text-sm text-muted-foreground">{s.summary}</p>
        </div>
      )}

      {commits.length > 0 && (
        <div>
          <h2 className="text-sm font-medium mb-2">Commits ({commits.length})</h2>
          <ul className="space-y-1">
            {commits.map(c => (
              <li key={c} className="font-mono text-xs bg-muted px-2 py-1 rounded">{c}</li>
            ))}
          </ul>
        </div>
      )}

      {files.length > 0 && (
        <div>
          <h2 className="text-sm font-medium mb-2">Files Changed ({files.length})</h2>
          <ul className="space-y-1">
            {files.map(f => (
              <li key={f} className="font-mono text-xs bg-muted px-2 py-1 rounded">{f}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}
```

- [ ] **Step 6: Run component test to verify pass**

```bash
cd D:/MEMGRAP/dashboard
npm test -- --testPathPattern=session-list 2>&1 | tail -10
```

- [ ] **Step 7: Commit**

```bash
cd D:/MEMGRAP
git add dashboard/components/session-list.tsx dashboard/app/sessions/
git commit -m "feat(dashboard): add /sessions page with list and detail views"
```
