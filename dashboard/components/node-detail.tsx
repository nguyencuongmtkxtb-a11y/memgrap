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

const EXCLUDED_KEYS = new Set(['_id', 'id', 'group_id', 'embedding', 'name_embedding'])

export function NodeDetail({ node, connections, onClose }: NodeDetailProps) {
  const props = Object.entries(node).filter(
    ([k]) => !EXCLUDED_KEYS.has(k) && k !== 'name' && k !== 'entityType'
  )

  return (
    <div className="w-80 flex-none border-l border-border bg-background flex flex-col h-full">
      <div className="flex items-center justify-between px-4 py-3 border-b border-border">
        <div className="min-w-0">
          <p className="font-medium text-sm truncate">
            {node.name ?? node.id}
          </p>
          {node.entityType && (
            <Badge variant="secondary" className="text-xs mt-0.5">
              {node.entityType}
            </Badge>
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
            <h3 className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
              Properties
            </h3>
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
              <div
                key={i}
                className="border border-border rounded p-2 space-y-1"
              >
                <p className="text-xs font-mono text-muted-foreground">
                  {String(c.rel.type ?? c.rel.label ?? 'RELATES_TO')}
                </p>
                <p className="text-xs truncate">
                  {String(c.neighbor.name ?? c.neighbor._id ?? '')}
                </p>
                {c.rel.fact ? (
                  <p className="text-xs text-muted-foreground">
                    {String(c.rel.fact)}
                  </p>
                ) : null}
              </div>
            ))}
          </div>
        )}

        {connections.length === 0 && props.length === 0 && (
          <p className="text-xs text-muted-foreground">
            No additional details.
          </p>
        )}
      </ScrollArea>
    </div>
  )
}
