import { useQuery } from '@tanstack/react-query'
import { AlertTriangle, CheckCircle2 } from 'lucide-react'
import { api } from '@/lib/api'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Progress } from '@/components/ui/progress'
import { Badge } from '@/components/ui/badge'

const FIELD_LABELS: Record<string, string> = {
  age: 'Age',
  salary: 'Salary',
  super_balance: 'Super Balance',
  risk_tolerance: 'Risk Tolerance',
  target_retirement_age: 'Target Retirement Age',
  contribution_history: 'Contribution History',
  concessional_contributions_ytd: 'Concessional Contributions (YTD)',
  non_concessional_contributions_ytd: 'Non-Concessional Contributions (YTD)',
  ttr_intent: 'Transition-to-Retirement Intent',
  investment_objectives: 'Investment Objectives',
  financial_goals: 'Financial Goals',
  constraints: 'Constraints',
}

function formatFieldValue(value: unknown): string {
  if (value === null || value === undefined) return '—'
  if (Array.isArray(value)) return value.length ? value.join(', ') : '—'
  if (typeof value === 'boolean') return value ? 'Yes' : 'No'
  return String(value)
}

export function FactFindPanel({ clientId }: { clientId: string }) {
  const { data, isLoading, isError } = useQuery({
    queryKey: ['fact-find', clientId],
    queryFn: () => api.getFactFind(clientId),
  })

  if (isLoading) return <p className="text-sm text-slate-500">Loading fact find…</p>
  if (isError || !data) return <p className="text-sm text-red-600">Failed to load fact find.</p>

  const present = data.fields.filter((f) => f.status === 'present').length
  const completion = data.fields.length ? Math.round((present / data.fields.length) * 100) : 0

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle>Fact Find Completion</CardTitle>
            <CardDescription>
              Fields never silently assumed — missing information is always surfaced explicitly.
            </CardDescription>
          </div>
          <span className="text-lg font-semibold text-slate-900">{completion}%</span>
        </div>
        <Progress value={completion} className="mt-2" />
      </CardHeader>
      <CardContent>
        <ul className="divide-y divide-slate-100">
          {data.fields.map((field) => (
            <li key={field.field} className="flex items-center justify-between gap-4 py-2.5">
              <div className="flex items-center gap-2">
                {field.status === 'present' ? (
                  <CheckCircle2 className="h-4 w-4 shrink-0 text-emerald-500" />
                ) : (
                  <AlertTriangle className="h-4 w-4 shrink-0 text-amber-500" />
                )}
                <span className="text-sm font-medium text-slate-700">
                  {FIELD_LABELS[field.field] ?? field.field}
                </span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-sm text-slate-500">{formatFieldValue(field.value)}</span>
                {field.status === 'missing' && <Badge variant="warning">missing</Badge>}
              </div>
            </li>
          ))}
        </ul>
      </CardContent>
    </Card>
  )
}
