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
  Sparkles
} from 'lucide-react'
import { apiFetch } from '../lib/api.js'

export default function HabitsPage() {
  const [data, setData] = useState({ habits: [], todos: [] })
  const [logs, setLogs] = useState([])
  const [loading, setLoading] = useState(true)
  const [breakdownInput, setBreakdownInput] = useState('')
  const [isBreakingDown, setIsBreakingDown] = useState(false)
  const [newTodoInput, setNewTodoInput] = useState('')

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

  const handleAddTodo = async (e) => {
    e.preventDefault()
    if (!newTodoInput.trim()) return
    try {
      await apiFetch('/habits/todos', {
        method: 'POST',
        body: JSON.stringify({ title: newTodoInput })
      })
      setNewTodoInput('')
      fetchAll()
    } catch (err) {
      console.error('Error adding todo:', err)
    }
  }

  const handleToggleTodo = async (todoId) => {
    try {
      await apiFetch(`/habits/todos/${todoId}/toggle`, { method: 'PUT' })
      fetchAll()
    } catch (err) {
      console.error('Error toggling todo:', err)
    }
  }

  const handleBreakdown = async () => {
    if (!breakdownInput.trim()) return
    setIsBreakingDown(true)
    try {
      await apiFetch('/habits/breakdown', {
        method: 'POST',
        body: JSON.stringify({ project_title: breakdownInput })
      })
      setBreakdownInput('')
      fetchAll()
    } catch (err) {
      console.error('Error breaking down project:', err)
    } finally {
      setIsBreakingDown(false)
    }
  }

  return (
    <div style={styles.root}>
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

      <div style={styles.mainGrid}>
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
                </div>
              ))}
              <div style={styles.addHabitPlaceholder}>
                <Plus size={16} /> Añadir hábito corporbot...
              </div>
            </div>
          </div>
        </div>

        {/* Right Column: Todos & Breakdown */}
        <div style={styles.rightCol}>
          {/* Todo List Card */}
          <div style={styles.card} className="glass-card">
            <div style={styles.cardHeader}>
              <ListTodo size={18} color="var(--color-primary-light)" />
              <h3 style={styles.cardTitle}>Tareas</h3>
            </div>
            <div style={styles.todoContent}>
              <form onSubmit={handleAddTodo} style={styles.todoInputBox}>
                <input 
                  style={styles.todoInput} 
                  placeholder="Añadir una tarea rápida..." 
                  value={newTodoInput}
                  onChange={e => setNewTodoInput(e.target.value)}
                />
                <button type="submit" style={styles.todoAddBtn}><Plus size={18} /></button>
              </form>
              <div style={styles.todoList}>
                {data.todos.map(todo => (
                  <div 
                    key={todo.id} 
                    style={styles.todoItem}
                    onClick={() => handleToggleTodo(todo.id)}
                  >
                     {todo.is_completed ? (
                      <CheckCircle2 size={20} color="var(--color-primary-light)" />
                    ) : (
                      <Circle size={20} color="var(--color-text-faint)" />
                    )}
                    <span style={{ 
                      ...styles.todoText,
                      ...(todo.is_completed ? styles.textStrikethroughMuted : {})
                    }}>
                      {todo.title}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* AI Breakdown Card */}
          <div style={{ ...styles.card, background: 'linear-gradient(135deg, rgba(124, 58, 237, 0.1), rgba(0,0,0,0))' }} className="glass-card">
            <div style={styles.cardHeader}>
              <Sparkles size={18} color="var(--color-primary-light)" />
              <h3 style={styles.cardTitle}>Desglosador IA</h3>
            </div>
            <p style={styles.cardSub}>Divide un gran proyecto en pasos accionables</p>
            <div style={styles.breakdownBox}>
              <input 
                style={styles.todoInput} 
                placeholder="Ej: 'Aprender Rust' o 'Mudanza'..." 
                value={breakdownInput}
                onChange={e => setBreakdownInput(e.target.value)}
                disabled={isBreakingDown}
              />
              <button 
                onClick={handleBreakdown} 
                style={styles.breakdownBtn}
                disabled={isBreakingDown || !breakdownInput.trim()}
              >
                {isBreakingDown ? <Loader2 size={16} className="spin" /> : 'Desglosar'}
              </button>
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
    <div style={styles.graphGrid}>
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
  mainGrid: { display: 'grid', gridTemplateColumns: '1fr 380px', gap: 24 },
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
  habitName: { fontSize: 15, fontWeight: 500 },
  textStrikethrough: { textDecoration: 'line-through', opacity: 0.6, color: 'var(--color-success)' },
  addHabitPlaceholder: { color: 'var(--color-text-faint)', fontSize: 13, padding: '0 16px', display: 'flex', alignItems: 'center', gap: 8 },

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
