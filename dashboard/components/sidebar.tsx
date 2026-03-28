'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { GitGraph, Clock, FileCode2, BarChart3, Download, Network, Settings } from 'lucide-react'
import { cn } from '@/lib/utils'
import { ConnectionStatus } from '@/components/connection-status'
import { ProjectSelector } from '@/components/project-selector'

const NAV = [
  { href: '/graph', label: 'Graph', icon: GitGraph },
  { href: '/sessions', label: 'Sessions', icon: Clock },
  { href: '/code', label: 'Code', icon: FileCode2 },
  { href: '/code-graph', label: 'Code Graph', icon: Network },
  { href: '/stats', label: 'Stats', icon: BarChart3 },
  { href: '/export', label: 'Export', icon: Download },
  { href: '/settings', label: 'Settings', icon: Settings },
]

export function Sidebar() {
  const pathname = usePathname()
  return (
    <aside className="w-52 flex-none flex flex-col border-r border-border bg-background h-screen sticky top-0">
      <div className="px-4 py-5 border-b border-border">
        <span className="text-sm font-semibold text-foreground tracking-wide">
          Memgrap
        </span>
      </div>
      <ProjectSelector />
      <nav className="flex-1 py-4">
        {NAV.map(({ href, label, icon: Icon }) => (
          <Link
            key={href}
            href={href}
            className={cn(
              'flex items-center gap-3 px-4 py-2 text-sm transition-colors hover:bg-accent',
              pathname.startsWith(href)
                ? 'text-foreground bg-accent'
                : 'text-muted-foreground'
            )}
          >
            <Icon className="h-4 w-4 shrink-0" />
            {label}
          </Link>
        ))}
      </nav>
      <div className="border-t border-border">
        <ConnectionStatus />
      </div>
    </aside>
  )
}
