/**
 * MarcoAI – Login Page
 *
 * Full-screen login with Google SSO. Design: premium dark theme,
 * glassmorphism card, animated mesh gradient background, feature pills.
 */
import {
  Calendar,
  BadgeDollarSign,
  Mail,
  Cloud,
  Flame,
  MessageSquare,
  Shield,
  Zap,
} from 'lucide-react'
import { loginWithGoogle } from '../lib/api'

/* ── Feature chips shown below the headline ─────────────────────────────── */
const FEATURES = [
  { icon: MessageSquare, label: 'Chat inteligente',  color: 'var(--color-primary-light)' },
  { icon: Calendar,      label: 'Agenda',            color: 'var(--color-calendar)'      },
  { icon: BadgeDollarSign, label: 'Finanzas',        color: 'var(--color-finance)'       },
  { icon: Mail,          label: 'Correo',            color: 'var(--color-mail)'          },
  { icon: Cloud,         label: 'Nube privada',      color: 'var(--color-files)'         },
  { icon: Flame,         label: 'Hábitos',           color: 'var(--color-habits)'        },
]

/* ── Google "G" SVG Logo ──────────────────────────────────────────────────── */
function GoogleLogo() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" aria-hidden="true">
      <path
        fill="#4285F4"
        d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
      />
      <path
        fill="#34A853"
        d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
      />
      <path
        fill="#FBBC05"
        d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
      />
      <path
        fill="#EA4335"
        d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
      />
    </svg>
  )
}

export default function LoginPage() {
  return (
    <div style={styles.root}>
      {/* ── Animated mesh / glow backdrop ───────────────────────────────── */}
      <div style={styles.backdrop} aria-hidden="true">
        <div style={styles.glow1} />
        <div style={styles.glow2} />
        <div style={styles.grid}  />
      </div>

      {/* ── Glass card ──────────────────────────────────────────────────── */}
      <main style={styles.card} className="glass-card fade-in-up">

        {/* Logo */}
        <div style={styles.logo} aria-label="MarcoAI">
          <img src="/logo.png" alt="MarcoAI" style={{ width: '100%', height: '100%', objectFit: 'cover', borderRadius: 'inherit' }} />
        </div>

        {/* Heading */}
        <h1 style={styles.heading}>
          Bienvenido a{' '}
          <span className="gradient-text">MarcoAI</span>
        </h1>
        <p style={styles.subtitle}>
          Tu asistente personal inteligente — todo en un solo lugar,
          privado y alojado en casa.
        </p>

        {/* Feature pills */}
        <div style={styles.features} role="list" aria-label="Módulos disponibles">
          {FEATURES.map(({ icon: Icon, label, color }) => (
            <div key={label} style={styles.pill} role="listitem">
              <Icon size={13} color={color} strokeWidth={2} />
              <span style={{ color: 'var(--color-text-muted)', fontSize: 12 }}>{label}</span>
            </div>
          ))}
        </div>

        {/* Divider */}
        <div style={styles.divider}>
          <div style={styles.dividerLine} />
          <span style={styles.dividerText}>Acceder con</span>
          <div style={styles.dividerLine} />
        </div>

        {/* Google SSO button */}
        <button
          id="btn-login-google"
          onClick={loginWithGoogle}
          style={styles.googleBtn}
          onMouseEnter={e => Object.assign(e.currentTarget.style, styles.googleBtnHover)}
          onMouseLeave={e => Object.assign(e.currentTarget.style, styles.googleBtn)}
        >
          <GoogleLogo />
          <span>Continuar con Google</span>
        </button>

        {/* Security note */}
        <p style={styles.securityNote}>
          <Shield size={12} style={{ display: 'inline', marginRight: 4 }} />
          Tus datos nunca salen de tu red local. Sin rastreo, sin anuncios.
        </p>

        {/* Performance note */}
        <p style={{ ...styles.securityNote, marginTop: 4 }}>
          <Zap size={12} style={{ display: 'inline', marginRight: 4 }} />
          Alojado en tu Raspberry Pi · Respuesta en tiempo real
        </p>
      </main>
    </div>
  )
}

