import { Badge } from '@/components/ui/badge'
import type { CaseStatus, ComplianceStatus } from '@/lib/api'

const STATUS_CONFIG: Record<CaseStatus | ComplianceStatus, { label: string; variant: 'success' | 'warning' | 'destructive' | 'purple' | 'default' }> = {
  PENDING: { label: 'Pending', variant: 'default' },
  IN_PROGRESS: { label: 'In Progress', variant: 'default' },
  COMPLIANT: { label: 'Compliant', variant: 'success' },
  WARNING: { label: 'Warning', variant: 'warning' },
  REQUIRES_HUMAN_REVIEW: { label: 'Requires Human Review', variant: 'purple' },
  REJECTED: { label: 'Rejected', variant: 'destructive' },
}

export function StatusBadge({ status, className }: { status: CaseStatus | ComplianceStatus; className?: string }) {
  const config = STATUS_CONFIG[status] ?? { label: status, variant: 'default' as const }
  return (
    <Badge variant={config.variant} className={className}>
      {config.label}
    </Badge>
  )
}
