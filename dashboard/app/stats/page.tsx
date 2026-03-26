'use client'

import { useEffect, useState, useCallback } from 'react'
import { StatCards } from '@/components/stat-cards'
import { ErrorBanner } from '@/components/error-banner'
import { ErrorBoundary } from '@/components/error-boundary'
import { useProject } from '@/contexts/project-context'

interface StatsData {
  entityCount: number
  edgeCount: number
  sessionCount: number
  codeFileCount: number
  recentEpisodes: Array<{
    _id: string
    content?: string
    created_at?: string
  }>
  health: { neo4j: string; groupId: string; llmModel: string }
}

export default function StatsPage() {
  const { project } = useProject()
  const [stats, setStats] = useState<StatsData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)

  const fetchStats = useCallback(async () => {
    setLoading(true)
    setError(false)
    try {
      const params = new URLSearchParams()
      if (project) params.set('project', project)
      const res = await fetch(`/api/stats?${params}`)
      if (!res.ok) throw new Error()
      setStats(await res.json())
    } catch {
      setError(true)
    } finally {
      setLoading(false)
    }
  }, [project])

  useEffect(() => { fetchStats() }, [fetchStats])

  return (
    <ErrorBoundary>
      <div className="p-8 max-w-5xl">
        <h1 className="text-xl font-semibold mb-6">Stats</h1>
        {error && <ErrorBanner />}
        {loading ? (
          <p className="text-sm text-muted-foreground">Loading...</p>
        ) : stats ? (
          <StatCards stats={stats} />
        ) : null}
      </div>
    </ErrorBoundary>
  )
}