/* ── Styles ────────────────────────────────────────────────────────────────── */
const styles = {
  root: {
    minHeight:       '100vh',
    display:         'flex',
    alignItems:      'center',
    justifyContent:  'center',
    background:      'var(--color-bg)',
    position:        'relative',
    overflow:        'hidden',
    padding:         24,
  },

  /* Decorative background */
  backdrop: {
    position: 'absolute', inset: 0,
    pointerEvents: 'none',
  },
  glow1: {
    position:     'absolute',
    top:          '-20%',
    left:         '-10%',
    width:        '60vw',
    height:       '60vw',
    borderRadius: '50%',
    background:   'radial-gradient(circle, rgba(124,58,237,0.12) 0%, transparent 70%)',
    filter:       'blur(60px)',
  },
  glow2: {
    position:     'absolute',
    bottom:       '-20%',
    right:        '-10%',
    width:        '50vw',
    height:       '50vw',
    borderRadius: '50%',
    background:   'radial-gradient(circle, rgba(167,139,250,0.08) 0%, transparent 70%)',
    filter:       'blur(80px)',
  },
  grid: {
    position:         'absolute',
    inset:            0,
    backgroundImage:  `linear-gradient(rgba(124,58,237,0.04) 1px, transparent 1px),
                       linear-gradient(90deg, rgba(124,58,237,0.04) 1px, transparent 1px)`,
    backgroundSize:   '48px 48px',
  },

  /* Card */
  card: {
    position:      'relative',
    width:         '100%',
    maxWidth:      460,
    padding:       '48px 40px',
    display:       'flex',
    flexDirection: 'column',
    alignItems:    'center',
    textAlign:     'center',
    gap:           0,
    zIndex:        1,
  },

  logo: {
    width:          64,
    height:         64,
    borderRadius:   16,
    background:     'linear-gradient(135deg, var(--color-primary), var(--color-primary-light))',
    display:        'flex',
    alignItems:     'center',
    justifyContent: 'center',
    fontSize:       32,
    fontFamily:     'var(--font-display)',
    fontWeight:     800,
    color:          'white',
    boxShadow:      'var(--shadow-glow)',
    marginBottom:   28,
    animation:      'pulse-glow 3s ease-in-out infinite',
  },

  heading: {
    fontSize:     28,
    fontFamily:   'var(--font-display)',
    fontWeight:   700,
    color:        'var(--color-text)',
    marginBottom: 10,
    lineHeight:   1.2,
  },

  subtitle: {
    fontSize:     14,
    color:        'var(--color-text-muted)',
    lineHeight:   1.65,
    maxWidth:     340,
    marginBottom: 28,
  },

  features: {
    display:        'flex',
    flexWrap:       'wrap',
    justifyContent: 'center',
    gap:            8,
    marginBottom:   32,
  },

  pill: {
    display:       'flex',
    alignItems:    'center',
    gap:           6,
    padding:       '5px 12px',
    borderRadius:  20,
    background:    'var(--color-surface-2)',
    border:        '1px solid var(--color-border-subtle)',
    whiteSpace:    'nowrap',
  },

  divider: {
    display:        'flex',
    alignItems:     'center',
    gap:            12,
    width:          '100%',
    marginBottom:   24,
  },
  dividerLine: {
    flex:       1,
    height:     1,
    background: 'var(--color-border-subtle)',
  },
  dividerText: {
    fontSize: 12,
    color:    'var(--color-text-faint)',
    flexShrink: 0,
  },

  /* Google button */
  googleBtn: {
    width:           '100%',
    display:         'flex',
    alignItems:      'center',
    justifyContent:  'center',
    gap:             12,
    padding:         '13px 20px',
    borderRadius:    'var(--radius-md)',
    background:      '#ffffff',
    color:           '#1a1a2e',
    fontFamily:      'var(--font-sans)',
    fontWeight:      600,
    fontSize:        15,
    border:          'none',
    cursor:          'pointer',
    transition:      'all 150ms ease',
    marginBottom:    24,
    boxShadow:       '0 2px 12px rgba(0,0,0,0.3)',
  },
  googleBtnHover: {
    width:           '100%',
    display:         'flex',
    alignItems:      'center',
    justifyContent:  'center',
    gap:             12,
    padding:         '13px 20px',
    borderRadius:    'var(--radius-md)',
    background:      '#f5f5f5',
    color:           '#1a1a2e',
    fontFamily:      'var(--font-sans)',
    fontWeight:      600,
    fontSize:        15,
    border:          'none',
    cursor:          'pointer',
    transition:      'all 150ms ease',
    marginBottom:    24,
    boxShadow:       '0 4px 20px rgba(0,0,0,0.4)',
    transform:       'translateY(-1px)',
  },

  securityNote: {
    fontSize:   11,
    color:      'var(--color-text-faint)',
    margin:     0,
    lineHeight: 1.5,
  },
}
