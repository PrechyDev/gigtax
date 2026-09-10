import { NavLink } from 'react-router-dom'
import { NAV_ITEMS } from './navItems'

// A compact subset for the small mobile bottom bar — the mockups used different,
// inconsistent mobile nav sets per screen (or none at all); one set, used everywhere.
// Settings was here before Ingestion — since the account menu (see AccountMenu.tsx)
// now reaches Settings from every breakpoint, Ingestion belongs in the bottom bar
// instead: it's where a statement actually gets uploaded, and previously had no path
// to it at all on mobile.
const MOBILE_ITEMS = NAV_ITEMS.filter((item) =>
  ['/dashboard', '/ingestion', '/ledger', '/reports', '/advisor'].includes(item.to),
)

export function MobileNav() {
  return (
    <nav className="fixed inset-x-0 bottom-0 z-40 flex border-t border-outline-variant bg-surface-container-lowest md:hidden">
      {MOBILE_ITEMS.map((item) => (
        <NavLink
          key={item.to}
          to={item.to}
          className={({ isActive }) =>
            `flex flex-1 flex-col items-center gap-0.5 py-2 text-xs ${isActive ? 'text-blue' : 'text-on-surface-variant'}`
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
  )
}
