# Phase 7: Docker Integration + Final Polish

**Context:** [Spec](../../docs/superpowers/specs/2026-03-26-dashboard-ui-design.md)

**Goal:** Dockerfile for dashboard, add to docker-compose.yml, verify full stack works.

---

### Task 12: Dockerfile

**Files:**
- Create: `dashboard/Dockerfile`
- Create: `dashboard/.dockerignore`

- [ ] **Step 1: Create .dockerignore**

```
node_modules
.next
.env.local
__tests__
*.test.ts
*.test.tsx
```

- [ ] **Step 2: Write Dockerfile**

```dockerfile
# dashboard/Dockerfile
FROM node:20-alpine AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

FROM node:20-alpine AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
# Build-time env vars — actual secrets come from env_file at runtime
ENV NEXT_TELEMETRY_DISABLED=1
RUN npm run build

FROM node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1
COPY --from=builder /app/public ./public
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
EXPOSE 3000
CMD ["node", "server.js"]
```

- [ ] **Step 3: Enable Next.js standalone output**

Edit `dashboard/next.config.ts` — add `output: 'standalone'`:

```typescript
// dashboard/next.config.ts
import type { NextConfig } from 'next'

const nextConfig: NextConfig = {
  output: 'standalone',
}

export default nextConfig
```

- [ ] **Step 4: Verify Docker build**

```bash
cd D:/MEMGRAP/dashboard
docker build -t memgrap-dashboard . 2>&1 | tail -10
```

Expected: `Successfully built ...`

- [ ] **Step 5: Commit**

```bash
cd D:/MEMGRAP
git add dashboard/Dockerfile dashboard/.dockerignore dashboard/next.config.ts
git commit -m "feat(dashboard): add Dockerfile with standalone output"
```

---

### Task 13: Update docker-compose.yml

**Files:**
- Modify: `D:\MEMGRAP\docker-compose.yml`

- [ ] **Step 1: Write failing integration test (verify dashboard service in compose)**

```bash
# Manual check — verify compose config is valid after edit
docker compose config 2>&1 | grep -E "dashboard|Error" | head -10
```

Expected: `dashboard:` section visible, no Error.

- [ ] **Step 2: Add dashboard service to docker-compose.yml**

Add the following service block to `D:\MEMGRAP\docker-compose.yml` (after the neo4j service):

```yaml
  dashboard:
    build: ./dashboard
    container_name: memgrap-dashboard
    restart: unless-stopped
    ports:
      - "3000:3000"
    env_file: .env
    environment:
      # Override NEO4J_URI to use Docker service name, not localhost
      - NEO4J_URI=bolt://neo4j:7687
    depends_on:
      neo4j:
        condition: service_healthy
```

- [ ] **Step 3: Run compose config validation**

```bash
cd D:/MEMGRAP
docker compose config 2>&1 | grep -E "dashboard|Error" | head -10
```

Expected: `dashboard:` block present, no errors.

- [ ] **Step 4: Full stack smoke test**

```bash
cd D:/MEMGRAP
docker compose up -d --build
sleep 10
curl -s http://localhost:3000/api/stats | python -m json.tool | head -10
```

Expected: JSON with `entityCount`, `sessionCount` etc.

- [ ] **Step 5: Verify graph page loads**

```bash
curl -s http://localhost:3000/api/graph/viz?limit=10 | python -m json.tool | head -10
```

Expected: `{"nodes": [...], "edges": [...]}`

- [ ] **Step 6: Commit**

```bash
cd D:/MEMGRAP
git add docker-compose.yml
git commit -m "feat(dashboard): add dashboard service to docker-compose"
```

---

### Task 14: Error Banner + Final Polish

**Files:**
- Create: `dashboard/components/error-banner.tsx`
- Verify all pages handle 503 from API

- [ ] **Step 1: Create reusable error banner**

```typescript
// dashboard/components/error-banner.tsx
export function ErrorBanner({ message }: { message?: string }) {
  return (
    <div className="rounded-md bg-destructive/10 border border-destructive/20 px-4 py-3 text-sm text-destructive">
      {message ?? 'Neo4j unreachable — ensure docker compose is running.'}
    </div>
  )
}
```

- [ ] **Step 2: Replace inline error divs in pages with ErrorBanner**

Update `dashboard/app/stats/page.tsx`, `dashboard/app/sessions/page.tsx`:
- Replace `<div className="rounded-md bg-destructive...">` with `<ErrorBanner />`

- [ ] **Step 3: Final build check**

```bash
cd D:/MEMGRAP/dashboard
npm run build 2>&1 | tail -10
```

Expected: `✓ Compiled successfully`

- [ ] **Step 4: Run all tests**

```bash
cd D:/MEMGRAP/dashboard
npm test 2>&1 | tail -20
```

Expected: All tests pass.

- [ ] **Step 5: Final commit**

```bash
cd D:/MEMGRAP
git add dashboard/
git commit -m "feat(dashboard): Phase 4 complete — Memgrap Dashboard UI"
```
