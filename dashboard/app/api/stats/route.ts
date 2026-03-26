import { NextRequest, NextResponse } from 'next/server'
import { runQuery } from '@/lib/neo4j'

export async function GET(req: NextRequest) {
  const project = req.nextUrl.searchParams.get('project') ?? ''
  try {
    const [entityRes, edgeRes, sessionRes, codeRes, episodeRes] =
      await Promise.all([
        runQuery<{ count: number }>(
          `MATCH (n:Entity)
           WHERE ($project = '' OR n.group_id = $project)
           RETURN count(n) AS count`,
          { project }
        ),
        runQuery<{ count: number }>(
          `MATCH (a:Entity)-[r:RELATES_TO]->()
           WHERE ($project = '' OR a.group_id = $project)
           RETURN count(r) AS count`,
          { project }
        ),
        runQuery<{ count: number }>(
          `MATCH (s:SessionEvent)
           WHERE ($project = '' OR s.project = $project)
           RETURN count(s) AS count`,
          { project }
        ),
        runQuery<{ count: number }>(
          `MATCH (f:CodeFile)
           WHERE ($project = '' OR f.project = $project)
           RETURN count(f) AS count`,
          { project }
        ),
        runQuery<{ episode: Record<string, unknown> }>(
          `MATCH (e:Episodic)
           WHERE ($project = '' OR e.group_id = $project)
           RETURN e AS episode
           ORDER BY e.created_at DESC
           LIMIT 10`,
          { project }
        ),
      ])

    return NextResponse.json({
      entityCount: entityRes[0]?.count ?? 0,
      edgeCount: edgeRes[0]?.count ?? 0,
      sessionCount: sessionRes[0]?.count ?? 0,
      codeFileCount: codeRes[0]?.count ?? 0,
      recentEpisodes: episodeRes.map((r) => r.episode),
      health: {
        neo4j: 'ok',
        project: project || 'all',
        llmModel: process.env.LLM_MODEL ?? 'gpt-4o-mini',
      },
    })
  } catch (err) {
    const message = err instanceof Error ? err.message : 'Unknown error'
    return NextResponse.json(
      { error: 'Neo4j unreachable', detail: message },
      { status: 503 }
    )
  }
}
