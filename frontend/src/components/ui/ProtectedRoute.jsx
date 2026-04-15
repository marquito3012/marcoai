/**
 * ProtectedRoute – Route guard for authenticated pages.
 *
 * While the JWT check is pending → shows a full-screen loader.
 * If unauthenticated    → redirects to /login.
 * If authenticated      → renders children.
 */
import { Navigate } from 'react-router-dom'
import useAuthStore from '../../store/authStore'

function LoadingScreen() {
  return (
    <div
      style={{
        display:        'flex',
        flexDirection:  'column',
        alignItems:     'center',
        justifyContent: 'center',
        height:         '100vh',
        background:     'var(--color-bg)',
        gap:            20,
      }}
    >
      {/* Animated logo */}
      <div
        style={{
          width:        56,
          height:       56,
          borderRadius: 14,
          background:   'linear-gradient(135deg, var(--color-primary), var(--color-primary-light))',
          display:      'flex',
          alignItems:   'center',
          justifyContent: 'center',
          fontSize:     28,
          fontFamily:   'var(--font-display)',
          fontWeight:   800,
          color:        'white',
          animation:    'pulse-glow 2s ease-in-out infinite',
          boxShadow:    'var(--shadow-glow)',
        }}
      >
        M
      </div>
      <p style={{ color: 'var(--color-text-muted)', fontSize: 14, margin: 0 }}>
        Verificando sesión…
      </p>
    </div>
  )
}

export default function ProtectedRoute({ children }) {
  const { isAuthenticated, isLoading } = useAuthStore()

  if (isLoading)       return <LoadingScreen />
  if (!isAuthenticated) return <Navigate to="/login" replace />
  return children
}
