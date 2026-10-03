import { useQuery } from '@tanstack/react-query'
import { api, API_BASE_URL } from '@/lib/api'
import { ROLE_LABELS, useAuth } from '@/lib/auth'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Separator } from '@/components/ui/separator'

function ConfigList({ items }: { items: { label: string; value: string }[] }) {
  return (
    <ul className="divide-y divide-slate-100">
      {items.map((item, i) => (
        <li key={item.label}>
          {i > 0 && <Separator className="mb-3" />}
          <div className="flex items-center justify-between gap-4 py-1">
            <span className="text-sm font-medium text-slate-700">{item.label}</span>
            <span className="text-right text-sm text-slate-500">{item.value}</span>
          </div>
        </li>
      ))}
    </ul>
  )
}

export function Settings() {
  const { data: health, isError } = useQuery({ queryKey: ['health'], queryFn: api.health })
  const { user } = useAuth()
  const retrieval = health?.retrieval
  const retrievalErrors = Object.entries(retrieval?.errors ?? {})

  const runtime = health
    ? [
        { label: 'Orchestrator', value: health.orchestrator === 'langgraph' ? 'LangGraph StateGraph' : health.orchestrator },
        { label: 'Max Self-Correction Iterations', value: String(health.max_iterations) },
        { label: 'Compliance Engine', value: 'Deterministic Pydantic rules + Z3 SMT solver (authoritative)' },
        {
          label: 'LLM Agents',
          value: health.llm_enabled
            ? `${health.llm_model} — ${health.llm_agents.join(', ')}`
            : 'Disabled — deterministic fallback for every agent',
        },
        { label: 'Persistence', value: health.persistence },
        { label: 'Authentication', value: health.auth_enabled ? 'JWT bearer tokens, role-based access' : 'Disabled' },
        { label: 'Rate Limiting', value: health.rate_limit_enabled ? 'Enabled' : 'Disabled' },
      ]
    : []

  const retrievalItems =
    retrieval?.mode === 'hybrid'
      ? [
          { label: 'Dense Vector Store', value: retrieval.dense ?? 'unavailable' },
          { label: 'Embedding Model', value: retrieval.embedding_model ?? 'unavailable' },
          { label: 'Sparse (Lexical)', value: retrieval.bm25 ?? 'unavailable' },
          { label: 'Knowledge Graph', value: retrieval.graph ?? 'unavailable' },
          { label: 'Fusion', value: retrieval.fusion ?? 'unavailable' },
          { label: 'Cross-Encoder Reranker', value: retrieval.reranker ?? 'unavailable' },
          { label: 'Indexed Chunks', value: String(retrieval.chunks ?? 0) },
        ]
      : [{ label: 'Mode', value: 'Keyword mock retriever (RETRIEVAL_BACKEND=mock)' }]

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-slate-900">Settings</h1>
        <p className="text-sm text-slate-500">Read-only view of the backends this deployment is actually running.</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>API Status</CardTitle>
          <CardDescription>{API_BASE_URL}</CardDescription>
        </CardHeader>
        <CardContent className="flex flex-wrap items-center gap-3">
          <Badge variant={isError ? 'destructive' : 'success'}>{isError ? 'Unreachable' : health?.status ?? 'Unknown'}</Badge>
          {health?.demo_mode && <Badge variant="warning">DEMO MODE — synthetic clients, products &amp; documents</Badge>}
          <Badge variant={health?.llm_enabled ? 'success' : 'default'}>
            {health?.llm_enabled ? `LLM Live: Claude ${health.llm_model}` : 'LLM: deterministic fallback'}
          </Badge>
          {user && (
            <Badge variant="outline">
              Signed in as {user.display_name} ({ROLE_LABELS[user.role]})
            </Badge>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Runtime Configuration</CardTitle>
          <CardDescription>
            LLM output is advisory only: the deterministic compliance engine has the final say and failed rules can
            never be overridden.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <ConfigList items={runtime} />
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle>Hybrid Retrieval</CardTitle>
            <CardDescription>Dense + BM25 + graph retrieval, fused with RRF and reranked.</CardDescription>
          </div>
          {retrieval?.mode === 'hybrid' && (
            <Badge variant={retrieval.ready ? 'success' : 'warning'}>{retrieval.ready ? 'Ready' : 'Degraded'}</Badge>
          )}
        </CardHeader>
        <CardContent className="space-y-3">
          <ConfigList items={retrievalItems} />
          {retrievalErrors.length > 0 && (
            <ul className="space-y-1 rounded-md bg-red-50 p-3 text-xs text-red-700">
              {retrievalErrors.map(([component, message]) => (
                <li key={component}>
                  <span className="font-medium">{component}:</span> {message}
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
