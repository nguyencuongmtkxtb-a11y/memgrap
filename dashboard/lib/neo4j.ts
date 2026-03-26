/**
 * Neo4j driver singleton for Next.js API routes.
 * Reads credentials from env vars (via .env.local or docker env_file).
 * Uses bolt protocol for direct Neo4j connection.
 */
import neo4j, { Driver, Integer, DateTime as Neo4jDateTime, Date as Neo4jDate } from 'neo4j-driver'

/** Convert any Neo4j temporal/integer value to a plain JS value. */
function toPlain(v: unknown): unknown {
  if (v == null) return v
  if (neo4j.isInt(v)) return (v as Integer).toNumber()
  if (neo4j.isDateTime(v)) return new Date((v as unknown as Neo4jDateTime<number>).toStandardDate().getTime()).toISOString()
  if (neo4j.isDate(v)) return (v as unknown as Neo4jDate<number>).toStandardDate().toISOString().slice(0, 10)
  if (neo4j.isTime(v) || neo4j.isLocalTime(v) || neo4j.isLocalDateTime(v) || neo4j.isDuration(v)) return v.toString()
  if (Array.isArray(v)) return v.map(toPlain)
  if (v && typeof v === 'object' && 'properties' in v) {
    const props: Record<string, unknown> = {}
    for (const [k, pv] of Object.entries((v as { properties: Record<string, unknown> }).properties)) {
      props[k] = toPlain(pv)
    }
    return { ...props, _id: (v as { elementId?: string }).elementId }
  }
  // Plain object with {low, high} shape — leftover Integer not caught by isInt
  if (v && typeof v === 'object' && 'low' in v && 'high' in v) {
    const { low, high } = v as { low: number; high: number }
    return high === 0 ? low : (high * 0x100000000 + (low >>> 0))
  }
  return v
}

let _driver: Driver | null = null

export function getDriver(): Driver {
  if (!_driver) {
    const uri = process.env.NEO4J_URI ?? 'bolt://localhost:7687'
    const user = process.env.NEO4J_USER ?? 'neo4j'
    const password = process.env.NEO4J_PASSWORD ?? 'password'
    _driver = neo4j.driver(uri, neo4j.auth.basic(user, password), {
      connectionTimeout: 5000,
      maxConnectionLifetime: 3600000,
    })
  }
  return _driver
}

/** Run a read query and return plain records (properties extracted). */
export async function runQuery<T = Record<string, unknown>>(
  cypher: string,
  params: Record<string, unknown>
): Promise<T[]> {
  const session = getDriver().session({ defaultAccessMode: neo4j.session.READ })
  try {
    const result = await session.run(cypher, params)
    return result.records.map((r) => {
      const obj: Record<string, unknown> = {}
      for (const key of r.keys) {
        obj[key as string] = toPlain(r.get(key))
      }
      return obj as T
    })
  } finally {
    await session.close()
  }
}

/** Return GROUP_ID from env — used to scope all graph queries. */
export function getGroupId(): string {
  return process.env.GROUP_ID ?? 'default'
}
