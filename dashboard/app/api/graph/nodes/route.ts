import { NextRequest, NextResponse } from 'next/server'
import neo4j from 'neo4j-driver'
import { runQuery } from '@/lib/neo4j'

export async function GET(req: NextRequest) {
  const { searchParams } = req.nextUrl
  const project = searchParams.get('project') ?? ''
  const type = searchParams.get('type') ?? ''
  const search = searchParams.get('search') ?? ''
  const from = searchParams.get('from') ?? ''
  const to = searchParams.get('to') ?? ''
  const parsed = parseInt(searchParams.get('limit') ?? '100', 10)
  const limit = neo4j.int(Math.max(0, Math.min(isNaN(parsed) ? 100 : parsed, 500)))

  try {
    // Entity types are labels (Concept, Tool, etc.), not entity_type property
    const rows = await runQuery<{ n: Record<string, unknown> }>(
      `MATCH (n:Entity)
       WHERE ($project = '' OR n.group_id = $project)
         AND ($type = '' OR $type IN labels(n))
         AND ($search = '' OR toLower(n.name) CONTAINS toLower($search))
         AND ($from = '' OR n.created_at >= $from)
         AND ($to = '' OR n.created_at <= $to)
       RETURN n
       ORDER BY n.created_at DESC
       LIMIT $limit`,
      { project, type, search, limit, from, to }
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
