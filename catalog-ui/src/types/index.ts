// OpenMetadata API response types

export interface DomainRef {
  id: string
  type: string
  name: string
  displayName?: string
  fullyQualifiedName?: string
  deleted?: boolean
}

export interface Domain {
  id: string
  name: string
  fullyQualifiedName: string
  displayName?: string
  description?: string
  domainType?: string
  version?: number
}

export interface Column {
  name: string
  dataType: string
  dataLength?: number
  dataTypeDisplay?: string
  description?: string
  fullyQualifiedName?: string
  constraint?: 'PRIMARY_KEY' | 'NOT_NULL' | 'NULL' | 'UNIQUE'
  tags?: Tag[]
}

export interface Tag {
  tagFQN?: string
  name?: string
}

export interface EntityRef {
  id: string
  type: string
  name: string
  displayName?: string
  fullyQualifiedName?: string
  deleted?: boolean
}

export interface Table {
  id: string
  name: string
  fullyQualifiedName: string
  description?: string
  tableType?: string
  columns?: Column[]
  tags?: Tag[]
  databaseSchema?: EntityRef
  database?: EntityRef
  service?: EntityRef
  owner?: EntityRef
  domain?: DomainRef
  version?: number
}

export interface TestDefinition {
  id?: string
  name?: string
  displayName?: string
}

export interface TestCaseResult {
  testCaseStatus?: string
  result?: string
  timestamp?: number
}

export interface ParameterValue {
  name?: string
  value?: string
}

export interface TestCase {
  id: string
  name: string
  entityFQN?: string
  testCaseStatus?: string
  testDefinition?: TestDefinition
  testCaseResult?: TestCaseResult
  parameterValues?: ParameterValue[]
}

export interface SampleData {
  columns?: string[]
  rows?: (string | number | null)[][]
}

export interface LineageEdge {
  fromEntity: string
  toEntity: string
}

export interface LineageNode {
  id: string
  name?: string
  fullyQualifiedName?: string
  type?: string
}

export interface Lineage {
  entity?: { id: string; name?: string; fullyQualifiedName?: string }
  nodes?: LineageNode[]
  upstreamEdges?: LineageEdge[]
  downstreamEdges?: LineageEdge[]
}

export interface PagedResponse<T> {
  data: T[]
  paging: { total: number; after?: string; before?: string }
}
