import { NextRequest, NextResponse } from 'next/server'
import { getDriver } from '@/lib/neo4j'

export const dynamic = 'force-dynamic'

const ALLOWED_CHILD_LABELS = new Set(['CodeFunction', 'CodeClass', 'CodeImport'])

// Whitelist of allowed properties per node type to prevent property stuffing
const ENTITY_FIELDS = new Set(['name', 'entity_type', 'summary', 'group_id', 'created_at', 'uuid'])
const FACT_FIELDS = new Set(['fact', 'fact_id', 'uuid', 'created_at', 'expired_at', 'valid_at', 'invalid_at'])
const SESSION_FIELDS = new Set([
  'session_id', 'project', 'branch', 'started_at', 'ended_at',
  'commits', 'files_changed', 'summary', 'transcript_path',
])
const CODE_FILE_FIELDS = new Set(['path', 'language', 'project', 'indexed_at', 'size'])
const CODE_CHILD_FIELDS = new Set(['name', 'file_path', 'type', 'line_start', 'line_end', 'source'])

function pickFields(obj: Record<string, unknown>, allowed: Set<string>): Record<string, unknown> {
  const result: Record<string, unknown> = {}
  for (const key of allowed) {
    if (key in obj && obj[key] !== undefined) result[key] = obj[key]
  }
  return result
}

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

  try {
    // Import entities
    for (const e of (data.entities as Record<string, unknown>[]) ?? []) {
      const props = pickFields(e, ENTITY_FIELDS)
      if (!props.name) continue
      await session.run(
        `MERGE (n:Entity {name: $name})
         SET n += $props`,
        { name: props.name, props }
      )
      stats.entities++
    }

    // Import facts (relationships)
    for (const f of (data.facts as Record<string, unknown>[]) ?? []) {
      const source = f.source as string
      const target = f.target as string
      if (!source || !target) continue
      const props = pickFields(f, FACT_FIELDS)
      await session.run(
        `MATCH (a:Entity {name: $source}), (b:Entity {name: $target})
         MERGE (a)-[r:RELATES_TO]->(b)
         SET r += $props`,
        { source, target, props }
      )
      stats.facts++
    }

    // Import sessions
    for (const s of (data.sessions as Record<string, unknown>[]) ?? []) {
      const props = pickFields(s, SESSION_FIELDS)
      if (!props.session_id) continue
      await session.run(
        `MERGE (s:SessionEvent {session_id: $sid})
         SET s += $props`,
        { sid: props.session_id, props }
      )
      stats.sessions++
    }

    // Import code files
    for (const f of (data.codeFiles as Record<string, unknown>[]) ?? []) {
      const children = (f.children ?? []) as Record<string, unknown>[]
      const fileProps = pickFields(f, CODE_FILE_FIELDS)
      if (!fileProps.path) continue

      await session.run(
        `MERGE (f:CodeFile {path: $path}) SET f += $props`,
        { path: fileProps.path, props: fileProps }
      )
      stats.codeFiles++

      for (const child of children) {
        if (!child || !child.name) continue
        const label = ALLOWED_CHILD_LABELS.has(child.type as string)
          ? (child.type as string)
          : 'CodeFunction'
        const childProps = pickFields(child, CODE_CHILD_FIELDS)
        await session.run(
          `MATCH (f:CodeFile {path: $fp})
           MERGE (c:\`${label}\` {name: $name, file_path: $fp})
           SET c += $props
           MERGE (f)-[:CONTAINS]->(c)`,
          { fp: fileProps.path, name: child.name, props: childProps }
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
