import { NextResponse } from 'next/server'
import { runQuery } from '@/lib/neo4j'

export const dynamic = 'force-dynamic'

export async function GET() {
  try {
    const rows = await runQuery<{ project: string }>(
      `CALL {
        MATCH (n) WHERE n.project IS NOT NULL RETURN DISTINCT n.project AS project
        UNION
        MATCH (n) WHERE n.group_id IS NOT NULL RETURN DISTINCT n.group_id AS project
      }
      RETURN project ORDER BY project`,
      {}
    )
    const projects = rows.map((r) => r.project).filter(Boolean)
    return NextResponse.json({ projects })
  } catch (err) {
    const message = err instanceof Error ? err.message : 'Unknown error'
    return NextResponse.json({ error: 'Neo4j unreachable', detail: message }, { status: 503 })
  }
}
