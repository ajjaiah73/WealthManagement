import { NavLink, Outlet } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import {
  LayoutDashboard,
  Users,
  ClipboardList,
  Workflow,
  Activity,
  ShieldCheck,
  Package,
  FileText,
  FileBarChart,
  History,
  Settings as SettingsIcon,
  Landmark,
  LogOut,
  UserCircle2,
} from 'lucide-react'
import { api } from '@/lib/api'
import { ROLE_LABELS, useAuth } from '@/lib/auth'
import { cn } from '@/lib/utils'
import { Badge } from '@/components/ui/badge'

const NAV_ITEMS = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard, end: true },
  { to: '/clients', label: 'Clients', icon: Users },
  { to: '/fact-find', label: 'Fact Find', icon: ClipboardList },
  { to: '/advisory', label: 'Advisory Workspace', icon: Workflow },
  { to: '/agent-execution', label: 'Agent Execution', icon: Activity },
  { to: '/compliance', label: 'Compliance', icon: ShieldCheck },
  { to: '/products', label: 'Products', icon: Package },
  { to: '/documents', label: 'Documents', icon: FileText },
  { to: '/reports', label: 'Reports', icon: FileBarChart },
  { to: '/audit-trail', label: 'Audit Trail', icon: History },
  { to: '/settings', label: 'Settings', icon: SettingsIcon },
] as const

export function AppLayout() {
  const { data: health } = useQuery({ queryKey: ['health'], queryFn: api.health, staleTime: 60_000 })
  const { user, logout } = useAuth()

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-slate-50 text-slate-900">
      <aside className="flex w-64 shrink-0 flex-col border-r border-slate-200 bg-white">
        <div className="flex items-center gap-2 border-b border-slate-100 px-4 py-4">
          <Landmark className="h-6 w-6 text-slate-900" />
          <div>
            <p className="text-sm font-semibold leading-tight">Super Advisory</p>
            <p className="text-xs leading-tight text-slate-500">Intelligence Platform</p>
          </div>
        </div>
        <nav className="flex-1 space-y-0.5 overflow-y-auto px-2 py-3">
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={'end' in item ? item.end : false}
              className={({ isActive }) =>
                cn(
                  'flex items-center gap-2.5 rounded-md px-3 py-2 text-sm font-medium transition-colors',
                  isActive ? 'bg-slate-900 text-white' : 'text-slate-600 hover:bg-slate-100',
                )
              }
            >
              <item.icon className="h-4 w-4 shrink-0" />
              {item.label}
            </NavLink>
          ))}
        </nav>
        <div className="border-t border-slate-100 p-3 text-xs text-slate-400">
          Neuro-Symbolic Compliance Engine
          <br />
          Deterministic rules cannot be overridden by LLM output.
        </div>
      </aside>

      <div className="flex flex-1 flex-col overflow-hidden">
        <header className="flex h-14 shrink-0 items-center justify-between border-b border-slate-200 bg-white px-6">
          <p className="text-sm text-slate-500">Australian Superannuation Advisory &amp; Regulatory Compliance</p>
          <div className="flex items-center gap-2">
            {health?.demo_mode && (
              <Badge variant="warning" title="Synthetic client, product and document data">
                DEMO MODE
              </Badge>
            )}
            {health && (
              <Badge variant={health.llm_enabled ? 'success' : 'default'} title={health.llm_agents.join(', ')}>
                {health.llm_enabled ? `Claude ${health.llm_model}` : 'LLM fallback'}
              </Badge>
            )}
            <Badge variant={health ? 'success' : 'destructive'}>{health ? 'API Online' : 'API Unreachable'}</Badge>
            {user && (
              <div className="ml-3 flex items-center gap-2 border-l border-slate-200 pl-3">
                <UserCircle2 className="h-5 w-5 text-slate-400" />
                <div className="leading-tight">
                  <p className="text-sm font-medium text-slate-900">{user.display_name}</p>
                  <p className="text-xs text-slate-500">{ROLE_LABELS[user.role]}</p>
                </div>
                <button
                  type="button"
                  onClick={logout}
                  title="Sign out"
                  aria-label="Sign out"
                  className="ml-1 rounded-md p-1.5 text-slate-500 hover:bg-slate-100 hover:text-slate-900"
                >
                  <LogOut className="h-4 w-4" />
                </button>
              </div>
            )}
          </div>
        </header>
        <main className="flex-1 overflow-y-auto p-6">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
