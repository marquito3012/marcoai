import {
  MessageSquare,
  Calendar,
  BadgeDollarSign,
  Mail,
  Cloud,
  Flame,
  Settings,
  User,
} from 'lucide-react'
import { NavLink, useLocation } from 'react-router-dom'

const NAV_ITEMS = [
  { to: '/chat',     icon: MessageSquare,    label: 'Chat',      id: 'nav-chat'     },
  { to: '/calendar', icon: Calendar,         label: 'Agenda',    id: 'nav-calendar' },
  { to: '/finance',  icon: BadgeDollarSign,  label: 'Finanzas',  id: 'nav-finance'  },
  { to: '/mail',     icon: Mail,             label: 'Correo',    id: 'nav-mail'     },
  { to: '/files',    icon: Cloud,            label: 'Nube',      id: 'nav-files'    },
  { to: '/habits',   icon: Flame,            label: 'Hábitos',   id: 'nav-habits'   },
]

export default function Sidebar() {
  return (
    <aside className="sidebar" role="navigation" aria-label="Navegación principal">
      {/* Logo */}
      <div className="sidebar__logo" title="MarcoAI">M</div>

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
            <Icon strokeWidth={1.75} />
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
          <Settings strokeWidth={1.75} />
          <span>Ajustes</span>
        </NavLink>

        {/* User avatar placeholder – will show Google photo after auth */}
        <button
          id="btn-user-avatar"
          className="sidebar__item"
          title="Perfil de usuario"
          style={{
            width: 40,
            height: 40,
            borderRadius: '50%',
            background: 'var(--color-surface-3)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}
        >
          <User size={18} strokeWidth={1.75} />
        </button>
      </div>
    </aside>
  )
}
