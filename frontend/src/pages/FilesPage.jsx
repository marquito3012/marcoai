/**
 * FilesPage – Nube Privada y Gestión de RAG (Fase 9)
 * ══════════════════════════════════════════════════════════════════════════════
 * 
 * Features:
 *   • File explorer with document metadata
 *   • Upload area for PDF/TXT files
 *   • Real-time indexing status icons
 *   • Integration with backend DocumentService
 */
import { useState, useEffect } from 'react'
import { 
  FileText, 
  Upload, 
  Trash2, 
  RefreshCw, 
  Clock, 
  CheckCircle, 
  AlertCircle,
  FileCode,
  Search,
  BookOpen,
  Activity
} from 'lucide-react'
import { apiFetch } from '../lib/api.js'

export default function FilesPage() {
  const [docs, setDocs] = useState([])
  const [loading, setLoading] = useState(true)
  const [uploading, setUploading] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')

  const fetchDocs = async () => {
    try {
      setLoading(true)
      const data = await apiFetch('/documents')
      setDocs(data || [])
    } catch (err) {
      console.error('Error fetching documents:', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchDocs()
    // Poll every 10 seconds if there are pending/processing files
    const interval = setInterval(() => {
      if (docs.some(d => d.status === 'pending' || d.status === 'processing')) {
        fetchDocs()
      }
    }, 10000)
    return () => clearInterval(interval)
  }, [docs])

  const handleUpload = async (e) => {
    const file = e.target.files[0]
    if (!file) return
    
    const formData = new FormData()
    formData.append('file', file)
    
    setUploading(true)
    try {
      // apiFetch doesn't handle FormData with its default Content-Type
      // We use base fetch or modify apiFetch, but here we'll use a local fetch call
      const res = await fetch('/api/v1/documents/upload', {
        method: 'POST',
        body: formData,
        // credentials: 'include' is needed for cookies
        credentials: 'include'
      })
      if (!res.ok) throw new Error('Error al subir archivo')
      fetchDocs()
    } catch (err) {
      alert('Error en la subida: ' + err.message)
    } finally {
      setUploading(false)
    }
  }

  const handleDelete = async (id) => {
    if (!confirm('¿Seguro que quieres eliminar este documento? Se borrará también de la memoria del asistente.')) return
    try {
      await apiFetch(`/documents/${id}`, { method: 'DELETE' })
      setDocs(docs.filter(d => d.id !== id))
    } catch (err) {
      console.error('Error deleting doc:', err)
    }
  }

  const filteredDocs = docs.filter(d => 
    d.filename.toLowerCase().includes(searchQuery.toLowerCase())
  )

  const formatSize = (bytes) => {
    if (bytes === 0) return '0 B'
    const k = 1024
    const sizes = ['B', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
  }

  return (
    <div style={styles.root}>
      {/* ── Header ───────────────────────────────────────────────────────── */}
      <header style={styles.header}>
        <div style={styles.headerLeft}>
          <h1 style={styles.title}>Nube Privada</h1>
          <p style={styles.headerSub}>Gestiona los documentos que alimentan la memoria de MarcoAI (RAG)</p>
        </div>
        <div style={styles.headerRight}>
          <button onClick={fetchDocs} style={styles.iconBtn} title="Sincronizar">
            <RefreshCw size={18} className={loading ? 'spin' : ''} />
          </button>
          <label style={styles.uploadBtn}>
            <Upload size={18} />
            <span>{uploading ? 'Subiendo...' : 'Subir archivo'}</span>
            <input type="file" style={{ display: 'none' }} onChange={handleUpload} disabled={uploading} accept=".pdf,.txt" />
          </label>
        </div>
      </header>

      {/* ── Dashboard Stats ─────────────────────────────────────────────── */}
      <div style={styles.statsRow}>
        <div style={styles.statCard} className="glass-card">
          <BookOpen size={20} color="var(--color-files)" />
          <div>
            <div style={styles.statVal}>{docs.length}</div>
            <div style={styles.statLabel}>Documentos Indexados</div>
          </div>
        </div>
        <div style={styles.statCard} className="glass-card">
          <Activity size={20} color="var(--color-success)" />
          <div>
            <div style={styles.statVal}>{formatSize(docs.reduce((acc, d) => acc + d.size_bytes, 0))}</div>
            <div style={styles.statLabel}>Memoria en uso</div>
          </div>
        </div>
      </div>

      {/* ── Content ─────────────────────────────────────────────────────── */}
      <div style={styles.mainContent} className="glass-card">
        <div style={styles.toolbar}>
          <div style={styles.searchBox}>
            <Search size={16} color="var(--color-text-faint)" />
            <input 
              style={styles.searchPrompt} 
              placeholder="Buscar por nombre..." 
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
            />
          </div>
        </div>

        <div style={styles.tableArea}>
          {loading && docs.length === 0 ? (
            <div style={styles.emptyState}>
              <RefreshCw size={32} className="spin" color="var(--color-primary)" />
              <p>Escaneando nube privada...</p>
            </div>
          ) : filteredDocs.length === 0 ? (
            <div style={styles.emptyState}>
              <FileText size={64} color="var(--color-surface-3)" strokeWidth={1} />
              <p>No se encontraron documentos.</p>
            </div>
          ) : (
            <table style={styles.table}>
              <thead>
                <tr>
                  <th style={styles.th}>Nombre</th>
                  <th style={styles.th}>Tamaño</th>
                  <th style={styles.th}>Fecha</th>
                  <th style={styles.th}>Estado de Indexación</th>
                  <th style={styles.th}>Acción</th>
                </tr>
              </thead>
              <tbody>
                {filteredDocs.map(doc => (
                  <tr key={doc.id} style={styles.tr}>
                    <td style={styles.td}>
                      <div style={styles.fileNameCell}>
                        {doc.mime_type.includes('pdf') ? <FileText size={18} color="#EF4444" /> : <FileCode size={18} color="#38BDF8" />}
                        <span>{doc.filename}</span>
                      </div>
                    </td>
                    <td style={styles.td}>{formatSize(doc.size_bytes)}</td>
                    <td style={styles.td}>{new Date(doc.created_at).toLocaleDateString()}</td>
                    <td style={styles.td}>
                      <StatusBadge status={doc.status} />
                    </td>
                    <td style={styles.td}>
                      <button onClick={() => handleDelete(doc.id)} style={styles.deleteBtn}>
                        <Trash2 size={16} />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  )
}

function StatusBadge({ status }) {
  const map = {
    completed:  { icon: CheckCircle,  color: 'var(--color-success)', text: 'Completado' },
    processing: { icon: RefreshCw,    color: 'var(--color-info)',    text: 'Procesando...', spin: true },
    pending:    { icon: Clock,        color: 'var(--color-warning)', text: 'Pendiente' },
    error:      { icon: AlertCircle,  color: 'var(--color-danger)',  text: 'Error' },
  }
  const config = map[status] || map.pending
  const Icon = config.icon

  return (
    <div style={{ ...styles.badge, color: config.color, background: `${config.color}15` }}>
      <Icon size={14} className={config.spin ? 'spin' : ''} />
      <span>{config.text}</span>
    </div>
  )
}

const styles = {
  root: { flex: 1, padding: 24, display: 'flex', flexDirection: 'column', gap: 24, overflowY: 'auto' },
  header: { display: 'flex', alignItems: 'center', justifyContent: 'space-between' },
  headerLeft: { display: 'flex', flexDirection: 'column', gap: 4 },
  headerSub: { fontSize: 13, color: 'var(--color-text-muted)', margin: 0 },
  title: { fontSize: 24, margin: 0 },
  iconBtn: { background: 'var(--color-surface-2)', border: '1px solid var(--color-border-subtle)', borderRadius: 'var(--radius-sm)', padding: 8, color: 'var(--color-text-muted)', cursor: 'pointer' },
  headerRight: { display: 'flex', gap: 12 },
  
  uploadBtn: { 
    background: 'var(--color-primary)', color: 'white', padding: '10px 20px', borderRadius: 'var(--radius-md)',
    display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer', fontWeight: 600, fontSize: 14,
    boxShadow: '0 4px 12px var(--color-primary-glow)'
  },

  statsRow: { display: 'flex', gap: 16 },
  statCard: { flex: 1, padding: 20, display: 'flex', alignItems: 'center', gap: 16 },
  statVal: { fontSize: 20, fontWeight: 700, color: 'var(--color-text)' },
  statLabel: { fontSize: 12, color: 'var(--color-text-faint)', textTransform: 'uppercase', letterSpacing: '0.05em' },

  mainContent: { flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' },
  toolbar: { padding: '16px 20px', borderBottom: '1px solid var(--color-border-subtle)' },
  searchBox: { display: 'flex', alignItems: 'center', gap: 10, background: 'var(--color-surface-3)', padding: '8px 16px', borderRadius: 'var(--radius-md)', width: 300 },
  searchPrompt: { background: 'transparent', border: 'none', color: 'var(--color-text)', fontSize: 14, outline: 'none', width: '100%' },

  tableArea: { flex: 1, overflowY: 'auto' },
  table: { width: '100%', borderCollapse: 'collapse', textAlign: 'left' },
  th: { padding: '16px 20px', fontSize: 13, color: 'var(--color-text-faint)', fontWeight: 600, borderBottom: '1px solid var(--color-border-subtle)' },
  tr: { borderBottom: '1px solid var(--color-border-subtle)', transition: 'background 0.2s' },
  td: { padding: '16px 20px', fontSize: 14, color: 'var(--color-text-muted)' },
  
  fileNameCell: { display: 'flex', alignItems: 'center', gap: 12, color: 'var(--color-text)', fontWeight: 500 },
  badge: { display: 'flex', alignItems: 'center', gap: 6, padding: '4px 10px', borderRadius: 20, fontSize: 12, fontWeight: 600, width: 'fit-content' },
  deleteBtn: { background: 'transparent', border: 'none', color: 'var(--color-text-faint)', cursor: 'pointer', transition: 'color 0.2s' },
  
  emptyState: { display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 16, padding: 60 },
  Activity: { width: 48, height: 48 },
}
