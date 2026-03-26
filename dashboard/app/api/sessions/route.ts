import { NextRequest, NextResponse } from 'next/server'
import { runQuery } from '@/lib/neo4j'

export async function GET(_req: NextRequest) {
  try {
    const rows = await runQuery<{ s: Record<string, unknown> }>(
      `MATCH (s:SessionEvent)
       RETURN s
       ORDER BY s.ended_at DESC
       LIMIT 100`,
      {}
    )
    const sessions = rows.map((r) => ({
      ...r.s,
      commitCount: Array.isArray(r.s.commits)
        ? (r.s.commits as unknown[]).length
        : 0,
      filesCount: Array.isArray(r.s.files_changed)
        ? (r.s.files_changed as unknown[]).length
        : 0,
    }))
    return NextResponse.json({ sessions })
  } catch (err) {
    const message = err instanceof Error ? err.message : 'Unknown error'
    return NextResponse.json(
      { error: 'Neo4j unreachable', detail: message },
      { status: 503 }
    )
  }
}
