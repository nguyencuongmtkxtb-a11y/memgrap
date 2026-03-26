'use client'

import { useEffect, useState, useCallback } from 'react'
import { SessionList } from '@/components/session-list'
import { ErrorBanner } from '@/components/error-banner'
import { ErrorBoundary } from '@/components/error-boundary'
import { useProject } from '@/contexts/project-context'
import { DateRangePicker } from '@/components/date-range-picker'

interface SessionRow {
  session_id: string
  branch: string
  ended_at: string
  commitCount: number
  filesCount: number
  summary?: string
  project?: string
}

export default function SessionsPage() {
  const { project } = useProject()
  const [sessions, setSessions] = useState<SessionRow[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')

  const fetchSessions = useCallback(async () => {
    setLoading(true)
    setError(false)
    try {
      const params = new URLSearchParams()
      if (project) params.set('project', project)
      if (dateFrom) params.set('from', dateFrom)
      if (dateTo) params.set('to', dateTo)
      const res = await fetch(`/api/sessions?${params}`)
      if (!res.ok) throw new Error()
      const data = await res.json()
      setSessions(data.sessions)
    } catch {
      setError(true)
    } finally {
      setLoading(false)
    }
  }, [project, dateFrom, dateTo])

  useEffect(() => { fetchSessions() }, [fetchSessions])

  return (
    <ErrorBoundary>
      <div className="p-8 max-w-4xl">
        <div className="flex items-center justify-between mb-6">
          <h1 className="text-xl font-semibold">Sessions</h1>
          <DateRangePicker
            from={dateFrom}
            to={dateTo}
            onChange={(f, t) => { setDateFrom(f); setDateTo(t) }}
          />
        </div>
        {error && <ErrorBanner />}
        {loading ? (
          <p className="text-sm text-muted-foreground">Loading...</p>
        ) : (
          <SessionList sessions={sessions} />
        )}
      </div>
    </ErrorBoundary>
  )
}
