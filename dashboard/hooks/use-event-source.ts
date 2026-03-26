'use client'

import { useEffect, useRef, useCallback } from 'react'

type EventHandler = (data: Record<string, unknown>) => void

export function useEventSource(onEvent: EventHandler) {
  const handlerRef = useRef(onEvent)
  handlerRef.current = onEvent

  const connect = useCallback(() => {
    const es = new EventSource('/api/events')

    es.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data)
        if (data.type !== 'connected') {
          handlerRef.current(data)
        }
      } catch {
        /* malformed event — ignore */
      }
    }

    es.onerror = () => {
      es.close()
      setTimeout(connect, 5000)
    }

    return es
  }, [])

  useEffect(() => {
    const es = connect()
    return () => es.close()
  }, [connect])
}
