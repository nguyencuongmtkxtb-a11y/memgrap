import { eventBus } from '@/lib/event-bus'

export const dynamic = 'force-dynamic'

export async function GET() {
  const encoder = new TextEncoder()
  let unsubscribe: (() => void) | null = null
  let interval: ReturnType<typeof setInterval> | null = null

  const stream = new ReadableStream({
    start(controller) {
      controller.enqueue(encoder.encode('data: {"type":"connected"}\n\n'))

      unsubscribe = eventBus.subscribe((event, data) => {
        const payload = JSON.stringify({ type: event, ...data })
        try {
          controller.enqueue(encoder.encode(`data: ${payload}\n\n`))
        } catch {
          // Stream closed — cleanup happens in cancel()
        }
      })

      interval = setInterval(() => {
        try {
          controller.enqueue(encoder.encode(': keepalive\n\n'))
        } catch {
          // Stream closed — cleanup happens in cancel()
        }
      }, 30_000)
    },
    cancel() {
      if (interval) clearInterval(interval)
      if (unsubscribe) unsubscribe()
    },
  })

  return new Response(stream, {
    headers: {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache',
      Connection: 'keep-alive',
    },
  })
}
