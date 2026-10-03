import { Link, useParams } from 'react-router-dom'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { CaseSelector } from '@/components/CaseSelector'
import { AgentTimeline } from '@/components/AgentTimeline'
import { useAgentStream } from '@/hooks/useAgentStream'

export function AgentExecution() {
  const { caseId } = useParams<{ caseId: string }>()
  const { events, streaming, error } = useAgentStream(caseId)

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-slate-900">Agent Execution</h1>
        <p className="text-sm text-slate-500">
          Live replay of the multi-agent pipeline: Intent &amp; Parameter Extraction → Hybrid RAG &amp; Market
          Context → Advisory Synthesis → Neuro-Symbolic Compliance Verification (with self-correction loop-back on
          failure, max 3 iterations).
        </p>
      </div>

      {!caseId && <CaseSelector basePath="/agent-execution" title="Select a Case" />}

      {caseId && (
        <>
          <Link to="/agent-execution" className="text-xs text-slate-500 hover:underline">
            ← Choose another case
          </Link>
          <Card>
            <CardHeader>
              <CardTitle>Execution Trace — {caseId}</CardTitle>
              <CardDescription>
                {error
                  ? 'Stream connection failed.'
                  : streaming
                    ? 'Streaming agent steps…'
                    : 'Replay complete.'}
              </CardDescription>
            </CardHeader>
            <CardContent>
              <AgentTimeline events={events} streaming={streaming} />
            </CardContent>
          </Card>
        </>
      )}
    </div>
  )
}
