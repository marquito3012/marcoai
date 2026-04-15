/**
 * ChatPage – Full streaming chat interface (HU02, HU03, HU06)
 *
 * Features:
 *   • SSE streaming via useStreamingChat hook (real-time typewriter effect)
 *   • Markdown rendering in assistant bubbles (react-markdown + remark-gfm)
 *   • Auto-scroll to latest message
 *   • Auto-resize textarea (grows up to 6 lines, then scrolls)
 *   • Shift+Enter = new line, Enter = send
 *   • Stop streaming button while assistant is typing
 *   • Message count in header
 */
import { useRef, useEffect, useLayoutEffect } from 'react'
import { Send, Square, MessageSquare } from 'lucide-react'
import { useState } from 'react'
import useAuthStore from '../store/authStore.js'
import { useStreamingChat } from '../hooks/useStreamingChat.js'
import MessageBubble from '../components/chat/MessageBubble.jsx'
import RouteIndicator from '../components/chat/RouteIndicator.jsx'

/* ── Typing indicator (three bouncing dots) ───────────────────────────────── */
function TypingIndicator() {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '0 0 8px 44px' }}>
      <div className="typing-indicator">
        <div className="typing-dot" />
        <div className="typing-dot" />
        <div className="typing-dot" />
      </div>
    </div>
  )
}

/* ── Main page ─────────────────────────────────────────────────────────────── */
export default function ChatPage() {
  const { user }                                                     = useAuthStore()
  const { messages, isStreaming, currentRoute, sendMessage, stopStreaming } = useStreamingChat(user?.name)
  const [input, setInput]                             = useState('')
  const bottomRef                                     = useRef(null)
  const textareaRef                                   = useRef(null)

  // Show typing indicator only when streaming but last message content is empty
  const lastMsg        = messages[messages.length - 1]
  const showTypingDots = isStreaming && lastMsg?.role === 'assistant' && lastMsg?.content === ''

  // Auto-scroll
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, showTypingDots])

  // Auto-resize textarea
  useLayoutEffect(() => {
    const el = textareaRef.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = `${Math.min(el.scrollHeight, 160)}px`
  }, [input])

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const handleSend = () => {
    if (!input.trim() || isStreaming) return
    sendMessage(input)
    setInput('')
  }

  const msgCount = messages.filter(m => m.role === 'user').length

  return (
    <div style={styles.root}>
      {/* ── Header ──────────────────────────────────────────────────────── */}
      <header style={styles.header}>
        <div style={styles.headerLeft}>
          <div style={styles.modelBadge}>
            <div style={{ width: 8, height: 8, borderRadius: '50%', background: 'var(--color-success)', animation: 'pulse-glow 2s infinite' }} />
            <span style={{ fontSize: 12, color: 'var(--color-text-muted)', letterSpacing: '0.02em' }}>
              Gemini · Groq · OpenRouter
            </span>
          </div>
          <h1 style={styles.headerTitle}>MarcoAI</h1>
          <p style={styles.headerSub}>Asistente personal inteligente</p>
        </div>
        {msgCount > 0 && (
          <span style={styles.msgCountBadge}>
            <MessageSquare size={12} />
            {msgCount} mensaje{msgCount !== 1 ? 's' : ''}
          </span>
        )}
      </header>

      {/* ── Message list ────────────────────────────────────────────────── */}
      <div style={styles.messageList} role="log" aria-label="Conversación" aria-live="polite">
        {messages.map((msg) => (
          <MessageBubble
            key={msg.id}
            message={msg}
            userInitial={(user?.name?.[0] ?? 'U').toUpperCase()}
            userPictureUrl={user?.picture_url}
          />
        ))}
        {/* Route indicator: shown while streaming, clears when done */}
        {currentRoute && <RouteIndicator route={currentRoute} />}
        {showTypingDots && <TypingIndicator />}
        <div ref={bottomRef} aria-hidden="true" />
      </div>

      {/* ── Disclaimer ──────────────────────────────────────────────────── */}
      <p style={styles.disclaimer}>
        MarcoAI puede cometer errores. Verifica la información importante.
      </p>

      {/* ── Input area ──────────────────────────────────────────────────── */}
      <div style={styles.inputWrapper}>
        <div style={styles.inputBox} className="glass-card" role="form" aria-label="Redactar mensaje">
          <textarea
            ref={textareaRef}
            id="chat-input"
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Escribe un mensaje… (Shift+Enter para nueva línea)"
            rows={1}
            disabled={isStreaming}
            aria-label="Mensaje"
            style={styles.textarea}
          />
          {isStreaming ? (
            <button
              id="btn-stop"
              onClick={stopStreaming}
              title="Detener respuesta"
              style={{ ...styles.sendBtn, background: 'rgba(239,68,68,0.2)', borderColor: 'rgba(239,68,68,0.4)' }}
            >
              <Square size={17} color="rgb(239,68,68)" strokeWidth={2.5} />
            </button>
          ) : (
            <button
              id="btn-send"
              onClick={handleSend}
              disabled={!input.trim()}
              title="Enviar (Enter)"
              style={{
                ...styles.sendBtn,
                opacity: input.trim() ? 1 : 0.4,
                cursor:  input.trim() ? 'pointer' : 'default',
              }}
            >
              <Send size={17} color="white" strokeWidth={2.5} />
            </button>
          )}
        </div>
      </div>
    </div>
  )
}

