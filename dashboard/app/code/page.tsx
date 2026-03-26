'use client'

import { useEffect, useState, useCallback } from 'react'
import { CodeTree } from '@/components/code-tree'
import { Input } from '@/components/ui/input'
import { useDebounce } from '@/lib/use-debounce'
import { ErrorBoundary } from '@/components/error-boundary'

export default function CodePage() {
  const [files, setFiles] = useState<unknown[]>([])
  const [search, setSearch] = useState('')
  const [lang, setLang] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)

  const debouncedSearch = useDebounce(search, 300)

  const fetchFiles = useCallback(async () => {
    setLoading(true)
    setError(false)
    try {
      const params = new URLSearchParams()
      if (debouncedSearch) params.set('search', debouncedSearch)
      if (lang) params.set('lang', lang)
      // Client component — relative URL works fine in browser
      const res = await fetch(`/api/code/files?${params}`)
      if (!res.ok) throw new Error()
      const data = await res.json()
      setFiles(data.files)
    } catch {
      setError(true)
    } finally {
      setLoading(false)
    }
  }, [debouncedSearch, lang])

  useEffect(() => {
    fetchFiles()
  }, [fetchFiles])

  return (
    <ErrorBoundary>
    <div className="p-8 max-w-4xl">
      <h1 className="text-xl font-semibold mb-6">Code Index</h1>
      {error && (
        <div className="rounded-md bg-destructive/10 border border-destructive/20 px-4 py-3 text-sm text-destructive mb-4">
          Neo4j unreachable.
        </div>
      )}
      <div className="flex gap-3 mb-4">
        <Input
          placeholder="Search files..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="max-w-xs"
        />
        <Input
          placeholder="Language (python, typescript...)"
          value={lang}
          onChange={(e) => setLang(e.target.value)}
          className="max-w-xs"
        />
      </div>
      {loading ? (
        <p className="text-sm text-muted-foreground">Loading...</p>
      ) : (
        <CodeTree
          files={files as Parameters<typeof CodeTree>[0]['files']}
        />
      )}
    </div>
    </ErrorBoundary>
  )
}
