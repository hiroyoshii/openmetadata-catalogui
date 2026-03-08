import type {
  Domain,
  Table,
  TestCase,
  SampleData,
  Lineage,
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

  getTables(): Promise<PagedResponse<Table>> {
    return get(
      '/tables?limit=100&fields=name,description,columns,tags,databaseSchema,database,domain'
    )
  },

  getTable(id: string): Promise<Table> {
    return get(
      `/tables/${id}?fields=name,description,columns,tags,databaseSchema,database,owners,domain`
    )
  },

  getLineage(id: string): Promise<Lineage> {
    return get(`/lineage/table/${id}?upstreamDepth=3&downstreamDepth=3`)
  },

  getTestCases(fqn: string): Promise<PagedResponse<TestCase>> {
    return get(
      `/dataQuality/testCases?entityFQN=${encodeURIComponent(fqn)}&limit=100&fields=testDefinition,testCaseResult,parameterValues`
    )
  },

  getSampleData(id: string): Promise<{ sampleData?: SampleData } & SampleData> {
    return get(`/tables/${id}/sampleData`)
  },
}
