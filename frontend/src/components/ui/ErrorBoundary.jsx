import { Component } from 'react'
import { useNavigate } from 'react-router-dom'

class ErrorBoundaryInner extends Component {
  constructor(props) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error }
  }

  render() {
    if (this.state.hasError) {
      return (
        <div
          style={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            minHeight: '60vh',
            padding: 40,
            textAlign: 'center',
          }}
        >
          <div
            style={{
              width: 56,
              height: 56,
              borderRadius: 14,
              background: 'linear-gradient(135deg, #ef4444, #dc2626)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: 28,
              fontWeight: 800,
              color: 'white',
              marginBottom: 20,
            }}
          >
            !
          </div>
          <h2 style={{ margin: '0 0 8px', fontSize: 20, color: 'var(--color-text)' }}>
            Algo salió mal
          </h2>
          <p style={{ margin: '0 0 24px', fontSize: 14, color: 'var(--color-text-muted)', maxWidth: 400 }}>
            {this.state.error?.message || 'Ha ocurrido un error inesperado.'}
          </p>
          <div style={{ display: 'flex', gap: 12 }}>
            <button
              onClick={() => this.props.onGoHome()}
              style={{
                padding: '10px 20px',
                borderRadius: 8,
                border: '1px solid var(--color-border)',
                background: 'var(--color-bg)',
                color: 'var(--color-text)',
                cursor: 'pointer',
                fontSize: 14,
              }}
            >
              Ir al inicio
            </button>
            <button
              onClick={() => this.setState({ hasError: false, error: null })}
              style={{
                padding: '10px 20px',
                borderRadius: 8,
                border: 'none',
                background: 'var(--color-primary)',
                color: 'white',
                cursor: 'pointer',
                fontSize: 14,
              }}
            >
              Intentar de nuevo
            </button>
          </div>
        </div>
      )
    }
    return this.props.children
  }
}

export default function ErrorBoundary({ children }) {
  const navigate = useNavigate()
  return (
    <ErrorBoundaryInner onGoHome={() => navigate('/chat')}>
      {children}
    </ErrorBoundaryInner>
  )
}
