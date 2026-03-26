import { NextRequest, NextResponse } from 'next/server'
import { runQuery, getGroupId } from '@/lib/neo4j'

export async function GET(_req: NextRequest) {
  const gid = getGroupId()
  try {
    const [entityRes, edgeRes, sessionRes, codeRes, episodeRes] =
      await Promise.all([
        runQuery<{ count: number }>(
          'MATCH (n:Entity {group_id: $gid}) RETURN count(n) AS count',
          { gid }
        ),
        runQuery<{ count: number }>(
          'MATCH (:Entity {group_id: $gid})-[r:RELATES_TO]->() RETURN count(r) AS count',
          { gid }
        ),
        runQuery<{ count: number }>(
          'MATCH (s:SessionEvent) RETURN count(s) AS count',
          {}
        ),
        runQuery<{ count: number }>(
          'MATCH (f:CodeFile) RETURN count(f) AS count',
          {}
        ),
        runQuery<{ episode: Record<string, unknown> }>(
          `MATCH (e:Episodic)
           WHERE e.group_id = $gid
           RETURN e AS episode
           ORDER BY e.created_at DESC
           LIMIT 10`,
          { gid }
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
        groupId: gid,
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
