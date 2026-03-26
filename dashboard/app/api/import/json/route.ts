import { NextRequest, NextResponse } from 'next/server'
import { getDriver } from '@/lib/neo4j'

export const dynamic = 'force-dynamic'

export async function POST(req: NextRequest) {
  let data: Record<string, unknown[]>

  try {
    data = await req.json()
  } catch {
    return NextResponse.json({ error: 'Invalid JSON' }, { status: 400 })
  }

  if (!data.version) {
    return NextResponse.json(
      { error: 'Missing version field — not a Memgrap export' },
      { status: 400 }
    )
  }

  const session = getDriver().session()
  const stats = { entities: 0, facts: 0, sessions: 0, codeFiles: 0 }
  const ALLOWED_LABELS = new Set(['CodeFunction', 'CodeClass', 'CodeImport'])

  try {
    // Import sessions
    for (const s of (data.sessions as Record<string, unknown>[]) ?? []) {
      await session.run(
        `MERGE (s:SessionEvent {session_id: $sid})
         SET s += $props`,
        { sid: s.session_id, props: s }
      )
      stats.sessions++
    }

    // Import code files
    for (const f of (data.codeFiles as Record<string, unknown>[]) ?? []) {
      const children = (f.children ?? []) as Record<string, unknown>[]
      const fileProps = { ...f }
      delete fileProps.children

      await session.run(
        `MERGE (f:CodeFile {path: $path}) SET f += $props`,
        { path: f.path, props: fileProps }
      )
      stats.codeFiles++

      for (const child of children) {
        if (!child || !child.name) continue
        // Whitelist labels to prevent Cypher injection
        const label = ALLOWED_LABELS.has(child.type as string)
          ? (child.type as string)
          : 'CodeFunction'
        await session.run(
          `MATCH (f:CodeFile {path: $fp})
           MERGE (c:\`${label}\` {name: $name, file_path: $fp})
           SET c += $props
           MERGE (f)-[:CONTAINS]->(c)`,
          { fp: f.path, name: child.name, props: child }
        )
      }
    }

    return NextResponse.json({ ok: true, imported: stats })
  } catch (err) {
    const message = err instanceof Error ? err.message : 'Unknown error'
    return NextResponse.json({ error: 'Import failed', detail: message }, { status: 500 })
  } finally {
    await session.close()
  }
}
