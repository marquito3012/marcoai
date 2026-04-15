/**
 * RouteIndicator – Shows which module the Supervisor agent routed to
 *
 * Appears as a small animated badge above the response bubble when the
 * LangGraph supervisor has classified the user's intent. Fades out after
 * the streaming response is complete.
 *
 * Props:
 *   route  – { intent: string, label: string } | null
 */

const MODULE_ICONS = {
  GENERAL_CHAT: '💬',
  CALENDAR:     '📅',
  FINANCE:      '💰',
  MAIL:         '📧',
  FILES:        '📁',
  HABITS:       '🔥',
}

const MODULE_COLORS = {
  GENERAL_CHAT: 'var(--color-primary-light)',
  CALENDAR:     'var(--color-calendar)',
  FINANCE:      'var(--color-finance)',
  MAIL:         'var(--color-mail)',
  FILES:        'var(--color-files)',
  HABITS:       'var(--color-habits)',
}

export default function RouteIndicator({ route }) {
  if (!route) return null

  const icon  = MODULE_ICONS[route.intent]  ?? '🤖'
  const color = MODULE_COLORS[route.intent] ?? 'var(--color-primary-light)'

  return (
    <div
      className="fade-in-up"
      style={{
        display:        'flex',
        alignItems:     'center',
        gap:            6,
        padding:        '4px 12px 4px 8px',
        borderRadius:   20,
        background:     `${color}14`,
        border:         `1px solid ${color}33`,
        width:          'fit-content',
        marginLeft:     44,  // align with assistant bubble
        marginBottom:   6,
      }}
      aria-label={`Módulo detectado: ${route.label}`}
    >
      <span style={{ fontSize: 13 }}>{icon}</span>
      <span style={{ fontSize: 11, color, fontWeight: 600, letterSpacing: '0.04em' }}>
        {route.label}
      </span>
      {/* Animated dot while still routing */}
      <div style={{
        width:        6,
        height:       6,
        borderRadius: '50%',
        background:   color,
        opacity:      0.6,
        animation:    'typing-dot 1.2s infinite',
      }} />
    </div>
  )
}
