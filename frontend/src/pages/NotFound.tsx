import { Link, useLocation } from 'react-router-dom'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'

export function NotFound() {
  const { pathname } = useLocation()

  return (
    <Card>
      <CardContent className="flex flex-col items-center gap-3 py-12 text-center">
        <p className="text-4xl font-semibold text-slate-300">404</p>
        <h1 className="text-lg font-semibold text-slate-900">Page not found</h1>
        <p className="text-sm text-slate-500">
          No section exists at <code className="rounded bg-slate-100 px-1">{pathname}</code>.
        </p>
        <Link to="/">
          <Button>Back to Dashboard</Button>
        </Link>
      </CardContent>
    </Card>
  )
}
