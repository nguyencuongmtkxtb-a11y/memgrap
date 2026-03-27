'use client'

import dynamic from 'next/dynamic'
import { useState, useEffect, useCallback } from 'react'
import { Input } from '@/components/ui/input'
import { Checkbox } from '@/components/ui/checkbox'
import { Badge } from '@/components/ui/badge'
import { useDebounce } from '@/lib/use-debounce'
import { ErrorBoundary } from '@/components/error-boundary'
import { useProject } from '@/contexts/project-context'
import { useEventSource } from '@/hooks/use-event-source'

const CodeGraphViewer = dynamic(
  () => import('@/components/code-graph-viewer').then((m) => m.CodeGraphViewer),
  {
    ssr: false,
    loading: () => (
      <div className="flex-1 flex items-center justify-center text-sm text-muted-foreground">
        Loading code graph...
      </div>
    ),
  }
)

const REL_TYPES = ['CALLS', 'EXTENDS', 'IMPORTS_FROM'] as const
const NODE_TYPES = ['file', 'function', 'class'] as const

interface CodeNode {
  id: string
  label: string
  type: 'file' | 'function' | 'class'
  language?: string
  project?: string
}

interface CodeEdge {
  source: string
  target: string
  type: string
  line?: number
}

export default function CodeGraphPage() {
  const { project } = useProject()
  const [graphData, setGraphData] = useState<{ nodes: CodeNode[]; edges: CodeEdge[] }>({
    nodes: [],
    edges: [],
  })
  const [search, setSearch] = useState('')
  const [selectedRels, setSelectedRels] = useState<Set<string>>(new Set(REL_TYPES))
  const [selectedNodes, setSelectedNodes] = useState<Set<string>>(new Set(NODE_TYPES))
  const [selectedNode, setSelectedNode] = useState<CodeNode | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)

  const debouncedSearch = useDebounce(search, 400)

  const fetchGraph = useCallback(async () => {
    setLoading(true)
    setError(false)
    try {
      const params = new URLSearchParams({ limit: '500' })
      if (project) params.set('project', project)
      if (debouncedSearch) params.set('search', debouncedSearch)
      const res = await fetch(`/api/code/graph?${params}`)
      if (!res.ok) throw new Error()
      const data = await res.json()

      // Client-side filter by selected node/edge types
      const filtered = (data.nodes as CodeNode[]).filter(
        (n) => selectedNodes.has(n.type)
      )
      const filteredIds = new Set(filtered.map((n) => n.id))
      const filteredEdges = (data.edges as CodeEdge[]).filter(
        (e) =>
          selectedRels.has(e.type) &&
          filteredIds.has(e.source) &&
          filteredIds.has(e.target)
      )
      setGraphData({ nodes: filtered, edges: filteredEdges })
    } catch {
      setError(true)
    } finally {
      setLoading(false)
    }
  }, [debouncedSearch, project, selectedRels, selectedNodes])

  useEffect(() => {
    fetchGraph()
  }, [fetchGraph])

  useEventSource(() => { fetchGraph() })

  const toggleRel = (type: string) => {
    setSelectedRels((prev) => {
      const next = new Set(prev)
      next.has(type) ? next.delete(type) : next.add(type)
      return next
    })
  }

  const toggleNode = (type: string) => {
    setSelectedNodes((prev) => {
      const next = new Set(prev)
      next.has(type) ? next.delete(type) : next.add(type)
      return next
    })
  }

  const relColors: Record<string, string> = {
    CALLS: 'text-green-400',
    EXTENDS: 'text-amber-400',
    IMPORTS_FROM: 'text-blue-400',
  }

  const nodeColors: Record<string, string> = {
    file: 'text-blue-400',
    function: 'text-green-400',
    class: 'text-amber-400',
  }

  return (
    <ErrorBoundary>
      <div className="flex h-screen overflow-hidden">
        {/* Left panel */}
        <div className="w-56 flex-none border-r border-border p-4 overflow-y-auto">
          <Input
            placeholder="Search code..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="mb-4 h-8 text-xs"
          />

          <h3 className="text-xs font-medium text-muted-foreground uppercase tracking-wide mb-2">
            Node Types
          </h3>
          <div className="space-y-2 mb-4">
            {NODE_TYPES.map((type) => (
              <label
                key={type}
                className="flex items-center gap-2 text-xs cursor-pointer"
              >
                <Checkbox
                  checked={selectedNodes.has(type)}
                  onCheckedChange={() => toggleNode(type)}
                  className="h-3.5 w-3.5"
                />
                <span className={nodeColors[type]}>{type}</span>
              </label>
            ))}
          </div>

          <h3 className="text-xs font-medium text-muted-foreground uppercase tracking-wide mb-2">
            Relationships
          </h3>
          <div className="space-y-2">
            {REL_TYPES.map((type) => (
              <label
                key={type}
                className="flex items-center gap-2 text-xs cursor-pointer"
              >
                <Checkbox
                  checked={selectedRels.has(type)}
                  onCheckedChange={() => toggleRel(type)}
                  className="h-3.5 w-3.5"
                />
                <span className={relColors[type]}>{type}</span>
              </label>
            ))}
          </div>

          <div className="mt-4 pt-4 border-t border-border">
            <Badge variant="outline" className="text-xs">
              {graphData.nodes.length} nodes · {graphData.edges.length} edges
            </Badge>
          </div>

          {/* Legend */}
          <div className="mt-4 pt-4 border-t border-border">
            <h3 className="text-xs font-medium text-muted-foreground uppercase tracking-wide mb-2">
              Legend
            </h3>
            <div className="space-y-1 text-xs">
              <div className="flex items-center gap-2">
                <span className="w-3 h-3 bg-blue-400 inline-block" />
                <span>File</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="w-3 h-3 bg-green-400 rounded-full inline-block" />
                <span>Function</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="w-3 h-3 bg-amber-400 rotate-45 inline-block" />
                <span>Class</span>
              </div>
            </div>
          </div>
        </div>

        {/* Graph canvas */}
        <div className="flex-1 relative bg-zinc-950">
          {error && (
            <div className="absolute top-4 left-1/2 -translate-x-1/2 z-10 rounded-md bg-destructive/10 border border-destructive/20 px-4 py-2 text-xs text-destructive">
              Neo4j unreachable — run the indexer first.
            </div>
          )}
          {!loading && !error && (
            <CodeGraphViewer
              data={graphData}
              onNodeClick={(node) => setSelectedNode(node)}
            />
          )}
          {loading && (
            <div className="flex items-center justify-center h-full text-sm text-muted-foreground">
              Loading code graph...
            </div>
          )}
        </div>

        {/* Right panel — selected node detail */}
        {selectedNode && (
          <div className="w-72 flex-none border-l border-border p-4 overflow-y-auto">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-semibold truncate">{selectedNode.label}</h3>
              <button
                onClick={() => setSelectedNode(null)}
                className="text-xs text-muted-foreground hover:text-foreground"
              >
                Close
              </button>
            </div>
            <div className="space-y-2 text-xs">
              <div>
                <span className="text-muted-foreground">Type: </span>
                <Badge variant="outline" className="text-xs">
                  {selectedNode.type}
                </Badge>
              </div>
              {selectedNode.language && (
                <div>
                  <span className="text-muted-foreground">Language: </span>
                  {selectedNode.language}
                </div>
              )}
              {selectedNode.project && (
                <div>
                  <span className="text-muted-foreground">Project: </span>
                  {selectedNode.project}
                </div>
              )}

              {/* Show related edges */}
              <div className="mt-4 pt-4 border-t border-border">
                <h4 className="text-xs font-medium text-muted-foreground uppercase tracking-wide mb-2">
                  Connections
                </h4>
                {graphData.edges
                  .filter(
                    (e) =>
                      e.source === selectedNode.id || e.target === selectedNode.id
                  )
                  .slice(0, 20)
                  .map((e, i) => {
                    const isSource = e.source === selectedNode.id
                    const otherId = isSource ? e.target : e.source
                    const other = graphData.nodes.find((n) => n.id === otherId)
                    return (
                      <div key={i} className="text-xs py-1">
                        <span className={relColors[e.type] ?? 'text-muted-foreground'}>
                          {e.type}
                        </span>
                        <span className="text-muted-foreground">
                          {isSource ? ' -> ' : ' <- '}
                        </span>
                        <span className="font-mono">{other?.label ?? otherId}</span>
                      </div>
                    )
                  })}
              </div>
            </div>
          </div>
        )}
      </div>
    </ErrorBoundary>
  )
}
