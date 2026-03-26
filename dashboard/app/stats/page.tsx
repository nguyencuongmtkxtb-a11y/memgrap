// Server Component — calls route handler directly (fix C2: no fetch localhost)
import { GET } from '@/app/api/stats/route'
import { NextRequest } from 'next/server'
import { StatCards } from '@/components/stat-cards'
import { ErrorBanner } from '@/components/error-banner'

// Force dynamic rendering — Neo4j is only available at runtime, not build time
export const dynamic = 'force-dynamic'

export default async function StatsPage() {
  const req = new NextRequest('http://localhost/api/stats')
  const res = await GET(req)
  const stats = await res.json()

  if (res.status !== 200 || stats.error) {
    return (
      <div className="p-8">
        <ErrorBanner />
      </div>
    )
  }

  return (
    <div className="p-8 max-w-5xl">
      <h1 className="text-xl font-semibold mb-6">Stats</h1>
      <StatCards stats={stats} />
    </div>
  )
}
