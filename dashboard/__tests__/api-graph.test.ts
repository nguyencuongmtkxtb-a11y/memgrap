/**
 * @jest-environment node
 */
import { GET as getViz } from '@/app/api/graph/viz/route'
import { NextRequest } from 'next/server'

describe('GET /api/graph/viz', () => {
  it('returns 200 with nodes and edges arrays', async () => {
    const req = new NextRequest('http://localhost:3000/api/graph/viz?limit=10')
    const res = await getViz(req)
    expect(res.status).toBe(200)
    const data = await res.json()
    expect(Array.isArray(data.nodes)).toBe(true)
    expect(Array.isArray(data.edges)).toBe(true)
  })
})
