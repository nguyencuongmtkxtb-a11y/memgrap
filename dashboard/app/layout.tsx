import type { Metadata } from 'next'
import { Geist, Geist_Mono } from 'next/font/google'
import './globals.css'
import { Sidebar } from '@/components/sidebar'
import { ProjectProvider } from '@/contexts/project-context'
import { SearchBar } from '@/components/search-bar'

const geistSans = Geist({ variable: '--font-geist-sans', subsets: ['latin'] })
const geistMono = Geist_Mono({ variable: '--font-geist-mono', subsets: ['latin'] })

export const metadata: Metadata = {
  title: 'Memgrap Dashboard',
  description: 'Knowledge graph explorer',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${geistSans.variable} ${geistMono.variable} dark`}>
      <body className="bg-background text-foreground min-h-screen flex">
        <ProjectProvider>
          <Sidebar />
          <div className="flex-1 flex flex-col overflow-hidden">
            <header className="flex items-center px-6 py-3 border-b border-border shrink-0">
              <SearchBar />
            </header>
            <main className="flex-1 overflow-auto">{children}</main>
          </div>
        </ProjectProvider>
      </body>
    </html>
  )
}
