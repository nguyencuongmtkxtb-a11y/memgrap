'use client'

import { useState, useMemo } from 'react'
import {
  ChevronRight,
  ChevronDown,
  File,
  Folder,
  FolderOpen,
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
  project?: string
  children: CodeChild[]
}

interface DirNode {
  name: string
  dirs: Map<string, DirNode>
  files: CodeFileNode[]
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
  go: 'text-cyan-400',
  rust: 'text-orange-400',
  default: 'text-muted-foreground',
}

function buildTree(files: CodeFileNode[]): Map<string, DirNode> {
  const root = new Map<string, DirNode>()

  for (const file of files) {
    // Group by project first, then by relative path
    const project = file.project || 'unknown'
    if (!root.has(project)) {
      root.set(project, { name: project, dirs: new Map(), files: [] })
    }
    const projectNode = root.get(project)!

    // Split path into segments, skip drive letter + project root
    const parts = file.path.replace(/\\/g, '/').split('/')
    // Find the project name in path and take everything after it
    const projIdx = parts.findIndex(
      (p) => p.toLowerCase() === project.toLowerCase()
    )
    const relParts = projIdx >= 0 ? parts.slice(projIdx + 1) : parts
    const fileName = relParts.pop()
    if (!fileName) continue

    // Navigate/create directory tree
    let current = projectNode
    for (const dir of relParts) {
      if (!current.dirs.has(dir)) {
        current.dirs.set(dir, { name: dir, dirs: new Map(), files: [] })
      }
      current = current.dirs.get(dir)!
    }
    current.files.push(file)
  }
  return root
}

function DirEntry({
  node,
  depth,
}: {
  node: DirNode
  depth: number
}) {
  const [open, setOpen] = useState(depth < 2)
  const dirCount = node.dirs.size
  const fileCount = node.files.length
  const total = dirCount + fileCount

  return (
    <div>
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center gap-2 px-2 py-1.5 rounded hover:bg-accent text-sm text-left"
        style={{ paddingLeft: `${depth * 12 + 8}px` }}
      >
        {open ? (
          <ChevronDown className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
        ) : (
          <ChevronRight className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
        )}
        {open ? (
          <FolderOpen className="h-3.5 w-3.5 shrink-0 text-blue-400" />
        ) : (
          <Folder className="h-3.5 w-3.5 shrink-0 text-blue-400" />
        )}
        <span className="font-medium truncate">{node.name}</span>
        <span className="ml-auto text-xs text-muted-foreground shrink-0">
          {total}
        </span>
      </button>
      {open && (
        <div>
          {[...node.dirs.values()]
            .sort((a, b) => a.name.localeCompare(b.name))
            .map((dir) => (
              <DirEntry key={dir.name} node={dir} depth={depth + 1} />
            ))}
          {node.files
            .sort((a, b) => a.path.localeCompare(b.path))
            .map((file) => (
              <FileEntry key={file._id} file={file} depth={depth + 1} />
            ))}
        </div>
      )}
    </div>
  )
}

function FileEntry({
  file,
  depth,
}: {
  file: CodeFileNode
  depth: number
}) {
  const [open, setOpen] = useState(false)
  const fileName = file.path.replace(/\\/g, '/').split('/').pop() || file.path
  const langColor = LANG_COLORS[file.language ?? ''] ?? LANG_COLORS.default

  return (
    <div>
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center gap-2 px-2 py-1.5 rounded hover:bg-accent text-sm text-left"
        style={{ paddingLeft: `${depth * 12 + 8}px` }}
      >
        {file.children.length > 0 ? (
          open ? (
            <ChevronDown className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
          ) : (
            <ChevronRight className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
          )
        ) : (
          <span className="w-3.5" />
        )}
        <File className={cn('h-3.5 w-3.5 shrink-0', langColor)} />
        <span className="font-mono truncate">{fileName}</span>
        {file.language && (
          <span className="ml-auto text-xs text-muted-foreground shrink-0">
            {file.language}
          </span>
        )}
      </button>
      {open && file.children.length > 0 && (
        <div
          className="border-l border-border space-y-0.5"
          style={{ marginLeft: `${(depth + 1) * 12 + 8}px`, paddingLeft: '8px' }}
        >
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
                  {(child.type ?? '').replace('Code', '')}
                </span>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}

export function CodeTree({ files }: { files: CodeFileNode[] }) {
  const tree = useMemo(() => buildTree(files), [files])

  if (files.length === 0) {
    return (
      <p className="text-sm text-muted-foreground py-4">
        No code files indexed.
      </p>
    )
  }

  return (
    <div className="space-y-0.5">
      {[...tree.values()]
        .sort((a, b) => a.name.localeCompare(b.name))
        .map((project) => (
          <DirEntry key={project.name} node={project} depth={0} />
        ))}
    </div>
  )
}
