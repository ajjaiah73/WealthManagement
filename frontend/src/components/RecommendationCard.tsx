import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import type { AdvisoryRecommendation } from '@/lib/api'
import { formatPercent } from '@/lib/utils'

export function RecommendationCard({ recommendation }: { recommendation: AdvisoryRecommendation }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>{recommendation.strategy_name}</CardTitle>
        <CardDescription>
          {recommendation.product_id} · {recommendation.product_type} · Allocation {recommendation.allocation} ·
          Total fee {formatPercent(recommendation.fee_percentage)}
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div>
          <p className="text-xs font-medium uppercase tracking-wide text-slate-400">Rationale</p>
          <p className="text-sm text-slate-700">{recommendation.rationale}</p>
        </div>

        {recommendation.assumptions.length > 0 && (
          <div>
            <p className="text-xs font-medium uppercase tracking-wide text-slate-400">Assumptions</p>
            <ul className="mt-1 list-inside list-disc text-sm text-slate-700">
              {recommendation.assumptions.map((a) => (
                <li key={a}>{a}</li>
              ))}
            </ul>
          </div>
        )}

        {recommendation.risks.length > 0 && (
          <div>
            <p className="text-xs font-medium uppercase tracking-wide text-slate-400">Risks</p>
            <ul className="mt-1 list-inside list-disc text-sm text-slate-700">
              {recommendation.risks.map((r) => (
                <li key={r}>{r}</li>
              ))}
            </ul>
          </div>
        )}

        {recommendation.source_documents.length > 0 && (
          <div>
            <p className="text-xs font-medium uppercase tracking-wide text-slate-400">Source Documents</p>
            <div className="mt-1 flex flex-wrap gap-1.5">
              {recommendation.source_documents.map((d) => (
                <Badge key={d} variant="outline">
                  {d}
                </Badge>
              ))}
            </div>
          </div>
        )}

        {recommendation.disclosures.length > 0 && (
          <div>
            <p className="text-xs font-medium uppercase tracking-wide text-slate-400">Mandatory Disclosures</p>
            <ul className="mt-1 space-y-1 text-xs text-slate-500">
              {recommendation.disclosures.map((d) => (
                <li key={d}>{d}</li>
              ))}
            </ul>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
