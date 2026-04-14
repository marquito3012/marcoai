import { Routes, Route, Navigate } from 'react-router-dom'
import AppShell from './components/layout/AppShell.jsx'
import ChatPage from './pages/ChatPage.jsx'

function App() {
  return (
    <AppShell>
      <Routes>
        <Route path="/" element={<Navigate to="/chat" replace />} />
        <Route path="/chat" element={<ChatPage />} />
        {/* Future routes: /calendar, /finance, /mail, /files, /habits */}
      </Routes>
    </AppShell>
  )
}

export default App
