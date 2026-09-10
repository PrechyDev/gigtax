import { NavLink } from 'react-router-dom'
import { NAV_ITEMS } from './navItems'
import { useAuth } from '../../context/AuthContext'

export function Sidebar() {
  const { logout } = useAuth()

  return (
    <aside className="hidden w-64 shrink-0 flex-col border-r border-outline-variant bg-surface-container-lowest md:flex">
      <div className="flex items-center gap-2 px-6 py-6">
        <h1 className="text-xl font-bold text-navy">GigTax</h1>
      </div>

      <nav className="flex-1 space-y-1 px-3">
        {NAV_ITEMS.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            className={({ isActive }) =>
              `flex items-center gap-3 rounded-md px-3 py-2.5 text-sm font-medium transition-colors ${
                isActive
                  ? 'border-r-4 border-blue bg-blue/10 text-blue-dark'
                  : 'text-on-surface-variant hover:bg-surface-container-low'
              }`
            }
          >
            {({ isActive }) => (
              <>
                <span className={`material-symbols-outlined text-xl ${isActive ? 'fill' : ''}`}>{item.icon}</span>
                {item.label}
              </>
            )}
          </NavLink>
        ))}
      </nav>

      <div className="space-y-2 border-t border-outline-variant px-3 py-4">
        <button
          onClick={logout}
          className="flex w-full items-center gap-3 rounded-md px-3 py-2.5 text-sm font-medium text-on-surface-variant hover:bg-surface-container-low"
        >
          <span className="material-symbols-outlined text-xl">logout</span>
          Log Out
        </button>
      </div>
    </aside>
  )
}
