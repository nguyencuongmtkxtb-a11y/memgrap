import { NextResponse } from 'next/server'
import { getDriver } from '@/lib/neo4j'

export const dynamic = 'force-dynamic'

export async function GET() {
  // Mask API key: show first 8 + last 4 chars
  const rawKey = process.env.OPENAI_API_KEY ?? ''
  const maskedKey = rawKey.length > 12
    ? rawKey.slice(0, 8) + '...' + rawKey.slice(-4)
    : rawKey ? '****' : '(not set)'

  // Neo4j config
  const neo4jUri = process.env.NEO4J_URI ?? 'bolt://localhost:7687'
  const neo4jUser = process.env.NEO4J_USER ?? 'neo4j'

  // Test Neo4j connection
  let neo4jStatus: 'ok' | 'error' = 'error'
  let neo4jDetail = ''
  const session = getDriver().session()
  try {
    await session.run('RETURN 1')
    neo4jStatus = 'ok'
  } catch (err) {
    neo4jDetail = err instanceof Error ? err.message : 'Unknown error'
  } finally {
    await session.close()
  }

  // System info from env
  const llmModel = process.env.LLM_MODEL ?? 'gpt-4o-mini'
  const embeddingModel = process.env.EMBEDDING_MODEL ?? 'text-embedding-3-small'

  return NextResponse.json({
    openai: { maskedKey, isSet: !!rawKey },
    neo4j: { uri: neo4jUri, user: neo4jUser, status: neo4jStatus, detail: neo4jDetail },
    system: { llmModel, embeddingModel },
  })
}
