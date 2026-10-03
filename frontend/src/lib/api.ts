// Types mirror the Pydantic domain models in backend/app/domain/*.py exactly.

export type RiskTolerance = 'Conservative' | 'Moderate' | 'Growth' | 'High Growth'

export type FieldStatus = 'present' | 'missing'

export interface FactFindField {
  field: string
  value: unknown
  status: FieldStatus
}

export interface FactFind {
  client_id: string
  fields: FactFindField[]
}

export interface ClientProfile {
  client_id: string
  first_name: string
  last_name: string
  age: number | null
  salary: number | null
  super_balance: number | null
  risk_tolerance: RiskTolerance | null
  target_retirement_age: number | null
  contribution_history: string[]
  concessional_contributions_ytd: number
  non_concessional_contributions_ytd: number
  ttr_intent: boolean | null
  investment_objectives: string[]
  financial_goals: string[]
  constraints: string[]
  advisory_status: string
  compliance_status: string | null
  last_review_date: string | null
}

export type ProductType = 'MySuper' | 'Choice' | 'SMSF' | 'TTR' | 'Defined Benefit'

export interface Product {
  product_id: string
  product_name: string
  product_type: ProductType
  management_fee_pct: number
  administration_fee_pct: number
  investment_option: string
  growth_defensive_split: string
  risk_level: string
  source_document_id: string | null
}

export type DocumentType = 'PDS' | 'Regulatory Guidance' | 'Legislation' | 'Fact Sheet'

export interface DocumentRecord {
  document_id: string
  title: string
  document_type: DocumentType
  source: string
  page_count: number | null
  published_date: string | null
  url: string | null
  full_text_excerpt: string
}

export interface AuditEvent {
  event_id: string
  timestamp: string
  session_id: string
  client_id: string | null
  case_id: string | null
  agent: string
  action: string
  model: string | null
  model_version: string | null
  prompt_version: string | null
  input_reference: string | null
  output_reference: string | null
  iteration: number
  status: 'success' | 'failure'
  details: string | null
}

export interface AdvisoryRecommendation {
  strategy_name: string
  product_id: string
  product_type: string
  allocation: string
  fee_percentage: number
  rationale: string
  assumptions: string[]
  risks: string[]
  source_documents: string[]
  disclosures: string[]
}

export type CaseStatus = 'PENDING' | 'IN_PROGRESS' | 'COMPLIANT' | 'WARNING' | 'REQUIRES_HUMAN_REVIEW' | 'REJECTED'

export interface AdvisoryCase {
  case_id: string
  client_id: string
  status: CaseStatus
  iteration_count: number
  recommendation: AdvisoryRecommendation | null
  created_at: string
  updated_at: string
}

export type ComplianceStatus = 'COMPLIANT' | 'WARNING' | 'REQUIRES_HUMAN_REVIEW' | 'REJECTED'

export interface ComplianceRuleResult {
  rule_id: string
  category: string
  passed: boolean
  is_warning: boolean
  detail: string
  evidence: string | null
}

export interface ComplianceResult {
  case_id: string
  status: ComplianceStatus
  rules_evaluated: number
  rules_passed: number
  rules_failed: number
  warnings: number
  rule_results: ComplianceRuleResult[]
  mandatory_disclosures: string[]
  engine_version: string
  validated_at: string
}

export interface StatementOfAdvice {
  case_id: string
  client_id: string
  generated_at: string
  executive_summary: string
  client_profile: ClientProfile
  objectives: string[]
  recommended_strategy: Record<string, unknown>
  compliance_verification: ComplianceResult
  disclosures: string[]
  is_demo_data: boolean
}

export type RetrievalMethod = 'dense' | 'bm25' | 'graph' | 'fused'

export interface RetrievedDocument {
  citation_id: string
  source: string
  document: string
  document_id: string
  page: number | null
  section: string | null
  snippet: string
  retrieval_method: RetrievalMethod
  rank: number
  rerank_score: number
  retrieval_sources: RetrievalMethod[]
  fusion_score: number | null
  graph_paths: string[]
}

export interface AdvisoryCaseDetail {
  case: AdvisoryCase
  request: string | null
  goal: string | null
  constraints: string[]
  retrieval_query: string | null
  graph_context: string[]
  critique_notes: string[]
  current_step: string | null
}

export interface RetrievalStatus {
  mode: 'hybrid' | 'mock'
  ready?: boolean
  dense?: string | null
  embedding_model?: string
  bm25?: string | null
  graph?: string | null
  reranker?: string | null
  fusion?: string
  chunks?: number
  errors?: Record<string, string>
}

export interface HealthStatus {
  status: string
  demo_mode: boolean
  llm_enabled: boolean
  llm_model: string | null
  llm_agents: string[]
  auth_enabled: boolean
  orchestrator: string
  max_iterations: number
  persistence: string
  retrieval: RetrievalStatus
  rate_limit_enabled: boolean
}

