// Server Component — calls route handler directly (fix C2)
import { GET } from '@/app/api/sessions/route'
import { NextRequest } from 'next/server'
import { SessionList } from '@/components/session-list'
import { ErrorBanner } from '@/components/error-banner'

// Force dynamic rendering — Neo4j is only available at runtime, not build time
export const dynamic = 'force-dynamic'

export default async function SessionsPage() {
  const req = new NextRequest('http://localhost/api/sessions')
  const res = await GET(req)
  const data = await res.json()

  if (res.status !== 200 || data.error) {
    return (
      <div className="p-8">
        <ErrorBanner />
      </div>
    )
  }

  return (
    <div className="p-8 max-w-4xl">
      <h1 className="text-xl font-semibold mb-6">Sessions</h1>
      <SessionList sessions={data.sessions} />
    </div>
  )
}
