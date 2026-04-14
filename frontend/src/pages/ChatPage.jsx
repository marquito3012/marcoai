import { useState, useRef, useEffect } from 'react'
import { Send, Sparkles } from 'lucide-react'

/** Initial greeting messages shown on first load */
const INITIAL_MESSAGES = [
  {
    id: 'welcome',
    role: 'assistant',
    content: '¡Hola! Soy **Marco**, tu asistente personal. Puedo ayudarte con tu calendario, finanzas, correos, documentos y hábitos. ¿En qué puedo ayudarte hoy?',
  },
]

function TypingIndicator() {
  return (
    <div className="fade-in-up" style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '8px 0' }}>
      <div className="typing-dot" />
      <div className="typing-dot" />
      <div className="typing-dot" />
    </div>
  )
}

function ChatMessage({ message }) {
  const isUser = message.role === 'user'
  return (
    <div
      className="fade-in-up"
      style={{
        display: 'flex',
        justifyContent: isUser ? 'flex-end' : 'flex-start',
        marginBottom: 12,
      }}
    >
      {!isUser && (
        <div
          style={{
            width: 32,
            height: 32,
            borderRadius: '50%',
            background: 'linear-gradient(135deg, var(--color-primary), var(--color-primary-light))',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            marginRight: 10,
            flexShrink: 0,
            marginTop: 4,
            boxShadow: 'var(--shadow-glow)',
          }}
        >
          <Sparkles size={15} color="white" />
        </div>
      )}
      <div
        style={{
          maxWidth: '72%',
          padding: '12px 16px',
          borderRadius: isUser
            ? 'var(--radius-lg) var(--radius-lg) var(--radius-sm) var(--radius-lg)'
            : 'var(--radius-lg) var(--radius-lg) var(--radius-lg) var(--radius-sm)',
          background: isUser
            ? 'var(--color-primary)'
            : 'var(--color-surface-2)',
          border: isUser ? 'none' : '1px solid var(--color-border-subtle)',
          color: 'var(--color-text)',
          fontSize: 14,
          lineHeight: 1.65,
          whiteSpace: 'pre-wrap',
        }}
      >
        {/* Very basic markdown: **bold** */}
        {message.content.split(/(\*\*[^*]+\*\*)/).map((seg, i) =>
          seg.startsWith('**') && seg.endsWith('**')
            ? <strong key={i}>{seg.slice(2, -2)}</strong>
            : seg
        )}
      </div>
    </div>
  )
}

export default function ChatPage() {
  const [messages, setMessages] = useState(INITIAL_MESSAGES)
  const [input, setInput]       = useState('')
  const [loading, setLoading]   = useState(false)
  const bottomRef               = useRef(null)
  const textareaRef             = useRef(null)

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  // Auto-resize textarea
  useEffect(() => {
    const el = textareaRef.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = Math.min(el.scrollHeight, 160) + 'px'
  }, [input])

  const sendMessage = async () => {
    const text = input.trim()
    if (!text || loading) return

    const userMsg = { id: Date.now().toString(), role: 'user', content: text }
    setMessages(prev => [...prev, userMsg])
    setInput('')
    setLoading(true)

    try {
      // Phase 5+ will replace this with real SSE streaming
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text }),
      })
      const data = await res.json()
      setMessages(prev => [
        ...prev,
        { id: (Date.now() + 1).toString(), role: 'assistant', content: data.response ?? '(Sin respuesta del servidor)' },
      ])
    } catch {
      setMessages(prev => [
        ...prev,
        { id: (Date.now() + 1).toString(), role: 'assistant', content: '⚠️ No se pudo conectar con el backend. Asegúrate de que el servidor esté en marcha.' },
      ])
    } finally {
      setLoading(false)
    }
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      {/* Header */}
      <header style={{
        padding: '16px 24px',
        borderBottom: '1px solid var(--color-border-subtle)',
        display: 'flex',
        alignItems: 'center',
        gap: 12,
        flexShrink: 0,
      }}>
        <div style={{
          width: 36,
          height: 36,
          borderRadius: 'var(--radius-md)',
          background: 'linear-gradient(135deg, var(--color-primary), var(--color-primary-light))',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          boxShadow: 'var(--shadow-glow)',
        }}>
          <Sparkles size={18} color="white" />
        </div>
        <div>
          <h1 style={{ fontSize: 16, fontFamily: 'var(--font-display)' }}>MarcoAI</h1>
          <p style={{ fontSize: 12, color: 'var(--color-text-muted)', margin: 0 }}>
            Asistente personal inteligente
          </p>
        </div>
      </header>

      {/* Messages */}
      <div style={{
        flex: 1,
        overflowY: 'auto',
        padding: '24px',
        display: 'flex',
        flexDirection: 'column',
      }}>
        {messages.map(msg => <ChatMessage key={msg.id} message={msg} />)}
        {loading && <TypingIndicator />}
        <div ref={bottomRef} />
      </div>

      {/* Input bar */}
      <div style={{
        padding: '16px 24px 24px',
        borderTop: '1px solid var(--color-border-subtle)',
        flexShrink: 0,
      }}>
        <div style={{
          display: 'flex',
          gap: 12,
          alignItems: 'flex-end',
          background: 'var(--color-surface-2)',
          border: '1px solid var(--color-border)',
          borderRadius: 'var(--radius-lg)',
          padding: '12px 16px',
          transition: 'border-color var(--transition-fast), box-shadow var(--transition-fast)',
        }}
          onFocusCapture={e => e.currentTarget.style.boxShadow = '0 0 0 3px rgba(124,58,237,0.15)'}
          onBlurCapture={e => e.currentTarget.style.boxShadow = 'none'}
        >
          <textarea
            ref={textareaRef}
            id="chat-input"
            className="input"
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Escribe un mensaje… (Shift+Enter para nueva línea)"
            rows={1}
            style={{
              flex: 1,
              resize: 'none',
              border: 'none',
              background: 'transparent',
              padding: 0,
              lineHeight: 1.6,
              maxHeight: 160,
              overflow: 'auto',
            }}
            disabled={loading}
          />
          <button
            id="btn-send-message"
            className="btn btn-primary"
            onClick={sendMessage}
            disabled={!input.trim() || loading}
            style={{ padding: '8px 12px', flexShrink: 0 }}
            aria-label="Enviar mensaje"
          >
            <Send size={16} />
          </button>
        </div>
        <p style={{
          textAlign: 'center',
          fontSize: 11,
          color: 'var(--color-text-faint)',
          marginTop: 8,
        }}>
          MarcoAI puede cometer errores. Verifica la información importante.
        </p>
      </div>
    </div>
  )
}
