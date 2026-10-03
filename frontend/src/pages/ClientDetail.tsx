import type { ReactNode } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { FactFindPanel } from '@/components/FactFindPanel'
import { formatCurrency } from '@/lib/utils'

function Field({ label, value }: { label: string; value: ReactNode }) {
  return (
    <div>
      <p className="text-xs font-medium uppercase tracking-wide text-slate-400">{label}</p>
      <p className="text-sm text-slate-900">{value ?? '—'}</p>
    </div>
  )
}

export function ClientDetail() {
  const { clientId } = useParams<{ clientId: string }>()
  const navigate = useNavigate()
  const { data: client, isLoading, isError } = useQuery({
    queryKey: ['client', clientId],
    queryFn: () => api.getClient(clientId!),
    enabled: !!clientId,
  })

  if (isLoading) return <p className="text-sm text-slate-500">Loading client…</p>
  if (isError || !client) return <p className="text-sm text-red-600">Client not found.</p>

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <Link to="/clients" className="text-xs text-slate-500 hover:underline">
            ← Back to Clients
          </Link>
          <h1 className="text-xl font-semibold text-slate-900">
            {client.first_name} {client.last_name}
          </h1>
          <p className="text-sm text-slate-500">{client.client_id}</p>
        </div>
        <Button onClick={() => navigate(`/advisory?clientId=${client.client_id}`)}>Start Advisory Case</Button>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Client Profile</CardTitle>
          </CardHeader>
          <CardContent className="grid grid-cols-2 gap-4">
            <Field label="Age" value={client.age} />
            <Field label="Salary" value={formatCurrency(client.salary)} />
            <Field label="Super Balance" value={formatCurrency(client.super_balance)} />
            <Field label="Target Retirement Age" value={client.target_retirement_age} />
            <Field
              label="Risk Tolerance"
              value={client.risk_tolerance ? <Badge variant="outline">{client.risk_tolerance}</Badge> : undefined}
            />
            <Field label="TTR Intent" value={client.ttr_intent === null ? undefined : client.ttr_intent ? 'Yes' : 'No'} />
            <Field label="Concessional Contributions (YTD)" value={formatCurrency(client.concessional_contributions_ytd)} />
            <Field
              label="Non-Concessional Contributions (YTD)"
              value={formatCurrency(client.non_concessional_contributions_ytd)}
            />
            <Field label="Advisory Status" value={client.advisory_status} />
            <Field label="Compliance Status" value={client.compliance_status} />
            <Field label="Last Review" value={client.last_review_date} />
            <div className="col-span-2">
              <Field label="Financial Goals" value={client.financial_goals.join(', ') || undefined} />
            </div>
            <div className="col-span-2">
              <Field label="Investment Objectives" value={client.investment_objectives.join(', ') || undefined} />
            </div>
            <div className="col-span-2">
              <Field label="Constraints" value={client.constraints.join(', ') || undefined} />
            </div>
          </CardContent>
        </Card>

        <FactFindPanel clientId={client.client_id} />
      </div>
    </div>
  )
}
