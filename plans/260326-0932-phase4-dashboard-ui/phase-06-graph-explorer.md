# Phase 6: Graph Explorer (`/graph`)

**Context:** [Spec](../../docs/superpowers/specs/2026-03-26-dashboard-ui-design.md)

**Goal:** react-force-graph-2d visualization with entity type filters, search, node click detail panel.

**CRITICAL rules:**
- `graph-viewer.tsx` MUST have `'use client'` directive
- `react-force-graph-2d` MUST be imported via `dynamic()` with `{ ssr: false }` — it uses browser APIs that crash on server
- Default node limit: 200

---

### Task 11: Graph Viewer Component

**Files:**
- Create: `dashboard/components/graph-viewer.tsx`
- Create: `dashboard/components/node-detail.tsx`
- Create: `dashboard/app/graph/page.tsx`

- [ ] **Step 1: Write failing test for node-detail component (pure component — no graph)**

```typescript
// dashboard/__tests__/node-detail.test.tsx
import { render, screen } from '@testing-library/react'
import { NodeDetail } from '@/components/node-detail'

const mockNode = {
  id: 'abc',
  name: 'AuthService',
  entityType: 'TechDecision',
  created_at: '2026-03-26T10:00:00Z',
  summary: 'Decided to use JWT tokens',
}

describe('NodeDetail', () => {
  it('renders node name and type', () => {
    render(<NodeDetail node={mockNode} connections={[]} onClose={() => {}} />)
    expect(screen.getByText('AuthService')).toBeInTheDocument()
    expect(screen.getByText('TechDecision')).toBeInTheDocument()
  })

  it('calls onClose when close button clicked', async () => {
    const onClose = jest.fn()
    render(<NodeDetail node={mockNode} connections={[]} onClose={onClose} />)
    await userEvent.click(screen.getByRole('button', { name: /close/i }))
    expect(onClose).toHaveBeenCalled()
  })
})
```

- [ ] **Step 2: Run test to verify fail**

```bash
cd D:/MEMGRAP/dashboard
npm test -- --testPathPattern=node-detail 2>&1 | tail -10
```

- [ ] **Step 3: Implement node-detail.tsx**

```typescript
// dashboard/components/node-detail.tsx
'use client'

import { X } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { ScrollArea } from '@/components/ui/scroll-area'

interface GraphNode {
  id: string
  name?: string
  entityType?: string
  [key: string]: unknown
}

interface Connection {
  rel: Record<string, unknown>
  neighbor: GraphNode
}

interface NodeDetailProps {
  node: GraphNode
  connections: Connection[]
  onClose: () => void
}

const EXCLUDED_KEYS = new Set(['_id', 'id', 'group_id', 'embedding'])

export function NodeDetail({ node, connections, onClose }: NodeDetailProps) {
  const props = Object.entries(node).filter(
    ([k]) => !EXCLUDED_KEYS.has(k) && k !== 'name' && k !== 'entityType'
  )

  return (
    <div className="w-80 flex-none border-l border-border bg-background flex flex-col h-full">
      <div className="flex items-center justify-between px-4 py-3 border-b border-border">
        <div className="min-w-0">
          <p className="font-medium text-sm truncate">{node.name ?? node.id}</p>
          {node.entityType && (
            <Badge variant="secondary" className="text-xs mt-0.5">{node.entityType}</Badge>
          )}
        </div>
        <button
          aria-label="close"
          onClick={onClose}
          className="ml-2 p-1 rounded hover:bg-accent text-muted-foreground"
        >
          <X className="h-4 w-4" />
        </button>
      </div>

      <ScrollArea className="flex-1 px-4 py-3">
        {props.length > 0 && (
          <div className="space-y-2 mb-4">
            <h3 className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Properties</h3>
            {props.map(([k, v]) => (
              <div key={k}>
                <span className="text-xs text-muted-foreground">{k}: </span>
                <span className="text-xs break-all">
                  {typeof v === 'string' ? v : JSON.stringify(v)}
                </span>
              </div>
            ))}
          </div>
        )}

        {connections.length > 0 && (
          <div className="space-y-2">
            <h3 className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
              Connections ({connections.length})
            </h3>
            {connections.map((c, i) => (
              <div key={i} className="border border-border rounded p-2 space-y-1">
                <p className="text-xs font-mono text-muted-foreground">
                  {String(c.rel.type ?? c.rel.label ?? 'RELATES_TO')}
                </p>
                <p className="text-xs truncate">{c.neighbor.name ?? c.neighbor._id}</p>
                {c.rel.fact && (
                  <p className="text-xs text-muted-foreground">{String(c.rel.fact)}</p>
                )}
              </div>
            ))}
          </div>
        )}

        {connections.length === 0 && props.length === 0 && (
          <p className="text-xs text-muted-foreground">No additional details.</p>
        )}
      </ScrollArea>
    </div>
  )
}
```

