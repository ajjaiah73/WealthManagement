import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { Card, CardContent } from '@/components/ui/card'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { formatCurrency } from '@/lib/utils'

export function Clients() {
  const { data, isLoading, isError } = useQuery({ queryKey: ['clients'], queryFn: api.listClients })
  const [search, setSearch] = useState('')

  const filtered = useMemo(() => {
    if (!data) return []
    const term = search.trim().toLowerCase()
    if (!term) return data
    return data.filter(
      (c) =>
        c.client_id.toLowerCase().includes(term) ||
        `${c.first_name} ${c.last_name}`.toLowerCase().includes(term),
    )
  }, [data, search])

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-slate-900">Clients</h1>
          <p className="text-sm text-slate-500">{data?.length ?? 0} clients onboarded (demo data).</p>
        </div>
        <Input
          placeholder="Search by name or client ID…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="w-72"
        />
      </div>

      <Card>
        <CardContent className="p-0">
          {isLoading && <p className="p-4 text-sm text-slate-500">Loading clients…</p>}
          {isError && <p className="p-4 text-sm text-red-600">Failed to load clients.</p>}
          {data && (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Client</TableHead>
                  <TableHead>Age</TableHead>
                  <TableHead>Super Balance</TableHead>
                  <TableHead>Risk Tolerance</TableHead>
                  <TableHead>Advisory Status</TableHead>
                  <TableHead>Compliance</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filtered.map((client) => (
                  <TableRow key={client.client_id}>
                    <TableCell>
                      <Link to={`/clients/${client.client_id}`} className="font-medium text-slate-900 hover:underline">
                        {client.first_name} {client.last_name}
                      </Link>
                      <p className="text-xs text-slate-400">{client.client_id}</p>
                    </TableCell>
                    <TableCell>{client.age ?? '—'}</TableCell>
                    <TableCell>{formatCurrency(client.super_balance)}</TableCell>
                    <TableCell>
                      {client.risk_tolerance ? <Badge variant="outline">{client.risk_tolerance}</Badge> : '—'}
                    </TableCell>
                    <TableCell>{client.advisory_status}</TableCell>
                    <TableCell>{client.compliance_status ?? '—'}</TableCell>
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
