import { useEffect } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'

import AppShell       from './components/layout/AppShell.jsx'
import CalendarPage   from './pages/CalendarPage.jsx'
import FinancePage    from './pages/FinancePage.jsx'
import MailPage       from './pages/MailPage.jsx'
import FilesPage      from './pages/FilesPage.jsx'
import HabitsPage     from './pages/HabitsPage.jsx'
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

                {/* Main functional modules */}
                <Route path="/calendar" element={<CalendarPage />} />
                <Route path="/finance"  element={<FinancePage />} />
                <Route path="/mail"     element={<MailPage />} />
                <Route path="/files"    element={<FilesPage />} />
                <Route path="/habits"   element={<HabitsPage />} />
              </Routes>
            </AppShell>
          </ProtectedRoute>
        }
      />
    </Routes>
  )
}

export default App
