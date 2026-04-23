/**
 * SettingsPage – Ajustes de Personalización y Notificaciones (Fase 11)
 */
import { useState, useEffect } from 'react'
import {
  Sparkles,
  Bell,
  BellOff,
  Briefcase,
  Smile,
  Zap,
  Save,
  CheckCircle2,
  Loader2,
  Globe,
  MessageSquare,
  Clock,
  Mail,
  CalendarDays,
  TrendingUp,
  Activity,
} from 'lucide-react'
import { apiFetch } from '../lib/api.js'

// ── Tone options ───────────────────────────────────────────────────────────
const TONE_OPTIONS = [
  {
    id: 'friendly',
    label: 'Amigable',
    description: 'Cercano, conversacional y con empatía. El modo por defecto.',
    icon: Smile,
    color: 'var(--color-primary)',
  },
  {
    id: 'professional',
    label: 'Profesional',
    description: 'Directo, preciso y sin coloquialismos. Ideal para el trabajo.',
    icon: Briefcase,
    color: 'var(--color-calendar)',
  },
  {
    id: 'motivational',
    label: 'Motivador',
    description: 'Energético y positivo. Marco te animará a dar lo mejor.',
    icon: Zap,
    color: 'var(--color-warning)',
  },
]

const HOURS = Array.from({ length: 24 }, (_, i) => i)

