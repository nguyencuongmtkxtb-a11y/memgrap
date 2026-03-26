/**
 * Force-directed graph visualization using react-force-graph-2d.
 * MUST be "use client" — react-force-graph-2d uses browser APIs.
 * MUST be loaded via dynamic() with ssr: false from the parent page.
 */
'use client'

import { useRef, useCallback, useMemo, useEffect, useState } from 'react'
import ForceGraph2D, {
  ForceGraphMethods,
  NodeObject,
  LinkObject,
} from 'react-force-graph-2d'

// Entity type → color map (dark palette)
const ENTITY_COLORS: Record<string, string> = {
  CodePattern: '#60a5fa',
  TechDecision: '#f59e0b',
  ProjectContext: '#34d399',
  Person: '#a78bfa',
  Tool: '#f472b6',
  Concept: '#22d3ee',
  BugReport: '#f87171',
  Requirement: '#fb923c',
  default: '#94a3b8',
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
  const containerRef = useRef<HTMLDivElement>(null)
  const [dimensions, setDimensions] = useState({ width: 800, height: 600 })

  // ResizeObserver for container-responsive sizing (fix S1)
  useEffect(() => {
    const el = containerRef.current
    if (!el) return
    const obs = new ResizeObserver((entries) => {
      const { width, height } = entries[0].contentRect
      setDimensions({ width: Math.floor(width), height: Math.floor(height) })
    })
    obs.observe(el)
    return () => obs.disconnect()
  }, [])

  const graphData = useMemo(
    () => ({
      nodes: data.nodes,
      links: data.edges,
    }),
    [data]
  )

  const nodeColor = useCallback(
    (node: NodeObject) =>
      ENTITY_COLORS[(node as VizNode).entityType ?? ''] ??
      ENTITY_COLORS.default,
    []
  )

  const nodeLabel = useCallback(
    (node: NodeObject) => (node as VizNode).name ?? (node as VizNode).id ?? '',
    []
  )

  const linkLabel = useCallback(
    (link: LinkObject) =>
      (link as VizEdge).fact ?? (link as VizEdge).label ?? '',
    []
  )

  const handleNodeClick = useCallback(
    (node: NodeObject) => onNodeClick(node as VizNode),
    [onNodeClick]
  )

  return (
    <div ref={containerRef} className="w-full h-full">
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
        width={dimensions.width}
        height={dimensions.height}
      />
    </div>
  )
}
