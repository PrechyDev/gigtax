import { useAuth } from '../../context/AuthContext'
import { AccountMenu } from './AccountMenu'

export function TopBar({ title }: { title: string }) {
  const { user } = useAuth()

  return (
    <header className="flex items-center justify-between border-b border-outline-variant bg-surface-container-lowest px-4 py-3 md:px-8">
      <h1 className="text-lg font-semibold text-navy md:hidden">GigTax</h1>
      <h1 className="hidden text-xl font-semibold text-navy md:block">{title}</h1>
      <div className="flex items-center gap-3">
        {user?.google_drive_connected && (
          <span
            className="material-symbols-outlined text-emerald"
            title="Google Drive connected"
          >
            cloud_done
          </span>
        )}
        <AccountMenu />
      </div>
    </header>
  )
}