export type Role = 'advisor' | 'compliance_officer' | 'admin'

export interface AuthUser {
  user_id: string
  display_name: string
  role: Role
}

export interface TokenResponse {
  access_token: string
  token_type: string
  expires_at: string
  user: AuthUser
}

const API_BASE_URL: string = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8010'

class ApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

// The JWT lives in sessionStorage (cleared when the tab closes). It only ever
// authorises calls to this backend; no third-party credentials reach the browser.
const TOKEN_KEY = 'advisory.token'
const USER_KEY = 'advisory.user'

export const session = {
  token: (): string | null => sessionStorage.getItem(TOKEN_KEY),
  user: (): AuthUser | null => {
    const raw = sessionStorage.getItem(USER_KEY)
    return raw ? (JSON.parse(raw) as AuthUser) : null
  },
  save: (response: TokenResponse) => {
    sessionStorage.setItem(TOKEN_KEY, response.access_token)
    sessionStorage.setItem(USER_KEY, JSON.stringify(response.user))
  },
  clear: () => {
    sessionStorage.removeItem(TOKEN_KEY)
    sessionStorage.removeItem(USER_KEY)
  },
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const token = session.token()
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...init?.headers,
    },
  })
  if (response.status === 401 && path !== '/api/auth/login') {
    // Expired or invalid session: drop it and send the user to the sign-in page.
    session.clear()
    if (window.location.pathname !== '/login') {
      const next = encodeURIComponent(window.location.pathname + window.location.search)
      window.location.assign(`/login?next=${next}`)
    }
  }
  if (!response.ok) {
    const body = await response.text()
    throw new ApiError(response.status, body || response.statusText)
  }
  if (response.status === 204) return undefined as T
  return (await response.json()) as T
}

export const api = {
  health: () => request<HealthStatus>('/api/health'),

  login: (username: string, password: string) =>
    request<TokenResponse>('/api/auth/login', { method: 'POST', body: JSON.stringify({ username, password }) }),
  me: () => request<AuthUser>('/api/auth/me'),

  listClients: () => request<ClientProfile[]>('/api/clients'),
  getClient: (clientId: string) => request<ClientProfile>(`/api/clients/${clientId}`),

  getFactFind: (clientId: string) => request<FactFind>(`/api/fact-find/${clientId}`),
  submitFactFind: (clientId: string, updates: Record<string, unknown>) =>
    request<FactFind>('/api/fact-find', {
      method: 'POST',
      body: JSON.stringify({ client_id: clientId, updates }),
    }),

  listAdvisoryCases: () => request<AdvisoryCase[]>('/api/advisory'),
  getAdvisoryCase: (caseId: string) => request<AdvisoryCase>(`/api/advisory/${caseId}`),
  runAdvisory: (clientId: string, requestText?: string) =>
    request<AdvisoryCase>('/api/advisory/run', {
      method: 'POST',
      body: JSON.stringify({ client_id: clientId, ...(requestText ? { request: requestText } : {}) }),
    }),
  /** Queues the LangGraph pipeline in the background (202); follow it via advisoryStreamUrl. */
  startAdvisory: (clientId: string, requestText?: string) =>
    request<AdvisoryCase>('/api/advisory/start', {
      method: 'POST',
      body: JSON.stringify({ client_id: clientId, ...(requestText ? { request: requestText } : {}) }),
    }),
  getCaseDetail: (caseId: string) => request<AdvisoryCaseDetail>(`/api/advisory/${caseId}/detail`),
  getRetrieval: (caseId: string) => request<RetrievedDocument[]>(`/api/advisory/${caseId}/retrieval`),
  getPipelineGraph: () => request<{ mermaid: string }>('/api/advisory/graph'),

  getCompliance: (caseId: string) => request<ComplianceResult>(`/api/compliance/${caseId}`),

  listAuditEvents: () => request<AuditEvent[]>('/api/audit'),
  getAuditTrail: (caseId: string) => request<AuditEvent[]>(`/api/audit/${caseId}`),

  listProducts: () => request<Product[]>('/api/products'),

  listDocuments: () => request<DocumentRecord[]>('/api/documents'),
  getDocument: (documentId: string) => request<DocumentRecord>(`/api/documents/${documentId}`),

  generateReport: (caseId: string) =>
    request<StatementOfAdvice>(`/api/reports/${caseId}/generate`, { method: 'POST' }),
}

/** EventSource cannot set headers, so the stream authenticates with ?access_token=. */
export function advisoryStreamUrl(caseId: string): string {
  const token = session.token()
  const query = token ? `?access_token=${encodeURIComponent(token)}` : ''
  return `${API_BASE_URL}/api/advisory/${caseId}/stream${query}`
}

export { ApiError, API_BASE_URL }
