/**
 * ComingSoonPage – Premium placeholder for unimplemented modules
 *
 * Accepts a `module` prop and renders the module-specific icon, title,
 * feature list and accent color from the MODULE_CONFIGS map.
 *
 * Routes:
 *   /calendar → ComingSoonPage module="calendar"
 *   /finance  → ComingSoonPage module="finance"
 *   /mail     → ComingSoonPage module="mail"
 *   /files    → ComingSoonPage module="files"
 *   /habits   → ComingSoonPage module="habits"
 */
import {
  Calendar,
  BadgeDollarSign,
  Mail,
  Cloud,
  Flame,
  Sparkles,
  Zap,
  Lock,
  Wifi,
} from 'lucide-react'

/* ── Module config table ──────────────────────────────────────────────────── */
const MODULE_CONFIGS = {
  calendar: {
    icon:     Calendar,
    label:    'Agenda',
    color:    'var(--color-calendar, #22c55e)',
    phase:    'Fase 6',
    tagline:  'Tu calendario, completamente bajo control.',
    features: [
      'Ver y crear eventos con lenguaje natural ("Añade reunión el lunes a las 10")',
      'Integración con Google Calendar vía API',
      'Recordatorios y resúmenes diarios automáticos',
      'Vista semanal y mensual integrada en el chat',
    ],
  },
  finance: {
    icon:     BadgeDollarSign,
    label:    'Finanzas',
    color:    'var(--color-finance, #f59e0b)',
    phase:    'Fase 7',
    tagline:  'Controla tus gastos sin esfuerzo.',
    features: [
      'Registro de gastos e ingresos por voz o texto',
      'Categorización automática con IA',
      'Visualización de balances y tendencias',
      'Exportación a CSV/Excel',
    ],
  },
  mail: {
    icon:     Mail,
    label:    'Correo',
    color:    'var(--color-mail, #3b82f6)',
    phase:    'Fase 8',
    tagline:  'Redacta y resume correos en segundos.',
    features: [
      'Resumen inteligente de bandeja de entrada',
      'Redacción de respuestas formales con IA',
      'Integración con Gmail / IMAP',
      'Filtros y etiquetas automáticas',
    ],
  },
  files: {
    icon:     Cloud,
    label:    'Nube',
    color:    'var(--color-files, #8b5cf6)',
    phase:    'Fase 9',
    tagline:  'Tus documentos, accesibles y buscables.',
    features: [
      'RAG – búsqueda semántica en tus documentos',
      'Subida de PDFs, Word, Markdown',
      'Preguntas y respuestas sobre el contenido',
      'Todo alojado localmente en tu Raspberry Pi',
    ],
  },
  habits: {
    icon:     Flame,
    label:    'Hábitos',
    color:    'var(--color-habits, #ef4444)',
    phase:    'Fase 10',
    tagline:  'Construye rutinas que duran.',
    features: [
      'Registro diario de hábitos con check-in por chat',
      'Estadísticas de rachas y constancia',
      'Recordatorios adaptativos inteligentes',
      'Visualización con gráficas de progreso',
    ],
  },
}

const PERKS = [
  { icon: Lock,  text: 'Privado — todo corre en tu RPi' },
  { icon: Zap,   text: 'Respuesta en tiempo real'        },
  { icon: Wifi,  text: 'Disponible sin internet'         },
]

export default function ComingSoonPage({ module: moduleName }) {
  const cfg = MODULE_CONFIGS[moduleName] ?? MODULE_CONFIGS.calendar
  const Icon = cfg.icon

  return (
    <div style={styles.root}>
      {/* ── Background glow matching module accent ─────────────────────── */}
      <div style={{ ...styles.glow, background: `radial-gradient(circle, ${cfg.color}22 0%, transparent 70%)` }} aria-hidden="true" />

      <div style={styles.card} className="glass-card fade-in-up">

        {/* Module icon badge */}
        <div style={{ ...styles.iconBadge, border: `2px solid ${cfg.color}44`, boxShadow: `0 0 24px ${cfg.color}33` }}>
          <Icon size={32} color={cfg.color} strokeWidth={1.5} />
        </div>

        {/* Phase label */}
        <span style={{ ...styles.phaseBadge, background: `${cfg.color}18`, color: cfg.color }}>
          {cfg.phase}
        </span>

        <h1 style={styles.title}>{cfg.label}</h1>
        <p style={styles.tagline}>{cfg.tagline}</p>

        {/* Feature list */}
        <ul style={styles.featureList} aria-label="Características planificadas">
          {cfg.features.map((feat, i) => (
            <li key={i} style={styles.featureItem}>
              <Sparkles size={13} color={cfg.color} style={{ flexShrink: 0, marginTop: 2 }} />
              <span style={{ color: 'var(--color-text-muted)', fontSize: 14 }}>{feat}</span>
            </li>
          ))}
        </ul>

        {/* Perks */}
        <div style={styles.perks}>
          {PERKS.map(({ icon: PIcon, text }) => (
            <div key={text} style={styles.perk}>
              <PIcon size={13} color="var(--color-text-faint)" />
              <span style={{ fontSize: 12, color: 'var(--color-text-faint)' }}>{text}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

/* ── Styles ─────────────────────────────────────────────────────────────── */
const styles = {
  root: {
    flex:            1,
    display:         'flex',
    alignItems:      'center',
    justifyContent:  'center',
    position:        'relative',
    overflow:        'hidden',
    padding:         32,
  },
  glow: {
    position:     'absolute',
    inset:        0,
    pointerEvents:'none',
    zIndex:       0,
  },
  card: {
    position:       'relative',
    zIndex:         1,
    display:        'flex',
    flexDirection:  'column',
    alignItems:     'center',
    textAlign:      'center',
    maxWidth:       480,
    width:          '100%',
    padding:        '48px 40px',
    gap:            0,
  },
  iconBadge: {
    width:          80,
    height:         80,
    borderRadius:   20,
    background:     'var(--color-surface-2)',
    display:        'flex',
    alignItems:     'center',
    justifyContent: 'center',
    marginBottom:   20,
  },
  phaseBadge: {
    fontSize:     11,
    fontWeight:   700,
    letterSpacing: '0.08em',
    textTransform: 'uppercase',
    padding:       '4px 12px',
    borderRadius:  20,
    marginBottom:  16,
  },
  title: {
    fontSize:     26,
    fontFamily:   'var(--font-display)',
    fontWeight:   700,
    color:        'var(--color-text)',
    marginBottom: 10,
  },
  tagline: {
    fontSize:     15,
    color:        'var(--color-text-muted)',
    marginBottom: 32,
    lineHeight:   1.6,
  },
  featureList: {
    listStyle:    'none',
    padding:      0,
    margin:       0,
    marginBottom: 32,
    width:        '100%',
    display:      'flex',
    flexDirection:'column',
    gap:          12,
    textAlign:    'left',
  },
  featureItem: {
    display:    'flex',
    alignItems: 'flex-start',
    gap:        10,
  },
  perks: {
    display:        'flex',
    gap:            16,
    flexWrap:       'wrap',
    justifyContent: 'center',
  },
  perk: {
    display:    'flex',
    alignItems: 'center',
    gap:        5,
  },
}
