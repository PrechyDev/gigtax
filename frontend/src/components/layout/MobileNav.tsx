import { useState } from 'react'
import { NavLink } from 'react-router-dom'
import { PRIMARY_NAV_ITEMS, SECONDARY_NAV_ITEMS } from './navItems'
import { useAuth } from '../../context/AuthContext'

export function MobileNav() {
  const [moreOpen, setMoreOpen] = useState(false)
  const { logout } = useAuth()

  return (
    <>
      {moreOpen && (
        <div 
          className="fixed inset-0 z-30 bg-navy/20 dark:bg-black/40 backdrop-blur-sm md:hidden"
          onClick={() => setMoreOpen(false)}
        />
      )}
      
      {moreOpen && (
        <div className="fixed inset-x-0 bottom-[60px] z-40 bg-surface-container-lowest rounded-t-xl border-t border-outline-variant p-4 shadow-level-2 md:hidden">
          <h3 className="text-sm font-bold text-navy dark:text-white mb-2 px-2">More</h3>
          <div className="flex flex-col gap-1">
            {SECONDARY_NAV_ITEMS.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                onClick={() => setMoreOpen(false)}
                className={({ isActive }) =>
                  `flex items-center gap-3 rounded-md px-3 py-3 text-sm font-medium transition-colors ${
                    isActive
                      ? 'bg-accent/10 text-accent-dark dark:text-accent'
                      : 'text-on-surface-variant'
                  }`
                }
              >
                <span className="material-symbols-outlined text-xl">{item.icon}</span>
                {item.label}
              </NavLink>
            ))}
            <button
              onClick={() => { setMoreOpen(false); logout(); }}
              className="flex items-center gap-3 rounded-md px-3 py-3 text-sm font-medium text-on-surface-variant mt-2 border-t border-outline-variant"
            >
              <span className="material-symbols-outlined text-xl">logout</span>
              Log Out
            </button>
          </div>
        </div>
      )}

      <nav className="fixed inset-x-0 bottom-0 z-50 flex border-t border-outline-variant bg-surface-container-lowest md:hidden pb-safe">
        {PRIMARY_NAV_ITEMS.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            className={({ isActive }) =>
              `flex flex-1 flex-col items-center gap-0.5 py-2 text-xs ${isActive ? 'text-accent' : 'text-on-surface-variant'}`
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
        
        <button
          onClick={() => setMoreOpen(!moreOpen)}
          className={`flex flex-1 flex-col items-center gap-0.5 py-2 text-xs ${moreOpen ? 'text-accent' : 'text-on-surface-variant'}`}
        >
          <span className={`material-symbols-outlined text-xl ${moreOpen ? 'fill' : ''}`}>menu</span>
          More
        </button>
      </nav>
    </>
  )
}
