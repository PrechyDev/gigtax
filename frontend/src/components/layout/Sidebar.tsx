import { useState } from 'react'
import { NavLink } from 'react-router-dom'
import { NAV_ITEMS } from './navItems'
import { useAuth } from '../../context/AuthContext'

export function Sidebar() {
  const { logout } = useAuth()
  const [collapsed, setCollapsed] = useState(false)

  return (
    <aside className={`hidden shrink-0 flex-col border-r border-outline-variant bg-surface-container-lowest md:flex transition-[width] duration-150 ease-in-out h-screen overflow-y-auto ${collapsed ? 'w-[72px]' : 'w-56'}`}>
      <button 
        onClick={() => setCollapsed(!collapsed)}
        className={`flex items-center gap-2 px-4 py-6 w-full text-navy dark:text-white hover:opacity-80 transition-opacity ${collapsed ? 'justify-center' : 'justify-start'}`}
        title="Toggle sidebar"
      >
        <span className="material-symbols-outlined text-xl shrink-0 text-accent">payments</span>
        {!collapsed && (
          <>
            <span className="text-xl font-bold">GigTax</span>
            <span className="material-symbols-outlined ml-auto text-on-surface-variant text-base">
              chevron_left
            </span>
          </>
        )}
      </button>

      <nav className="flex-1 space-y-1 px-3">
        {NAV_ITEMS.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            title={collapsed ? item.label : undefined}
            className={({ isActive }) =>
              `flex items-center gap-3 rounded-md px-3 py-2.5 text-sm font-medium transition-colors border-l-2 ${
                isActive
                  ? 'border-accent bg-accent/10 text-accent-dark dark:text-accent'
                  : 'text-on-surface-variant hover:bg-surface-container-low border-transparent'
              } ${collapsed ? 'justify-center' : ''}`
            }
          >
            {({ isActive }) => (
              <>
                <span className={`material-symbols-outlined text-xl shrink-0 ${isActive ? 'fill' : ''}`}>{item.icon}</span>
                {!collapsed && item.label}
              </>
            )}
          </NavLink>
        ))}
      </nav>

      <div className="border-t border-outline-variant px-3 py-4 mt-2">
        <button
          onClick={logout}
          title={collapsed ? "Log Out" : undefined}
          className={`flex w-full items-center gap-3 rounded-md px-3 py-2.5 text-sm font-medium text-on-surface-variant hover:bg-surface-container-low ${collapsed ? 'justify-center' : ''}`}
        >
          <span className="material-symbols-outlined text-xl shrink-0">logout</span>
          {!collapsed && "Log Out"}
        </button>
      </div>
    </aside>
  )
}
