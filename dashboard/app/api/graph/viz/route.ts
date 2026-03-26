import { NextRequest, NextResponse } from 'next/server'
import neo4j from 'neo4j-driver'
import { runQuery } from '@/lib/neo4j'

/** Returns nodes + edges shaped for react-force-graph-2d. */
export async function GET(req: NextRequest) {
  const project = req.nextUrl.searchParams.get('project') ?? ''
  const parsed = parseInt(req.nextUrl.searchParams.get('limit') ?? '200', 10)
  const limit = neo4j.int(Math.max(0, Math.min(isNaN(parsed) ? 200 : parsed, 500)))
  const type = req.nextUrl.searchParams.get('type') ?? ''
  const from = req.nextUrl.searchParams.get('from') ?? ''
  const to = req.nextUrl.searchParams.get('to') ?? ''

  try {
    const [nodeRows, edgeRows] = await Promise.all([
      runQuery<{ n: Record<string, unknown>; nodeLabels: string[] }>(
        `MATCH (n:Entity)
         WHERE ($project = '' OR n.group_id = $project)
           AND ($type = '' OR $type IN labels(n))
           AND ($from = '' OR n.created_at >= $from)
           AND ($to = '' OR n.created_at <= $to)
         RETURN n, labels(n) AS nodeLabels
         LIMIT $limit`,
        { project, limit, type, from, to }
      ),
      runQuery<{ sid: string; tid: string; label: string; fact: string }>(
        `MATCH (a:Entity)-[r:RELATES_TO]->(b:Entity)
         WHERE ($project = '' OR a.group_id = $project)
           AND ($type = '' OR $type IN labels(a))
           AND ($from = '' OR a.created_at >= $from)
           AND ($to = '' OR a.created_at <= $to)
         RETURN elementId(a) AS sid, elementId(b) AS tid,
                type(r) AS label, r.fact AS fact
         LIMIT $limit`,
        { project, limit, type, from, to }
      ),
    ])

    const nodes = nodeRows.map((r) => {
      // Derive entityType from labels, excluding "Entity"
      const entityType =
        (r.nodeLabels as string[]).find((l) => l !== 'Entity') ?? 'Entity'
      return {
        id: r.n._id as string,
        name: r.n.name as string,
        entityType,
        ...r.n,
      }
    })
    const edges = edgeRows.map((r) => ({
      source: r.sid,
      target: r.tid,
      label: r.label,
      fact: r.fact,
    }))

    return NextResponse.json({ nodes, edges })
  } catch (err) {
    const message = err instanceof Error ? err.message : 'Unknown error'
    return NextResponse.json(
      { error: 'Neo4j unreachable', detail: message },
      { status: 503 }
    )
  }
}
