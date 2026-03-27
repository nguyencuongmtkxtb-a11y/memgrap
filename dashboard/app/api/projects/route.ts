import { NextRequest, NextResponse } from 'next/server'
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

export async function DELETE(req: NextRequest) {
  try {
    const { project } = await req.json()
    if (!project || typeof project !== 'string') {
      return NextResponse.json({ error: 'project name is required' }, { status: 400 })
    }

    const stats: Record<string, number> = {}

    // 1. Entities (Graphiti nodes)
    const e1 = await runQuery<{ cnt: number }>(
      'MATCH (n:Entity) WHERE n.group_id = $gid DETACH DELETE n RETURN count(n) AS cnt',
      { gid: project }
    )
    stats.entities = e1[0]?.cnt ?? 0

    // 2. Episodes
    const e2 = await runQuery<{ cnt: number }>(
      'MATCH (ep:EpisodicNode) WHERE ep.group_id = $gid DETACH DELETE ep RETURN count(ep) AS cnt',
      { gid: project }
    )
    stats.episodes = e2[0]?.cnt ?? 0

    // 3. Orphaned facts
    const e3 = await runQuery<{ cnt: number }>(
      'MATCH ()-[e:RELATES_TO]->() WHERE e.group_id = $gid DELETE e RETURN count(e) AS cnt',
      { gid: project }
    )
    stats.facts = e3[0]?.cnt ?? 0

    // 4. Code nodes
    for (const label of ['CodeFile', 'CodeFunction', 'CodeClass', 'CodeImport']) {
      const r = await runQuery<{ cnt: number }>(
        `MATCH (n:${label}) WHERE n.project = $gid DETACH DELETE n RETURN count(n) AS cnt`,
        { gid: project }
      )
      stats[label] = r[0]?.cnt ?? 0
    }

    // 5. Sessions
    const e5 = await runQuery<{ cnt: number }>(
      'MATCH (s:SessionEvent) WHERE s.project = $gid DETACH DELETE s RETURN count(s) AS cnt',
      { gid: project }
    )
    stats.sessions = e5[0]?.cnt ?? 0

    // 6. Project marker
    const e6 = await runQuery<{ cnt: number }>(
      'MATCH (p:Project) WHERE p.name = $gid DETACH DELETE p RETURN count(p) AS cnt',
      { gid: project }
    )
    stats.projectNode = e6[0]?.cnt ?? 0

    const total = Object.values(stats).reduce((a, b) => a + b, 0)
    return NextResponse.json({ deleted: true, project, stats, total })
  } catch (err) {
    const message = err instanceof Error ? err.message : 'Unknown error'
    return NextResponse.json({ error: 'Delete failed', detail: message }, { status: 500 })
  }
}
