/**
 * FinancePage – Dashboard de Finanzas (Fase 7)
 *
 * Features:
 *   • Balance mensual con tasa de ahorro
 *   • Gráfica de gastos por categoría (donut chart)
 *   • Lista de transacciones recientes
 *   • Formulario para añadir nueva transacción
 *   • Filtros por mes y tipo
 */
import { useEffect, useState, useMemo } from 'react'
import {
  TrendingUp,
  TrendingDown,
  Plus,
  Filter,
  Euro,
  PieChart as PieChartIcon,
  List,
  Calendar,
  X,
  Check,
  Trash2,
} from 'lucide-react'
import { apiFetch } from '../lib/api.js'
import {
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
  Tooltip,
} from 'recharts'

// ══════════════════════════════════════════════════════════════════════════════
//  Utils y constantes
// ══════════════════════════════════════════════════════════════════════════════

const MONTHS = [
  'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
  'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'
]

const CATEGORY_COLORS = {
  alimentacion: '#22c55e',
  transporte: '#f59e0b',
  ocio: '#ef4444',
  tecnologia: '#3b82f6',
  salud: '#8b5cf6',
  hogar: '#06b6d4',
  servicios: '#f97316',
  compras: '#ec4899',
  otros: '#6b7280',
  salario: '#10b981',
  freelance: '#34d399',
  inversiones: '#6ee7b7',
  regalo: '#a7f3d0',
}

const CATEGORY_EMOJIS = {
  alimentacion: '🍔',
  transporte: '🚗',
  ocio: '🎬',
  tecnologia: '💻',
  salud: '🏥',
  hogar: '🏠',
  servicios: '💡',
  compras: '🛍️',
  otros: '📦',
  salario: '💰',
  freelance: '💼',
  inversiones: '📈',
  regalo: '🎁',
}

function formatCurrency(amount) {
  return new Intl.NumberFormat('es-ES', {
    style: 'currency',
    currency: 'EUR',
  }).format(amount)
}

// ══════════════════════════════════════════════════════════════════════════════
//  Main component
// ══════════════════════════════════════════════════════════════════════════════

