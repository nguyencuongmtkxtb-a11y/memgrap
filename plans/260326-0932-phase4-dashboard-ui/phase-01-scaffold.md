# Phase 1: Project Scaffold

**Context:** [Spec](../../docs/superpowers/specs/2026-03-26-dashboard-ui-design.md) | [Arch](../../docs/system-architecture.md)

**Goal:** Bootstrap Next.js 15 project with shadcn/ui, Tailwind dark theme, sidebar layout, and root redirect.

**Priority:** Critical — all other phases depend on this.

---

### Task 1: Create Next.js 15 App

**Files:**
- Create: `dashboard/package.json`
- Create: `dashboard/next.config.ts`
- Create: `dashboard/tailwind.config.ts`
- Create: `dashboard/tsconfig.json`
- Create: `dashboard/postcss.config.mjs`
- Create: `dashboard/.env.local` (gitignored, references parent .env)

- [ ] **Step 1: Scaffold Next.js app**

```bash
cd D:/MEMGRAP
npx create-next-app@latest dashboard \
  --typescript \
  --tailwind \
  --eslint \
  --app \
  --no-src-dir \
  --import-alias "@/*"
```

Expected output: `dashboard/` directory created with `app/`, `components/`, `public/`, `package.json`.

- [ ] **Step 2: Verify scaffold compiled**

```bash
cd D:/MEMGRAP/dashboard
npm run build 2>&1 | tail -5
```

Expected: `✓ Compiled successfully` (or similar — no errors).

- [ ] **Step 3: Install additional dependencies**

```bash
cd D:/MEMGRAP/dashboard
npm install neo4j-driver
npm install react-force-graph-2d
npm install @types/react-force-graph-2d --save-dev
```

- [ ] **Step 4: Install shadcn/ui**

```bash
cd D:/MEMGRAP/dashboard
npx shadcn@latest init --defaults
```

When prompted:
- Style: Default
- Base color: Slate
- CSS variables: Yes

- [ ] **Step 5: Add shadcn components used by the dashboard**

```bash
cd D:/MEMGRAP/dashboard
npx shadcn@latest add card badge separator scroll-area input checkbox
```

- [ ] **Step 6: Verify tailwind.config.ts has dark mode set**

Open `dashboard/tailwind.config.ts` — ensure it has `darkMode: ["class"]` (shadcn sets this). Confirm `content` array includes `./app/**/*.{ts,tsx}` and `./components/**/*.{ts,tsx}`.

- [ ] **Step 7: Commit**

```bash
cd D:/MEMGRAP
git add dashboard/
git commit -m "feat(dashboard): scaffold Next.js 15 app with shadcn/ui and Tailwind"
```

---

### Task 2: Root Layout — Sidebar + Dark Theme

**Files:**
- Create: `dashboard/app/layout.tsx`
- Create: `dashboard/app/globals.css`
- Create: `dashboard/components/sidebar.tsx`
- Create: `dashboard/app/page.tsx`

- [ ] **Step 1: Write test — sidebar renders nav links**

```typescript
// dashboard/__tests__/sidebar.test.tsx
import { render, screen } from '@testing-library/react'
import { Sidebar } from '@/components/sidebar'

describe('Sidebar', () => {
  it('renders all nav links', () => {
    render(<Sidebar />)
    expect(screen.getByText('Graph')).toBeInTheDocument()
    expect(screen.getByText('Sessions')).toBeInTheDocument()
    expect(screen.getByText('Code')).toBeInTheDocument()
    expect(screen.getByText('Stats')).toBeInTheDocument()
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd D:/MEMGRAP/dashboard
npm test -- --testPathPattern=sidebar 2>&1 | tail -10
```

Expected: FAIL — `Cannot find module '@/components/sidebar'`

- [ ] **Step 3: Install testing deps**

```bash
cd D:/MEMGRAP/dashboard
npm install --save-dev jest jest-environment-jsdom @testing-library/react @testing-library/jest-dom ts-jest
```

Add to `dashboard/package.json` `scripts`:
```json
"test": "jest"
```

Add `dashboard/jest.config.ts`:
```typescript
import type { Config } from 'jest'
const config: Config = {
  testEnvironment: 'jsdom',
  setupFilesAfterFramework: ['<rootDir>/jest.setup.ts'],
  moduleNameMapper: { '^@/(.*)$': '<rootDir>/$1' },
  transform: { '^.+\\.tsx?$': ['ts-jest', { tsconfig: { jsx: 'react-jsx' } }] },
}
export default config
```

Add `dashboard/jest.setup.ts`:
```typescript
import '@testing-library/jest-dom'
```

- [ ] **Step 4: Implement sidebar.tsx**

```typescript
// dashboard/components/sidebar.tsx
'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { GitGraph, Clock, FileCode2, BarChart3 } from 'lucide-react'
import { cn } from '@/lib/utils'

const NAV = [
  { href: '/graph',    label: 'Graph',    icon: GitGraph },
  { href: '/sessions', label: 'Sessions', icon: Clock },
  { href: '/code',     label: 'Code',     icon: FileCode2 },
  { href: '/stats',    label: 'Stats',    icon: BarChart3 },
]

export function Sidebar() {
  const pathname = usePathname()
  return (
    <aside className="w-52 flex-none flex flex-col border-r border-border bg-background h-screen sticky top-0">
      <div className="px-4 py-5 border-b border-border">
        <span className="text-sm font-semibold text-foreground tracking-wide">Memgrap</span>
      </div>
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
    </aside>
  )
}
```

- [ ] **Step 5: Implement root layout**

```typescript
// dashboard/app/layout.tsx
import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'
import { Sidebar } from '@/components/sidebar'

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
  title: 'Memgrap Dashboard',
  description: 'Knowledge graph explorer',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body className={`${inter.className} bg-background text-foreground min-h-screen flex`}>
        <Sidebar />
        <main className="flex-1 overflow-auto">
          {children}
        </main>
      </body>
    </html>
  )
}
```

- [ ] **Step 6: Implement root redirect page**

```typescript
// dashboard/app/page.tsx
import { redirect } from 'next/navigation'

export default function Home() {
  redirect('/graph')
}
```

- [ ] **Step 7: Run test to verify pass**

```bash
cd D:/MEMGRAP/dashboard
npm test -- --testPathPattern=sidebar 2>&1 | tail -10
```

Expected: PASS

- [ ] **Step 8: Verify dev server starts**

```bash
cd D:/MEMGRAP/dashboard
npm run dev &
sleep 3
curl -s http://localhost:3000/ | head -5
kill %1
```

Expected: Response (or redirect header to /graph).

- [ ] **Step 9: Commit**

```bash
cd D:/MEMGRAP
git add dashboard/
git commit -m "feat(dashboard): add sidebar layout and root redirect to /graph"
```
