import { NextRequest, NextResponse } from 'next/server'
import { runQuery } from '@/lib/neo4j'

export async function GET(
  _req: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params
  try {
    const rows = await runQuery<{ s: Record<string, unknown> }>(
      'MATCH (s:SessionEvent {session_id: $id}) RETURN s',
      { id }
    )
    if (rows.length === 0) {
      return NextResponse.json({ error: 'Not found' }, { status: 404 })
    }
    return NextResponse.json({ session: rows[0].s })
  } catch (err) {
    const message = err instanceof Error ? err.message : 'Unknown error'
    return NextResponse.json(
      { error: 'Neo4j unreachable', detail: message },
      { status: 503 }
    )
  }
}
