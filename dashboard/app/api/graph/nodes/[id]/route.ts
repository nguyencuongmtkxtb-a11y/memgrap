import { NextRequest, NextResponse } from 'next/server'
import { runQuery } from '@/lib/neo4j'

export async function GET(
  _req: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params
  try {
    const rows = await runQuery<{
      n: Record<string, unknown>
      r: Record<string, unknown>
      m: Record<string, unknown>
    }>(
      `MATCH (n:Entity)-[r]-(m)
       WHERE elementId(n) = $id
       RETURN n, r, m
       LIMIT 50`,
      { id }
    )
    if (rows.length === 0) {
      // Node may have no edges
      const solo = await runQuery<{ n: Record<string, unknown> }>(
        'MATCH (n:Entity) WHERE elementId(n) = $id RETURN n',
        { id }
      )
      if (solo.length === 0)
        return NextResponse.json({ error: 'Not found' }, { status: 404 })
      return NextResponse.json({ node: solo[0].n, connections: [] })
    }
    const node = rows[0].n
    const connections = rows.map((r) => ({ rel: r.r, neighbor: r.m }))
    return NextResponse.json({ node, connections })
  } catch (err) {
    const message = err instanceof Error ? err.message : 'Unknown error'
    return NextResponse.json(
      { error: 'Neo4j unreachable', detail: message },
      { status: 503 }
    )
  }
}
