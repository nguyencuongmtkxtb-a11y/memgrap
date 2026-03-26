'use client'

import { useState } from 'react'
import {
  ChevronRight,
  ChevronDown,
  File,
  FunctionSquare,
  BoxSelect,
  Import,
} from 'lucide-react'
import { cn } from '@/lib/utils'

interface CodeChild {
  _id: string
  name: string
  type: string
  line?: number
}

interface CodeFileNode {
  _id: string
  path: string
  language?: string
  children: CodeChild[]
}

const CHILD_ICONS: Record<string, React.ComponentType<{ className?: string }>> =
  {
    CodeFunction: FunctionSquare,
    CodeClass: BoxSelect,
    CodeImport: Import,
  }

const LANG_COLORS: Record<string, string> = {
  python: 'text-yellow-400',
  typescript: 'text-blue-400',
  javascript: 'text-yellow-300',
  default: 'text-muted-foreground',
}

export function CodeTree({ files }: { files: CodeFileNode[] }) {
  const [expanded, setExpanded] = useState<Set<string>>(new Set())

  const toggle = (id: string) =>
    setExpanded((prev) => {
      const next = new Set(prev)
      next.has(id) ? next.delete(id) : next.add(id)
      return next
    })

  if (files.length === 0) {
    return (
      <p className="text-sm text-muted-foreground py-4">
        No code files indexed.
      </p>
    )
  }

  return (
    <div className="space-y-0.5">
      {files.map((file) => {
        const isOpen = expanded.has(file._id)
        const langColor =
          LANG_COLORS[file.language ?? ''] ?? LANG_COLORS.default
        return (
          <div key={file._id}>
            <button
              onClick={() => toggle(file._id)}
              className="w-full flex items-center gap-2 px-2 py-1.5 rounded hover:bg-accent text-sm text-left"
            >
              {isOpen ? (
                <ChevronDown className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
              ) : (
                <ChevronRight className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
              )}
              <File className={cn('h-3.5 w-3.5 shrink-0', langColor)} />
              <span className="font-mono truncate">{file.path}</span>
              {file.language && (
                <span className="ml-auto text-xs text-muted-foreground shrink-0">
                  {file.language}
                </span>
              )}
            </button>
            {isOpen && file.children.length > 0 && (
              <div className="ml-6 border-l border-border pl-2 space-y-0.5">
                {file.children.map((child) => {
                  const Icon = CHILD_ICONS[child.type] ?? File
                  return (
                    <div
                      key={child._id}
                      className="flex items-center gap-2 px-2 py-1 text-xs text-muted-foreground"
                    >
                      <Icon className="h-3 w-3 shrink-0" />
                      <span className="font-mono truncate">{child.name}</span>
                      {child.line != null && (
                        <span className="ml-auto shrink-0">:{child.line}</span>
                      )}
                      <span className="text-muted-foreground/50">
                        {child.type.replace('Code', '')}
                      </span>
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
