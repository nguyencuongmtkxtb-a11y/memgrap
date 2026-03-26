'use client'

import { useState } from 'react'
import { useProject } from '@/contexts/project-context'

export default function ExportPage() {
  const { project } = useProject()
  const [importing, setImporting] = useState(false)
  const [importResult, setImportResult] = useState<string | null>(null)

  const handleExportJson = () => {
    const params = new URLSearchParams()
    if (project) params.set('project', project)
    window.open(`/api/export/json?${params}`, '_blank')
  }

  const handleImportJson = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    setImporting(true)
    setImportResult(null)
    try {
      const text = await file.text()
      const data = JSON.parse(text)
      const res = await fetch('/api/import/json', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      })
      const result = await res.json()
      if (res.ok) {
        const s = result.imported
        setImportResult(
          `Imported: ${s.entities} entities, ${s.facts} facts, ${s.sessions} sessions, ${s.codeFiles} code files`
        )
      } else {
        setImportResult(`Error: ${result.error}`)
      }
    } catch (err) {
      setImportResult(`Error: ${err instanceof Error ? err.message : 'Unknown'}`)
    } finally {
      setImporting(false)
      e.target.value = ''
    }
  }

  return (
    <div className="p-8 max-w-2xl space-y-8">
      <h1 className="text-xl font-semibold">Export &amp; Import</h1>

      <section className="space-y-3">
        <h2 className="text-sm font-medium">Neo4j Backup (CLI)</h2>
        <p className="text-sm text-muted-foreground">
          Full database backup requires CLI access. Run from project root:
        </p>
        <pre className="bg-muted rounded-md p-3 text-xs overflow-x-auto">
          {`# Backup\n./scripts/backup.sh\n\n# Restore\n./scripts/restore.sh path/to/backup.dump`}
        </pre>
      </section>

      <section className="space-y-3">
        <h2 className="text-sm font-medium">Export JSON</h2>
        <p className="text-sm text-muted-foreground">
          Export {project ? `project "${project}"` : 'all projects'} as JSON file.
        </p>
        <button
          onClick={handleExportJson}
          className="px-4 py-2 text-sm rounded-md bg-primary text-primary-foreground hover:bg-primary/90"
        >
          Download JSON
        </button>
      </section>

      <section className="space-y-3">
        <h2 className="text-sm font-medium">Import JSON</h2>
        <p className="text-sm text-muted-foreground">
          Import a previously exported JSON file. Additive — won&apos;t delete existing data.
        </p>
        <label className="inline-block px-4 py-2 text-sm rounded-md border border-border cursor-pointer hover:bg-accent">
          {importing ? 'Importing...' : 'Choose file'}
          <input
            type="file"
            accept=".json"
            onChange={handleImportJson}
            className="hidden"
            disabled={importing}
          />
        </label>
        {importResult && (
          <p
            className={`text-sm ${importResult.startsWith('Error') ? 'text-destructive' : 'text-green-500'}`}
          >
            {importResult}
          </p>
        )}
      </section>
    </div>
  )
}
