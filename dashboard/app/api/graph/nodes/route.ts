import { NextRequest, NextResponse } from 'next/server'
import neo4j from 'neo4j-driver'
import { runQuery, getGroupId } from '@/lib/neo4j'

export async function GET(req: NextRequest) {
  const gid = getGroupId()
  const { searchParams } = req.nextUrl
  const type = searchParams.get('type') ?? ''
  const search = searchParams.get('search') ?? ''
  const limit = neo4j.int(
    Math.min(parseInt(searchParams.get('limit') ?? '100', 10), 500)
  )

  try {
    // Entity types are labels (Concept, Tool, etc.), not entity_type property
    const rows = await runQuery<{ n: Record<string, unknown> }>(
      `MATCH (n:Entity)
       WHERE n.group_id = $gid
         AND ($type = '' OR $type IN labels(n))
         AND ($search = '' OR toLower(n.name) CONTAINS toLower($search))
       RETURN n
       ORDER BY n.created_at DESC
       LIMIT $limit`,
      { gid, type, search, limit }
    )
    return NextResponse.json({ nodes: rows.map((r) => r.n) })
  } catch (err) {
    const message = err instanceof Error ? err.message : 'Unknown error'
    return NextResponse.json(
      { error: 'Neo4j unreachable', detail: message },
      { status: 503 }
    )
  }
}
