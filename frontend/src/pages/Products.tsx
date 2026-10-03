import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Select } from '@/components/ui/select'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { formatPercent } from '@/lib/utils'
import type { ProductType } from '@/lib/api'

const PRODUCT_TYPES: (ProductType | 'All')[] = ['All', 'MySuper', 'Choice', 'SMSF', 'TTR', 'Defined Benefit']

export function Products() {
  const { data: products, isLoading } = useQuery({ queryKey: ['products'], queryFn: api.listProducts })
  const [typeFilter, setTypeFilter] = useState<(ProductType | 'All')>('All')
  const [search, setSearch] = useState('')
  const [sortDesc, setSortDesc] = useState(false)

  const rows = useMemo(() => {
    const withFees = (products ?? []).map((p) => ({
      ...p,
      total_fee_pct: p.management_fee_pct + p.administration_fee_pct,
    }))
    const filtered = withFees.filter((p) => {
      if (typeFilter !== 'All' && p.product_type !== typeFilter) return false
      if (search && !p.product_name.toLowerCase().includes(search.toLowerCase())) return false
      return true
    })
    return filtered.sort((a, b) => (sortDesc ? b.total_fee_pct - a.total_fee_pct : a.total_fee_pct - b.total_fee_pct))
  }, [products, typeFilter, search, sortDesc])

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-slate-900">Products</h1>
        <p className="text-sm text-slate-500">Superannuation product catalogue sourced from ingested PDS documents.</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Filter</CardTitle>
          <CardDescription>{rows.length} of {products?.length ?? 0} products</CardDescription>
        </CardHeader>
        <CardContent className="flex flex-wrap gap-3">
          <Input
            placeholder="Search product name…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="max-w-xs"
          />
          <Select value={typeFilter} onChange={(e) => setTypeFilter(e.target.value as ProductType | 'All')} className="max-w-[10rem]">
            {PRODUCT_TYPES.map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </Select>
        </CardContent>
      </Card>

      <Card>
        <CardContent className="p-0">
          {isLoading ? (
            <p className="p-4 text-sm text-slate-500">Loading products…</p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Product</TableHead>
                  <TableHead>Type</TableHead>
                  <TableHead>Investment Option</TableHead>
                  <TableHead>Growth/Defensive</TableHead>
                  <TableHead>Risk</TableHead>
                  <TableHead
                    className="cursor-pointer select-none"
                    onClick={() => setSortDesc((v) => !v)}
                  >
                    Total Fee {sortDesc ? '↓' : '↑'}
                  </TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {rows.map((p) => (
                  <TableRow key={p.product_id}>
                    <TableCell className="font-medium text-slate-900">
                      {p.product_name}
                      <div className="font-mono text-xs text-slate-400">{p.product_id}</div>
                    </TableCell>
                    <TableCell>
                      <Badge variant="outline">{p.product_type}</Badge>
                    </TableCell>
                    <TableCell>{p.investment_option}</TableCell>
                    <TableCell>{p.growth_defensive_split}</TableCell>
                    <TableCell>{p.risk_level}</TableCell>
                    <TableCell>{formatPercent(p.total_fee_pct)}</TableCell>
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
