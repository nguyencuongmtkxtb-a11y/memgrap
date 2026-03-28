import { NextRequest, NextResponse } from 'next/server'

export const dynamic = 'force-dynamic'

export async function POST(req: NextRequest) {
  const body = await req.json().catch(() => ({}))
  const apiKey = (body as { key?: string }).key || process.env.OPENAI_API_KEY || ''

  if (!apiKey) {
    return NextResponse.json({ valid: false, error: 'No API key provided' })
  }

  try {
    const res = await fetch('https://api.openai.com/v1/models', {
      headers: { Authorization: `Bearer ${apiKey}` },
    })
    if (!res.ok) {
      const data = await res.json().catch(() => ({}))
      return NextResponse.json({
        valid: false,
        error: (data as { error?: { message?: string } }).error?.message ?? `HTTP ${res.status}`,
      })
    }
    const data = await res.json()
    const modelCount = (data as { data?: unknown[] }).data?.length ?? 0
    return NextResponse.json({ valid: true, modelCount })
  } catch (err) {
    return NextResponse.json({
      valid: false,
      error: err instanceof Error ? err.message : 'Network error',
    })
  }
}
