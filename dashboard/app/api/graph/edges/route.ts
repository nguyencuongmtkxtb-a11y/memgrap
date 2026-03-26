import { NextRequest, NextResponse } from 'next/server'
import neo4j from 'neo4j-driver'
import { runQuery, getGroupId } from '@/lib/neo4j'

export async function GET(req: NextRequest) {
  const gid = getGroupId()
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
       WHERE a.group_id = $gid
       RETURN elementId(a) AS sourceId, elementId(b) AS targetId,
              type(r) AS label, r.fact AS fact
       LIMIT $limit`,
      { gid, limit }
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
