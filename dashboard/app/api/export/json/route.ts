import { NextRequest, NextResponse } from 'next/server'
import { runQuery } from '@/lib/neo4j'

export const dynamic = 'force-dynamic'

type Obj = Record<string, unknown>

export async function GET(req: NextRequest) {
  const project = req.nextUrl.searchParams.get('project') ?? ''

  try {
    const [entities, facts, sessions, codeFiles] = await Promise.all([
      runQuery(
        `MATCH (n:Entity) WHERE ($project = '' OR n.group_id = $project) RETURN properties(n) AS props`,
        { project }
      ),
      runQuery(
        `MATCH (a:Entity)-[r:RELATES_TO]->(b:Entity)
         WHERE ($project = '' OR a.group_id = $project)
         RETURN properties(r) AS props, a.name AS source, b.name AS target`,
        { project }
      ),
      runQuery(
        `MATCH (s:SessionEvent) WHERE ($project = '' OR s.project = $project) RETURN properties(s) AS props`,
        { project }
      ),
      runQuery(
        `MATCH (f:CodeFile) WHERE ($project = '' OR f.project = $project)
         OPTIONAL MATCH (f)-[:CONTAINS|IMPORTS]->(c)
         RETURN properties(f) AS file, collect(properties(c)) AS children`,
        { project }
      ),
    ])

    const exportData = {
      version: 1,
      exported_at: new Date().toISOString(),
      project: project || 'all',
      entities: entities.map((r) => r.props),
      facts: facts.map((r) => ({
        ...(r.props as Obj),
        source: r.source,
        target: r.target,
      })),
      sessions: sessions.map((r) => r.props),
      codeFiles: codeFiles.map((r) => ({
        ...(r.file as Obj),
        children: r.children,
      })),
    }

    const json = JSON.stringify(exportData, null, 2)
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19)
    const filename = `memgrap-export-${project || 'all'}-${timestamp}.json`

    return new Response(json, {
      headers: {
        'Content-Type': 'application/json',
        'Content-Disposition': `attachment; filename="${filename}"`,
      },
    })
  } catch (err) {
    const message = err instanceof Error ? err.message : 'Unknown error'
    return NextResponse.json({ error: 'Export failed', detail: message }, { status: 503 })
  }
}
