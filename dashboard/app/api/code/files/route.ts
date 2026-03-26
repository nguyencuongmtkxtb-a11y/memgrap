import { NextRequest, NextResponse } from 'next/server'
import { runQuery } from '@/lib/neo4j'

export async function GET(req: NextRequest) {
  const { searchParams } = req.nextUrl
  const search = searchParams.get('search') ?? ''
  const lang = searchParams.get('lang') ?? ''

  try {
    // WHERE before OPTIONAL MATCH (fix I3 from review)
    const rows = await runQuery<{
      f: Record<string, unknown>
      children: Array<Record<string, unknown>>
    }>(
      `MATCH (f:CodeFile)
       WHERE ($search = '' OR toLower(f.path) CONTAINS toLower($search))
         AND ($lang = '' OR f.language = $lang)
       OPTIONAL MATCH (f)-[:CONTAINS|IMPORTS]->(c)
       RETURN f, collect(c) AS children
       ORDER BY f.path
       LIMIT 200`,
      { search, lang }
    )
    const files = rows.map((r) => ({
      ...r.f,
      children: r.children.filter(Boolean),
    }))
    return NextResponse.json({ files })
  } catch (err) {
    const message = err instanceof Error ? err.message : 'Unknown error'
    return NextResponse.json(
      { error: 'Neo4j unreachable', detail: message },
      { status: 503 }
    )
  }
}
