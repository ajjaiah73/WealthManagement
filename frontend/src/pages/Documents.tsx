import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { formatDateTime } from '@/lib/utils'

export function Documents() {
  const { data: documents, isLoading } = useQuery({ queryKey: ['documents'], queryFn: api.listDocuments })
  const [search, setSearch] = useState('')
  const [selectedId, setSelectedId] = useState<string | null>(null)

  const filtered = useMemo(
    () => (documents ?? []).filter((d) => d.title.toLowerCase().includes(search.toLowerCase())),
    [documents, search],
  )

  const selected = documents?.find((d) => d.document_id === selectedId) ?? null

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-slate-900">Documents</h1>
        <p className="text-sm text-slate-500">
          Corpus of PDS, regulatory guidance, legislation, and fact sheets backing hybrid retrieval.
        </p>
      </div>

      <Card>
        <CardContent className="p-4">
          <Input
            placeholder="Search document title…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="max-w-sm"
          />
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Document Corpus</CardTitle>
            <CardDescription>{filtered.length} of {documents?.length ?? 0} documents</CardDescription>
          </CardHeader>
          <CardContent className="p-0">
            {isLoading ? (
              <p className="p-4 text-sm text-slate-500">Loading documents…</p>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Title</TableHead>
                    <TableHead>Type</TableHead>
                    <TableHead>Source</TableHead>
                    <TableHead>Published</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filtered.map((d) => (
                    <TableRow
                      key={d.document_id}
                      className="cursor-pointer"
                      onClick={() => setSelectedId(d.document_id)}
                    >
                      <TableCell className="font-medium text-slate-900">{d.title}</TableCell>
                      <TableCell>
                        <Badge variant="outline">{d.document_type}</Badge>
                      </TableCell>
                      <TableCell>{d.source}</TableCell>
                      <TableCell>{d.published_date ?? '—'}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Detail</CardTitle>
            <CardDescription>Select a document to view its excerpt.</CardDescription>
          </CardHeader>
          <CardContent>
            {!selected && <p className="text-sm text-slate-500">No document selected.</p>}
            {selected && (
              <div className="space-y-3">
                <div>
                  <p className="text-xs font-medium uppercase tracking-wide text-slate-400">Title</p>
                  <p className="text-sm font-semibold text-slate-900">{selected.title}</p>
                </div>
                <div className="flex gap-4 text-xs text-slate-500">
                  <span>{selected.document_type}</span>
                  <span>{selected.page_count ? `${selected.page_count} pages` : ''}</span>
                  <span>{formatDateTime(selected.published_date)}</span>
                </div>
                <div>
                  <p className="text-xs font-medium uppercase tracking-wide text-slate-400">Excerpt</p>
                  <p className="text-sm text-slate-700">{selected.full_text_excerpt}</p>
                </div>
                {selected.url && (
                  <a href={selected.url} target="_blank" rel="noreferrer" className="text-xs text-slate-900 underline">
                    Source URL
                  </a>
                )}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
