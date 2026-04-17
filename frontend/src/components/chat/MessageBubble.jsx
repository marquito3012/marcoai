/**
 * MessageBubble – Chat message component with full Markdown support
 *
 * • Assistant messages: rendered with react-markdown + remark-gfm
 *   (bold, italic, lists, tables, code blocks, inline code)
 * • User messages: plain pre-wrap text (no injection risk)
 * • Streaming cursor: blinking ▍ appended while streaming: true
 * • Copy button: appears on completed assistant messages
 */
import { useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Sparkles, Copy, Check, User } from 'lucide-react'

/* ── Copy button ─────────────────────────────────────────────────────────── */
function CopyButton({ text }) {
  const [copied, setCopied] = useState(false)

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(text)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch { /* clipboard not available */ }
  }

  return (
    <button
      onClick={handleCopy}
      title="Copiar"
      style={{
        position:       'absolute',
        top:            8,
        right:          8,
        background:     'var(--color-surface-3)',
        border:         '1px solid var(--color-border-subtle)',
        borderRadius:   'var(--radius-sm)',
        padding:        '3px 7px',
        cursor:         'pointer',
        display:        'flex',
        alignItems:     'center',
        gap:            4,
        opacity:        0,
        transition:     'opacity 150ms ease',
        color:          copied ? 'var(--color-success)' : 'var(--color-text-faint)',
      }}
      className="copy-btn"
    >
      {copied
        ? <Check size={12} />
        : <Copy size={12} />
      }
    </button>
  )
}

/* ── Avatar ──────────────────────────────────────────────────────────────── */
function Avatar({ isUser, userInitial, pictureUrl }) {
  if (isUser) {
    return (
      <div style={{ ...styles.avatar, background: 'var(--color-surface-3)', flexShrink: 0 }}>
        {pictureUrl
          ? <img src={pictureUrl} alt="tú" style={{ width: '100%', height: '100%', objectFit: 'cover', borderRadius: '50%' }} referrerPolicy="no-referrer" />
          : <span style={{ fontSize: 12, fontWeight: 700, color: 'var(--color-primary-light)' }}>{userInitial}</span>
        }
      </div>
    )
  }
  return (
    <div style={{ ...styles.avatar, background: 'linear-gradient(135deg, var(--color-primary), var(--color-primary-dark))', flexShrink: 0 }}>
      <Sparkles size={14} color="#000" strokeWidth={2.5} />
    </div>
  )
}

/* ── Main component ──────────────────────────────────────────────────────── */
export default function MessageBubble({ message, userInitial, userPictureUrl }) {
  const isUser     = message.role === 'user'
  const isStreaming = message.streaming

  // Append blinking cursor while streaming
  const displayContent = isUser
    ? message.content
    : message.content + (isStreaming ? '▍' : '')

  return (
    <div
      className="fade-in-up msg-row"
      style={{
        display:        'flex',
        justifyContent: isUser ? 'flex-end' : 'flex-start',
        alignItems:     'flex-start',
        gap:            10,
        marginBottom:   4,
      }}
    >
      {!isUser && (
        <Avatar isUser={false} />
      )}

      <div style={{ maxWidth: '75%', minWidth: 60, position: 'relative' }} className="bubble-wrapper">
        <div
          style={{
            padding:      '10px 14px',
            borderRadius: isUser
              ? '18px 18px 4px 18px'
              : '18px 18px 18px 4px',
            background: isUser
              ? 'rgba(212, 175, 55, 0.95)'
              : 'var(--color-surface-2)',
            border: isUser
              ? '1px solid var(--color-primary-light)'
              : '1px solid var(--color-border)',
            fontSize:   14,
            lineHeight: 1.65,
            color:      isUser ? '#000' : 'var(--color-text)',
            wordBreak:  'break-word',
            boxShadow:  isUser ? '0 4px 12px rgba(212, 175, 55, 0.15)' : 'none',
          }}
        >
          {isUser ? (
            <p style={{ margin: 0, whiteSpace: 'pre-wrap' }}>{displayContent}</p>
          ) : (
            <div className="markdown-body">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {displayContent}
              </ReactMarkdown>
            </div>
          )}
        </div>

        {/* Copy button – shown on hover for assistant messages */}
        {!isUser && !isStreaming && message.content && (
          <CopyButton text={message.content} />
        )}
      </div>

      {isUser && (
        <Avatar isUser={true} userInitial={userInitial} pictureUrl={userPictureUrl} />
      )}
    </div>
  )
}

const styles = {
  avatar: {
    width:          34,
    height:         34,
    borderRadius:   '50%',
    display:        'flex',
    alignItems:     'center',
    justifyContent: 'center',
    flexShrink:     0,
    marginTop:      4,
  },
}
