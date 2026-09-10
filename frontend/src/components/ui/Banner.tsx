interface BannerProps {
  message: string
  onRetry?: () => void
  onDismiss?: () => void
}

/** Every failed query/mutation renders through here — always the backend's `detail`
 * string (already a safe, friendly message; see the backend's global exception
 * handler and per-route error wrapping), never raw technical detail.
 */
export function ErrorBanner({ message, onRetry, onDismiss }: BannerProps) {
  return (
    <div className="flex items-start gap-3 rounded-lg border border-error/20 bg-error-container px-4 py-3 text-on-error-container">
      <span className="material-symbols-outlined mt-0.5 shrink-0 text-error">error</span>
      <p className="flex-1 text-sm">{message}</p>
      {onRetry && (
        <button
          onClick={onRetry}
          className="shrink-0 rounded-md px-2 py-1 text-sm font-semibold underline hover:no-underline"
        >
          Retry
        </button>
      )}
      {onDismiss && (
        <button onClick={onDismiss} aria-label="Dismiss" className="shrink-0 text-on-error-container/70">
          <span className="material-symbols-outlined text-lg">close</span>
        </button>
      )}
    </div>
  )
}

export function SuccessBanner({ message, onDismiss }: BannerProps) {
  return (
    <div className="flex items-start gap-3 rounded-lg border border-emerald/20 bg-emerald/10 px-4 py-3 text-emerald-dark">
      <span className="material-symbols-outlined mt-0.5 shrink-0 text-emerald">check_circle</span>
      <p className="flex-1 text-sm">{message}</p>
      {onDismiss && (
        <button onClick={onDismiss} aria-label="Dismiss" className="shrink-0 text-emerald-dark/70">
          <span className="material-symbols-outlined text-lg">close</span>
        </button>
      )}
    </div>
  )
}
