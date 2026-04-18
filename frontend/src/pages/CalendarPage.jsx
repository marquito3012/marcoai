/**
 * CalendarPage – Google Calendar Dashboard (Fase 6)
 *
 * Features:
 *   • Monthly calendar view with event indicators
 *   • Week view with time slots
 *   • Event creation modal
 *   • Integration with Google Calendar API via backend
 *   • Sync status indicator
 */
import { useEffect, useState, useMemo } from 'react'
import {
  ChevronLeft,
  ChevronRight,
  Plus,
  Calendar as CalendarIcon,
  Clock,
  MapPin,
  Users,
  RefreshCw,
  ExternalLink,
} from 'lucide-react'
import { apiFetch } from '../lib/api.js'

// ── Helper: date utilities ───────────────────────────────────────────────────
const DAYS = ['Dom', 'Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb']
const MONTHS = [
  'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
  'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'
]

function getDaysInMonth(year, month) {
  return new Date(year, month + 1, 0).getDate()
}

function getFirstDayOfMonth(year, month) {
  return new Date(year, month, 1).getDay()
}

function formatDateKey(date) {
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`
}

function parseGoogleDate(dateObj) {
  if (!dateObj) return null
  const dateTime = dateObj.dateTime || dateObj.date
  if (!dateTime) return null
  return new Date(dateTime.replace('Z', '+00:00'))
}

function formatTime(date) {
  if (!date) return ''
  return date.toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' })
}

function formatDay(date) {
  if (!date) return ''
  return date.toLocaleDateString('es-ES', { day: 'numeric' })
}

// ── Main component ───────────────────────────────────────────────────────────
export default function CalendarPage() {
  const [currentDate, setCurrentDate] = useState(new Date())
  const [events, setEvents] = useState([])
  const [loading, setLoading] = useState(true)
  const [syncing, setSyncing] = useState(false)
  const [view, setView] = useState('month') // 'month' | 'week'
  const [selectedEvent, setSelectedEvent] = useState(null)
  const [showCreateModal, setShowCreateModal] = useState(false)

  // Fetch events from backend
  const fetchEvents = async () => {
    try {
      setLoading(true)
      
      let start, end;
      if (view === 'month') {
        const y = currentDate.getFullYear()
        const m = currentDate.getMonth()
        start = new Date(y, m, 1, 0, 0, 0).toISOString()
        end = new Date(y, m + 1, 0, 23, 59, 59).toISOString()
      } else {
        const d = new Date(currentDate)
        const day = d.getDay()
        const diff = d.getDate() - day
        const startOfWeek = new Date(d.setDate(diff))
        startOfWeek.setHours(0, 0, 0, 0)
        
        const endOfWeek = new Date(startOfWeek)
        endOfWeek.setDate(startOfWeek.getDate() + 6)
        endOfWeek.setHours(23, 59, 59, 999)
        
        start = startOfWeek.toISOString()
        end = endOfWeek.toISOString()
      }

      const data = await apiFetch(`/calendar/events?time_min=${start}&time_max=${end}`)
      setEvents(data.events || [])
    } catch (err) {
      console.error('Error fetching calendar events:', err)
      setEvents([])
    } finally {
      setLoading(false)
    }
  }

  const handleSync = async () => {
    setSyncing(true)
    await fetchEvents()
    setSyncing(false)
  }

  useEffect(() => {
    fetchEvents()
  }, [currentDate, view]) // eslint-disable-line react-hooks/exhaustive-deps

  // Calendar grid computation
  const calendarGrid = useMemo(() => {
    const year = currentDate.getFullYear()
    const month = currentDate.getMonth()
    const daysInMonth = getDaysInMonth(year, month)
    const firstDay = getFirstDayOfMonth(year, month)

    const days = []
    // Previous month padding
    for (let i = 0; i < firstDay; i++) {
      days.push({ type: 'padding', key: `pad-${i}` })
    }
    // Current month days
    for (let day = 1; day <= daysInMonth; day++) {
      const date = new Date(year, month, day)
      const key = formatDateKey(date)
      const dayEvents = events.filter(e => {
        const start = parseGoogleDate(e.start)
        return start && formatDateKey(start) === key
      })
      days.push({
        type: 'day',
        date,
        key,
        day,
        events: dayEvents,
        isToday: formatDateKey(new Date()) === key,
      })
    }
    return days
  }, [currentDate, events])

  const goToPrevious = () => {
    if (view === 'month') {
      setCurrentDate(new Date(currentDate.getFullYear(), currentDate.getMonth() - 1, 1))
    } else {
      const d = new Date(currentDate)
      d.setDate(d.getDate() - 7)
      setCurrentDate(d)
    }
  }

  const goToNext = () => {
    if (view === 'month') {
      setCurrentDate(new Date(currentDate.getFullYear(), currentDate.getMonth() + 1, 1))
    } else {
      const d = new Date(currentDate)
      d.setDate(d.getDate() + 7)
      setCurrentDate(d)
    }
  }

  const goToToday = () => {
    setCurrentDate(new Date())
  }

  return (
    <div className="calendar-root" style={styles.root}>
      {/* ── Header ───────────────────────────────────────────────────────── */}
      <header style={styles.header}>
        <div style={styles.headerLeft}>
          <div style={styles.navGroup}>
            <button onClick={goToPrevious} style={styles.navBtn} aria-label="Anterior">
              <ChevronLeft size={20} />
            </button>
            <button onClick={goToNext} style={styles.navBtn} aria-label="Siguiente">
              <ChevronRight size={20} />
            </button>
          </div>
          <h1 style={styles.title}>
            {MONTHS[currentDate.getMonth()]} <span style={{ color: 'var(--color-primary)', fontWeight: 300 }}>{currentDate.getFullYear()}</span>
          </h1>
          <button onClick={goToToday} style={styles.todayBtn}>
            Hoy
          </button>
        </div>

        <div style={styles.headerRight}>
          {/* View toggle */}
          <div style={styles.viewToggle}>
            <button
              onClick={() => setView('month')}
              style={{
                ...styles.viewBtn,
                ...(view === 'month' ? styles.viewBtnActive : {}),
              }}
            >
              Mes
            </button>
            <button
              onClick={() => setView('week')}
              style={{
                ...styles.viewBtn,
                ...(view === 'week' ? styles.viewBtnActive : {}),
              }}
            >
              Semana
            </button>
          </div>

          {/* Sync button */}
          <button
            onClick={handleSync}
            disabled={syncing}
            style={{
              ...styles.syncBtn,
              opacity: syncing ? 0.6 : 1,
            }}
            title="Sincronizar con Google Calendar"
          >
            <RefreshCw size={16} className={syncing ? 'spin' : ''} />
            <span style={{ fontSize: 13 }}>{syncing ? 'Sincronizando...' : 'Sincronizar'}</span>
          </button>

          {/* Create event button */}
          <button onClick={() => setShowCreateModal(true)} style={styles.createBtn}>
            <Plus size={18} />
            <span style={{ fontSize: 13 }}>Crear evento</span>
          </button>
        </div>
      </header>

      {/* ── Content ──────────────────────────────────────────────────────── */}
      <div style={styles.content}>
        {view === 'month' ? (
          <MonthView
            grid={calendarGrid}
            loading={loading}
            onEventClick={setSelectedEvent}
          />
        ) : (
          <WeekView
            currentDate={currentDate}
            events={events}
            loading={loading}
            onEventClick={setSelectedEvent}
          />
        )}
      </div>

      {/* ── Event detail modal ─────────────────────────────────────────── */}
      {selectedEvent && (
        <EventDetailModal
          event={selectedEvent}
          onClose={() => setSelectedEvent(null)}
        />
      )}

      {/* ── Create event modal ─────────────────────────────────────────── */}
      {showCreateModal && (
        <CreateEventModal
          onClose={() => setShowCreateModal(false)}
          onCreated={() => {
            setShowCreateModal(false)
            fetchEvents()
          }}
        />
      )}
    </div>
  )
}

// ── Month View ───────────────────────────────────────────────────────────────
function MonthView({ grid, loading, onEventClick }) {
  return (
    <div className="calendar-month-view" style={styles.monthView}>
      {/* Day headers */}
      <div style={styles.weekDaysRow}>
        {DAYS.map(day => (
          <div key={day} style={styles.weekDayHeader}>{day}</div>
        ))}
      </div>

      {/* Calendar grid */}
      <div style={styles.calendarGrid}>
        {loading ? (
          <div style={styles.loadingState}>
            <RefreshCw size={24} className="spin" />
            <span style={{ color: 'var(--color-text-muted)' }}>Cargando eventos...</span>
          </div>
        ) : (
          grid.map((cell) => {
            if (cell.type === 'padding') {
              return <div key={cell.key} style={styles.emptyCell} />
            }
            return (
              <div
                key={cell.key}
                style={{
                  ...styles.dayCell,
                  ...(cell.isToday ? styles.todayCell : {}),
                }}
              >
                <div style={styles.dayNumber}>{cell.day}</div>
                <div style={styles.eventsList}>
                  {cell.events.slice(0, 3).map(event => (
                    <button
                      key={event.id}
                      onClick={() => onEventClick(event)}
                      className="event-chip"
                      style={styles.eventChip}
                      title={event.summary}
                    >
                      {event.summary}
                    </button>
                  ))}
                  {cell.events.length > 3 && (
                    <div style={styles.moreEvents}>
                      +{cell.events.length - 3} más
                    </div>
                  )}
                </div>
              </div>
            )
          })
        )}
      </div>
    </div>
  )
}

// ── Week View ────────────────────────────────────────────────────────────────
function WeekView({ currentDate, events, loading, onEventClick }) {
  const weekDays = useMemo(() => {
    const startOfWeek = new Date(currentDate)
    startOfWeek.setDate(currentDate.getDate() - currentDate.getDay())

    const days = []
    for (let i = 0; i < 7; i++) {
      const date = new Date(startOfWeek)
      date.setDate(startOfWeek.getDate() + i)
      days.push(date)
    }
    return days
  }, [currentDate])

  const hours = Array.from({ length: 24 }, (_, i) => i)

  return (
    <div style={styles.weekView}>
      {/* Day headers */}
      <div style={styles.weekHeaderRow}>
        <div style={styles.hourLabel} />
        {weekDays.map((date, i) => {
          const key = formatDateKey(date)
          const isToday = key === formatDateKey(new Date())
          return (
            <div
              key={i}
              style={{
                ...styles.weekDayColumn,
                ...(isToday ? styles.todayColumn : {}),
              }}
            >
              <div style={styles.weekDayName}>{DAYS[date.getDay()]}</div>
              <div style={{
                ...styles.weekDayNumber,
                ...(isToday ? styles.todayNumber : {}),
              }}>
                {date.getDate()}
              </div>
            </div>
          )
        })}
      </div>

      {/* Time slots */}
      <div style={styles.weekGrid}>
        {hours.map(hour => (
          <div key={hour} style={styles.hourRow}>
            <div style={styles.hourLabel}>{String(hour).padStart(2, '0')}:00</div>
            {weekDays.map((date, i) => {
              const key = formatDateKey(date)
              const hourEvents = events.filter(e => {
                const start = parseGoogleDate(e.start)
                return start && formatDateKey(start) === key && start.getHours() === hour
              })
              return (
                <div key={i} style={styles.weekCell}>
                  {hourEvents.map(event => (
                    <button
                      key={event.id}
                      onClick={() => onEventClick(event)}
                      style={styles.weekEvent}
                    >
                      <div style={styles.weekEventTitle}>{event.summary}</div>
                      <div style={styles.weekEventTime}>
                        {formatTime(parseGoogleDate(event.start))}
                      </div>
                    </button>
                  ))}
                </div>
              )
            })}
          </div>
        ))}
      </div>
    </div>
  )
}

// ── Event Detail Modal ───────────────────────────────────────────────────────
function EventDetailModal({ event, onClose }) {
  const startDate = parseGoogleDate(event.start)
  const endDate = parseGoogleDate(event.end)

  return (
    <div style={styles.modalOverlay} onClick={onClose}>
      <div style={styles.modalContent} onClick={e => e.stopPropagation()}>
        <div style={styles.modalHeader}>
          <h2 style={styles.modalTitle}>{event.summary}</h2>
          <button onClick={onClose} style={styles.closeBtn} aria-label="Cerrar">
            ×
          </button>
        </div>

        <div style={styles.modalBody}>
          {startDate && (
            <div style={styles.detailRow}>
              <Clock size={18} color="var(--color-text-muted)" />
              <span>
                {startDate.toLocaleDateString('es-ES', {
                  weekday: 'long',
                  year: 'numeric',
                  month: 'long',
                  day: 'numeric',
                })}
                {' · '}
                {formatTime(startDate)} - {endDate ? formatTime(endDate) : '...'}
              </span>
            </div>
          )}

          {event.location && (
            <div style={styles.detailRow}>
              <MapPin size={18} color="var(--color-text-muted)" />
              <span>{event.location}</span>
            </div>
          )}

          {event.attendees && event.attendees.length > 0 && (
            <div style={styles.detailRow}>
              <Users size={18} color="var(--color-text-muted)" />
              <span>{event.attendees.map(a => a.email).join(', ')}</span>
            </div>
          )}

          {event.description && (
            <div style={styles.descriptionBlock}>
              <p style={{ whiteSpace: 'pre-wrap' }}>{event.description}</p>
            </div>
          )}
        </div>

        {event.htmlLink && (
          <div style={styles.modalFooter}>
            <a
              href={event.htmlLink}
              target="_blank"
              rel="noopener noreferrer"
              style={styles.googleLink}
            >
              <ExternalLink size={16} />
              Abrir en Google Calendar
            </a>
          </div>
        )}
      </div>
    </div>
  )
}

// ── Create Event Modal ───────────────────────────────────────────────────────
function CreateEventModal({ onClose, onCreated }) {
  const [formData, setFormData] = useState({
    summary: '',
    description: '',
    location: '',
    start_date: formatDateKey(new Date()),
    start_time: '09:00',
    end_date: formatDateKey(new Date()),
    end_time: '10:00',
  })
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState(null)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setSubmitting(true)
    setError(null)

    try {
      const start_datetime = `${formData.start_date}T${formData.start_time}:00`
      const end_datetime = `${formData.end_date}T${formData.end_time}:00`

      await apiFetch('/calendar/events', {
        method: 'POST',
        body: JSON.stringify({
          summary: formData.summary,
          description: formData.description || null,
          location: formData.location || null,
          start_datetime,
          end_datetime,
        }),
      })

      onCreated()
    } catch (err) {
      setError(err.message || 'Error al crear el evento')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div style={styles.modalOverlay} onClick={onClose}>
      <div style={styles.modalContent} onClick={e => e.stopPropagation()}>
        <div style={styles.modalHeader}>
          <h2 style={styles.modalTitle}>Crear evento</h2>
          <button onClick={onClose} style={styles.closeBtn} aria-label="Cerrar">
            ×
          </button>
        </div>

        <form onSubmit={handleSubmit} style={styles.form}>
          <div style={styles.formGroup}>
            <label style={styles.label}>Título</label>
            <input
              type="text"
              value={formData.summary}
              onChange={e => setFormData({ ...formData, summary: e.target.value })}
              style={styles.input}
              placeholder="Ej: Reunión con equipo"
              required
              autoFocus
            />
          </div>

          <div style={styles.formRow}>
            <div style={styles.formGroup}>
              <label style={styles.label}>Fecha inicio</label>
              <input
                type="date"
                value={formData.start_date}
                onChange={e => setFormData({ ...formData, start_date: e.target.value })}
                style={styles.input}
                required
              />
            </div>
            <div style={styles.formGroup}>
              <label style={styles.label}>Hora inicio</label>
              <input
                type="time"
                value={formData.start_time}
                onChange={e => setFormData({ ...formData, start_time: e.target.value })}
                style={styles.input}
                required
              />
            </div>
          </div>

          <div style={styles.formRow}>
            <div style={styles.formGroup}>
              <label style={styles.label}>Fecha fin</label>
              <input
                type="date"
                value={formData.end_date}
                onChange={e => setFormData({ ...formData, end_date: e.target.value })}
                style={styles.input}
                required
              />
            </div>
            <div style={styles.formGroup}>
              <label style={styles.label}>Hora fin</label>
              <input
                type="time"
                value={formData.end_time}
                onChange={e => setFormData({ ...formData, end_time: e.target.value })}
                style={styles.input}
                required
              />
            </div>
          </div>

          <div style={styles.formGroup}>
            <label style={styles.label}>Ubicación (opcional)</label>
            <input
              type="text"
              value={formData.location}
              onChange={e => setFormData({ ...formData, location: e.target.value })}
              style={styles.input}
              placeholder="Ej: Oficina, Zoom..."
            />
          </div>

          <div style={styles.formGroup}>
            <label style={styles.label}>Descripción (opcional)</label>
            <textarea
              value={formData.description}
              onChange={e => setFormData({ ...formData, description: e.target.value })}
              style={{ ...styles.input, minHeight: 80, resize: 'vertical' }}
              placeholder="Detalles adicionales..."
              rows={3}
            />
          </div>

          {error && <p style={styles.errorText}>{error}</p>}

          <div style={styles.formActions}>
            <button type="button" onClick={onClose} style={styles.cancelBtn}>
              Cancelar
            </button>
            <button
              type="submit"
              disabled={submitting}
              style={{
                ...styles.submitBtn,
                opacity: submitting ? 0.6 : 1,
              }}
            >
              {submitting ? 'Creando...' : 'Crear evento'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

// ── Styles ───────────────────────────────────────────────────────────────────
const styles = {
  root: {
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
    height: '100%',
    overflow: 'hidden',
    padding: 24,
    gap: 20,
  },
  header: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    flexShrink: 0,
  },
  headerLeft: {
    display: 'flex',
    alignItems: 'center',
    gap: 16,
  },
  headerRight: {
    display: 'flex',
    alignItems: 'center',
    gap: 12,
  },
  navGroup: {
    display: 'flex',
    borderRadius: 8,
    border: '1px solid var(--color-border-subtle)',
    overflow: 'hidden',
  },
  navBtn: {
    padding: 8,
    background: 'transparent',
    border: 'none',
    cursor: 'pointer',
    color: 'var(--color-text)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
  },
  title: {
    fontSize: 24,
    fontFamily: 'var(--font-display)',
    fontWeight: 700,
    color: 'var(--color-text)',
    margin: 0,
    minWidth: 200,
    textAlign: 'center',
    letterSpacing: '-0.01em',
  },
  todayBtn: {
    padding: '6px 14px',
    fontSize: 13,
    fontWeight: 500,
    background: 'var(--color-surface-2)',
    border: '1px solid var(--color-border-subtle)',
    borderRadius: 6,
    color: 'var(--color-text)',
    cursor: 'pointer',
  },
  viewToggle: {
    display: 'flex',
    borderRadius: 6,
    border: '1px solid var(--color-border-subtle)',
    overflow: 'hidden',
  },
  viewBtn: {
    padding: '6px 12px',
    fontSize: 13,
    fontWeight: 500,
    background: 'transparent',
    border: 'none',
    cursor: 'pointer',
    color: 'var(--color-text-muted)',
  },
  viewBtnActive: {
    background: 'var(--color-primary)',
    color: '#000',
    fontWeight: 700,
  },
  syncBtn: {
    display: 'flex',
    alignItems: 'center',
    gap: 6,
    padding: '6px 12px',
    fontSize: 13,
    fontWeight: 500,
    background: 'var(--color-surface-2)',
    border: '1px solid var(--color-border-subtle)',
    borderRadius: 6,
    color: 'var(--color-text)',
    cursor: 'pointer',
  },
  createBtn: {
    display: 'flex',
    alignItems: 'center',
    gap: 6,
    padding: '8px 14px',
    fontSize: 13,
    fontWeight: 700,
    background: 'linear-gradient(135deg, var(--color-primary), var(--color-primary-dark))',
    border: 'none',
    borderRadius: 'var(--radius-md)',
    color: '#000',
    cursor: 'pointer',
    boxShadow: '0 4px 15px rgba(212, 175, 55, 0.2)',
  },
  content: {
    flex: 1,
    overflow: 'hidden',
    display: 'flex',
    flexDirection: 'column',
  },
  monthView: {
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
    overflow: 'hidden',
  },
  weekDaysRow: {
    display: 'grid',
    gridTemplateColumns: 'repeat(7, 1fr)',
    gap: 1,
    padding: '0 0 8px',
    borderBottom: '1px solid var(--color-border-subtle)',
  },
  weekDayHeader: {
    fontSize: 12,
    fontWeight: 600,
    color: 'var(--color-text-faint)',
    textTransform: 'uppercase',
    letterSpacing: '0.05em',
    textAlign: 'center',
    padding: 8,
  },
  calendarGrid: {
    flex: 1,
    display: 'grid',
    gridTemplateColumns: 'repeat(7, 1fr)',
    gap: 1,
    overflow: 'auto',
  },
  dayCell: {
    minHeight: 100,
    padding: 8,
    border: '1px solid var(--color-border-subtle)',
    background: 'var(--color-surface)',
    display: 'flex',
    flexDirection: 'column',
    gap: 4,
  },
  todayCell: {
    background: 'var(--color-primary-alpha)',
    borderColor: 'var(--color-primary)',
  },
  emptyCell: {
    background: 'var(--color-surface-2)',
    border: '1px solid var(--color-border-subtle)',
  },
  dayNumber: {
    fontSize: 13,
    fontWeight: 600,
    color: 'var(--color-text)',
    marginBottom: 4,
  },
  eventsList: {
    display: 'flex',
    flexDirection: 'column',
    gap: 2,
    overflow: 'hidden',
  },
  eventChip: {
    padding: '3px 6px',
    fontSize: 11,
    fontWeight: 500,
    background: 'var(--color-primary-alpha)',
    border: 'none',
    borderRadius: 3,
    color: 'var(--color-primary)',
    cursor: 'pointer',
    textAlign: 'left',
    whiteSpace: 'nowrap',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    display: 'block',
    width: '100%',
  },
  moreEvents: {
    fontSize: 11,
    color: 'var(--color-text-muted)',
    padding: '2px 4px',
  },
  loadingState: {
    gridColumn: '1 / -1',
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 12,
    padding: 60,
  },
  weekView: {
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
    overflow: 'hidden',
  },
  weekHeaderRow: {
    display: 'grid',
    gridTemplateColumns: '60px repeat(7, 1fr)',
    gap: 1,
    padding: '0 0 8px',
    borderBottom: '1px solid var(--color-border-subtle)',
  },
  hourLabel: {
    fontSize: 11,
    color: 'var(--color-text-faint)',
    textAlign: 'right',
    padding: '8px 8px 8px 0',
  },
  weekDayColumn: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    padding: 8,
  },
  todayColumn: {
    background: 'var(--color-primary-alpha)',
  },
  weekDayName: {
    fontSize: 11,
    fontWeight: 600,
    color: 'var(--color-text-faint)',
    textTransform: 'uppercase',
  },
  weekDayNumber: {
    fontSize: 18,
    fontWeight: 600,
    color: 'var(--color-text)',
    marginTop: 2,
  },
  todayNumber: {
    background: 'var(--color-primary)',
    color: 'white',
    width: 32,
    height: 32,
    borderRadius: '50%',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
  },
  weekGrid: {
    flex: 1,
    overflow: 'auto',
  },
  hourRow: {
    display: 'grid',
    gridTemplateColumns: '60px repeat(7, 1fr)',
    gap: 1,
    borderBottom: '1px solid var(--color-border-subtle)',
    minHeight: 50,
  },
  weekCell: {
    padding: 4,
    background: 'var(--color-surface)',
  },
  weekEvent: {
    padding: '4px 8px',
    background: 'var(--color-primary-alpha)',
    border: '1px solid var(--color-primary)',
    borderRadius: 4,
    textAlign: 'left',
    cursor: 'pointer',
    marginBottom: 2,
  },
  weekEventTitle: {
    fontSize: 12,
    fontWeight: 600,
    color: 'var(--color-primary)',
  },
  weekEventTime: {
    fontSize: 10,
    color: 'var(--color-text-muted)',
  },
  modalOverlay: {
    position: 'fixed',
    inset: 0,
    background: 'rgba(0, 0, 0, 0.5)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    zIndex: 1000,
    padding: 20,
  },
  modalContent: {
    background: 'var(--color-surface)',
    borderRadius: 12,
    border: '1px solid var(--color-border-subtle)',
    maxWidth: 500,
    width: '100%',
    maxHeight: '90vh',
    overflow: 'auto',
  },
  modalHeader: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: 16,
    borderBottom: '1px solid var(--color-border-subtle)',
  },
  modalTitle: {
    fontSize: 18,
    fontFamily: 'var(--font-display)',
    fontWeight: 600,
    color: 'var(--color-text)',
    margin: 0,
  },
  closeBtn: {
    background: 'transparent',
    border: 'none',
    fontSize: 24,
    color: 'var(--color-text-muted)',
    cursor: 'pointer',
    width: 32,
    height: 32,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
  },
  modalBody: {
    padding: 16,
    display: 'flex',
    flexDirection: 'column',
    gap: 12,
  },
  detailRow: {
    display: 'flex',
    alignItems: 'flex-start',
    gap: 10,
    fontSize: 14,
    color: 'var(--color-text)',
  },
  descriptionBlock: {
    marginTop: 8,
    padding: 12,
    background: 'var(--color-surface-2)',
    borderRadius: 8,
    fontSize: 14,
    color: 'var(--color-text-muted)',
  },
  modalFooter: {
    padding: 16,
    borderTop: '1px solid var(--color-border-subtle)',
    display: 'flex',
    justifyContent: 'flex-end',
  },
  googleLink: {
    display: 'flex',
    alignItems: 'center',
    gap: 6,
    padding: '8px 12px',
    fontSize: 13,
    fontWeight: 500,
    color: 'var(--color-primary)',
    textDecoration: 'none',
    background: 'var(--color-primary-alpha)',
    borderRadius: 6,
  },
  form: {
    padding: 16,
    display: 'flex',
    flexDirection: 'column',
    gap: 16,
  },
  formGroup: {
    display: 'flex',
    flexDirection: 'column',
    gap: 6,
  },
  formRow: {
    display: 'grid',
    gridTemplateColumns: '1fr 1fr',
    gap: 12,
  },
  label: {
    fontSize: 13,
    fontWeight: 500,
    color: 'var(--color-text)',
  },
  input: {
    padding: 10,
    fontSize: 14,
    background: 'var(--color-surface-2)',
    border: '1px solid var(--color-border-subtle)',
    borderRadius: 6,
    color: 'var(--color-text)',
    outline: 'none',
  },
  errorText: {
    fontSize: 13,
    color: 'var(--color-error)',
    margin: 0,
  },
  formActions: {
    display: 'flex',
    justifyContent: 'flex-end',
    gap: 10,
    paddingTop: 8,
  },
  cancelBtn: {
    padding: '8px 16px',
    fontSize: 14,
    fontWeight: 500,
    background: 'transparent',
    border: '1px solid var(--color-border-subtle)',
    borderRadius: 6,
    color: 'var(--color-text)',
    cursor: 'pointer',
  },
  submitBtn: {
    padding: '8px 16px',
    fontSize: 14,
    fontWeight: 600,
    background: 'var(--color-primary)',
    border: 'none',
    borderRadius: 6,
    color: 'white',
    cursor: 'pointer',
  },
}
