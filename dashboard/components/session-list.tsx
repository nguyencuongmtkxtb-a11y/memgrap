'use client'

import Link from 'next/link'
import { Badge } from '@/components/ui/badge'
import { GitBranch, GitCommit, FileCode2, Clock } from 'lucide-react'

interface SessionRow {
  session_id: string
  branch: string
  ended_at: string
  commitCount: number
  filesCount: number
  summary?: string
  project?: string
}

export function SessionList({ sessions }: { sessions: SessionRow[] }) {
  if (sessions.length === 0) {
    return (
      <p className="text-sm text-muted-foreground py-4">
        No sessions recorded yet.
      </p>
    )
  }

  return (
    <div className="divide-y divide-border rounded-lg border border-border overflow-hidden">
      {sessions.map((s) => (
        <Link
          key={s.session_id}
          href={`/sessions/${s.session_id}`}
          className="flex items-center gap-4 px-4 py-3 hover:bg-accent transition-colors"
        >
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-0.5">
              <GitBranch className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
              <span className="text-sm font-medium truncate">{s.branch}</span>
              {s.project && (
                <Badge variant="outline" className="text-xs">
                  {s.project}
                </Badge>
              )}
            </div>
            {s.summary && (
              <p className="text-xs text-muted-foreground truncate">
                {s.summary}
              </p>
            )}
          </div>
          <div className="flex items-center gap-4 text-xs text-muted-foreground shrink-0">
            <span className="flex items-center gap-1">
              <GitCommit className="h-3.5 w-3.5" />
              {s.commitCount} commits
            </span>
            <span className="flex items-center gap-1">
              <FileCode2 className="h-3.5 w-3.5" />
              {s.filesCount} files
            </span>
            <span className="flex items-center gap-1">
              <Clock className="h-3.5 w-3.5" />
              {new Date(s.ended_at).toLocaleDateString()}
            </span>
          </div>
        </Link>
      ))}
    </div>
  )
}
