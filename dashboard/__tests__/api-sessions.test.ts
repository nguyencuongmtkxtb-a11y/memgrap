/**
 * @jest-environment node
 */
import { GET as listSessions } from '@/app/api/sessions/route'
import { NextRequest } from 'next/server'

describe('GET /api/sessions', () => {
  it('returns 200 with sessions array', async () => {
    const req = new NextRequest('http://localhost:3000/api/sessions')
    const res = await listSessions(req)
    expect(res.status).toBe(200)
    const data = await res.json()
    expect(Array.isArray(data.sessions)).toBe(true)
  })
})
