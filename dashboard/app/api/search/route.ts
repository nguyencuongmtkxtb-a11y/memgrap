import { NextRequest, NextResponse } from 'next/server'
import { runQuery } from '@/lib/neo4j'

export const dynamic = 'force-dynamic'

interface SearchResult {
  type: string
  id: string
  name: string
  summary: string
  score: number
}

export async function GET(req: NextRequest) {
  const { searchParams } = req.nextUrl
  const q = searchParams.get('q')?.trim()
  const project = searchParams.get('project') ?? ''
  const from = searchParams.get('from') ?? ''
  const to = searchParams.get('to') ?? ''

  if (!q) {
    return NextResponse.json({ results: [] })
  }

  const escaped = q.replace(/[+\-&|!(){}[\]^"~*?:\\/]/g, '\\$&')

  try {
    const results: SearchResult[] = []

    // Search entities via built-in entity_name fulltext index
    const entities = await runQuery<{
      name: string
      summary: string
      id: string
      score: number
    }>(
      `CALL db.index.fulltext.queryNodes('entity_name', $q) YIELD node, score
       WHERE ($project = '' OR node.group_id = $project)
         AND ($from = '' OR node.created_at >= $from)
         AND ($to = '' OR node.created_at <= $to)
       RETURN node.name AS name, node.summary AS summary,
              elementId(node) AS id, score
       LIMIT 20`,
      { q: escaped + '*', project, from, to }
    )
    for (const e of entities) {
      results.push({
        type: 'entity',
        id: e.id,
        name: e.name,
        summary: e.summary ?? '',
        score: e.score,
      })
    }

    // Search sessions
    try {
      const sessions = await runQuery<{
        name: string
        summary: string
        id: string
        score: number
      }>(
        `CALL db.index.fulltext.queryNodes('session_search', $q) YIELD node, score
         WHERE ($project = '' OR node.project = $project)
           AND ($from = '' OR node.started_at >= $from)
           AND ($to = '' OR node.started_at <= $to)
         RETURN node.branch AS name, node.summary AS summary,
                elementId(node) AS id, score
         LIMIT 10`,
        { q: escaped + '*', project, from, to }
      )
      for (const s of sessions) {
        results.push({
          type: 'session',
          id: s.id,
          name: s.name ?? '',
          summary: s.summary ?? '',
          score: s.score,
        })
      }
    } catch {
      /* index may not exist yet */
    }

    // Search code files
    try {
      const code = await runQuery<{
        name: string
        id: string
        score: number
      }>(
        `CALL db.index.fulltext.queryNodes('code_file_search', $q) YIELD node, score
         WHERE ($project = '' OR node.project = $project)
         RETURN node.path AS name, elementId(node) AS id, score
         LIMIT 10`,
        { q: escaped + '*', project }
      )
      for (const c of code) {
        results.push({
          type: 'code',
          id: c.id,
          name: c.name,
          summary: '',
          score: c.score,
        })
      }
    } catch {
      /* index may not exist yet */
    }

    // Search code functions
    try {
      const funcs = await runQuery<{
        name: string
        id: string
        fp: string
        score: number
      }>(
        `CALL db.index.fulltext.queryNodes('code_function_search', $q) YIELD node, score
         WHERE ($project = '' OR node.project = $project)
         RETURN node.name AS name, elementId(node) AS id,
                node.file_path AS fp, score
         LIMIT 10`,
        { q: escaped + '*', project }
      )
      for (const f of funcs) {
        results.push({
          type: 'function',
          id: f.id,
          name: f.name,
          summary: f.fp ?? '',
          score: f.score,
        })
      }
    } catch {
      /* index may not exist yet */
    }

    results.sort((a, b) => b.score - a.score)
    return NextResponse.json({ results: results.slice(0, 30) })
  } catch (err) {
    const message = err instanceof Error ? err.message : 'Unknown error'
    return NextResponse.json(
      { error: 'Search failed', detail: message },
      { status: 503 }
    )
  }
}
