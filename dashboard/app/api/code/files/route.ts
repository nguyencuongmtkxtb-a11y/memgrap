import { NextRequest, NextResponse } from 'next/server'
import { runQuery } from '@/lib/neo4j'

/** Recursively convert leftover {low,high} Neo4j integers to plain numbers. */
function sanitize(v: unknown): unknown {
  if (v == null) return v
  if (Array.isArray(v)) return v.map(sanitize)
  if (typeof v === 'object') {
    const obj = v as Record<string, unknown>
    if ('low' in obj && 'high' in obj && Object.keys(obj).length === 2) {
      return (obj.high as number) === 0 ? obj.low : Number(obj.low)
    }
    const out: Record<string, unknown> = {}
    for (const [k, val] of Object.entries(obj)) out[k] = sanitize(val)
    return out
  }
  return v
}

export async function GET(req: NextRequest) {
  const { searchParams } = req.nextUrl
  const search = searchParams.get('search') ?? ''
  const lang = searchParams.get('lang') ?? ''

  try {
    const rows = await runQuery<{
      f: Record<string, unknown>
      children: Array<Record<string, unknown>>
    }>(
      `MATCH (f:CodeFile)
       WHERE ($search = '' OR toLower(f.path) CONTAINS toLower($search))
         AND ($lang = '' OR f.language = $lang)
       OPTIONAL MATCH (f)-[:CONTAINS|IMPORTS]->(c)
       WITH f, collect({ props: properties(c), labels: labels(c), eid: elementId(c) }) AS rawChildren
       RETURN f, [ch IN rawChildren WHERE ch.props IS NOT NULL |
         apoc.map.merge(ch.props, { type: ch.labels[0], _id: ch.eid })] AS children
       ORDER BY f.path
       LIMIT 200`,
      { search, lang }
    )
    const files = rows.map((r) => ({
      ...r.f,
      children: (r.children.filter(Boolean) as unknown[]).map(sanitize),
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
