import { NextResponse } from 'next/server'
import { getDriver } from '@/lib/neo4j'

export const dynamic = 'force-dynamic'

export async function GET() {
  const session = getDriver().session()
  try {
    await session.run('RETURN 1')
    return NextResponse.json({ status: 'ok' })
  } catch (err) {
    const message = err instanceof Error ? err.message : 'Unknown error'
    return NextResponse.json({ status: 'error', detail: message }, { status: 503 })
  } finally {
    await session.close()
  }
}