- [ ] **Step 4: Implement graph-viewer.tsx (force-graph with dynamic import)**

```typescript
// dashboard/components/graph-viewer.tsx
/**
 * Force-directed graph visualization using react-force-graph-2d.
 *
 * MUST be "use client" — react-force-graph-2d uses browser APIs.
 * MUST be loaded via dynamic() with ssr: false from the parent page.
 */
'use client'

import { useRef, useCallback, useMemo } from 'react'
import ForceGraph2D, { ForceGraphMethods, NodeObject, LinkObject } from 'react-force-graph-2d'

// Entity type → color map (dark palette)
const ENTITY_COLORS: Record<string, string> = {
  CodePattern:    '#60a5fa', // blue
  TechDecision:   '#f59e0b', // amber
  ProjectContext: '#34d399', // green
  Person:         '#a78bfa', // violet
  Tool:           '#f472b6', // pink
  Concept:        '#22d3ee', // cyan
  BugReport:      '#f87171', // red
  Requirement:    '#fb923c', // orange
  default:        '#94a3b8', // slate
}

interface VizNode extends NodeObject {
  id: string
  name?: string
  entityType?: string
  [key: string]: unknown
}

interface VizEdge extends LinkObject {
  source: string
  target: string
  label?: string
  fact?: string
}

interface GraphData {
  nodes: VizNode[]
  edges: VizEdge[]
}

interface GraphViewerProps {
  data: GraphData
  onNodeClick: (node: VizNode) => void
}

export function GraphViewer({ data, onNodeClick }: GraphViewerProps) {
  const graphRef = useRef<ForceGraphMethods>(undefined)

  const graphData = useMemo(() => ({
    nodes: data.nodes,
    links: data.edges,
  }), [data])

  const nodeColor = useCallback(
    (node: NodeObject) =>
      ENTITY_COLORS[(node as VizNode).entityType ?? ''] ?? ENTITY_COLORS.default,
    []
  )

  const nodeLabel = useCallback(
    (node: NodeObject) => (node as VizNode).name ?? (node as VizNode).id ?? '',
    []
  )

  const linkLabel = useCallback(
    (link: LinkObject) => (link as VizEdge).fact ?? (link as VizEdge).label ?? '',
    []
  )

  const handleNodeClick = useCallback(
    (node: NodeObject) => onNodeClick(node as VizNode),
    [onNodeClick]
  )

  return (
    <ForceGraph2D
      ref={graphRef}
      graphData={graphData}
      nodeColor={nodeColor}
      nodeLabel={nodeLabel}
      linkLabel={linkLabel}
      onNodeClick={handleNodeClick}
      backgroundColor="#09090b"
      nodeRelSize={5}
      linkColor={() => '#334155'}
      linkDirectionalArrowLength={3}
      linkDirectionalArrowRelPos={1}
      width={undefined}
      height={undefined}
    />
  )
}
```

- [ ] **Step 5: Implement graph page**

