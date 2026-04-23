import {
  MessageSquare,
  Calendar,
  BadgeDollarSign,
  Mail,
  Cloud,
  Flame,
  Settings,
  LogOut,
} from 'lucide-react'
import { NavLink } from 'react-router-dom'
import { useAuth } from '../../hooks/useAuth.js'

const NAV_ITEMS = [
  { to: '/chat',     icon: MessageSquare,    label: 'Chat',      id: 'nav-chat'     },
  { to: '/calendar', icon: Calendar,         label: 'Agenda',    id: 'nav-calendar' },
  { to: '/finance',  icon: BadgeDollarSign,  label: 'Finanzas',  id: 'nav-finance'  },
  { to: '/mail',     icon: Mail,             label: 'Correo',    id: 'nav-mail'     },
  { to: '/files',    icon: Cloud,            label: 'Nube',      id: 'nav-files'    },
  { to: '/habits',   icon: Flame,            label: 'Hábitos',   id: 'nav-habits'   },
]

export default function Sidebar() {
  const { user, logout } = useAuth()

  return (
    <aside className="sidebar" role="navigation" aria-label="Navegación principal">
      {/* Logo */}
      <div className="sidebar__logo" title="MarcoAI">
        <img src="/logo.png?v=2" alt="MarcoAI" style={{ width: '100%', height: '100%', objectFit: 'cover', borderRadius: 'inherit' }} />
      </div>

      <nav className="sidebar__nav">
        {NAV_ITEMS.map(({ to, icon: Icon, label, id }) => (
          <NavLink
            key={to}
            to={to}
            id={id}
            className={({ isActive }) =>
              `sidebar__item${isActive ? ' active' : ''}`
            }
            title={label}
          >
            <Icon strokeWidth={1.25} />
            <span>{label}</span>
          </NavLink>
        ))}
      </nav>

      <div className="sidebar__bottom">
        <NavLink
          to="/settings"
          id="nav-settings"
          className={({ isActive }) =>
            `sidebar__item${isActive ? ' active' : ''}`
          }
          title="Ajustes"
        >
          <Settings strokeWidth={1.25} />
          <span>Ajustes</span>
        </NavLink>

        {/* Logout */}
        <button
          id="btn-logout"
          className="sidebar__item"
          title="Cerrar sesión"
          onClick={logout}
        >
          <LogOut strokeWidth={1.25} />
          <span>Salir</span>
        </button>

        {/* User avatar – Google picture or initials fallback */}
        <div
          id="user-avatar"
          title={user?.name ?? 'Usuario'}
          style={{
            width:          40,
            height:         40,
            borderRadius:   '50%',
            overflow:       'hidden',
            border:         '1px solid var(--color-primary)',
            flexShrink:     0,
            display:        'flex',
            alignItems:     'center',
            justifyContent: 'center',
            background:     'var(--color-surface-3)',
            fontSize:       15,
            fontWeight:     600,
            color:          'var(--color-primary)',
            cursor:         'default',
          }}
        >
          {user?.picture_url ? (
            <img
              src={user.picture_url}
              alt={user.name}
              style={{ width: '100%', height: '100%', objectFit: 'cover' }}
              referrerPolicy="no-referrer"
            />
          ) : (
            (user?.name?.[0] ?? '?').toUpperCase()
          )}
        </div>
      </div>
    </aside>
  )
}

