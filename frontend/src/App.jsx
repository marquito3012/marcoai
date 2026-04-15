import { useEffect } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'

import AppShell       from './components/layout/AppShell.jsx'
import CalendarPage   from './pages/CalendarPage.jsx'
import FinancePage    from './pages/FinancePage.jsx'
import LoginPage      from './pages/LoginPage.jsx'
import ChatPage       from './pages/ChatPage.jsx'
import ComingSoonPage from './pages/ComingSoonPage.jsx'
import ProtectedRoute from './components/ui/ProtectedRoute.jsx'
import { useAuth }    from './hooks/useAuth.js'

function App() {
  const { initAuth } = useAuth()

  useEffect(() => {
    initAuth()
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <Routes>
      {/* ── Public ──────────────────────────────────────────────────── */}
      <Route path="/login" element={<LoginPage />} />

      {/* ── Protected – all pages inside AppShell ───────────────────── */}
      <Route
        path="/*"
        element={
          <ProtectedRoute>
            <AppShell>
              <Routes>
                <Route path="/"         element={<Navigate to="/chat" replace />} />
                <Route path="/chat"     element={<ChatPage />} />

                {/* Module placeholders (Phases 6–10) */}
                <Route path="/calendar" element={<CalendarPage />} />
                <Route path="/finance"  element={<FinancePage />} />
                <Route path="/mail"     element={<ComingSoonPage module="mail"     />} />
                <Route path="/files"    element={<ComingSoonPage module="files"    />} />
                <Route path="/habits"   element={<ComingSoonPage module="habits"   />} />
              </Routes>
            </AppShell>
          </ProtectedRoute>
        }
      />
    </Routes>
  )
}

export default App
