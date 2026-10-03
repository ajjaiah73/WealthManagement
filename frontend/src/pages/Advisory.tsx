import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Select } from '@/components/ui/select'
import { Textarea } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { StatusBadge } from '@/components/StatusBadge'
import { RecommendationCard } from '@/components/RecommendationCard'
import { AgentTimeline } from '@/components/AgentTimeline'
import { RetrievedEvidence } from '@/components/RetrievedEvidence'
import { useAgentStream } from '@/hooks/useAgentStream'
import { useCanAdvise } from '@/lib/auth'
import { Loader2 } from 'lucide-react'

export function Advisory() {
  const { caseId } = useParams<{ caseId: string }>()
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  const { data: clients } = useQuery({ queryKey: ['clients'], queryFn: api.listClients })
  const [clientId, setClientId] = useState(searchParams.get('clientId') ?? '')
  const [requestText, setRequestText] = useState('Recommend a superannuation strategy')

  useEffect(() => {
    if (!clientId && clients?.length) setClientId(clients[0].client_id)
  }, [clients, clientId])

  const canAdvise = useCanAdvise()
  const { events, streaming, finalCase } = useAgentStream(caseId)

  // Re-read the case each time a pipeline node completes so the status, iteration
  // count and current draft recommendation track the live LangGraph run.
  const caseQuery = useQuery({
    queryKey: ['advisory-case', caseId, events.length],
    queryFn: () => api.getAdvisoryCase(caseId!),
    enabled: !!caseId,
    placeholderData: (previous) => previous,
  })
  const detailQuery = useQuery({
    queryKey: ['case-detail', caseId, events.length],
    queryFn: () => api.getCaseDetail(caseId!),
    enabled: !!caseId,
    placeholderData: (previous) => previous,
  })

  useEffect(() => {
    if (finalCase) {
      queryClient.invalidateQueries({ queryKey: ['advisory-cases'] })
      queryClient.invalidateQueries({ queryKey: ['audit'] })
    }
  }, [finalCase, queryClient])

  const runMutation = useMutation({
    mutationFn: () => api.startAdvisory(clientId, requestText),
    onSuccess: (started) => {
      queryClient.invalidateQueries({ queryKey: ['advisory-cases'] })
      navigate(`/advisory/${started.case_id}`)
    },
  })

  const activeCase = finalCase ?? caseQuery.data
  const detail = detailQuery.data
  const inProgress = activeCase?.status === 'IN_PROGRESS'

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-slate-900">Advisory Workspace</h1>
        <p className="text-sm text-slate-500">
          Runs the synthesis → deterministic compliance verification → self-correction pipeline (max 3 iterations).
        </p>
      </div>

      {!caseId && (
        <Card>
          <CardHeader>
            <CardTitle>Run a New Advisory Case</CardTitle>
            <CardDescription>Select a client and describe the advice request.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <p className="mb-1 text-xs font-medium uppercase tracking-wide text-slate-400">Client</p>
              <Select value={clientId} onChange={(e) => setClientId(e.target.value)} className="max-w-sm">
                {(clients ?? []).map((c) => (
                  <option key={c.client_id} value={c.client_id}>
                    {c.first_name} {c.last_name} ({c.client_id})
                  </option>
                ))}
              </Select>
            </div>
            <div>
              <p className="mb-1 text-xs font-medium uppercase tracking-wide text-slate-400">Request</p>
              <Textarea value={requestText} onChange={(e) => setRequestText(e.target.value)} rows={3} />
            </div>
            {runMutation.isError && (
              <p className="text-sm text-red-600">Failed to start advisory case. Please try again.</p>
            )}
            {!canAdvise && (
              <p className="text-sm text-amber-700">
                Your role is read-only: only advisers and administrators can run advisory cases.
              </p>
            )}
            <Button onClick={() => runMutation.mutate()} disabled={!canAdvise || !clientId || runMutation.isPending}>
              {runMutation.isPending ? 'Starting Agent Pipeline…' : 'Run Advisory Case'}
            </Button>
          </CardContent>
        </Card>
      )}

      {caseId && (
        <>
          <Link to="/advisory" className="text-xs text-slate-500 hover:underline">
            ← Run another case
          </Link>

          {caseQuery.isLoading && <p className="text-sm text-slate-500">Loading case…</p>}
          {caseQuery.isError && <p className="text-sm text-red-600">Advisory case not found.</p>}

          {activeCase && (
            <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
              <div className="space-y-4">
                <Card>
                  <CardHeader className="flex flex-row items-center justify-between">
                    <div>
                      <CardTitle>Case {activeCase.case_id}</CardTitle>
                      <CardDescription>Client {activeCase.client_id}</CardDescription>
                    </div>
                    <div className="flex items-center gap-2">
                      <StatusBadge status={activeCase.status} />
                    </div>
                  </CardHeader>
                  <CardContent className="space-y-3 text-sm text-slate-600">
                    <div className="flex flex-wrap items-center gap-6">
                      <span>Iterations: {activeCase.iteration_count}</span>
                      {inProgress ? (
                        <span className="flex items-center gap-1.5 text-blue-700">
                          <Loader2 className="h-4 w-4 animate-spin" />
                          Running{detail?.current_step ? ` — last completed step: ${detail.current_step}` : '…'}
                        </span>
                      ) : (
                        <>
                          <Link to={`/compliance/${activeCase.case_id}`} className="text-slate-900 underline-offset-2 hover:underline">
                            View compliance detail →
                          </Link>
                          <Link to={`/reports/${activeCase.case_id}`} className="text-slate-900 underline-offset-2 hover:underline">
                            Generate report →
                          </Link>
                        </>
                      )}
                    </div>
                    {detail?.request && (
                      <p className="text-xs text-slate-500">
                        <span className="font-medium text-slate-700">Request:</span> {detail.request}
                      </p>
                    )}
                    {detail && detail.critique_notes.length > 0 && (
                      <div className="rounded-md border border-amber-200 bg-amber-50 p-3 text-xs text-amber-900">
                        <p className="mb-1 font-medium">Compliance critique fed back to synthesis</p>
                        <ul className="list-disc space-y-0.5 pl-4">
                          {detail.critique_notes.map((note, i) => (
                            <li key={i}>{note}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </CardContent>
                </Card>

                {activeCase.recommendation && <RecommendationCard recommendation={activeCase.recommendation} />}
              </div>

              <div className="space-y-4">
                <Card>
                  <CardHeader>
                    <CardTitle>Agent Execution Trace</CardTitle>
                    <CardDescription>
                      {streaming
                        ? 'Streaming LangGraph node completions live.'
                        : 'Recorded audit trail for this case.'}
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <AgentTimeline events={events} streaming={streaming} />
                  </CardContent>
                </Card>
                <RetrievedEvidence caseId={activeCase.case_id} refreshKey={inProgress ? events.length : 'final'} />
              </div>
            </div>
          )}
        </>
      )}
    </div>
  )
}
