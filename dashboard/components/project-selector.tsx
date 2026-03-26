'use client'

import { useState, useEffect } from 'react'
import { useProject } from '@/contexts/project-context'

export function ProjectSelector() {
  const { project, setProject } = useProject()
  const [projects, setProjects] = useState<string[]>([])

  useEffect(() => {
    fetch('/api/projects')
      .then((r) => r.json())
      .then((d) => setProjects(d.projects ?? []))
      .catch(() => {})
  }, [])

  return (
    <div className="px-4 py-3 border-b border-border">
      <label className="text-xs text-muted-foreground uppercase tracking-wide block mb-1">
        Project
      </label>
      <select
        value={project ?? ''}
        onChange={(e) => setProject(e.target.value || null)}
        className="w-full bg-background border border-border rounded-md px-2 py-1 text-sm text-foreground"
      >
        <option value="">All Projects</option>
        {projects.map((p) => (
          <option key={p} value={p}>
            {p}
          </option>
        ))}
      </select>
    </div>
  )
}