export default function FinancePage() {
  const [currentMonth, setCurrentMonth] = useState(new Date().getMonth() + 1)
  const [currentYear, setCurrentYear] = useState(new Date().getFullYear())
  const [balance, setBalance] = useState(null)
  const [categories, setCategories] = useState([])
  const [transactions, setTransactions] = useState([])
  const [loading, setLoading] = useState(true)
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [filterType, setFilterType] = useState('all') // all, income, expense

  const fetchData = async () => {
    try {
      setLoading(true)
      const [balanceRes, categoriesRes, transactionsRes] = await Promise.all([
        apiFetch(`/finance/balance?month=${currentMonth}&year=${currentYear}`),
        apiFetch(`/finance/categories?month=${currentMonth}&year=${currentYear}`),
        apiFetch(`/finance/transactions?limit=20&month=${currentMonth}&year=${currentYear}`),
      ])

      setBalance(balanceRes)
      setCategories(categoriesRes.categories || [])
      setTransactions(transactionsRes.transactions || [])
    } catch (err) {
      console.error('Error fetching finance data:', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
  }, [currentMonth, currentYear])

  const handlePreviousMonth = () => {
    if (currentMonth === 1) {
      setCurrentMonth(12)
      setCurrentYear(currentYear - 1)
    } else {
      setCurrentMonth(currentMonth - 1)
    }
  }

  const handleNextMonth = () => {
    if (currentMonth === 12) {
      setCurrentMonth(1)
      setCurrentYear(currentYear + 1)
    } else {
      setCurrentMonth(currentMonth + 1)
    }
  }

  const handleDeleteTransaction = async (txId) => {
    if (!window.confirm('¿Estás seguro de que quieres eliminar esta transacción?')) return

    try {
      await apiFetch(`/finance/transactions/${txId}`, {
        method: 'DELETE',
      })
      // Refrescar datos
      fetchData()
    } catch (err) {
      console.error('Error deleting transaction:', err)
      alert('Error al eliminar la transacción')
    }
  }

  const filteredTransactions = useMemo(() => {
    if (filterType === 'all') return transactions
    return transactions.filter(tx => tx.type === filterType)
  }, [transactions, filterType])

  return (
    <div style={styles.root}>
      {/* ── Header ───────────────────────────────────────────────────────── */}
      <header style={styles.header}>
        <div style={styles.headerLeft}>
          <div style={styles.navGroup}>
            <button onClick={handlePreviousMonth} style={styles.navBtn}>
              <ChevronLeft size={20} />
            </button>
            <button onClick={handleNextMonth} style={styles.navBtn}>
              <ChevronRight size={20} />
            </button>
          </div>
          <h1 style={styles.title}>
            {MONTHS[currentMonth - 1]} {currentYear}
          </h1>
        </div>

        <div style={styles.headerRight}>
          {/* Filter toggle */}
          <div style={styles.filterToggle}>
            <button
              onClick={() => setFilterType('all')}
              style={{
                ...styles.filterBtn,
                ...(filterType === 'all' ? styles.filterBtnActive : {}),
              }}
            >
              Todas
            </button>
            <button
              onClick={() => setFilterType('income')}
              style={{
                ...styles.filterBtn,
                ...(filterType === 'income' ? styles.filterBtnActive : {}),
              }}
            >
              Ingresos
            </button>
            <button
              onClick={() => setFilterType('expense')}
              style={{
                ...styles.filterBtn,
                ...(filterType === 'expense' ? styles.filterBtnActive : {}),
              }}
            >
              Gastos
            </button>
          </div>

          <button onClick={() => setShowCreateModal(true)} style={styles.createBtn}>
            <Plus size={18} />
            <span style={{ fontSize: 13 }}>Añadir</span>
          </button>
        </div>
      </header>

      {/* ── Content ──────────────────────────────────────────────────────── */}
      <div style={styles.content}>
        {loading ? (
          <div style={styles.loadingState}>
            <div className="spin" style={{ width: 32, height: 32, border: '3px solid var(--color-border-subtle)', borderTopColor: 'var(--color-primary)', borderRadius: '50%' }} />
            <span style={{ color: 'var(--color-text-muted)' }}>Cargando datos financieros...</span>
          </div>
        ) : (
          <>
            {/* Balance cards */}
            <div style={styles.balanceCards}>
              <BalanceCard
                title="Ingresos"
                amount={balance?.income || 0}
                icon={TrendingUp}
                color="var(--color-success)"
              />
              <BalanceCard
                title="Gastos"
                amount={balance?.expenses || 0}
                icon={TrendingDown}
                color="var(--color-error)"
              />
              <BalanceCard
                title="Balance"
                amount={balance?.balance || 0}
                icon={Euro}
                color={balance?.balance >= 0 ? 'var(--color-success)' : 'var(--color-error)'}
                isBalance
              />
            </div>

            {/* Charts row */}
            <div style={styles.chartsRow}>
              {/* Categories donut chart */}
              <div style={styles.chartCard}>
                <div style={styles.chartHeader}>
                  <PieChartIcon size={18} color="var(--color-text-muted)" />
                  <h3 style={styles.chartTitle}>Gastos por categoría</h3>
                </div>
                {categories.length > 0 ? (
                  <div style={styles.chartContainer}>
                    <ResponsiveContainer width="100%" height={200}>
                      <PieChart>
                        <Pie
                          data={categories}
                          dataKey="total"
                          nameKey="category"
                          cx="50%"
                          cy="50%"
                          innerRadius={50}
                          outerRadius={80}
                          paddingAngle={2}
                        >
                          {categories.map((entry, index) => (
                            <Cell
                              key={`cell-${index}`}
                              fill={CATEGORY_COLORS[entry.category] || '#6b7280'}
                            />
                          ))}
                        </Pie>
                        <Tooltip
                          contentStyle={{
                            background: 'var(--color-surface)',
                            border: '1px solid var(--color-border-subtle)',
                            borderRadius: 8,
                            fontSize: 13,
                          }}
                          formatter={(value) => formatCurrency(value)}
                        />
                      </PieChart>
                    </ResponsiveContainer>
                    {/* Legend */}
                    <div style={styles.legend}>
                      {categories.map((cat) => (
                        <div key={cat.category} style={styles.legendItem}>
                          <div
                            style={{
                              width: 12,
                              height: 12,
                              borderRadius: 2,
                              background: CATEGORY_COLORS[cat.category] || '#6b7280',
                            }}
                          />
                          <span style={{ fontSize: 12, color: 'var(--color-text-muted)' }}>
                            {CATEGORY_EMOJIS[cat.category]} {cat.category}
                          </span>
                          <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--color-text)' }}>
                            {formatCurrency(cat.total)}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                ) : (
                  <div style={styles.emptyChart}>
                    <PieChartIcon size={48} color="var(--color-text-faint)" />
                    <p style={{ color: 'var(--color-text-muted)', fontSize: 13 }}>
                      No hay gastos registrados este mes
                    </p>
                  </div>
                )}
              </div>

              {/* Transactions list */}
              <div style={styles.transactionsCard}>
                <div style={styles.chartHeader}>
                  <List size={18} color="var(--color-text-muted)" />
                  <h3 style={styles.chartTitle}>Transacciones recientes</h3>
                </div>
                <div style={styles.transactionsList}>
                  {filteredTransactions.length > 0 ? (
                    filteredTransactions.map((tx) => (
                      <TransactionItem 
                        key={tx.id} 
                        transaction={tx} 
                        onDelete={() => handleDeleteTransaction(tx.id)}
                      />
                    ))
                  ) : (
                    <div style={styles.emptyState}>
                      <List size={48} color="var(--color-text-faint)" />
                      <p style={{ color: 'var(--color-text-muted)', fontSize: 13 }}>
                        No hay transacciones
                      </p>
                    </div>
                  )}
                </div>
              </div>
            </div>
          </>
        )}
      </div>

      {/* ── Create transaction modal ─────────────────────────────────────── */}
      {showCreateModal && (
        <CreateTransactionModal
          onClose={() => setShowCreateModal(false)}
          onCreated={() => {
            setShowCreateModal(false)
            fetchData()
          }}
        />
      )}
    </div>
  )
}

// ══════════════════════════════════════════════════════════════════════════════
//  Balance Card component
// ══════════════════════════════════════════════════════════════════════════════

function BalanceCard({ title, amount, icon: Icon, color, isBalance }) {
  return (
    <div style={{ ...styles.balanceCard, borderLeft: `3px solid ${color}` }}>
      <div style={styles.balanceCardHeader}>
        <span style={styles.balanceCardTitle}>{title}</span>
        <Icon size={18} color={color} />
      </div>
      <div style={{ ...styles.balanceCardAmount, color }}>
        {formatCurrency(amount)}
      </div>
    </div>
  )
}

// ══════════════════════════════════════════════════════════════════════════════
//  Transaction Item component
// ══════════════════════════════════════════════════════════════════════════════

function TransactionItem({ transaction, onDelete }) {
  const isIncome = transaction.type === 'income'
  const date = new Date(transaction.date)

  return (
    <div style={styles.transactionItem}>
      <div style={{
        ...styles.transactionIcon,
        background: `${isIncome ? 'var(--color-success)' : 'var(--color-error)'}15`,
      }}>
        {isIncome ? <TrendingUp size={16} color="var(--color-success)" /> : <TrendingDown size={16} color="var(--color-error)" />}
      </div>
      <div style={styles.transactionInfo}>
        <div style={styles.transactionDescription}>{transaction.description}</div>
        <div style={styles.transactionMeta}>
          <span style={styles.transactionCategory}>
            {CATEGORY_EMOJIS[transaction.category]} {transaction.category}
          </span>
          <span style={styles.transactionDate}>
            {date.toLocaleDateString('es-ES', { day: 'numeric', month: 'short' })}
          </span>
        </div>
      </div>
      <div style={{
        ...styles.transactionAmount,
        color: isIncome ? 'var(--color-success)' : 'var(--color-error)',
      }}>
        {isIncome ? '+' : '-'}{formatCurrency(transaction.amount)}
      </div>
      <button 
        onClick={(e) => {
          e.stopPropagation()
          onDelete()
        }}
        style={styles.deleteTxBtn}
        title="Eliminar transacción"
      >
        <Trash2 size={14} />
      </button>
    </div>
  )
}

// ══════════════════════════════════════════════════════════════════════════════
//  Create Transaction Modal
// ══════════════════════════════════════════════════════════════════════════════

function CreateTransactionModal({ onClose, onCreated }) {
  const [formData, setFormData] = useState({
    type: 'expense',
    amount: '',
    category: 'otros',
    description: '',
    date: new Date().toISOString().split('T')[0],
    is_fixed: false,
  })
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState(null)

  const expenseCategories = ['alimentacion', 'transporte', 'ocio', 'tecnologia', 'salud', 'hogar', 'servicios', 'compras', 'otros']
  const incomeCategories = ['salario', 'freelance', 'inversiones', 'regalo', 'otros']

  const categories = formData.type === 'expense' ? expenseCategories : incomeCategories

  const handleSubmit = async (e) => {
    e.preventDefault()
    setSubmitting(true)
    setError(null)

    try {
      await apiFetch('/finance/transactions', {
        method: 'POST',
        body: JSON.stringify({
          ...formData,
          amount: parseFloat(formData.amount),
        }),
      })
      onCreated()
    } catch (err) {
      setError(err.message || 'Error al crear la transacción')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div style={styles.modalOverlay} onClick={onClose}>
      <div style={styles.modalContent} onClick={e => e.stopPropagation()}>
        <div style={styles.modalHeader}>
          <h2 style={styles.modalTitle}>Nueva transacción</h2>
          <button onClick={onClose} style={styles.closeBtn}>×</button>
        </div>

        <form onSubmit={handleSubmit} style={styles.form}>
          {/* Type selector */}
          <div style={styles.typeSelector}>
            <button
              type="button"
              onClick={() => setFormData({ ...formData, type: 'expense' })}
              style={{
                ...styles.typeBtn,
                ...(formData.type === 'expense' ? styles.typeBtnActiveExpense : {}),
              }}
            >
              <TrendingDown size={16} />
              Gasto
            </button>
            <button
              type="button"
              onClick={() => setFormData({ ...formData, type: 'income' })}
              style={{
                ...styles.typeBtn,
                ...(formData.type === 'income' ? styles.typeBtnActiveIncome : {}),
              }}
            >
              <TrendingUp size={16} />
              Ingreso
            </button>
          </div>

          <div style={styles.formGroup}>
            <label style={styles.label}>Cantidad (€)</label>
            <input
              type="number"
              step="0.01"
              min="0"
              value={formData.amount}
              onChange={e => setFormData({ ...formData, amount: e.target.value })}
              style={styles.input}
              placeholder="0.00"
              required
              autoFocus
            />
          </div>

          <div style={styles.formGroup}>
            <label style={styles.label}>Categoría</label>
            <select
              value={formData.category}
              onChange={e => setFormData({ ...formData, category: e.target.value })}
              style={styles.select}
            >
              {categories.map(cat => (
                <option key={cat} value={cat}>
                  {CATEGORY_EMOJIS[cat]} {cat.charAt(0).toUpperCase() + cat.slice(1)}
                </option>
              ))}
            </select>
          </div>

          <div style={styles.formGroup}>
            <label style={styles.label}>Descripción</label>
            <input
              type="text"
              value={formData.description}
              onChange={e => setFormData({ ...formData, description: e.target.value })}
              style={styles.input}
              placeholder="Ej: Compra en Mercadona"
              required
            />
          </div>

          <div style={styles.formGroup}>
            <label style={styles.label}>Fecha</label>
            <input
              type="date"
              value={formData.date}
              onChange={e => setFormData({ ...formData, date: e.target.value })}
              style={styles.input}
              required
            />
          </div>

          <div style={styles.checkboxGroup}>
            <label style={styles.checkboxLabel}>
              <input
                type="checkbox"
                checked={formData.is_fixed}
                onChange={e => setFormData({ ...formData, is_fixed: e.target.checked })}
                style={styles.checkbox}
              />
              <span style={{ fontSize: 14, color: 'var(--color-text)' }}>
                Transacción fija/recurrente
              </span>
            </label>
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
              {submitting ? 'Guardando...' : 'Guardar'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

// ══════════════════════════════════════════════════════════════════════════════
//  Icons (inline to avoid extra imports)
// ══════════════════════════════════════════════════════════════════════════════

function ChevronLeft({ size, ...props }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" {...props}>
      <path d="m15 18-6-6 6-6" />
    </svg>
  )
}

function ChevronRight({ size, ...props }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" {...props}>
      <path d="m9 18 6-6-6-6" />
    </svg>
  )
}

// ══════════════════════════════════════════════════════════════════════════════
//  Styles
// ══════════════════════════════════════════════════════════════════════════════

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
    fontSize: 20,
    fontFamily: 'var(--font-display)',
    fontWeight: 600,
    color: 'var(--color-text)',
    margin: 0,
    minWidth: 200,
    textAlign: 'center',
  },
  filterToggle: {
    display: 'flex',
    borderRadius: 6,
    border: '1px solid var(--color-border-subtle)',
    overflow: 'hidden',
  },
  filterBtn: {
    padding: '6px 12px',
    fontSize: 13,
    fontWeight: 500,
    background: 'transparent',
    border: 'none',
    cursor: 'pointer',
    color: 'var(--color-text-muted)',
  },
  filterBtnActive: {
    background: 'var(--color-primary)',
    color: 'white',
  },
  createBtn: {
    display: 'flex',
    alignItems: 'center',
    gap: 6,
    padding: '8px 14px',
    fontSize: 13,
    fontWeight: 600,
    background: 'var(--color-primary)',
    border: 'none',
    borderRadius: 8,
    color: 'white',
    cursor: 'pointer',
  },
  content: {
    flex: 1,
    overflow: 'auto',
    display: 'flex',
    flexDirection: 'column',
    gap: 20,
  },
  loadingState: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 16,
    flex: 1,
  },
  balanceCards: {
    display: 'grid',
    gridTemplateColumns: 'repeat(3, 1fr)',
    gap: 16,
  },
  balanceCard: {
    background: 'var(--color-surface)',
    borderRadius: 12,
    padding: 20,
    border: '1px solid var(--color-border-subtle)',
  },
  balanceCardHeader: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 12,
  },
  balanceCardTitle: {
    fontSize: 13,
    fontWeight: 500,
    color: 'var(--color-text-muted)',
  },
  balanceCardAmount: {
    fontSize: 28,
    fontWeight: 700,
    fontFamily: 'var(--font-display)',
  },
  chartsRow: {
    display: 'grid',
    gridTemplateColumns: '1fr 1fr',
    gap: 16,
    flex: 1,
    minHeight: 0,
  },
  chartCard: {
    background: 'var(--color-surface)',
    borderRadius: 12,
    border: '1px solid var(--color-border-subtle)',
    padding: 16,
    display: 'flex',
    flexDirection: 'column',
  },
  transactionsCard: {
    background: 'var(--color-surface)',
    borderRadius: 12,
    border: '1px solid var(--color-border-subtle)',
    padding: 16,
    display: 'flex',
    flexDirection: 'column',
    overflow: 'hidden',
  },
  chartHeader: {
    display: 'flex',
    alignItems: 'center',
    gap: 8,
    marginBottom: 16,
  },
  chartTitle: {
    fontSize: 14,
    fontWeight: 600,
    color: 'var(--color-text)',
    margin: 0,
  },
  chartContainer: {
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
    gap: 16,
  },
  legend: {
    display: 'flex',
    flexDirection: 'column',
    gap: 8,
    maxHeight: 200,
    overflow: 'auto',
  },
  legendItem: {
    display: 'flex',
    alignItems: 'center',
    gap: 8,
    padding: '4px 0',
  },
  emptyChart: {
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 12,
  },
  emptyState: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 12,
    padding: 40,
  },
  transactionsList: {
    flex: 1,
    overflow: 'auto',
    display: 'flex',
    flexDirection: 'column',
    gap: 8,
  },
  transactionItem: {
    display: 'flex',
    alignItems: 'center',
    gap: 12,
    padding: 12,
    background: 'var(--color-surface-2)',
    borderRadius: 8,
  },
  transactionIcon: {
    width: 36,
    height: 36,
    borderRadius: 8,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    flexShrink: 0,
  },
  transactionInfo: {
    flex: 1,
    minWidth: 0,
  },
  transactionDescription: {
    fontSize: 14,
    fontWeight: 500,
    color: 'var(--color-text)',
    whiteSpace: 'nowrap',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
  },
  transactionMeta: {
    display: 'flex',
    alignItems: 'center',
    gap: 12,
    marginTop: 4,
  },
  transactionCategory: {
    fontSize: 12,
    color: 'var(--color-text-muted)',
  },
  transactionDate: {
    fontSize: 12,
    color: 'var(--color-text-faint)',
  },
  transactionAmount: {
    fontSize: 14,
    fontWeight: 600,
    whiteSpace: 'nowrap',
  },
  deleteTxBtn: {
    padding: 6,
    background: 'transparent',
    border: 'none',
    borderRadius: 6,
    color: 'var(--color-text-faint)',
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    transition: 'all 0.2s ease',
    opacity: 0.6,
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
    maxWidth: 450,
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
  form: {
    padding: 16,
    display: 'flex',
    flexDirection: 'column',
    gap: 16,
  },
  typeSelector: {
    display: 'grid',
    gridTemplateColumns: '1fr 1fr',
    gap: 8,
  },
  typeBtn: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    padding: 12,
    fontSize: 14,
    fontWeight: 600,
    background: 'var(--color-surface-2)',
    border: '2px solid var(--color-border-subtle)',
    borderRadius: 8,
    color: 'var(--color-text)',
    cursor: 'pointer',
  },
  typeBtnActiveExpense: {
    background: 'var(--color-error-alpha)',
    borderColor: 'var(--color-error)',
    color: 'var(--color-error)',
  },
  typeBtnActiveIncome: {
    background: 'var(--color-success-alpha)',
    borderColor: 'var(--color-success)',
    color: 'var(--color-success)',
  },
  formGroup: {
    display: 'flex',
    flexDirection: 'column',
    gap: 6,
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
  select: {
    padding: 10,
    fontSize: 14,
    background: 'var(--color-surface-2)',
    border: '1px solid var(--color-border-subtle)',
    borderRadius: 6,
    color: 'var(--color-text)',
    outline: 'none',
    cursor: 'pointer',
  },
  checkboxGroup: {
    padding: 8,
  },
  checkboxLabel: {
    display: 'flex',
    alignItems: 'center',
    gap: 8,
    cursor: 'pointer',
  },
  checkbox: {
    width: 18,
    height: 18,
    cursor: 'pointer',
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
