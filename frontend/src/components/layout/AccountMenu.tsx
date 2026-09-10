import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'

/** Replaces what used to be an inert avatar circle — on mobile there was no other way
 * to reach Settings or log out at all (the sidebar with the only Log Out button is
 * desktop-only). Rendered at every breakpoint; desktop keeps its sidebar shortcuts too.
 */
export function AccountMenu() {
  const { user, logout } = useAuth()
  const [isOpen, setIsOpen] = useState(false)
  const containerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!isOpen) return
    function handleClickOutside(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setIsOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [isOpen])

  return (
    <div ref={containerRef} className="relative">
      <button
        onClick={() => setIsOpen((v) => !v)}
        aria-label="Account menu"
        className="flex h-9 w-9 items-center justify-center rounded-full bg-blue/10 text-sm font-semibold text-blue-dark"
      >
        {user?.name?.charAt(0).toUpperCase() ?? '?'}
      </button>

      {isOpen && (
        <div className="absolute right-0 top-full z-50 mt-2 w-56 rounded-lg border border-outline-variant bg-surface-container-lowest py-2 shadow-level-1">
          <div className="border-b border-outline-variant px-4 py-2">
            <p className="truncate text-sm font-semibold text-navy">{user?.name}</p>
            <p className="truncate text-xs text-on-surface-variant">{user?.email}</p>
          </div>
          <Link
            to="/settings"
            onClick={() => setIsOpen(false)}
            className="flex items-center gap-2 px-4 py-2 text-sm text-on-surface hover:bg-surface-container-low"
          >
            <span className="material-symbols-outlined text-lg">settings</span>
            Settings
          </Link>
          <Link
            to="/assets"
            onClick={() => setIsOpen(false)}
            className="flex items-center gap-2 px-4 py-2 text-sm text-on-surface hover:bg-surface-container-low"
          >
            <span className="material-symbols-outlined text-lg">inventory_2</span>
            Assets
          </Link>
          <button
            onClick={logout}
            className="flex w-full items-center gap-2 px-4 py-2 text-left text-sm text-error hover:bg-surface-container-low"
          >
            <span className="material-symbols-outlined text-lg">logout</span>
            Log Out
          </button>
        </div>
      )}
    </div>
  )
}