/* ── Styles ─────────────────────────────────────────────────────────────── */
const styles = {
  root: {
    flex:           1,
    display:        'flex',
    flexDirection:  'column',
    height:         '100%',
    overflow:       'hidden',
    position:       'relative',
  },
  header: {
    display:        'flex',
    alignItems:     'flex-start',
    justifyContent: 'space-between',
    padding:        '20px 24px 14px',
    borderBottom:   '1px solid var(--color-border-subtle)',
    flexShrink:     0,
  },
  headerLeft: { display: 'flex', flexDirection: 'column', gap: 3 },
  modelBadge: {
    display:      'flex',
    alignItems:   'center',
    gap:          6,
    marginBottom: 2,
  },
  headerTitle: {
    fontSize:   20,
    fontFamily: 'var(--font-display)',
    fontWeight: 700,
    color:      'var(--color-text)',
    margin:     0,
  },
  headerSub: {
    fontSize: 13,
    color:    'var(--color-text-muted)',
    margin:   0,
  },
  msgCountBadge: {
    display:    'flex',
    alignItems: 'center',
    gap:        5,
    fontSize:   12,
    color:      'var(--color-text-faint)',
    background: 'var(--color-surface-2)',
    padding:    '4px 10px',
    borderRadius: 20,
    border:     '1px solid var(--color-border-subtle)',
  },
  messageList: {
    flex:           1,
    overflowY:      'auto',
    padding:        '20px 24px',
    display:        'flex',
    flexDirection:  'column',
    gap:            2,
    scrollbarWidth: 'thin',
    scrollbarColor: 'var(--color-surface-3) transparent',
  },
  disclaimer: {
    textAlign:  'center',
    fontSize:   11,
    color:      'var(--color-text-faint)',
    margin:     '0 0 6px',
    flexShrink: 0,
  },
  inputWrapper: {
    padding:    '0 16px 16px',
    flexShrink: 0,
  },
  inputBox: {
    display:    'flex',
    alignItems: 'flex-end',
    gap:        10,
    padding:    '10px 10px 10px 16px',
    borderRadius: 'var(--radius-lg)',
  },
  textarea: {
    flex:      1,
    resize:    'none',
    border:    'none',
    outline:   'none',
    background:'transparent',
    color:     'var(--color-text)',
    fontFamily:'var(--font-sans)',
    fontSize:   14,
    lineHeight: 1.6,
    padding:    0,
    maxHeight:  160,
    overflowY:  'auto',
  },
  sendBtn: {
    width:        38,
    height:       38,
    borderRadius: '50%',
    background:   'var(--color-primary)',
    border:       '1px solid transparent',
    display:      'flex',
    alignItems:   'center',
    justifyContent: 'center',
    cursor:       'pointer',
    flexShrink:   0,
    transition:   'all 150ms ease',
  },
}
