/**
 * @jest-environment node
 */
// Integration test — requires Neo4j running (docker compose up -d)
import { getDriver, runQuery } from '@/lib/neo4j'

describe('neo4j client', () => {
  afterAll(async () => {
    const driver = getDriver()
    await driver.close()
  })

  it('connects and runs a simple query', async () => {
    const result = await runQuery<{ n: number }>('RETURN 1 AS n', {})
    expect(result[0].n).toBe(1)
  })

  it('getDriver returns singleton', () => {
    const a = getDriver()
    const b = getDriver()
    expect(a).toBe(b)
  })
})
