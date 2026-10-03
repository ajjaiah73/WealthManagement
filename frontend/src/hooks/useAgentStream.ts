import { useEffect, useState } from 'react'
import { advisoryStreamUrl, type AdvisoryCase, type AuditEvent } from '@/lib/api'

interface AgentStreamState {
  events: AuditEvent[]
  streaming: boolean
  error: boolean
  finalCase: AdvisoryCase | null
}

/** Subscribes to a case's agent stream. While the LangGraph pipeline is running the
 * backend pushes one audit event per completed node (intent → retrieval → synthesis
 * → compliance → critique/escalate/narrate) as it happens; for a finished case it
 * replays the recorded trail. A final `done` event carries the terminal case. */
export function useAgentStream(caseId: string | undefined): AgentStreamState {
  const [events, setEvents] = useState<AuditEvent[]>([])
  const [streaming, setStreaming] = useState(true)
  const [error, setError] = useState(false)
  const [finalCase, setFinalCase] = useState<AdvisoryCase | null>(null)

  useEffect(() => {
    if (!caseId) return
    setEvents([])
    setStreaming(true)
    setError(false)
    setFinalCase(null)

    const source = new EventSource(advisoryStreamUrl(caseId))

    source.onmessage = (message) => {
      try {
        const event = JSON.parse(message.data) as AuditEvent
        setEvents((prev) => (prev.some((e) => e.event_id === event.event_id) ? prev : [...prev, event]))
      } catch {
        // ignore malformed keep-alive payloads
      }
    }
    source.addEventListener('done', (message) => {
      try {
        setFinalCase(JSON.parse((message as MessageEvent<string>).data) as AdvisoryCase)
      } catch {
        // terminal case is also available via GET /api/advisory/{id}
      }
      setStreaming(false)
      source.close()
    })
    source.addEventListener('timeout', () => {
      setStreaming(false)
      setError(true)
      source.close()
    })
    source.onerror = () => {
      setStreaming(false)
      setError(true)
      source.close()
    }

    return () => {
      source.close()
    }
  }, [caseId])

  return { events, streaming, error, finalCase }
}
