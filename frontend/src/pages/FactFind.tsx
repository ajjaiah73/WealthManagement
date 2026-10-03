import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Select } from '@/components/ui/select'
import { FactFindPanel } from '@/components/FactFindPanel'

export function FactFind() {
  const { data: clients } = useQuery({ queryKey: ['clients'], queryFn: api.listClients })
  const [clientId, setClientId] = useState<string>('')

  const selected = clientId || clients?.[0]?.client_id || ''

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-slate-900">Fact Find</h1>
        <p className="text-sm text-slate-500">
          The Intent &amp; Parameter Extraction Agent never silently assumes missing information — every gap is
          surfaced explicitly here.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Select Client</CardTitle>
          <CardDescription>Choose a client to view their fact-find completeness.</CardDescription>
        </CardHeader>
        <CardContent>
          <Select value={selected} onChange={(e) => setClientId(e.target.value)} className="max-w-sm">
            {(clients ?? []).map((c) => (
              <option key={c.client_id} value={c.client_id}>
                {c.first_name} {c.last_name} ({c.client_id})
              </option>
            ))}
          </Select>
        </CardContent>
      </Card>

      {selected && <FactFindPanel clientId={selected} />}
    </div>
  )
}
