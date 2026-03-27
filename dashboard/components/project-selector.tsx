'use client'

import { useState, useEffect, useCallback } from 'react'
import { Trash2 } from 'lucide-react'
import { useProject } from '@/contexts/project-context'

export function ProjectSelector() {
  const { project, setProject } = useProject()
  const [projects, setProjects] = useState<string[]>([])
  const [deleting, setDeleting] = useState<string | null>(null)

  const loadProjects = useCallback(() => {
    fetch('/api/projects')
      .then((r) => r.json())
      .then((d) => setProjects(d.projects ?? []))
      .catch(() => {})
  }, [])

  useEffect(() => { loadProjects() }, [loadProjects])

  async function handleDelete() {
    if (!project) return
    const name = project
    setDeleting(name)
    try {
      const res = await fetch('/api/projects', {
        method: 'DELETE',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ project: name }),
      })
      if (res.ok) {
        setProjects((prev) => prev.filter((p) => p !== name))
        setProject(null)
        loadProjects()
      }
    } catch { /* ignore */ }
    setDeleting(null)
  }

  return (
    <div className="px-4 py-3 border-b border-border">
      <label className="text-xs text-muted-foreground uppercase tracking-wide block mb-1">
        Project
      </label>
      <div className="flex items-center gap-1">
        <select
          value={project ?? ''}
          onChange={(e) => setProject(e.target.value || null)}
          className="flex-1 min-w-0 bg-background border border-border rounded-md px-2 py-1 text-sm text-foreground"
        >
          <option value="">All Projects</option>
          {projects.map((p) => (
            <option key={p} value={p}>{p}</option>
          ))}
        </select>
        {project && (
          <button
            onClick={() => {
              if (deleting) return
              if (!confirm(`Delete ALL data for project "${project}"?\n\nThis removes entities, memories, code index, sessions — everything.\n\nThis cannot be undone.`)) return
              handleDelete()
            }}
            disabled={!!deleting}
            title={`Delete project "${project}"`}
            className="p-1 rounded-md text-muted-foreground hover:text-destructive hover:bg-destructive/10 transition-colors disabled:opacity-50"
          >
            <Trash2 className="h-3.5 w-3.5" />
          </button>
        )}
      </div>
      {deleting && (
        <p className="text-xs text-destructive mt-1">Deleting {deleting}...</p>
      )}
    </div>
  )
}
