/**
 * MailPage – Gmail Dashboard (Fase 8)
 * ══════════════════════════════════════════════════════════════════════════════
 * 
 * Features:
 *   • Master-Detail layout for listing and reading emails
 *   • Search functionality (via Gmail query)
 *   • Send new email modal
 *   • Glassmorphism aesthetics and smooth transitions
 */
import { useState, useEffect } from 'react'
import { 
  Search, 
  Mail, 
  Send, 
  RefreshCw, 
  ChevronRight, 
  User, 
  Clock, 
  ArrowLeft,
  Paperclip,
  Trash2,
  Reply,
  SquarePen
} from 'lucide-react'
import { apiFetch } from '../lib/api.js'

export default function MailPage() {
  const [emails, setEmails] = useState([])
  const [loading, setLoading] = useState(true)
  const [selectedMail, setSelectedMail] = useState(null)
  const [loadingDetail, setLoadingDetail] = useState(false)
  const [mailContent, setMailContent] = useState(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [showCompose, setShowCompose] = useState(false)
  const [error, setError] = useState(null)

  // Fetch email list
  const fetchEmails = async (query = '') => {
    try {
      setLoading(true)
      setError(null)
      const data = await apiFetch(`/gmail/list?q=${encodeURIComponent(query)}&max_results=15`)
      setEmails(data.messages || [])
    } catch (err) {
      console.error('Error fetching emails:', err)
      setError(err.message || 'Error al conectar con Gmail')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchEmails()
  }, [])

  // Fetch individual mail detail
  const handleSelectMail = async (mail) => {
    setSelectedMail(mail)
    setLoadingDetail(true)
    setMailContent(null)
    
    // Optimistic update: mark as read locally
    if (mail.is_unread) {
      setEmails(prev => prev.map(m => m.id === mail.id ? { ...m, is_unread: false } : m))
    }

    try {
      const data = await apiFetch(`/gmail/messages/${mail.id}`)
      setMailContent(data)
    } catch (err) {
      console.error('Error fetching mail detail:', err)
      setError('Error al cargar el detalle del correo')
    } finally {
      setLoadingDetail(false)
    }
  }

  const handleSearch = (e) => {
    if (e.key === 'Enter') {
      fetchEmails(searchQuery)
    }
  }

  return (
    <div style={styles.root}>
      {/* ── Header ───────────────────────────────────────────────────────── */}
      <header style={styles.header}>
        <div style={styles.headerLeft}>
          <h1 style={styles.title}>Correo</h1>
          <div style={styles.searchWrapper}>
            <Search size={16} color="var(--color-text-faint)" />
            <input 
              type="text" 
              placeholder="Buscar correos..." 
              style={styles.searchInput}
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyDown={handleSearch}
            />
          </div>
        </div>
        <div style={styles.headerRight}>
          <button onClick={() => fetchEmails(searchQuery)} style={styles.iconBtn} title="Refrescar">
            <RefreshCw size={18} className={loading ? 'spin' : ''} />
          </button>
          <button onClick={() => setShowCompose(true)} style={styles.composeBtn}>
            <SquarePen size={18} />
            <span>Redactar</span>
          </button>
        </div>
      </header>

      {/* ── Main Content ─────────────────────────────────────────────────── */}
      <div className="mail-container" style={styles.mainContainer}>
        {/* Left Sidebar: Email List */}
        <div className={`mail-list-pane ${selectedMail ? 'hidden-mobile' : ''}`} style={styles.listPane}>
          {loading ? (
            <div style={styles.emptyState}>
              <RefreshCw size={32} className="spin" color="var(--color-primary)" />
              <p>Cargando bandeja de entrada...</p>
            </div>
          ) : error && emails.length === 0 ? (
            <div style={styles.emptyState}>
              <RefreshCw size={48} color="var(--color-error)" />
              <p style={{ color: 'var(--color-error)', textAlign: 'center', padding: '0 20px' }}>
                {error}
                <br />
                <button onClick={() => fetchEmails(searchQuery)} style={styles.retryBtn}>Reintentar</button>
              </p>
            </div>
          ) : emails.length === 0 ? (
            <div style={styles.emptyState}>
              <Mail size={48} color="var(--color-text-faint)" />
              <p>No hay mensajes que mostrar.</p>
            </div>
          ) : (
            <div style={styles.scrollArea}>
              {emails.map(mail => (
                <div 
                  key={mail.id} 
                  onClick={() => handleSelectMail(mail)}
                  style={{
                    ...styles.mailItem,
                    ...(selectedMail?.id === mail.id ? styles.mailItemActive : {})
                  }}
                >
                  <div style={styles.mailItemHeader}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      {mail.is_unread && <div style={styles.unreadDot} />}
                      <span style={{
                        ...styles.mailSender,
                        fontWeight: mail.is_unread ? 800 : styles.mailSender.fontWeight
                      }}>{mail.sender?.split(' <')[0] || 'Desconocido'}</span>
                    </div>
                    <span style={styles.mailDate}>{mail.date ? new Date(mail.date).toLocaleDateString() : ''}</span>
                  </div>
                  <div style={{
                    ...styles.mailSubject,
                    fontWeight: mail.is_unread ? 700 : styles.mailSubject.fontWeight,
                    color: mail.is_unread ? 'var(--color-text)' : styles.mailSubject.color
                  }}>{mail.subject || '(Sin asunto)'}</div>
                  <div style={styles.mailSnippet}>{mail.snippet}</div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Right Pane: Mail Detail */}
        <div className={`mail-detail-pane ${selectedMail ? 'visible-mobile' : ''}`} style={styles.detailPane}>
          {selectedMail ? (
            <div style={styles.detailWrapper}>
              {/* Detail Header / Toolbar */}
              <div style={styles.detailToolbar}>
                <button onClick={() => setSelectedMail(null)} className="mail-back-btn" style={styles.backBtn}>
                  <ArrowLeft size={20} />
                </button>
                <div style={styles.toolbarActions}>
                  <button style={styles.iconBtn}><Reply size={18} /></button>
                  <button style={styles.iconBtn}><Trash2 size={18} /></button>
                </div>
              </div>

              {loadingDetail ? (
                <div style={styles.emptyState}>
                  <RefreshCw size={32} className="spin" color="var(--color-primary)" />
                </div>
              ) : mailContent ? (
                <div style={styles.mailBodyScroll}>
                  <div style={styles.mailDetailInfo}>
                    <div style={styles.avatar}>
                      <User size={24} color="white" />
                    </div>
                    <div style={{ flex: 1 }}>
                      <h2 style={styles.detailSubject}>{mailContent.subject}</h2>
                      <div style={styles.detailMeta}>
                        <span style={{ fontWeight: 600 }}>De: {mailContent.sender}</span>
                        <span style={styles.detailDate}>
                          <Clock size={14} /> {mailContent.date}
                        </span>
                      </div>
                    </div>
                  </div>
                  <div style={styles.divider} />
                  <div style={styles.mailContent}>
                    {mailContent.is_html ? (
                      <iframe 
                        title="Email Content"
                        srcDoc={mailContent.body}
                        style={styles.mailIframe}
                        sandbox="allow-popups allow-popups-to-escape-sandbox"
                      />
                    ) : (
                      mailContent.body?.split('\n').map((line, i) => (
                        <p key={i} style={{ margin: '0 0 1em' }}>{line}</p>
                      )) || <p>No se pudo cargar el contenido del mensaje.</p>
                    )}
                  </div>
                </div>
              ) : null}
            </div>
          ) : (
            <div style={styles.emptyState}>
              <Mail size={64} color="var(--color-surface-3)" strokeWidth={1} />
              <p style={{ color: 'var(--color-text-faint)', fontSize: 16 }}>Selecciona un correo para leerlo</p>
            </div>
          )}
        </div>
      </div>

      {/* ── Compose Modal ───────────────────────────────────────────────── */}
      {showCompose && (
        <ComposeModal 
          onClose={() => setShowCompose(false)} 
          onSent={() => {
            setShowCompose(false)
            fetchEmails()
          }}
        />
      )}
    </div>
  )
}

function ComposeModal({ onClose, onSent }) {
  const [to, setTo] = useState('')
  const [subject, setSubject] = useState('')
  const [body, setBody] = useState('')
  const [sending, setSending] = useState(false)

  const handleSend = async (e) => {
    e.preventDefault()
    setSending(true)
    try {
      await apiFetch('/gmail/send', {
        method: 'POST',
        body: JSON.stringify({ to, subject, body })
      })
      onSent()
    } catch (err) {
      alert('Error enviando correo: ' + err.message)
    } finally {
      setSending(false)
    }
  }

  return (
    <div style={styles.modalOverlay} onClick={onClose}>
      <div style={styles.modalContent} onClick={e => e.stopPropagation()} className="glass-card">
        <div style={styles.modalHeader}>
          <h3 style={{ margin: 0, fontSize: 18 }}>Nuevo mensaje</h3>
          <button onClick={onClose} style={styles.closeBtn}>×</button>
        </div>
        <form onSubmit={handleSend} style={styles.composeForm}>
          <input 
            style={styles.modalInput} 
            placeholder="Para" 
            value={to}
            onChange={e => setTo(e.target.value)}
            required 
          />
          <input 
            style={styles.modalInput} 
            placeholder="Asunto" 
            value={subject}
            onChange={e => setSubject(e.target.value)}
            required 
          />
          <textarea 
            style={styles.modalTextarea} 
            placeholder="Escribe tu mensaje aquí..."
            value={body}
            onChange={e => setBody(e.target.value)}
            required 
          />
          <div style={styles.modalFooter}>
            <button type="submit" disabled={sending} style={styles.sendSubmitBtn}>
              {sending ? 'Enviando...' : <><Send size={16} /> Enviar</>}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

const styles = {
  root: {
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
    height: '100%',
    overflow: 'hidden',
    padding: '20px 24px',
    background: 'var(--color-bg)',
  },
  header: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 20,
    flexShrink: 0,
  },
  headerLeft: {
    display: 'flex',
    alignItems: 'center',
    gap: 24,
  },
  headerRight: {
    display: 'flex',
    alignItems: 'center',
    gap: 12,
  },
  title: {
    fontSize:   28,
    fontFamily: 'var(--font-display)',
    fontWeight: 700,
    color:      'var(--color-primary)',
    margin:     0,
    letterSpacing: '-0.01em',
  },
  searchWrapper: {
    display: 'flex',
    alignItems: 'center',
    gap: 10,
    background: 'var(--color-surface-2)',
    padding: '8px 16px',
    borderRadius: 'var(--radius-md)',
    width: 320,
    border: '1px solid var(--color-border-subtle)',
  },
  searchInput: {
    background: 'transparent',
    border: 'none',
    outline: 'none',
    color: 'var(--color-text)',
    fontSize: 14,
    width: '100%',
  },
  composeBtn: {
    background: 'linear-gradient(135deg, var(--color-primary), var(--color-primary-dark))',
    color: '#000',
    border: 'none',
    borderRadius: 'var(--radius-md)',
    padding: '10px 18px',
    display: 'flex',
    alignItems: 'center',
    gap: 8,
    fontWeight: 700,
    cursor: 'pointer',
    boxShadow: '0 4px 15px rgba(212, 175, 55, 0.2)',
  },
  retryBtn: {
    marginTop: 12,
    background: 'var(--color-primary)',
    color: 'white',
    border: 'none',
    borderRadius: 'var(--radius-sm)',
    padding: '6px 14px',
    fontSize: 13,
    cursor: 'pointer',
  },
  iconBtn: {
    background: 'var(--color-surface-2)',
    border: '1px solid var(--color-border-subtle)',
    borderRadius: 'var(--radius-sm)',
    padding: 8,
    color: 'var(--color-text-muted)',
    cursor: 'pointer',
  },
  mainContainer: {
    flex: 1,
    display: 'flex',
    overflow: 'hidden',
    gap: 20,
  },
  listPane: {
    width: 400,
    flexDirection: 'column',
    background: 'var(--color-surface)',
    borderRadius: 'var(--radius-lg)',
    border: '1px solid var(--color-border-subtle)',
    overflow: 'hidden',
    flexShrink: 0,
  },
  detailPane: {
    flex: 1,
    background: 'var(--color-surface)',
    borderRadius: 'var(--radius-lg)',
    border: '1px solid var(--color-border-subtle)',
    flexDirection: 'column',
    overflow: 'hidden',
  },
  scrollArea: {
    flex: 1,
    overflowY: 'auto',
  },
  mailItem: {
    padding: '16px 20px',
    borderBottom: '1px solid var(--color-border-subtle)',
    cursor: 'pointer',
    transition: 'background 0.2s',
  },
  mailItemActive: {
    background: 'rgba(212, 175, 55, 0.05)',
    boxShadow: 'inset 4px 0 0 var(--color-primary)',
  },
  unreadDot: {
    width: 8,
    height: 8,
    borderRadius: '50%',
    background: '#3b82f6', // Bright blue for unread
  },
  mailItemHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    marginBottom: 4,
  },
  mailSender: {
    fontSize: 14,
    fontWeight: 700,
    color: 'var(--color-text)',
  },
  mailDate: {
    fontSize: 12,
    color: 'var(--color-text-faint)',
  },
  mailSubject: {
    fontSize: 13,
    fontWeight: 600,
    color: 'var(--color-text-muted)',
    marginBottom: 4,
    whiteSpace: 'nowrap',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
  },
  mailSnippet: {
    fontSize: 12,
    color: 'var(--color-text-faint)',
    display: '-webkit-box',
    WebkitLineClamp: 2,
    WebkitBoxOrient: 'vertical',
    overflow: 'hidden',
  },
  emptyState: {
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 16,
    color: 'var(--color-text-muted)',
  },
  detailToolbar: {
    padding: '12px 20px',
    borderBottom: '1px solid var(--color-border-subtle)',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  toolbarActions: {
    display: 'flex',
    gap: 8,
  },
  backBtn: {
    background: 'transparent',
    border: 'none',
    color: 'var(--color-text)',
    cursor: 'pointer',
    display: 'block', // Default for mobile logic
  },
  mailBodyScroll: {
    flex: 1,
    overflowY: 'auto',
    padding: '24px 32px',
  },
  mailDetailInfo: {
    display: 'flex',
    gap: 16,
    marginBottom: 24,
  },
  avatar: {
    width: 48,
    height: 48,
    borderRadius: '50%',
    background: 'var(--color-mail)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
  },
  detailSubject: {
    fontSize: 28,
    fontFamily: 'var(--font-display)',
    fontWeight: 700,
    margin: '0 0 12px',
    color: 'var(--color-text)',
    lineHeight: 1.2,
  },
  detailMeta: {
    display: 'flex',
    gap: 12,
    fontSize: 13,
    color: 'var(--color-text-muted)',
    alignItems: 'center',
  },
  detailDate: {
    display: 'flex',
    alignItems: 'center',
    gap: 4,
  },
  divider: {
    height: 1,
    background: 'var(--color-border-subtle)',
    margin: '0 0 24px',
  },
  mailContent: {
    fontSize: 15,
    lineHeight: 1.8,
    color: 'var(--color-text)',
    fontFamily: 'var(--font-sans)',
  },
  mailIframe: {
    width: '100%',
    height: '600px',
    border: 'none',
    background: 'white',
    borderRadius: 'var(--radius-md)',
  },
  // Modal styles
  modalOverlay: {
    position: 'fixed',
    top: 0, left: 0, right: 0, bottom: 0,
    background: 'rgba(0,0,0,0.6)',
    backdropFilter: 'blur(4px)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    zIndex: 1000,
  },
  modalContent: {
    width: 600,
    maxHeight: '90vh',
    display: 'flex',
    flexDirection: 'column',
    padding: 0,
    overflow: 'hidden',
  },
  modalHeader: {
    padding: '20px 24px',
    borderBottom: '1px solid var(--color-border-subtle)',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  closeBtn: {
    background: 'transparent',
    border: 'none',
    fontSize: 24,
    color: 'var(--color-text-faint)',
    cursor: 'pointer',
  },
  composeForm: {
    display: 'flex',
    flexDirection: 'column',
    padding: 24,
    gap: 16,
  },
  modalInput: {
    background: 'var(--color-surface-2)',
    border: '1px solid var(--color-border-subtle)',
    borderRadius: 'var(--radius-md)',
    padding: '12px 16px',
    color: 'var(--color-text)',
    fontSize: 14,
  },
  modalTextarea: {
    background: 'var(--color-surface-2)',
    border: '1px solid var(--color-border-subtle)',
    borderRadius: 'var(--radius-md)',
    padding: '12px 16px',
    color: 'var(--color-text)',
    fontSize: 14,
    minHeight: 250,
    resize: 'vertical',
  },
  modalFooter: {
    display: 'flex',
    justifyContent: 'flex-end',
  },
  sendSubmitBtn: {
    background: 'var(--color-mail)',
    color: 'white',
    border: 'none',
    borderRadius: 'var(--radius-md)',
    padding: '12px 24px',
    fontSize: 14,
    fontWeight: 600,
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
    gap: 8,
  },
}
