import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Select } from '@/components/ui/select'
import { Badge } from '@/components/ui/badge'
import { formatDateTime } from '@/lib/utils'

const AGENT_LABELS: Record<string, string> = {
  intent_agent: 'Intent & Parameter Extraction',
  retrieval_agent: 'Hybrid RAG & Market Context',
  advisory_synthesis_agent: 'Advisory Synthesis',
  compliance_agent: 'Compliance Verification',
}

export function AuditTrail() {
  const { data: events, isLoading } = useQuery({ queryKey: ['audit-events'], queryFn: api.listAuditEvents })
  const [agentFilter, setAgentFilter] = useState('All')
  const [statusFilter, setStatusFilter] = useState('All')

  const agents = useMemo(() => ['All', ...new Set((events ?? []).map((e) => e.agent))], [events])

  const filtered = useMemo(() => {
    return [...(events ?? [])]
      .reverse()
      .filter((e) => agentFilter === 'All' || e.agent === agentFilter)
      .filter((e) => statusFilter === 'All' || e.status === statusFilter)
  }, [events, agentFilter, statusFilter])

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-slate-900">Audit Trail</h1>
        <p className="text-sm text-slate-500">
          Immutable, timestamped log of every agent action across all cases — required for regulatory
          reproducibility.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Filters</CardTitle>
          <CardDescription>{filtered.length} of {events?.length ?? 0} events</CardDescription>
        </CardHeader>
        <CardContent className="flex flex-wrap gap-3">
          <Select value={agentFilter} onChange={(e) => setAgentFilter(e.target.value)} className="max-w-[16rem]">
            {agents.map((a) => (
              <option key={a} value={a}>
                {a === 'All' ? 'All Agents' : AGENT_LABELS[a] ?? a}
              </option>
            ))}
          </Select>
          <Select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)} className="max-w-[10rem]">
            <option value="All">All Statuses</option>
            <option value="success">Success</option>
            <option value="failure">Failure</option>
          </Select>
        </CardContent>
      </Card>

      <Card>
        <CardContent className="p-0">
          {isLoading ? (
            <p className="p-4 text-sm text-slate-500">Loading audit events…</p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Timestamp</TableHead>
                  <TableHead>Case</TableHead>
                  <TableHead>Agent</TableHead>
                  <TableHead>Action</TableHead>
                  <TableHead>Iteration</TableHead>
                  <TableHead>Status</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filtered.map((e) => (
                  <TableRow key={e.event_id}>
                    <TableCell className="whitespace-nowrap text-xs">{formatDateTime(e.timestamp)}</TableCell>
                    <TableCell className="font-mono text-xs">
                      {e.case_id ? (
                        <Link to={`/agent-execution/${e.case_id}`} className="text-slate-900 underline-offset-2 hover:underline">
                          {e.case_id}
                        </Link>
                      ) : (
                        '—'
                      )}
                    </TableCell>
                    <TableCell>{AGENT_LABELS[e.agent] ?? e.agent}</TableCell>
                    <TableCell>{e.action}</TableCell>
                    <TableCell>{e.iteration}</TableCell>
                    <TableCell>
                      <Badge variant={e.status === 'success' ? 'success' : 'destructive'}>{e.status}</Badge>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
