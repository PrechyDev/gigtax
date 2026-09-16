import { Link } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'
import { useTheme } from '../../context/ThemeContext'
import { AccountMenu } from './AccountMenu'

export function TopBar({ title }: { title: string }) {
  const { user } = useAuth()
  const { themeMode, toggleTheme } = useTheme()

  const getThemeIcon = () => {
    if (themeMode === 'auto') {
      const isDark = window.matchMedia('(prefers-color-scheme: dark)').matches
      return isDark ? 'dark_mode' : 'light_mode'
    }
    return themeMode === 'dark' ? 'dark_mode' : 'light_mode'
  }

  return (
    <header className="flex items-center justify-between border-b border-outline-variant bg-surface-container-lowest px-4 py-3 md:px-8">
      <Link to="/dashboard" className="md:hidden flex items-center gap-2 text-navy dark:text-white hover:opacity-80 transition-opacity">
        <span className="text-lg font-bold">GigTax</span>
      </Link>
      <h1 className="hidden text-xl font-semibold text-navy dark:text-white md:block">{title}</h1>
      <div className="flex items-center gap-3">
        {user?.google_drive_connected && (
          <span
            className="material-symbols-outlined text-emerald"
            title="Google Drive connected"
          >
            cloud_done
          </span>
        )}
        <button 
          onClick={toggleTheme} 
          className="p-1 rounded-md text-on-surface hover:bg-surface-container-low transition-colors"
          title="Toggle theme"
        >
          <span className="material-symbols-outlined text-xl">{getThemeIcon()}</span>
        </button>
        <AccountMenu />
      </div>
    </header>
  )
}
