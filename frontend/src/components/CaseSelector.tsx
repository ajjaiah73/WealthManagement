import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Select } from '@/components/ui/select'
import { Button } from '@/components/ui/button'
import { StatusBadge } from '@/components/StatusBadge'

export function CaseSelector({ basePath, title }: { basePath: string; title: string }) {
  const { data: cases, isLoading } = useQuery({ queryKey: ['advisory-cases'], queryFn: api.listAdvisoryCases })
  const navigate = useNavigate()
  const [selected, setSelected] = useState('')

  const options = [...(cases ?? [])].reverse()
  const active = selected || options[0]?.case_id || ''

  if (isLoading) return <p className="text-sm text-slate-500">Loading cases…</p>

  if (options.length === 0) {
    return (
      <Card>
        <CardContent className="p-6 text-sm text-slate-500">
          No advisory cases have been run yet this session. Run one from the{' '}
          <a href="/advisory" className="text-slate-900 underline">
            Advisory Workspace
          </a>{' '}
          first.
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
        <CardDescription>Select an advisory case to inspect.</CardDescription>
      </CardHeader>
      <CardContent className="flex flex-wrap items-center gap-3">
        <Select value={active} onChange={(e) => setSelected(e.target.value)} className="max-w-sm">
          {options.map((c) => (
            <option key={c.case_id} value={c.case_id}>
              {c.case_id} — {c.client_id} ({c.status})
            </option>
          ))}
        </Select>
        {active && <StatusBadge status={options.find((c) => c.case_id === active)!.status} />}
        <Button size="sm" onClick={() => navigate(`${basePath}/${active}`)} disabled={!active}>
          View
        </Button>
      </CardContent>
    </Card>
  )
}
