/**
 * Neo4j driver singleton for Next.js API routes.
 * Reads credentials from env vars (via .env.local or docker env_file).
 * Uses bolt protocol for direct Neo4j connection.
 */
import neo4j, { Driver, Integer } from 'neo4j-driver'

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
        const val = r.get(key)
        if (neo4j.isInt(val)) {
          obj[key as string] = (val as Integer).toNumber()
        } else if (val && typeof val === 'object' && 'properties' in val) {
          // Node — extract properties and add elementId
          const props: Record<string, unknown> = {}
          for (const [k, v] of Object.entries(
            val.properties as Record<string, unknown>
          )) {
            props[k] = neo4j.isInt(v) ? (v as Integer).toNumber() : v
          }
          obj[key as string] = { ...props, _id: val.elementId }
        } else if (Array.isArray(val)) {
          // Handle arrays of nodes (e.g. collect())
          obj[key as string] = val.map((item) => {
            if (item && typeof item === 'object' && 'properties' in item) {
              const props: Record<string, unknown> = {}
              for (const [k, v] of Object.entries(
                item.properties as Record<string, unknown>
              )) {
                props[k] = neo4j.isInt(v) ? (v as Integer).toNumber() : v
              }
              return { ...props, _id: item.elementId }
            }
            return neo4j.isInt(item) ? (item as Integer).toNumber() : item
          })
        } else {
          obj[key as string] = val
        }
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