```typescript
// dashboard/app/graph/page.tsx
'use client'

import dynamic from 'next/dynamic'
import { useState, useEffect, useCallback } from 'react'
import { NodeDetail } from '@/components/node-detail'
import { Input } from '@/components/ui/input'
import { Checkbox } from '@/components/ui/checkbox'
import { Badge } from '@/components/ui/badge'
import { useDebounce } from '@/lib/use-debounce'

// MUST use dynamic import with ssr:false — react-force-graph-2d uses browser APIs
const GraphViewer = dynamic(
  () => import('@/components/graph-viewer').then(m => m.GraphViewer),
  { ssr: false, loading: () => <div className="flex-1 flex items-center justify-center text-sm text-muted-foreground">Loading graph...</div> }
)

const ENTITY_TYPES = [
  'CodePattern', 'TechDecision', 'ProjectContext', 'Person',
  'Tool', 'Concept', 'BugReport', 'Requirement',
]

interface VizNode {
  id: string
  name?: string
  entityType?: string
  [key: string]: unknown
}

interface Connection {
  rel: Record<string, unknown>
  neighbor: VizNode
}

export default function GraphPage() {
  const [graphData, setGraphData] = useState<{ nodes: VizNode[]; edges: unknown[] }>({ nodes: [], edges: [] })
  const [selectedTypes, setSelectedTypes] = useState<Set<string>>(new Set(ENTITY_TYPES))
  const [search, setSearch] = useState('')
  const [selectedNode, setSelectedNode] = useState<VizNode | null>(null)
  const [connections, setConnections] = useState<Connection[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)

  const debouncedSearch = useDebounce(search, 400)

  const fetchGraph = useCallback(async () => {
    setLoading(true)
    setError(false)
    try {
      const params = new URLSearchParams({ limit: '200' })
      const res = await fetch(`/api/graph/viz?${params}`)
      if (!res.ok) throw new Error()
      const data = await res.json()
      // Client-side filter by selected types and search
      const filtered = data.nodes.filter((n: VizNode) => {
        const typeOk = selectedTypes.has(n.entityType ?? '')
        const searchOk = !debouncedSearch ||
          (n.name ?? '').toLowerCase().includes(debouncedSearch.toLowerCase())
        return typeOk && searchOk
      })
      const filteredIds = new Set(filtered.map((n: VizNode) => n.id))
      const filteredEdges = (data.edges as Array<{ source: string; target: string }>)
        .filter(e => filteredIds.has(e.source) && filteredIds.has(e.target))
      setGraphData({ nodes: filtered, edges: filteredEdges })
    } catch {
      setError(true)
    } finally {
      setLoading(false)
    }
  }, [selectedTypes, debouncedSearch])

  useEffect(() => { fetchGraph() }, [fetchGraph])

  const handleNodeClick = useCallback(async (node: VizNode) => {
    setSelectedNode(node)
    try {
      const res = await fetch(`/api/graph/nodes/${encodeURIComponent(node.id)}`)
      if (res.ok) {
        const data = await res.json()
        setConnections(data.connections ?? [])
      }
    } catch { /* ignore */ }
  }, [])

  const toggleType = (type: string) => {
    setSelectedTypes(prev => {
      const next = new Set(prev)
      next.has(type) ? next.delete(type) : next.add(type)
      return next
    })
  }

  return (
    <div className="flex h-screen overflow-hidden">
      {/* Left panel */}
      <div className="w-56 flex-none border-r border-border p-4 overflow-y-auto">
        <Input
          placeholder="Search entities..."
          value={search}
          onChange={e => setSearch(e.target.value)}
          className="mb-4 h-8 text-xs"
        />
        <h3 className="text-xs font-medium text-muted-foreground uppercase tracking-wide mb-2">
          Entity Types
        </h3>
        <div className="space-y-2">
          {ENTITY_TYPES.map(type => (
            <label key={type} className="flex items-center gap-2 text-xs cursor-pointer">
              <Checkbox
                checked={selectedTypes.has(type)}
                onCheckedChange={() => toggleType(type)}
                className="h-3.5 w-3.5"
              />
              <span className="truncate">{type}</span>
            </label>
          ))}
        </div>
        <div className="mt-4 pt-4 border-t border-border">
          <Badge variant="outline" className="text-xs">
            {graphData.nodes.length} nodes · {graphData.edges.length} edges
          </Badge>
        </div>
      </div>

      {/* Graph canvas */}
      <div className="flex-1 relative bg-zinc-950">
        {error && (
          <div className="absolute top-4 left-1/2 -translate-x-1/2 z-10 rounded-md bg-destructive/10 border border-destructive/20 px-4 py-2 text-xs text-destructive">
            Neo4j unreachable.
          </div>
        )}
        {!loading && !error && (
          <GraphViewer
            data={graphData as Parameters<typeof GraphViewer>[0]['data']}
            onNodeClick={handleNodeClick}
          />
        )}
        {loading && (
          <div className="flex items-center justify-center h-full text-sm text-muted-foreground">
            Loading graph...
          </div>
        )}
      </div>

      {/* Right panel — node detail */}
      {selectedNode && (
        <NodeDetail
          node={selectedNode}
          connections={connections}
          onClose={() => { setSelectedNode(null); setConnections([]) }}
        />
      )}
    </div>
  )
}
```

- [ ] **Step 6: Run node-detail test to verify pass**

```bash
cd D:/MEMGRAP/dashboard
npm test -- --testPathPattern=node-detail 2>&1 | tail -10
```

- [ ] **Step 7: Build check (catches SSR/TS errors)**

```bash
cd D:/MEMGRAP/dashboard
npm run build 2>&1 | tail -20
```

Expected: `✓ Compiled successfully` with no errors.

- [ ] **Step 8: Commit**

```bash
cd D:/MEMGRAP
git add dashboard/components/graph-viewer.tsx dashboard/components/node-detail.tsx dashboard/app/graph/
git commit -m "feat(dashboard): add /graph explorer with force-graph viz and node detail panel"
```
