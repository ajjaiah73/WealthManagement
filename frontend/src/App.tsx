import { Routes, Route } from 'react-router-dom'
import { AppLayout } from '@/components/layout/AppLayout'
import { RequireAuth } from '@/lib/auth'
import { Login } from '@/pages/Login'
import { Dashboard } from '@/pages/Dashboard'
import { Clients } from '@/pages/Clients'
import { ClientDetail } from '@/pages/ClientDetail'
import { FactFind } from '@/pages/FactFind'
import { Advisory } from '@/pages/Advisory'
import { AgentExecution } from '@/pages/AgentExecution'
import { Compliance } from '@/pages/Compliance'
import { Products } from '@/pages/Products'
import { Documents } from '@/pages/Documents'
import { Reports } from '@/pages/Reports'
import { AuditTrail } from '@/pages/AuditTrail'
import { Settings } from '@/pages/Settings'
import { NotFound } from '@/pages/NotFound'

function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route element={<RequireAuth />}>
        <Route element={<AppLayout />}>
          <Route path="/" element={<Dashboard />} />
          <Route path="/clients" element={<Clients />} />
          <Route path="/clients/:clientId" element={<ClientDetail />} />
          <Route path="/fact-find" element={<FactFind />} />
          <Route path="/advisory" element={<Advisory />} />
          <Route path="/advisory/:caseId" element={<Advisory />} />
          <Route path="/agent-execution" element={<AgentExecution />} />
          <Route path="/agent-execution/:caseId" element={<AgentExecution />} />
          <Route path="/compliance" element={<Compliance />} />
          <Route path="/compliance/:caseId" element={<Compliance />} />
          <Route path="/products" element={<Products />} />
          <Route path="/documents" element={<Documents />} />
          <Route path="/reports" element={<Reports />} />
          <Route path="/reports/:caseId" element={<Reports />} />
          <Route path="/audit-trail" element={<AuditTrail />} />
          <Route path="/settings" element={<Settings />} />
          <Route path="*" element={<NotFound />} />
        </Route>
      </Route>
    </Routes>
  )
}

export default App
