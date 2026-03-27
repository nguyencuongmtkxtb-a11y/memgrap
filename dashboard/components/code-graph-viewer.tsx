'use client'

import { useRef, useCallback, useMemo, useEffect, useState } from 'react'
import ForceGraph2D, {
  ForceGraphMethods,
  NodeObject,
  LinkObject,
} from 'react-force-graph-2d'

const NODE_COLORS: Record<string, string> = {
  file: '#60a5fa',       // blue
  function: '#34d399',   // green
  class: '#f59e0b',      // amber
  default: '#94a3b8',
}

const EDGE_COLORS: Record<string, string> = {
  CALLS: '#34d399',
  EXTENDS: '#f59e0b',
  IMPORTS_FROM: '#60a5fa',
  CONTAINS: '#334155',
  default: '#334155',
}

interface CodeNode extends NodeObject {
  id: string
  label: string
  type: 'file' | 'function' | 'class'
  language?: string
  project?: string
}

interface CodeEdge extends LinkObject {
  source: string
  target: string
  type: string
  line?: number
}

interface CodeGraphData {
  nodes: CodeNode[]
  edges: CodeEdge[]
}

interface CodeGraphViewerProps {
  data: CodeGraphData
  onNodeClick?: (node: CodeNode) => void
}

export function CodeGraphViewer({ data, onNodeClick }: CodeGraphViewerProps) {
  const graphRef = useRef<ForceGraphMethods>(undefined)
  const containerRef = useRef<HTMLDivElement>(null)
  const [dimensions, setDimensions] = useState({ width: 800, height: 600 })

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
      NODE_COLORS[(node as CodeNode).type] ?? NODE_COLORS.default,
    []
  )

  const nodeLabel = useCallback(
    (node: NodeObject) => {
      const n = node as CodeNode
      return `${n.label} (${n.type})`
    },
    []
  )

  const nodeCanvasObject = useCallback(
    (node: NodeObject, ctx: CanvasRenderingContext2D, globalScale: number) => {
      const n = node as CodeNode
      const x = n.x ?? 0
      const y = n.y ?? 0
      const fontSize = Math.max(10 / globalScale, 2)
      const color = NODE_COLORS[n.type] ?? NODE_COLORS.default
      const size = n.type === 'file' ? 5 : 3.5

      // Draw node
      ctx.beginPath()
      if (n.type === 'file') {
        // Square for files
        ctx.rect(x - size, y - size, size * 2, size * 2)
      } else if (n.type === 'class') {
        // Diamond for classes
        ctx.moveTo(x, y - size)
        ctx.lineTo(x + size, y)
        ctx.lineTo(x, y + size)
        ctx.lineTo(x - size, y)
        ctx.closePath()
      } else {
        // Circle for functions
        ctx.arc(x, y, size, 0, 2 * Math.PI)
      }
      ctx.fillStyle = color
      ctx.fill()

      // Draw label if zoomed enough
      if (globalScale > 1.2) {
        ctx.font = `${fontSize}px monospace`
        ctx.textAlign = 'center'
        ctx.textBaseline = 'top'
        ctx.fillStyle = '#e2e8f0'
        ctx.fillText(n.label, x, y + size + 2)
      }
    },
    []
  )

  const linkColor = useCallback(
    (link: LinkObject) =>
      EDGE_COLORS[(link as CodeEdge).type] ?? EDGE_COLORS.default,
    []
  )

  const linkLabel = useCallback(
    (link: LinkObject) => (link as CodeEdge).type,
    []
  )

  const handleNodeClick = useCallback(
    (node: NodeObject) => onNodeClick?.(node as CodeNode),
    [onNodeClick]
  )

  return (
    <div ref={containerRef} className="w-full h-full">
      <ForceGraph2D
        ref={graphRef}
        graphData={graphData}
        nodeColor={nodeColor}
        nodeLabel={nodeLabel}
        nodeCanvasObject={nodeCanvasObject}
        linkColor={linkColor}
        linkLabel={linkLabel}
        onNodeClick={handleNodeClick}
        backgroundColor="#09090b"
        nodeRelSize={4}
        linkDirectionalArrowLength={4}
        linkDirectionalArrowRelPos={1}
        linkWidth={1.5}
        width={dimensions.width}
        height={dimensions.height}
        cooldownTicks={100}
      />
    </div>
  )
}
