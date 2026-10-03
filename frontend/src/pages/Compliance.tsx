import { Link, useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { CheckCircle2, XCircle, AlertTriangle } from 'lucide-react'
import { api } from '@/lib/api'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { CaseSelector } from '@/components/CaseSelector'
import { StatusBadge } from '@/components/StatusBadge'
import { formatDateTime } from '@/lib/utils'

export function Compliance() {
  const { caseId } = useParams<{ caseId: string }>()
  const { data, isLoading, isError } = useQuery({
    queryKey: ['compliance', caseId],
    queryFn: () => api.getCompliance(caseId!),
    enabled: !!caseId,
  })

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-slate-900">Compliance</h1>
        <p className="text-sm text-slate-500">
          Deterministic, Z3-backed rule verification. LLM output can never override a failed rule.
        </p>
      </div>

      {!caseId && <CaseSelector basePath="/compliance" title="Select a Case" />}

      {caseId && (
        <>
          <Link to="/compliance" className="text-xs text-slate-500 hover:underline">
            ← Choose another case
          </Link>

          {isLoading && <p className="text-sm text-slate-500">Loading compliance result…</p>}
          {isError && <p className="text-sm text-red-600">No compliance result found for this case.</p>}

          {data && (
            <>
              <Card>
                <CardHeader className="flex flex-row items-center justify-between">
                  <div>
                    <CardTitle>Case {data.case_id}</CardTitle>
                    <CardDescription>Validated {formatDateTime(data.validated_at)} · engine {data.engine_version}</CardDescription>
                  </div>
                  <StatusBadge status={data.status} />
                </CardHeader>
                <CardContent className="flex gap-6 text-sm text-slate-600">
                  <span>{data.rules_evaluated} rules evaluated</span>
                  <span className="text-emerald-700">{data.rules_passed} passed</span>
                  <span className="text-amber-700">{data.warnings} warnings</span>
                  <span className="text-red-700">{data.rules_failed} failed</span>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle>Rule-by-Rule Breakdown</CardTitle>
                </CardHeader>
                <CardContent className="p-0">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Rule</TableHead>
                        <TableHead>Category</TableHead>
                        <TableHead>Result</TableHead>
                        <TableHead>Detail</TableHead>
                        <TableHead>Evidence</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {data.rule_results.map((r) => (
                        <TableRow key={r.rule_id}>
                          <TableCell className="font-mono text-xs">{r.rule_id}</TableCell>
                          <TableCell>{r.category}</TableCell>
                          <TableCell>
                            <div className="flex items-center gap-1.5">
                              {r.is_warning ? (
                                <AlertTriangle className="h-4 w-4 text-amber-500" />
                              ) : r.passed ? (
                                <CheckCircle2 className="h-4 w-4 text-emerald-500" />
                              ) : (
                                <XCircle className="h-4 w-4 text-red-500" />
                              )}
                              {r.is_warning ? 'Warning' : r.passed ? 'Pass' : 'Fail'}
                            </div>
                          </TableCell>
                          <TableCell className="max-w-xs text-sm">{r.detail}</TableCell>
                          <TableCell className="max-w-xs text-xs text-slate-500">{r.evidence ?? '—'}</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </CardContent>
              </Card>

              {data.mandatory_disclosures.length > 0 && (
                <Card>
                  <CardHeader>
                    <CardTitle>Mandatory Disclosures</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <ul className="list-inside list-disc space-y-1 text-sm text-slate-700">
                      {data.mandatory_disclosures.map((d) => (
                        <li key={d}>{d}</li>
                      ))}
                    </ul>
                  </CardContent>
                </Card>
              )}
            </>
          )}
        </>
      )}
    </div>
  )
}
