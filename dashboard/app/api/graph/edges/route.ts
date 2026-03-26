import { NextRequest, NextResponse } from 'next/server'
import neo4j from 'neo4j-driver'
import { runQuery } from '@/lib/neo4j'

export async function GET(req: NextRequest) {
  const project = req.nextUrl.searchParams.get('project') ?? ''
  const parsed = parseInt(req.nextUrl.searchParams.get('limit') ?? '200', 10)
  const limit = neo4j.int(Math.max(0, Math.min(isNaN(parsed) ? 200 : parsed, 500)))
  try {
    const rows = await runQuery<{
      sourceId: string
      targetId: string
      label: string
      fact: string
    }>(
      `MATCH (a:Entity)-[r:RELATES_TO]->(b:Entity)
       WHERE ($project = '' OR a.group_id = $project)
       RETURN elementId(a) AS sourceId, elementId(b) AS targetId,
              type(r) AS label, r.fact AS fact
       LIMIT $limit`,
      { project, limit }
    )
    return NextResponse.json({ edges: rows })
  } catch (err) {
    const message = err instanceof Error ? err.message : 'Unknown error'
    return NextResponse.json(
      { error: 'Neo4j unreachable', detail: message },
      { status: 503 }
    )
  }
}
