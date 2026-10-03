import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { GitBranch } from 'lucide-react'
import { api, type RetrievalMethod } from '@/lib/api'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'

const METHOD_LABELS: Record<RetrievalMethod, string> = {
  dense: 'Dense (Qdrant)',
  bm25: 'BM25',
  graph: 'Knowledge graph',
  fused: 'Fused',
}

/** Evidence the Hybrid RAG agent retrieved for a case: which retrievers found each
 * document, its RRF fusion score, cross-encoder rerank score and graph paths. */
export function RetrievedEvidence({ caseId, refreshKey }: { caseId: string; refreshKey?: unknown }) {
  const { data: docs, isLoading } = useQuery({
    queryKey: ['retrieval', caseId, refreshKey],
    queryFn: () => api.getRetrieval(caseId),
  })
  const { data: detail } = useQuery({
    queryKey: ['case-detail', caseId, refreshKey],
    queryFn: () => api.getCaseDetail(caseId),
  })

  return (
    <Card>
      <CardHeader>
        <CardTitle>Retrieved Evidence</CardTitle>
        <CardDescription>
          Hybrid retrieval: dense vectors + BM25 + knowledge graph, fused with Reciprocal Rank Fusion and reranked by
          a cross-encoder.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {detail && (detail.goal || detail.retrieval_query) && (
          <div className="space-y-1 rounded-md bg-slate-50 p-3 text-xs text-slate-600">
            {detail.goal && (
              <p>
                <span className="font-medium text-slate-700">Extracted goal:</span> {detail.goal}
              </p>
            )}
            {detail.constraints.length > 0 && (
              <p>
                <span className="font-medium text-slate-700">Constraints:</span> {detail.constraints.join('; ')}
              </p>
            )}
            {detail.retrieval_query && (
              <p>
                <span className="font-medium text-slate-700">Retrieval query:</span> {detail.retrieval_query}
              </p>
            )}
            {detail.graph_context.length > 0 && (
              <p>
                <span className="font-medium text-slate-700">Graph topics:</span> {detail.graph_context.join('; ')}
              </p>
            )}
          </div>
        )}
        {isLoading && <p className="text-sm text-slate-500">Loading evidence…</p>}
        {docs && docs.length === 0 && <p className="text-sm text-slate-500">Retrieval has not completed yet.</p>}
        <ol className="space-y-3">
          {(docs ?? []).map((doc) => (
            <li key={doc.citation_id} className="rounded-md border border-slate-200 p-3">
              <div className="flex flex-wrap items-center gap-2">
                <span className="text-xs font-semibold text-slate-400">#{doc.rank}</span>
                <Link to={`/documents?doc=${doc.document_id}`} className="text-sm font-medium text-slate-900 hover:underline">
                  {doc.document}
                </Link>
                <Badge variant="outline">{doc.document_id}</Badge>
                <Badge variant="default">{doc.source}</Badge>
              </div>
              <div className="mt-2 flex flex-wrap items-center gap-1.5">
                {doc.retrieval_sources.map((method) => (
                  <Badge key={method} variant={method === 'graph' ? 'purple' : method === 'dense' ? 'success' : 'warning'}>
                    {METHOD_LABELS[method]}
                  </Badge>
                ))}
                <span className="ml-auto text-xs text-slate-500">
                  rerank {doc.rerank_score.toFixed(3)}
                  {doc.fusion_score !== null && ` · RRF ${doc.fusion_score.toFixed(4)}`}
                </span>
              </div>
              <p className="mt-2 line-clamp-3 text-xs text-slate-600">{doc.snippet}</p>
              {doc.graph_paths.length > 0 && (
                <ul className="mt-2 space-y-0.5">
                  {doc.graph_paths.slice(0, 3).map((path) => (
                    <li key={path} className="flex items-center gap-1 text-xs text-violet-700">
                      <GitBranch className="h-3 w-3 shrink-0" />
                      <code>{path}</code>
                    </li>
                  ))}
                </ul>
              )}
            </li>
          ))}
        </ol>
      </CardContent>
    </Card>
  )
}
