// Server Component — calls route handler directly (fix C2)
import { GET } from '@/app/api/sessions/[id]/route'
import { NextRequest } from 'next/server'
import { Badge } from '@/components/ui/badge'
import { notFound } from 'next/navigation'

export default async function SessionDetailPage({
  params,
}: {
  params: Promise<{ id: string }>
}) {
  const { id } = await params
  const req = new NextRequest(
    `http://localhost/api/sessions/${encodeURIComponent(id)}`
  )
  const res = await GET(req, { params: Promise.resolve({ id }) })
  if (res.status === 404) notFound()
  const data = await res.json()
  if (!data.session) notFound()
  const s = data.session

  const commits: string[] = Array.isArray(s.commits) ? s.commits : []
  const files: string[] = Array.isArray(s.files_changed) ? s.files_changed : []

  return (
    <div className="p-8 max-w-3xl space-y-6">
      <div>
        <h1 className="text-xl font-semibold">Session Detail</h1>
        <p className="text-sm text-muted-foreground mt-1 font-mono">
          {s.session_id}
        </p>
      </div>

      <div className="flex flex-wrap gap-3 text-sm">
        <Badge variant="outline">{s.branch}</Badge>
        {s.project && <Badge variant="secondary">{s.project}</Badge>}
        <span className="text-muted-foreground">
          {s.started_at ? new Date(s.started_at).toLocaleString() : ''}
          {' → '}
          {s.ended_at ? new Date(s.ended_at).toLocaleString() : ''}
        </span>
      </div>

      {s.summary && (
        <div>
          <h2 className="text-sm font-medium mb-1">Summary</h2>
          <p className="text-sm text-muted-foreground">{s.summary}</p>
        </div>
      )}

      {commits.length > 0 && (
        <div>
          <h2 className="text-sm font-medium mb-2">
            Commits ({commits.length})
          </h2>
          <ul className="space-y-1">
            {commits.map((c) => (
              <li key={c} className="font-mono text-xs bg-muted px-2 py-1 rounded">
                {c}
              </li>
            ))}
          </ul>
        </div>
      )}

      {files.length > 0 && (
        <div>
          <h2 className="text-sm font-medium mb-2">
            Files Changed ({files.length})
          </h2>
          <ul className="space-y-1">
            {files.map((f) => (
              <li key={f} className="font-mono text-xs bg-muted px-2 py-1 rounded">
                {f}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}
