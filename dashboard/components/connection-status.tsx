'use client'

import { useState, useEffect } from 'react'

export function ConnectionStatus() {
  const [status, setStatus] = useState<'ok' | 'error' | 'loading'>('loading')
  const [detail, setDetail] = useState('')

  useEffect(() => {
    let mounted = true
    const check = async () => {
      try {
        const res = await fetch('/api/health')
        const data = await res.json()
        if (!mounted) return
        setStatus(data.status === 'ok' ? 'ok' : 'error')
        setDetail(data.detail ?? '')
      } catch {
        if (!mounted) return
        setStatus('error')
        setDetail('Dashboard cannot reach health endpoint')
      }
    }
    check()
    const interval = setInterval(check, 30_000)
    return () => {
      mounted = false
      clearInterval(interval)
    }
  }, [])

  const color =
    status === 'ok'
      ? 'bg-green-500'
      : status === 'error'
        ? 'bg-red-500'
        : 'bg-yellow-500'

  return (
    <div
      className="flex items-center gap-2 px-4 py-2 text-xs text-muted-foreground"
      title={detail || `Neo4j: ${status}`}
    >
      <span className={`h-2 w-2 rounded-full ${color}`} />
      <span>
        {status === 'ok'
          ? 'Connected'
          : status === 'error'
            ? 'Disconnected'
            : 'Checking...'}
      </span>
    </div>
  )
}
