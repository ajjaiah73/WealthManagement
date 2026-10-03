import { CheckCircle2, XCircle, Loader2 } from 'lucide-react'
import type { AuditEvent } from '@/lib/api'
import { formatDateTime } from '@/lib/utils'
import { Badge } from '@/components/ui/badge'

const AGENT_LABELS: Record<string, string> = {
  intent_agent: 'Intent & Parameter Extraction',
  retrieval_agent: 'Hybrid RAG & Market Context',
  advisory_synthesis_agent: 'Advisory Synthesis',
  compliance_agent: 'Neuro-Symbolic Compliance Verification',
}

export function AgentTimeline({ events, streaming }: { events: AuditEvent[]; streaming?: boolean }) {
  if (events.length === 0) {
    return <p className="text-sm text-slate-500">No agent activity recorded for this case yet.</p>
  }

  return (
    <ol className="relative space-y-0">
      {events.map((event, index) => {
        const isLast = index === events.length - 1
        const failed = event.status === 'failure'
        return (
          <li key={event.event_id} className="relative flex gap-3 pb-6 last:pb-0">
            {!isLast && <span className="absolute left-[11px] top-6 h-full w-px bg-slate-200" />}
            <span className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full border bg-white">
              {failed ? (
                <XCircle className="h-4 w-4 text-red-500" />
              ) : (
                <CheckCircle2 className="h-4 w-4 text-emerald-500" />
              )}
            </span>
            <div className="flex-1 pt-0.5">
              <div className="flex flex-wrap items-center gap-2">
                <span className="text-sm font-semibold text-slate-900">
                  {AGENT_LABELS[event.agent] ?? event.agent}
                </span>
                <Badge variant="outline">{event.action}</Badge>
                <Badge variant="outline">iteration {event.iteration}</Badge>
                {failed && <Badge variant="destructive">failure</Badge>}
              </div>
              <p className="mt-1 text-xs text-slate-500">{formatDateTime(event.timestamp)}</p>
              {event.details && <p className="mt-1 text-sm text-slate-600">{event.details}</p>}
              {event.case_id && (
                <p className="mt-1 text-xs text-slate-400">
                  case {event.case_id} {event.client_id ? `· client ${event.client_id}` : ''}
                </p>
              )}
            </div>
          </li>
        )
      })}
      {streaming && (
        <li className="flex items-center gap-2 pt-1 text-xs text-slate-400">
          <Loader2 className="h-3.5 w-3.5 animate-spin" /> streaming…
        </li>
      )}
    </ol>
  )
}
