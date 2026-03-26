'use client'

import { useState, useEffect, useRef } from 'react'
import { useRouter } from 'next/navigation'
import { Search } from 'lucide-react'
import { useProject } from '@/contexts/project-context'
import { useDebounce } from '@/lib/use-debounce'

interface SearchResult {
  type: string
  id: string
  name: string
  summary: string
  score: number
}

export function SearchBar() {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<SearchResult[]>([])
  const [open, setOpen] = useState(false)
  const debouncedQuery = useDebounce(query, 400)
  const { project } = useProject()
  const router = useRouter()
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!debouncedQuery) {
      setResults([])
      return
    }
    const params = new URLSearchParams({ q: debouncedQuery })
    if (project) params.set('project', project)
    fetch(`/api/search?${params}`)
      .then((r) => r.json())
      .then((d) => {
        setResults(d.results ?? [])
        setOpen(true)
      })
      .catch(() => setResults([]))
  }, [debouncedQuery, project])

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node))
        setOpen(false)
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  const navigate = (r: SearchResult) => {
    setOpen(false)
    setQuery('')
    if (r.type === 'entity') router.push('/graph')
    else if (r.type === 'session') router.push('/sessions')
    else router.push('/code')
  }

  const typeLabel: Record<string, string> = {
    entity: 'Entity',
    session: 'Session',
    code: 'File',
    function: 'Function',
  }

  return (
    <div ref={ref} className="relative">
      <div className="flex items-center gap-2 bg-background border border-border rounded-md px-3 py-1.5">
        <Search className="h-3.5 w-3.5 text-muted-foreground" />
        <input
          type="text"
          placeholder="Search everything..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onFocus={() => results.length > 0 && setOpen(true)}
          className="bg-transparent text-sm outline-none w-64 placeholder:text-muted-foreground"
        />
      </div>
      {open && results.length > 0 && (
        <div className="absolute top-full mt-1 left-0 w-96 bg-popover border border-border rounded-md shadow-lg z-50 max-h-80 overflow-y-auto">
          {results.map((r, i) => (
            <button
              key={`${r.id}-${i}`}
              onClick={() => navigate(r)}
              className="w-full text-left px-3 py-2 hover:bg-accent text-sm flex items-center gap-2"
            >
              <span className="text-xs text-muted-foreground shrink-0 w-16">
                {typeLabel[r.type] ?? r.type}
              </span>
              <span className="truncate font-medium">{r.name}</span>
              {r.summary && (
                <span className="truncate text-xs text-muted-foreground ml-auto">
                  {r.summary}
                </span>
              )}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
