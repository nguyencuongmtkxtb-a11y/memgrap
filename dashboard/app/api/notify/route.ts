import { NextRequest, NextResponse } from 'next/server'
import { eventBus } from '@/lib/event-bus'

export async function POST(req: NextRequest) {
  try {
    const body = await req.json()
    const event = body.event as string
    if (!event) {
      return NextResponse.json(
        { error: 'Missing event field' },
        { status: 400 },
      )
    }
    eventBus.publish(event, { project: body.project ?? null })
    return NextResponse.json({
      ok: true,
      subscribers: eventBus.subscriberCount,
    })
  } catch {
    return NextResponse.json({ error: 'Invalid JSON' }, { status: 400 })
  }
}
