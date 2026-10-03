import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { StatusBadge } from '@/components/StatusBadge'
import { Button } from '@/components/ui/button'
import { formatDateTime } from '@/lib/utils'

export function Dashboard() {
  const clientsQuery = useQuery({ queryKey: ['clients'], queryFn: api.listClients })
  const casesQuery = useQuery({ queryKey: ['advisory-cases'], queryFn: api.listAdvisoryCases })

  const cases = casesQuery.data ?? []
  const compliant = cases.filter((c) => c.status === 'COMPLIANT').length
  const warning = cases.filter((c) => c.status === 'WARNING').length
  const humanReview = cases.filter((c) => c.status === 'REQUIRES_HUMAN_REVIEW').length

  const tiles = [
    { label: 'Clients Onboarded', value: clientsQuery.data?.length ?? '—' },
    { label: 'Advisory Cases Run', value: cases.length },
    { label: 'Compliant Outcomes', value: compliant },
    { label: 'Requires Human Review', value: humanReview },
  ]

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-slate-900">Dashboard</h1>
        <p className="text-sm text-slate-500">
          Overview of client onboarding, advisory case outcomes, and compliance posture (demo data).
        </p>
      </div>

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        {tiles.map((tile) => (
          <Card key={tile.label}>
            <CardContent className="p-5">
              <p className="text-xs font-medium uppercase tracking-wide text-slate-500">{tile.label}</p>
              <p className="mt-2 text-2xl font-semibold text-slate-900">{tile.value}</p>
            </CardContent>
          </Card>
        ))}
        <Card className="col-span-2 lg:col-span-4 bg-amber-50/60 border-amber-200">
          <CardContent className="flex items-center justify-between p-5">
            <div>
              <p className="text-sm font-medium text-amber-800">Fee-Warning Cases</p>
              <p className="text-xs text-amber-700">
                {warning} case{warning === 1 ? '' : 's'} flagged for elevated fees requiring advisor attention.
              </p>
            </div>
            <span className="text-2xl font-semibold text-amber-800">{warning}</span>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>Recent Advisory Cases</CardTitle>
          <Link to="/advisory">
            <Button size="sm">Run New Advisory Case</Button>
          </Link>
        </CardHeader>
        <CardContent className="p-0">
          {cases.length === 0 ? (
            <p className="p-4 text-sm text-slate-500">
              No advisory cases have been run yet this session. Start one from the Advisory Workspace.
            </p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Case</TableHead>
                  <TableHead>Client</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Iterations</TableHead>
                  <TableHead>Updated</TableHead>
                  <TableHead />
                </TableRow>
              </TableHeader>
              <TableBody>
                {[...cases].reverse().map((c) => (
                  <TableRow key={c.case_id}>
                    <TableCell className="font-mono text-xs">{c.case_id}</TableCell>
                    <TableCell>
                      <Link to={`/clients/${c.client_id}`} className="text-slate-900 underline-offset-2 hover:underline">
                        {c.client_id}
                      </Link>
                    </TableCell>
                    <TableCell>
                      <StatusBadge status={c.status} />
                    </TableCell>
                    <TableCell>{c.iteration_count}</TableCell>
                    <TableCell>{formatDateTime(c.updated_at)}</TableCell>
                    <TableCell>
                      <Link to={`/compliance/${c.case_id}`} className="text-xs font-medium text-slate-600 hover:underline">
                        View compliance →
                      </Link>
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
