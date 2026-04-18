/**
 * HabitsPage – Dashboard de Hábitos y Tareas (Fase 10)
 * ══════════════════════════════════════════════════════════════════════════════
 * 
 * Features:
 *   • GitHub-style Contribution Graph for habits
 *   • Daily habits checklist
 *   • Todo list with smart breakdown (LLM)
 *   • Premium dark-mode aesthetics
 */
import { useState, useEffect, useMemo } from 'react'
import { 
  CheckCircle2, 
  Circle, 
  Plus, 
  Zap, 
  ListTodo, 
  Activity,
  ChevronRight,
  Loader2,
  Sparkles,
  Trash2
} from 'lucide-react'
import { apiFetch } from '../lib/api.js'

export default function HabitsPage() {
  const [data, setData] = useState({ habits: [], other_habits: [], todos: [] })
  const [logs, setLogs] = useState([])
  const [loading, setLoading] = useState(true)
  const [newHabitName, setNewHabitName] = useState('')
  const [isCreating, setIsCreating] = useState(false)
  const [selectedDays, setSelectedDays] = useState([0,1,2,3,4,5,6])
  const DAYS = ['L', 'M', 'X', 'J', 'V', 'S', 'D']

  const toggleDay = (idx) => {
    if (selectedDays.includes(idx)) {
      setSelectedDays(selectedDays.filter(d => d !== idx))
    } else {
      setSelectedDays([...selectedDays, idx].sort())
    }
  }

  const fetchAll = async () => {
    try {
      setLoading(true)
      const [summary, logData] = await Promise.all([
        apiFetch('/habits/summary'),
        apiFetch('/habits/logs')
      ])
      setData(summary)
      setLogs(logData)
    } catch (err) {
      console.error('Error fetching habits data:', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchAll()
  }, [])

  const handleToggleHabit = async (habitId) => {
    const today = new Date().toISOString().split('T')[0]
    try {
      await apiFetch('/habits/track', {
        method: 'POST',
        body: JSON.stringify({ habit_id: habitId, date: today })
      })
      fetchAll() // Refresh both list and graph
    } catch (err) {
      console.error('Error tracking habit:', err)
    }
  }

  const handleCreateHabit = async (e) => {
    e.preventDefault()
    if (!newHabitName.trim() || isCreating) return
    setIsCreating(true)
    try {
      await apiFetch('/habits', {
        method: 'POST',
        body: JSON.stringify({ 
           name: newHabitName.trim(),
           target_days: selectedDays.length > 0 ? selectedDays.join(',') : "0,1,2,3,4,5,6"
        })
      })
      setNewHabitName('')
      setSelectedDays([0,1,2,3,4,5,6])
      fetchAll()
    } catch (err) {
      console.error('Error creating habit:', err)
    } finally {
      setIsCreating(false)
    }
  }

  const handleDeleteHabit = async (e, habitId) => {
    e.stopPropagation()
    if (!window.confirm('¿Seguro que quieres borrar este hábito? Esta acción no se puede deshacer.')) return
    try {
      await apiFetch(`/habits/${habitId}`, {
        method: 'DELETE'
      })
      fetchAll()
    } catch (err) {
      console.error('Error deleting habit:', err)
    }
  }

  return (
    <div className="habits-root" style={styles.root}>
      {/* ── Header ───────────────────────────────────────────────────────── */}
      <header style={styles.header}>
        <div style={styles.headerLeft}>
          <h1 style={styles.title}>Hábitos y Tareas</h1>
          <div style={styles.statsRow}>
            <div style={styles.statItem}>
              <Zap size={14} color="var(--color-warning)" />
              <span>{data.habits.filter(h => h.is_done_today).length}/{data.habits.length} Hoy</span>
            </div>
            <div style={styles.statItem}>
              <ListTodo size={14} color="var(--color-primary-light)" />
              <span>{data.todos.filter(t => !t.is_completed).length} Pendientes</span>
            </div>
          </div>
        </div>
      </header>

      <div className="habits-grid">
        {/* Left Column: Graph & Habits */}
        <div style={styles.leftCol}>
          {/* Contribution Graph Card */}
          <div style={styles.card} className="glass-card">
            <div style={styles.cardHeader}>
              <Activity size={18} color="var(--color-habits)" />
              <h3 style={styles.cardTitle}>Consistencia</h3>
            </div>
            <div style={styles.graphWrapper}>
              {loading ? <Loader2 className="spin" /> : <ContributionGraph logs={logs} />}
            </div>
          </div>

          {/* Daily Habits Card */}
          <div style={styles.card} className="glass-card">
            <div style={styles.cardHeader}>
              <Zap size={18} color="var(--color-warning)" />
              <h3 style={styles.cardTitle}>Hábitos de Hoy</h3>
            </div>
            <div style={styles.habitList}>
              {data.habits.map(habit => (
                <div 
                  key={habit.id} 
                  style={styles.habitItem}
                  onClick={() => handleToggleHabit(habit.id)}
                >
                  {habit.is_done_today ? (
                    <CheckCircle2 size={24} color="var(--color-success)" />
                  ) : (
                    <Circle size={24} color="var(--color-text-faint)" />
                  )}
                  <span style={{ 
                    ...styles.habitName,
                    ...(habit.is_done_today ? styles.textStrikethrough : {})
                  }}>
                    {habit.name}
                  </span>
                  <button 
                    style={styles.deleteBtn} 
                    onClick={(e) => handleDeleteHabit(e, habit.id)}
                    title="Borrar hábito"
                  >
                    <Trash2 size={16} />
                  </button>
                </div>
              ))}
              
              <form onSubmit={handleCreateHabit} style={styles.addHabitFormContainer}>
                <div style={styles.addHabitForm}>
                  <Plus size={16} color="var(--color-text-muted)" />
                  <input 
                    type="text" 
                    value={newHabitName}
                    onChange={(e) => setNewHabitName(e.target.value)}
                    placeholder="Añadir hábito..."
                    style={styles.addHabitInput}
                    disabled={isCreating}
                  />
                </div>
                {newHabitName.trim() !== '' && (
                  <div style={styles.habitCreationActions}>
                    <div style={styles.daySelector}>
                      {DAYS.map((d, idx) => (
                        <button 
                          key={idx} 
                          type="button"
                          onClick={() => toggleDay(idx)}
                          style={{
                            ...styles.dayBtn,
                            backgroundColor: selectedDays.includes(idx) ? 'var(--color-primary)' : 'var(--color-surface-3)',
                            color: selectedDays.includes(idx) ? 'white' : 'var(--color-text-muted)'
                          }}
                        >
                          {d}
                        </button>
                      ))}
                    </div>
                    <button 
                      type="submit" 
                      style={styles.saveHabitBtn}
                      disabled={isCreating}
                    >
                      {isCreating ? <Loader2 size={16} className="spin" /> : <CheckCircle2 size={16} />}
                      <span>{isCreating ? 'Guardando...' : 'Confirmar'}</span>
                    </button>
                  </div>
                )}
              </form>
            </div>
          </div>
        </div>

        {/* Right Column: Programmed Habits */}
        <div style={styles.rightCol}>
          <div style={styles.card} className="glass-card">
            <div style={styles.cardHeader}>
              <ListTodo size={18} color="var(--color-primary-light)" />
              <h3 style={styles.cardTitle}>Otros Hábitos</h3>
            </div>
            <div style={styles.habitList}>
              {data.other_habits && data.other_habits.length > 0 ? (
                data.other_habits.map(habit => (
                  <div key={habit.id} style={styles.habitItemOther}>
                    <div style={styles.habitItemOtherInfo}>
                      <span style={styles.habitNameOther}>{habit.name}</span>
                      <div style={styles.habitDaysTags}>
                        {(() => {
                           const days = habit.target_days ? habit.target_days.split(',').map(Number) : [0,1,2,3,4,5,6];
                           if (days.length === 7) return <span style={styles.dayTag}>Todos los días</span>;
                           return days.map(d => <span key={d} style={styles.dayTag}>{DAYS[d]}</span>)
                        })()}
                      </div>
                    </div>
                    <button 
                      style={styles.deleteBtn} 
                      onClick={(e) => handleDeleteHabit(e, habit.id)}
                      title="Borrar hábito"
                    >
                      <Trash2 size={16} />
                    </button>
                  </div>
                ))
              ) : (
                <div style={{color: 'var(--color-text-muted)', fontSize: 14}}>No tienes hábitos programados para otros días.</div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

function ContributionGraph({ logs }) {
  // Simple representation of the last 12 weeks
  const today = new Date()
  const days = []
  
  // Backtrack 84 days (12 weeks)
  for (let i = 83; i >= 0; i--) {
    const d = new Date()
    d.setDate(today.getDate() - i)
    const key = d.toISOString().split('T')[0]
    const log = logs.find(l => l.date === key)
    days.push({ key, count: log ? log.count : 0 })
  }

  return (
    <div className="habits-consistency-grid" style={styles.graphGrid}>
      {days.map(day => (
        <div 
          key={day.key} 
          style={{
            ...styles.graphCell,
            backgroundColor: day.count > 0 
              ? `rgba(244, 114, 182, ${Math.min(0.2 + day.count * 0.2, 1)})`
              : 'var(--color-surface-3)'
          }}
          title={`${day.key}: ${day.count} hábitos`}
        />
      ))}
    </div>
  )
}

const styles = {
  root: { flex: 1, padding: 24, display: 'flex', flexDirection: 'column', gap: 24, overflowY: 'auto' },
  header: { display: 'flex', flexDirection: 'column', gap: 8 },
  title: { fontSize: 24, margin: 0 },
  statsRow: { display: 'flex', gap: 16 },
  statItem: { display: 'flex', alignItems: 'center', gap: 6, fontSize: 13, color: 'var(--color-text-muted)' },
  leftCol: { display: 'flex', flexDirection: 'column', gap: 24 },
  rightCol: { display: 'flex', flexDirection: 'column', gap: 24 },
  card: { padding: 20, display: 'flex', flexDirection: 'column', gap: 16 },
  cardHeader: { display: 'flex', alignItems: 'center', gap: 10 },
  cardTitle: { fontSize: 16, margin: 0, fontWeight: 600 },
  cardSub: { fontSize: 13, color: 'var(--color-text-muted)', margin: '-10px 0 0' },
  
  // Habits List
  habitList: { display: 'flex', flexDirection: 'column', gap: 12 },
  habitItem: { 
    display: 'flex', alignItems: 'center', gap: 16, cursor: 'pointer',
    padding: '12px 16px', borderRadius: 'var(--radius-md)', background: 'var(--color-surface-2)',
    transition: 'transform 0.1s',
  },
  habitName: { fontSize: 15, fontWeight: 500, flex: 1 },
  textStrikethrough: { textDecoration: 'line-through', opacity: 0.6, color: 'var(--color-success)' },
  deleteBtn: { background: 'none', border: 'none', color: 'var(--color-text-faint)', cursor: 'pointer', display: 'flex', padding: 4 },
  addHabitFormContainer: { display: 'flex', flexDirection: 'column', gap: 8 },
  addHabitForm: { 
    display: 'flex', alignItems: 'center', gap: 12, padding: '8px 16px', 
    background: 'var(--color-surface-3)', borderRadius: 'var(--radius-md)',
    border: '1px solid var(--color-border-subtle)'
  },
  addHabitInput: { 
    flex: 1, background: 'transparent', border: 'none', color: 'var(--color-text)', 
    fontSize: 14, outline: 'none'
  },
  daySelector: { display: 'flex', gap: 6, justifyContent: 'center' },
  dayBtn: { width: 28, height: 28, borderRadius: '50%', border: 'none', cursor: 'pointer', fontSize: 12, fontWeight: 600, display: 'flex', alignItems: 'center', justifyContent: 'center', transition: 'all 0.2s' },
  habitCreationActions: { display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 16, marginTop: 4, padding: '0 8px' },
  saveHabitBtn: {
    display: 'flex', alignItems: 'center', gap: 8, padding: '8px 16px', borderRadius: 'var(--radius-md)',
    background: 'var(--color-primary)', color: 'white', border: 'none', cursor: 'pointer',
    fontSize: 13, fontWeight: 600, transition: 'all 0.2s'
  },
  habitItemOther: { display: 'flex', alignItems: 'center', gap: 12, padding: '12px', borderRadius: 'var(--radius-md)', background: 'var(--color-surface-2)' },
  habitItemOtherInfo: { flex: 1, display: 'flex', flexDirection: 'column', gap: 4 },
  habitNameOther: { fontSize: 14, fontWeight: 500, color: 'var(--color-text-muted)' },
  habitDaysTags: { display: 'flex', gap: 4, flexWrap: 'wrap' },
  dayTag: { fontSize: 10, padding: '2px 6px', borderRadius: 4, background: 'var(--color-surface-3)', color: 'var(--color-text-faint)' },
 
  // Graph
  graphWrapper: { padding: '8px 0' },
  graphGrid: { 
    display: 'grid', gridTemplateColumns: 'repeat(14, 1fr)', gridAutoRows: '20px', gap: 4,
    maxWidth: 'fit-content'
  },
  graphCell: { width: 20, height: 20, borderRadius: 3 },

  // Todos
  todoContent: { display: 'flex', flexDirection: 'column', gap: 16 },
  todoInputBox: { display: 'flex', gap: 8 },
  todoInput: { 
    flex: 1, background: 'var(--color-surface-3)', border: '1px solid var(--color-border-subtle)',
    borderRadius: 'var(--radius-md)', padding: '10px 14px', color: 'var(--color-text)', fontSize: 14, outline: 'none'
  },
  todoAddBtn: { 
    background: 'var(--color-primary)', border: 'none', borderRadius: 'var(--radius-md)', 
    width: 40, color: 'white', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center'
  },
  todoList: { display: 'flex', flexDirection: 'column', gap: 8, maxHeight: 400, overflowY: 'auto' },
  todoItem: { 
    display: 'flex', alignItems: 'center', gap: 12, padding: '10px 12px', cursor: 'pointer',
    borderBottom: '1px solid var(--color-border-subtle)'
  },
  todoText: { fontSize: 14 },
  textStrikethroughMuted: { textDecoration: 'line-through', opacity: 0.4 },

  // Breakdown
  breakdownBox: { display: 'flex', flexDirection: 'column', gap: 12 },
  breakdownBtn: { 
    background: 'var(--color-primary)', color: 'white', border: 'none', padding: '10px',
    borderRadius: 'var(--radius-md)', fontWeight: 600, cursor: 'pointer', display: 'flex', 
    alignItems: 'center', justifyContent: 'center', gap: 8
  }
}
