import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from 'react'
import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { useQueryClient } from '@tanstack/react-query'
import { api, session, type AuthUser, type Role } from '@/lib/api'

interface AuthContextValue {
  user: AuthUser | null
  login: (username: string, password: string) => Promise<AuthUser>
  logout: () => void
  hasRole: (...roles: Role[]) => boolean
}

const AuthContext = createContext<AuthContextValue | null>(null)

export const ROLE_LABELS: Record<Role, string> = {
  advisor: 'Financial Adviser',
  compliance_officer: 'Compliance Officer',
  admin: 'Administrator',
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(() => (session.token() ? session.user() : null))
  const queryClient = useQueryClient()

  const login = useCallback(async (username: string, password: string) => {
    const response = await api.login(username, password)
    session.save(response)
    setUser(response.user)
    return response.user
  }, [])

  const logout = useCallback(() => {
    session.clear()
    queryClient.clear()
    setUser(null)
  }, [queryClient])

  const value = useMemo<AuthContextValue>(
    () => ({ user, login, logout, hasRole: (...roles) => !!user && roles.includes(user.role) }),
    [user, login, logout],
  )
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used inside <AuthProvider>')
  return ctx
}

/** Route guard: renders child routes only for a signed-in user. */
export function RequireAuth() {
  const { user } = useAuth()
  const location = useLocation()
  if (!user) {
    const next = encodeURIComponent(location.pathname + location.search)
    return <Navigate to={`/login?next=${next}`} replace />
  }
  return <Outlet />
}

/** Advisory runs and fact-find edits are restricted to advisers and admins (enforced server-side too). */
export function useCanAdvise(): boolean {
  return useAuth().hasRole('advisor', 'admin')
}
