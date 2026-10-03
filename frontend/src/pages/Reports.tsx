import { Link, useParams } from 'react-router-dom'
import { useMutation } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { CaseSelector } from '@/components/CaseSelector'
import { StatusBadge } from '@/components/StatusBadge'
import { formatDateTime } from '@/lib/utils'

export function Reports() {
  const { caseId } = useParams<{ caseId: string }>()

  const generateMutation = useMutation({
    mutationFn: () => api.generateReport(caseId!),
  })

  const report = generateMutation.data

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-slate-900">Reports</h1>
        <p className="text-sm text-slate-500">Generate a formatted Statement of Advice from a completed advisory case.</p>
      </div>

      {!caseId && <CaseSelector basePath="/reports" title="Select a Case" />}

      {caseId && (
        <>
          <Link to="/reports" className="text-xs text-slate-500 hover:underline">
            ← Choose another case
          </Link>

          {!report && (
            <Card>
              <CardContent className="flex items-center justify-between p-6">
                <p className="text-sm text-slate-600">No report generated yet for case {caseId}.</p>
                <Button onClick={() => generateMutation.mutate()} disabled={generateMutation.isPending}>
                  {generateMutation.isPending ? 'Generating…' : 'Generate Statement of Advice'}
                </Button>
              </CardContent>
            </Card>
          )}

          {generateMutation.isError && (
            <p className="text-sm text-red-600">Failed to generate report. Confirm the case has completed compliance verification.</p>
          )}

          {report && (
            <Card>
              <CardHeader className="flex flex-row items-center justify-between">
                <div>
                  <CardTitle>Statement of Advice — {report.case_id}</CardTitle>
                  <CardDescription>
                    Client {report.client_id} · Generated {formatDateTime(report.generated_at)}
                  </CardDescription>
                </div>
                <div className="flex items-center gap-2">
                  {report.is_demo_data && <Badge variant="warning">DEMO DATA</Badge>}
                  <StatusBadge status={report.compliance_verification.status} />
                </div>
              </CardHeader>
              <CardContent className="space-y-5">
                <div>
                  <p className="text-xs font-medium uppercase tracking-wide text-slate-400">Executive Summary</p>
                  <p className="text-sm text-slate-700">{report.executive_summary}</p>
                </div>

                <div>
                  <p className="text-xs font-medium uppercase tracking-wide text-slate-400">Objectives</p>
                  <ul className="mt-1 list-inside list-disc text-sm text-slate-700">
                    {report.objectives.map((o) => (
                      <li key={o}>{o}</li>
                    ))}
                  </ul>
                </div>

                <div>
                  <p className="text-xs font-medium uppercase tracking-wide text-slate-400">Recommended Strategy</p>
                  <pre className="mt-1 whitespace-pre-wrap rounded-md bg-slate-50 p-3 text-xs text-slate-700">
                    {JSON.stringify(report.recommended_strategy, null, 2)}
                  </pre>
                </div>

                <div>
                  <p className="text-xs font-medium uppercase tracking-wide text-slate-400">Compliance Verification</p>
                  <p className="text-sm text-slate-700">
                    {report.compliance_verification.rules_passed}/{report.compliance_verification.rules_evaluated} rules
                    passed, {report.compliance_verification.warnings} warnings, {report.compliance_verification.rules_failed} failed.
                  </p>
                </div>

                {report.disclosures.length > 0 && (
                  <div>
                    <p className="text-xs font-medium uppercase tracking-wide text-slate-400">Mandatory Disclosures</p>
                    <ul className="mt-1 space-y-1 text-xs text-slate-500">
                      {report.disclosures.map((d) => (
                        <li key={d}>{d}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </CardContent>
            </Card>
          )}
        </>
      )}
    </div>
  )
}
