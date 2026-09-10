interface EmptyStateProps {
  icon?: string
  message: string
  action?: { label: string; onClick: () => void }
}

/** Matches the one empty-state precedent in the mockups (upload_manual_entry's
 * "No recent uploads") — italic muted text, extended slightly with an optional icon
 * and action so it's usable across every list in the app, not just that one screen.
 */
export function EmptyState({ icon, message, action }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 py-12 text-center">
      {icon && <span className="material-symbols-outlined text-3xl text-outline">{icon}</span>}
      <p className="italic text-on-surface-variant">{message}</p>
      {action && (
        <button
          onClick={action.onClick}
          className="mt-2 rounded-md bg-blue px-4 py-2 text-sm font-semibold text-white hover:bg-blue-dark"
        >
          {action.label}
        </button>
      )}
    </div>
  )
}
