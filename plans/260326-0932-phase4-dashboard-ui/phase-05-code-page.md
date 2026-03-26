# Phase 5: Code Index Page (`/code`)

**Context:** [Spec](../../docs/superpowers/specs/2026-03-26-dashboard-ui-design.md)

**Goal:** Tree view of CodeFile nodes with their children (CodeFunction, CodeClass, CodeImport). Filter by language, search by name.

---

### Task 10: Code Tree Component + Page

**Files:**
- Create: `dashboard/components/code-tree.tsx`
- Create: `dashboard/app/code/page.tsx`

- [ ] **Step 1: Write failing test**

```typescript
// dashboard/__tests__/code-tree.test.tsx
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { CodeTree } from '@/components/code-tree'

const mockFiles = [
  {
    _id: 'f1',
    path: 'src/auth.py',
    language: 'python',
    children: [
      { _id: 'c1', name: 'login', type: 'CodeFunction', line_start: 10 },
      { _id: 'c2', name: 'AuthClass', type: 'CodeClass', line_start: 1 },
    ],
  },
]

describe('CodeTree', () => {
  it('renders file path', () => {
    render(<CodeTree files={mockFiles} />)
    expect(screen.getByText('src/auth.py')).toBeInTheDocument()
  })

  it('toggles children on click', async () => {
    render(<CodeTree files={mockFiles} />)
    expect(screen.queryByText('login')).not.toBeInTheDocument()
    await userEvent.click(screen.getByText('src/auth.py'))
    expect(screen.getByText('login')).toBeInTheDocument()
    expect(screen.getByText('AuthClass')).toBeInTheDocument()
  })
})
```

- [ ] **Step 2: Run test to verify fail**

```bash
cd D:/MEMGRAP/dashboard
npm install --save-dev @testing-library/user-event
npm test -- --testPathPattern=code-tree 2>&1 | tail -10
```

- [ ] **Step 3: Implement code-tree.tsx**

```typescript
// dashboard/components/code-tree.tsx
'use client'

import { useState } from 'react'
import { ChevronRight, ChevronDown, File, FunctionSquare, BoxSelect, Import } from 'lucide-react'
import { cn } from '@/lib/utils'

interface CodeChild {
  _id: string
  name: string
  type: string
  line_start?: number
}

interface CodeFileNode {
  _id: string
  path: string
  language?: string
  children: CodeChild[]
}

const CHILD_ICONS: Record<string, React.ComponentType<{ className?: string }>> = {
  CodeFunction: FunctionSquare,
  CodeClass:    BoxSelect,
  CodeImport:   Import,
}

const LANG_COLORS: Record<string, string> = {
  python:     'text-yellow-400',
  typescript: 'text-blue-400',
  javascript: 'text-yellow-300',
  default:    'text-muted-foreground',
}

export function CodeTree({ files }: { files: CodeFileNode[] }) {
  const [expanded, setExpanded] = useState<Set<string>>(new Set())

  const toggle = (id: string) =>
    setExpanded(prev => {
      const next = new Set(prev)
      next.has(id) ? next.delete(id) : next.add(id)
      return next
    })

  if (files.length === 0) {
    return <p className="text-sm text-muted-foreground py-4">No code files indexed.</p>
  }

  return (
    <div className="space-y-0.5">
      {files.map(file => {
        const isOpen = expanded.has(file._id)
        const langColor = LANG_COLORS[file.language ?? ''] ?? LANG_COLORS.default
        return (
          <div key={file._id}>
            <button
              onClick={() => toggle(file._id)}
              className="w-full flex items-center gap-2 px-2 py-1.5 rounded hover:bg-accent text-sm text-left"
            >
              {isOpen
                ? <ChevronDown className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
                : <ChevronRight className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
              }
              <File className={cn('h-3.5 w-3.5 shrink-0', langColor)} />
              <span className="font-mono truncate">{file.path}</span>
              {file.language && (
                <span className="ml-auto text-xs text-muted-foreground shrink-0">{file.language}</span>
              )}
            </button>
            {isOpen && file.children.length > 0 && (
              <div className="ml-6 border-l border-border pl-2 space-y-0.5">
                {file.children.map(child => {
                  const Icon = CHILD_ICONS[child.type] ?? File
                  return (
                    <div key={child._id} className="flex items-center gap-2 px-2 py-1 text-xs text-muted-foreground">
                      <Icon className="h-3 w-3 shrink-0" />
                      <span className="font-mono truncate">{child.name}</span>
                      {child.line_start != null && (
                        <span className="ml-auto shrink-0">:{child.line_start}</span>
                      )}
                      <span className="text-muted-foreground/50">{child.type.replace('Code', '')}</span>
                    </div>
                  )
                })}
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}
```

- [ ] **Step 4: Implement code page**

```typescript
// dashboard/app/code/page.tsx
'use client'

import { useEffect, useState, useCallback } from 'react'
import { CodeTree } from '@/components/code-tree'
import { Input } from '@/components/ui/input'
import { useDebounce } from '@/lib/use-debounce'

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

  useEffect(() => { fetchFiles() }, [fetchFiles])

  return (
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
          onChange={e => setSearch(e.target.value)}
          className="max-w-xs"
        />
        <Input
          placeholder="Language (python, typescript...)"
          value={lang}
          onChange={e => setLang(e.target.value)}
          className="max-w-xs"
        />
      </div>
      {loading ? (
        <p className="text-sm text-muted-foreground">Loading...</p>
      ) : (
        <CodeTree files={files as Parameters<typeof CodeTree>[0]['files']} />
      )}
    </div>
  )
}
```

- [ ] **Step 5: Create useDebounce hook**

```typescript
// dashboard/lib/use-debounce.ts
import { useState, useEffect } from 'react'

export function useDebounce<T>(value: T, delay: number): T {
  const [debounced, setDebounced] = useState(value)
  useEffect(() => {
    const timer = setTimeout(() => setDebounced(value), delay)
    return () => clearTimeout(timer)
  }, [value, delay])
  return debounced
}
```

- [ ] **Step 6: Run test to verify pass**

```bash
cd D:/MEMGRAP/dashboard
npm test -- --testPathPattern=code-tree 2>&1 | tail -10
```

- [ ] **Step 7: Commit**

```bash
cd D:/MEMGRAP
git add dashboard/components/code-tree.tsx dashboard/app/code/ dashboard/lib/use-debounce.ts
git commit -m "feat(dashboard): add /code page with collapsible code tree"
```
