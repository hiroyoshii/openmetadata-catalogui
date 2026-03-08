import type {
  Domain,
  Table,
  TestCase,
  SampleData,
  EntityLineage,
  DatabaseService,
  PagedResponse,
} from '@/types'

const BASE = '/api/v1'

async function get<T>(path: string): Promise<T> {
  const res = await fetch(BASE + path)
  if (!res.ok) throw new Error(`API ${path} failed: ${res.status}`)
  return res.json() as Promise<T>
}

export const api = {
  getDomains(): Promise<PagedResponse<Domain>> {
    return get('/domains?limit=50')
  },

  /** 全 DatabaseService 一覧 (収集元 + 公開サービス) */
  getDatabaseServices(): Promise<PagedResponse<DatabaseService>> {
    return get('/services/databaseServices?limit=50&fields=name,description,owners,domain')
  },

  getDatabaseService(name: string): Promise<DatabaseService> {
    return get(`/services/databaseServices/name/${encodeURIComponent(name)}?fields=name,description,owners,domain`)
  },

  /** サービスのスキーマ一覧を取得してから、スキーマ別テーブルを集約する */
  async getTablesByServiceName(svcName: string): Promise<PagedResponse<Table>> {
    const schemas = await get<PagedResponse<{ name: string; fullyQualifiedName: string }>>(
      `/databaseSchemas?service=${encodeURIComponent(svcName)}&limit=50&fields=name,fullyQualifiedName`
    )
    const svcSchemas = schemas.data.filter((s) =>
      (s.fullyQualifiedName ?? '').startsWith(svcName + '.')
    )
    const results: Table[] = []
    await Promise.all(
      svcSchemas.map(async (schema) => {
        const fqn = schema.fullyQualifiedName ?? ''
        const res = await get<PagedResponse<Table>>(
          `/tables?databaseSchema=${encodeURIComponent(fqn)}&limit=100&fields=name,description,tags,service,owners`
        )
        results.push(...res.data)
      })
    )
    return { data: results, paging: { total: results.length } }
  },

  getTables(): Promise<PagedResponse<Table>> {
    return get('/tables?limit=100&fields=name,description,columns,tags,databaseSchema,database,service,domain,owners')
  },

  getTable(id: string): Promise<Table> {
    return get(`/tables/${id}?fields=name,description,columns,tags,databaseSchema,database,service,owners,domain`)
  },

  getLineage(id: string): Promise<EntityLineage> {
    return get(`/lineage/table/${id}?upstreamDepth=3&downstreamDepth=3`)
  },

  getTestCases(fqn: string): Promise<PagedResponse<TestCase>> {
    return get(`/dataQuality/testCases?entityFQN=${encodeURIComponent(fqn)}&limit=100&fields=testDefinition,testCaseResult,parameterValues`)
  },

  getSampleData(id: string): Promise<{ sampleData?: SampleData } & SampleData> {
    return get(`/tables/${id}/sampleData`)
  },
}
