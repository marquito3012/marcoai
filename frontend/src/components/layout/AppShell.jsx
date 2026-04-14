import Sidebar from './Sidebar.jsx'

export default function AppShell({ children }) {
  return (
    <div className="app-shell">
      <Sidebar />
      <main className="main-content" id="main-content">
        {children}
      </main>
    </div>
  )
}
