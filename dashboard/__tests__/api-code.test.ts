/**
 * @jest-environment node
 */
import { GET } from '@/app/api/code/files/route'
import { NextRequest } from 'next/server'

describe('GET /api/code/files', () => {
  it('returns 200 with files array', async () => {
    const req = new NextRequest('http://localhost:3000/api/code/files')
    const res = await GET(req)
    expect(res.status).toBe(200)
    const data = await res.json()
    expect(Array.isArray(data.files)).toBe(true)
  })
})
