'use client'

import dynamic from 'next/dynamic'
import { useState, useEffect, useCallback } from 'react'
import { NodeDetail } from '@/components/node-detail'
import { Input } from '@/components/ui/input'
import { Checkbox } from '@/components/ui/checkbox'
import { Badge } from '@/components/ui/badge'
import { useDebounce } from '@/lib/use-debounce'
import { ErrorBoundary } from '@/components/error-boundary'
import { useProject } from '@/contexts/project-context'

// MUST use dynamic import with ssr:false — react-force-graph-2d uses browser APIs
const GraphViewer = dynamic(
  () => import('@/components/graph-viewer').then((m) => m.GraphViewer),
  {
    ssr: false,
    loading: () => (
      <div className="flex-1 flex items-center justify-center text-sm text-muted-foreground">
        Loading graph...
      </div>
    ),
  }
)

const ENTITY_TYPES = [
  'CodePattern',
  'TechDecision',
  'ProjectContext',
  'Person',
  'Tool',
  'Concept',
  'BugReport',
  'Requirement',
]

interface VizNode {
  id: string
  name?: string
  entityType?: string
  [key: string]: unknown
}

interface VizEdge {
  source: string
  target: string
  label?: string
  fact?: string
}

interface Connection {
  rel: Record<string, unknown>
  neighbor: VizNode
}

export default function GraphPage() {
  const { project } = useProject()
  const [graphData, setGraphData] = useState<{
    nodes: VizNode[]
    edges: VizEdge[]
  }>({ nodes: [], edges: [] })
  const [selectedTypes, setSelectedTypes] = useState<Set<string>>(
    new Set(ENTITY_TYPES)
  )
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
      if (project) params.set('project', project)
      const res = await fetch(`/api/graph/viz?${params}`)
      if (!res.ok) throw new Error()
      const data = await res.json()
      // Client-side filter by selected types and search
      const filtered = data.nodes.filter((n: VizNode) => {
        const typeOk = selectedTypes.has(n.entityType ?? '')
        const searchOk =
          !debouncedSearch ||
          (n.name ?? '').toLowerCase().includes(debouncedSearch.toLowerCase())
        return typeOk && searchOk
      })
      const filteredIds = new Set(filtered.map((n: VizNode) => n.id))
      const filteredEdges = (data.edges as VizEdge[]).filter(
        (e) => filteredIds.has(e.source) && filteredIds.has(e.target)
      )
      setGraphData({ nodes: filtered, edges: filteredEdges })
    } catch {
      setError(true)
    } finally {
      setLoading(false)
    }
  }, [selectedTypes, debouncedSearch, project])

  useEffect(() => {
    fetchGraph()
  }, [fetchGraph])

  const handleNodeClick = useCallback(async (node: VizNode) => {
    setSelectedNode(node)
    try {
      const res = await fetch(
        `/api/graph/nodes/${encodeURIComponent(node.id)}`
      )
      if (res.ok) {
        const data = await res.json()
        setConnections(data.connections ?? [])
      }
    } catch {
      /* ignore */
    }
  }, [])

  const toggleType = (type: string) => {
    setSelectedTypes((prev) => {
      const next = new Set(prev)
      next.has(type) ? next.delete(type) : next.add(type)
      return next
    })
  }

  return (
    <ErrorBoundary>
    <div className="flex h-screen overflow-hidden">
      {/* Left panel */}
      <div className="w-56 flex-none border-r border-border p-4 overflow-y-auto">
        <Input
          placeholder="Search entities..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="mb-4 h-8 text-xs"
        />
        <h3 className="text-xs font-medium text-muted-foreground uppercase tracking-wide mb-2">
          Entity Types
        </h3>
        <div className="space-y-2">
          {ENTITY_TYPES.map((type) => (
            <label
              key={type}
              className="flex items-center gap-2 text-xs cursor-pointer"
            >
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
            data={graphData as { nodes: VizNode[]; edges: VizEdge[] }}
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
          onClose={() => {
            setSelectedNode(null)
            setConnections([])
          }}
        />
      )}
    </div>
    </ErrorBoundary>
  )
}
