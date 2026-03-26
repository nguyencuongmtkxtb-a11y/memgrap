/**
 * @jest-environment node
 */
// Integration test — hits real Neo4j
import { GET } from '@/app/api/stats/route'
import { NextRequest } from 'next/server'

describe('GET /api/stats', () => {
  it('returns 200 with expected shape', async () => {
    const req = new NextRequest('http://localhost:3000/api/stats')
    const res = await GET(req)
    expect(res.status).toBe(200)
    const data = await res.json()
    expect(typeof data.entityCount).toBe('number')
    expect(typeof data.edgeCount).toBe('number')
    expect(typeof data.sessionCount).toBe('number')
    expect(typeof data.codeFileCount).toBe('number')
    expect(Array.isArray(data.recentEpisodes)).toBe(true)
    expect(data.health).toHaveProperty('neo4j')
    expect(data.health).toHaveProperty('groupId')
  })
})
