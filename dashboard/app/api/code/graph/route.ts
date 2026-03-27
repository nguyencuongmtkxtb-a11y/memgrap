import { NextRequest, NextResponse } from 'next/server'
import neo4j from 'neo4j-driver'
import { runQuery } from '@/lib/neo4j'

interface GraphNode {
  id: string
  label: string
  type: 'file' | 'function' | 'class'
  language?: string
  project?: string
}

interface GraphEdge {
  source: string
  target: string
  type: 'CALLS' | 'EXTENDS' | 'IMPORTS_FROM' | 'CONTAINS'
  line?: number
}

export async function GET(req: NextRequest) {
  const { searchParams } = req.nextUrl
  const project = searchParams.get('project') ?? ''
  const relType = searchParams.get('rel') ?? ''  // filter by relationship type
  const search = searchParams.get('search') ?? ''
  const limit = neo4j.int(Math.min(parseInt(searchParams.get('limit') ?? '500') || 500, 2000))

  try {
    // Fetch nodes: files, functions, classes that have relationships
    const nodeRows = await runQuery<{
      id: string; label: string; type: string;
      language: string | null; project: string | null
    }>(
      `// Files with relationships
       MATCH (f:CodeFile)
       WHERE ($project = '' OR f.project = $project)
         AND ($search = '' OR toLower(f.path) CONTAINS toLower($search))
       OPTIONAL MATCH (f)-[r]->()
       WHERE type(r) IN ['CALLS', 'EXTENDS', 'IMPORTS_FROM', 'CONTAINS']
       WITH f, count(r) AS rels
       WHERE rels > 0
       RETURN elementId(f) AS id,
              CASE WHEN size(split(f.path, '/')) > 1
                THEN split(f.path, '/')[-1]
                ELSE f.path END AS label,
              'file' AS type, f.language AS language, f.project AS project
       LIMIT $limit
       UNION
       // Functions and classes
       MATCH (n)
       WHERE (n:CodeFunction OR n:CodeClass)
         AND ($project = '' OR n.project = $project)
         AND ($search = '' OR toLower(n.name) CONTAINS toLower($search))
       OPTIONAL MATCH (n)-[r]->()
       WHERE type(r) IN ['CALLS', 'EXTENDS']
       OPTIONAL MATCH ()-[r2]->(n)
       WHERE type(r2) IN ['CALLS', 'EXTENDS']
       WITH n, count(r) + count(r2) AS rels,
            CASE WHEN n:CodeFunction THEN 'function' ELSE 'class' END AS ntype
       WHERE rels > 0
       RETURN elementId(n) AS id, n.name AS label,
              ntype AS type, null AS language, n.project AS project
       LIMIT $limit`,
      { project, search, limit }
    )

    // Fetch edges
    const relFilter = relType
      ? `AND type(r) = $relType`
      : `AND type(r) IN ['CALLS', 'EXTENDS', 'IMPORTS_FROM']`

    const edgeRows = await runQuery<{
      source: string; target: string; type: string; line: number | null
    }>(
      `MATCH (a)-[r]->(b)
       WHERE type(r) IN ['CALLS', 'EXTENDS', 'IMPORTS_FROM']
         ${relFilter}
         AND ($project = '' OR (
           CASE WHEN a:CodeFile THEN a.project ELSE a.project END = $project
         ))
       RETURN elementId(a) AS source, elementId(b) AS target,
              type(r) AS type, r.line AS line
       LIMIT $limit`,
      { project, relType, limit }
    )

    const nodes: GraphNode[] = nodeRows.map(r => ({
      id: r.id,
      label: r.label,
      type: r.type as GraphNode['type'],
      language: r.language ?? undefined,
      project: r.project ?? undefined,
    }))

    const edges: GraphEdge[] = edgeRows.map(r => ({
      source: r.source,
      target: r.target,
      type: r.type as GraphEdge['type'],
      line: r.line ?? undefined,
    }))

    // Filter edges to only include nodes we have
    const nodeIds = new Set(nodes.map(n => n.id))
    const filteredEdges = edges.filter(e => nodeIds.has(e.source) && nodeIds.has(e.target))

    return NextResponse.json({ nodes, edges: filteredEdges })
  } catch (err) {
    const message = err instanceof Error ? err.message : 'Unknown error'
    return NextResponse.json(
      { error: 'Neo4j unreachable', detail: message },
      { status: 503 }
    )
  }
}