// ── Main component ─────────────────────────────────────────────────────────
export default function SettingsPage() {
  const [settings, setSettings] = useState(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)

  const fetchSettings = async () => {
    try {
      setLoading(true)
      const data = await apiFetch('/settings')
      setSettings(data)
    } catch (err) {
      console.error('Error fetching settings:', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { fetchSettings() }, [])

  const handleSave = async () => {
    if (!settings) return
    setSaving(true)
    try {
      const saved = await apiFetch('/settings', {
        method: 'PUT',
        body: JSON.stringify(settings),
      })
      // Sync state with what the server actually stored
      setSettings(saved)
      setSaved(true)
      setTimeout(() => setSaved(false), 2500)
    } catch (err) {
      console.error('Error saving settings:', err)
    } finally {
      setSaving(false)
    }
  }

  // Immediately persists a single field without requiring the user
  // to click the main "Guardar" button — used for the hour picker
  const autoSaveField = async (key, value) => {
    update(key, value)
    try {
      await apiFetch('/settings', {
        method: 'PUT',
        body: JSON.stringify({ [key]: value }),
      })
    } catch (err) {
      console.error(`Error auto-saving ${key}:`, err)
    }
  }

  const update = (key, value) => setSettings(prev => ({ ...prev, [key]: value }))

  if (loading) {
    return (
      <div style={styles.loadingScreen}>
        <Loader2 size={32} className="spin" color="var(--color-primary)" />
        <span style={{ color: 'var(--color-text-muted)', marginTop: 12 }}>Cargando ajustes...</span>
      </div>
    )
  }

  return (
    <div className="settings-root" style={styles.root}>
      {/* ── Header ─────────────────────────────────────────────────────── */}
      <header className="settings-header" style={styles.header}>
        <div>
          <h1 style={styles.title}>Ajustes</h1>
          <p style={styles.subtitle}>Personaliza cómo Marco trabaja contigo</p>
        </div>
        <button
          onClick={handleSave}
          disabled={saving}
          style={{
            ...styles.saveBtn,
            background: saved
              ? 'linear-gradient(135deg, var(--color-success), #6a9a5b)'
              : 'linear-gradient(135deg, var(--color-primary), var(--color-primary-dark))',
          }}
        >
          {saving ? (
            <Loader2 size={16} className="spin" />
          ) : saved ? (
            <CheckCircle2 size={16} />
          ) : (
            <Save size={16} />
          )}
          <span>{saving ? 'Guardando...' : saved ? '¡Guardado!' : 'Guardar cambios'}</span>
        </button>
      </header>

      <div style={styles.grid}>

        {/* ── Sección: Personalización de la IA ─────────────────────── */}
        <section style={styles.section}>
          <div style={styles.sectionHeader}>
            <div style={styles.sectionIconWrap}>
              <Sparkles size={20} color="var(--color-primary)" />
            </div>
            <div>
              <h2 style={styles.sectionTitle}>Personalización de la IA</h2>
              <p style={styles.sectionDesc}>Define cómo quieres que Marco se comunique contigo</p>
            </div>
          </div>

          {/* Tono */}
          <div style={styles.field}>
            <label style={styles.fieldLabel}>
              <MessageSquare size={14} />
              Tono del asistente
            </label>
            <div className="settings-tone-grid" style={styles.toneGrid}>
              {TONE_OPTIONS.map(tone => {
                const Icon = tone.icon
                const isActive = settings?.ai_tone === tone.id
                return (
                  <button
                    key={tone.id}
                    onClick={() => update('ai_tone', tone.id)}
                    style={{
                      ...styles.toneCard,
                      ...(isActive ? {
                        borderColor: tone.color,
                        background: `${tone.color}12`,
                        boxShadow: `0 0 20px ${tone.color}22`,
                      } : {}),
                    }}
                  >
                    <Icon size={22} color={isActive ? tone.color : 'var(--color-text-muted)'} />
                    <span style={{
                      ...styles.toneName,
                      color: isActive ? tone.color : 'var(--color-text)',
                    }}>
                      {tone.label}
                    </span>
                    <span style={styles.toneDesc}>{tone.description}</span>
                    {isActive && (
                      <div style={{ ...styles.activeDot, background: tone.color }} />
                    )}
                  </button>
                )
              })}
            </div>
          </div>

          {/* Instrucciones personalizadas */}
          <div style={styles.field}>
            <label style={styles.fieldLabel}>
              <Globe size={14} />
              Instrucciones permanentes
              <span className="settings-badge" style={styles.fieldBadge}>Contexto persistente</span>
            </label>
            <textarea
              value={settings?.custom_instructions || ''}
              onChange={e => update('custom_instructions', e.target.value)}
              placeholder={`Escribe aquí todo lo que quieras que Marco recuerde siempre sobre ti.\n\nEjemplos:\n• Soy estudiante de máster en IA\n• Mi objetivo financiero es ahorrar 300€ al mes\n• Prefiero respuestas cortas y directas\n• Trabajo en el sector tecnológico`}
              style={styles.textarea}
              rows={6}
              maxLength={1000}
            />
            <div style={styles.charCount}>
              {(settings?.custom_instructions || '').length}/1000 caracteres
            </div>
          </div>
        </section>

        {/* ── Sección: Notificaciones ────────────────────────────────── */}
        <section style={styles.section}>
          <div style={styles.sectionHeader}>
            <div style={{ ...styles.sectionIconWrap, background: 'rgba(69, 123, 157, 0.15)' }}>
              <Bell size={20} color="var(--color-calendar)" />
            </div>
            <div>
              <h2 style={styles.sectionTitle}>Resumen Diario</h2>
              <p style={styles.sectionDesc}>Recibe un correo cada mañana con lo más importante</p>
            </div>
          </div>

          {/* Toggle principal */}
          <div style={styles.toggleRow}>
            <div style={styles.toggleInfo}>
              {settings?.notifications_enabled
                ? <Bell size={18} color="var(--color-calendar)" />
                : <BellOff size={18} color="var(--color-text-faint)" />
              }
              <div>
                <span style={styles.toggleLabel}>
                  Resumen diario por correo
                </span>
                <span style={styles.toggleSub}>
                  Se enviará a tu cuenta de Google
                </span>
              </div>
            </div>
            <button
              onClick={() => update('notifications_enabled', !settings?.notifications_enabled)}
              style={{
                ...styles.toggle,
                background: settings?.notifications_enabled
                  ? 'var(--color-calendar)'
                  : 'var(--color-surface-3)',
              }}
              role="switch"
              aria-checked={settings?.notifications_enabled}
            >
              <div style={{
                ...styles.toggleKnob,
                transform: settings?.notifications_enabled ? 'translateX(22px)' : 'translateX(0)',
              }} />
            </button>
          </div>

          {/* Sub-settings, visible when enabled */}
          {settings?.notifications_enabled && (
            <div style={styles.subSettings}>
              {/* Hour picker */}
              <div style={styles.field}>
                <label style={styles.fieldLabel}>
                  <Clock size={14} />
                  Hora de envío
                </label>
                <div style={styles.hourRow}>
                  <select
                    value={settings?.notification_hour ?? 8}
                    onChange={e => autoSaveField('notification_hour', parseInt(e.target.value, 10))}
                    style={styles.select}
                  >
                    {HOURS.map(h => (
                      <option key={h} value={h}>
                        {String(h).padStart(2, '0')}:00
                      </option>
                    ))}
                  </select>
                  <span style={{ fontSize: 13, color: 'var(--color-text-muted)' }}>
                    hora local (Europa/Madrid)
                  </span>
                </div>
              </div>

              {/* Content checkboxes */}
              <div style={styles.field}>
                <label style={styles.fieldLabel}>
                  <Mail size={14} />
                  Contenido del resumen
                </label>
                <div style={styles.checkList}>
                  <CheckRow
                    icon={CalendarDays}
                    color="var(--color-calendar)"
                    label="Eventos del día"
                    desc="Qué tienes en el calendario hoy"
                    checked={settings?.notify_calendar ?? true}
                    onChange={v => update('notify_calendar', v)}
                  />
                  <CheckRow
                    icon={Activity}
                    color="var(--color-habits)"
                    label="Hábitos pendientes"
                    desc="Qué hábitos te quedan por completar"
                    checked={settings?.notify_habits ?? true}
                    onChange={v => update('notify_habits', v)}
                  />
                  <CheckRow
                    icon={TrendingUp}
                    color="var(--color-finance)"
                    label="Balance del mes"
                    desc="Resumen de ingresos y gastos mensuales"
                    checked={settings?.notify_finance ?? false}
                    onChange={v => update('notify_finance', v)}
                  />
                </div>
              </div>
            </div>
          )}
        </section>
      </div>
    </div>
  )
}

// ── Sub-component: checkbox row ────────────────────────────────────────────
function CheckRow({ icon: Icon, color, label, desc, checked, onChange }) {
  return (
    <button
      onClick={() => onChange(!checked)}
      style={{
        ...styles.checkRow,
        background: checked ? `${color}10` : 'var(--color-surface-2)',
        borderColor: checked ? `${color}40` : 'var(--color-border-subtle)',
      }}
    >
      <div style={{ ...styles.checkIcon, background: `${color}20` }}>
        <Icon size={15} color={color} />
      </div>
      <div style={styles.checkText}>
        <span style={styles.checkLabel}>{label}</span>
        <span style={styles.checkDesc}>{desc}</span>
      </div>
      <div style={{
        ...styles.checkbox,
        background: checked ? color : 'transparent',
        borderColor: checked ? color : 'var(--color-text-faint)',
      }}>
        {checked && <CheckCircle2 size={12} color="white" />}
      </div>
    </button>
  )
}

// ── Styles ─────────────────────────────────────────────────────────────────
const styles = {
  root: {
    flex: 1,
    padding: 32,
    display: 'flex',
    flexDirection: 'column',
    gap: 28,
    overflowY: 'auto',
    maxWidth: 900,
    margin: '0 auto',
    width: '100%',
  },
  loadingScreen: {
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
  },
  header: {
    display: 'flex',
    alignItems: 'flex-start',
    justifyContent: 'space-between',
    flexWrap: 'wrap',
    gap: 16,
  },
  title: {
    fontSize: 28,
    fontFamily: 'var(--font-display)',
    fontWeight: 700,
    margin: 0,
    color: 'var(--color-text)',
  },
  subtitle: {
    fontSize: 14,
    color: 'var(--color-text-muted)',
    margin: '6px 0 0',
  },
  saveBtn: {
    display: 'flex',
    alignItems: 'center',
    gap: 8,
    padding: '10px 20px',
    border: 'none',
    borderRadius: 'var(--radius-md)',
    color: '#000',
    fontSize: 14,
    fontWeight: 700,
    cursor: 'pointer',
    transition: 'all 0.3s ease',
    boxShadow: '0 4px 15px rgba(212, 175, 55, 0.2)',
  },
  grid: {
    display: 'flex',
    flexDirection: 'column',
    gap: 24,
  },
  section: {
    background: 'var(--color-surface)',
    border: '1px solid var(--color-border-subtle)',
    borderRadius: 'var(--radius-lg)',
    padding: 28,
    display: 'flex',
    flexDirection: 'column',
    gap: 24,
  },
  sectionHeader: {
    display: 'flex',
    alignItems: 'flex-start',
    gap: 16,
    paddingBottom: 16,
    borderBottom: '1px solid var(--color-border-subtle)',
  },
  sectionIconWrap: {
    width: 44,
    height: 44,
    borderRadius: 10,
    background: 'rgba(212, 175, 55, 0.1)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    flexShrink: 0,
  },
  sectionTitle: {
    fontSize: 18,
    fontFamily: 'var(--font-display)',
    fontWeight: 600,
    margin: 0,
    color: 'var(--color-text)',
  },
  sectionDesc: {
    fontSize: 13,
    color: 'var(--color-text-muted)',
    margin: '4px 0 0',
  },
  field: {
    display: 'flex',
    flexDirection: 'column',
    gap: 10,
  },
  fieldLabel: {
    display: 'flex',
    alignItems: 'center',
    gap: 7,
    fontSize: 13,
    fontWeight: 600,
    color: 'var(--color-text)',
    letterSpacing: '0.02em',
  },
  fieldBadge: {
    marginLeft: 6,
    fontSize: 10,
    fontWeight: 700,
    letterSpacing: '0.06em',
    textTransform: 'uppercase',
    padding: '2px 7px',
    borderRadius: 20,
    background: 'rgba(212, 175, 55, 0.12)',
    color: 'var(--color-primary)',
  },
  toneGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(3, 1fr)',
    gap: 12,
  },
  toneCard: {
    position: 'relative',
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'flex-start',
    gap: 6,
    padding: '16px 18px',
    background: 'var(--color-surface-2)',
    border: '1px solid var(--color-border-subtle)',
    borderRadius: 'var(--radius-md)',
    cursor: 'pointer',
    transition: 'all 0.2s ease',
    textAlign: 'left',
  },
  toneName: {
    fontSize: 14,
    fontWeight: 600,
    marginTop: 4,
  },
  toneDesc: {
    fontSize: 12,
    color: 'var(--color-text-muted)',
    lineHeight: 1.4,
  },
  activeDot: {
    position: 'absolute',
    top: 12,
    right: 12,
    width: 8,
    height: 8,
    borderRadius: '50%',
  },
  textarea: {
    width: '100%',
    background: 'var(--color-surface-2)',
    border: '1px solid var(--color-border-subtle)',
    borderRadius: 'var(--radius-md)',
    color: 'var(--color-text)',
    fontSize: 14,
    lineHeight: 1.6,
    padding: '14px 16px',
    outline: 'none',
    resize: 'vertical',
    fontFamily: 'var(--font-sans)',
    boxSizing: 'border-box',
  },
  charCount: {
    fontSize: 12,
    color: 'var(--color-text-faint)',
    textAlign: 'right',
    marginTop: -4,
  },
  toggleRow: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: 16,
    padding: '16px 20px',
    background: 'var(--color-surface-2)',
    borderRadius: 'var(--radius-md)',
    border: '1px solid var(--color-border-subtle)',
  },
  toggleInfo: {
    display: 'flex',
    alignItems: 'center',
    gap: 14,
  },
  toggleLabel: {
    display: 'block',
    fontSize: 15,
    fontWeight: 600,
    color: 'var(--color-text)',
  },
  toggleSub: {
    display: 'block',
    fontSize: 12,
    color: 'var(--color-text-muted)',
    marginTop: 2,
  },
  toggle: {
    position: 'relative',
    width: 46,
    height: 24,
    borderRadius: 99,
    border: 'none',
    cursor: 'pointer',
    transition: 'background 0.25s ease',
    flexShrink: 0,
  },
  toggleKnob: {
    position: 'absolute',
    top: 3,
    left: 3,
    width: 18,
    height: 18,
    borderRadius: '50%',
    background: 'white',
    transition: 'transform 0.25s ease',
    boxShadow: '0 1px 4px rgba(0,0,0,0.4)',
  },
  subSettings: {
    display: 'flex',
    flexDirection: 'column',
    gap: 20,
    paddingTop: 4,
  },
  hourRow: {
    display: 'flex',
    alignItems: 'center',
    gap: 14,
  },
  select: {
    background: 'var(--color-surface-2)',
    border: '1px solid var(--color-border-subtle)',
    borderRadius: 'var(--radius-md)',
    color: 'var(--color-text)',
    fontSize: 14,
    fontWeight: 600,
    padding: '8px 14px',
    outline: 'none',
    cursor: 'pointer',
    fontFamily: 'var(--font-sans)',
  },
  checkList: {
    display: 'flex',
    flexDirection: 'column',
    gap: 8,
  },
  checkRow: {
    display: 'flex',
    alignItems: 'center',
    gap: 14,
    padding: '12px 16px',
    borderRadius: 'var(--radius-md)',
    border: '1px solid',
    cursor: 'pointer',
    transition: 'all 0.2s ease',
    textAlign: 'left',
    width: '100%',
  },
  checkIcon: {
    width: 34,
    height: 34,
    borderRadius: 8,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    flexShrink: 0,
  },
  checkText: {
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
    gap: 2,
  },
  checkLabel: {
    fontSize: 14,
    fontWeight: 600,
    color: 'var(--color-text)',
  },
  checkDesc: {
    fontSize: 12,
    color: 'var(--color-text-muted)',
  },
  checkbox: {
    width: 22,
    height: 22,
    borderRadius: 6,
    border: '1.5px solid',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    transition: 'all 0.2s ease',
    flexShrink: 0,
  },
}
