import type { Metadata } from 'next'
import { Geist, Geist_Mono } from 'next/font/google'
import './globals.css'
import { Sidebar } from '@/components/sidebar'
import { ProjectProvider } from '@/contexts/project-context'

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
          <main className="flex-1 overflow-auto">{children}</main>
        </ProjectProvider>
      </body>
    </html>
  )
}
