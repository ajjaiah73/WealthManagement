import { useState, type FormEvent } from 'react'
import { Navigate, useNavigate, useSearchParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Landmark, LogIn } from 'lucide-react'
import { api, ApiError } from '@/lib/api'
import { useAuth } from '@/lib/auth'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'

const DEMO_ACCOUNTS = [
  { username: 'advisor', password: 'advisor-demo', label: 'Financial Adviser', note: 'run advice, edit fact finds' },
  { username: 'compliance', password: 'compliance-demo', label: 'Compliance Officer', note: 'read-only review' },
  { username: 'admin', password: 'admin-demo', label: 'Administrator', note: 'full access' },
]

function safeNext(raw: string | null): string {
  // Only allow in-app relative paths to prevent open redirects.
  return raw && raw.startsWith('/') && !raw.startsWith('//') && !raw.startsWith('/login') ? raw : '/'
}

export function Login() {
  const { user, login } = useAuth()
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const next = safeNext(searchParams.get('next'))
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [pending, setPending] = useState(false)
  const { data: health } = useQuery({ queryKey: ['health'], queryFn: api.health, staleTime: 60_000 })

  if (user) return <Navigate to={next} replace />

  const submit = async (event: FormEvent) => {
    event.preventDefault()
    setPending(true)
    setError(null)
    try {
      await login(username, password)
      navigate(next, { replace: true })
    } catch (err) {
      if (err instanceof ApiError && err.status === 429) setError('Too many sign-in attempts. Please wait a minute.')
      else if (err instanceof ApiError && err.status === 401) setError('Invalid username or password.')
      else setError('Unable to reach the advisory API.')
    } finally {
      setPending(false)
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-50 p-6">
      <div className="w-full max-w-md space-y-4">
        <div className="flex items-center justify-center gap-2">
          <Landmark className="h-7 w-7 text-slate-900" />
          <div>
            <p className="text-base font-semibold leading-tight">Super Advisory</p>
            <p className="text-xs leading-tight text-slate-500">Intelligence Platform</p>
          </div>
        </div>
        <Card>
          <CardHeader>
            <CardTitle>Sign in</CardTitle>
            <CardDescription>Access is restricted to authorised advisory and compliance staff.</CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={submit} className="space-y-3">
              <div>
                <label htmlFor="username" className="mb-1 block text-xs font-medium uppercase tracking-wide text-slate-400">
                  Username
                </label>
                <Input id="username" autoComplete="username" value={username} onChange={(e) => setUsername(e.target.value)} required />
              </div>
              <div>
                <label htmlFor="password" className="mb-1 block text-xs font-medium uppercase tracking-wide text-slate-400">
                  Password
                </label>
                <Input
                  id="password"
                  type="password"
                  autoComplete="current-password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                />
              </div>
              {error && (
                <p role="alert" className="text-sm text-red-600">
                  {error}
                </p>
              )}
              <Button type="submit" className="w-full" disabled={pending || !username || !password}>
                <LogIn className="mr-2 h-4 w-4" />
                {pending ? 'Signing in…' : 'Sign in'}
              </Button>
            </form>
          </CardContent>
        </Card>

        {health?.demo_mode && (
          <Card>
            <CardHeader>
              <div className="flex items-center gap-2">
                <CardTitle className="text-sm">Demo accounts</CardTitle>
                <Badge variant="warning">DEMO MODE</Badge>
              </div>
              <CardDescription>Seeded only when DEMO_MODE is enabled.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-2">
              {DEMO_ACCOUNTS.map((account) => (
                <button
                  key={account.username}
                  type="button"
                  onClick={() => {
                    setUsername(account.username)
                    setPassword(account.password)
                  }}
                  className="flex w-full items-center justify-between rounded-md border border-slate-200 px-3 py-2 text-left text-sm hover:bg-slate-50"
                >
                  <span>
                    <span className="font-medium text-slate-900">{account.label}</span>
                    <span className="ml-2 text-xs text-slate-500">{account.note}</span>
                  </span>
                  <code className="text-xs text-slate-500">{account.username}</code>
                </button>
              ))}
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  )
}
