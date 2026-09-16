import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

const DISMISSED_KEY = 'gigtax:profile-banner-dismissed'

function isDismissedThisSession(): boolean {
  try {
    return sessionStorage.getItem(DISMISSED_KEY) === '1'
  } catch {
    return false
  }
}

export function ProfileCompletionBanner() {
  const { user } = useAuth()
  const [dismissed, setDismissed] = useState(isDismissedThisSession)

  if (!user || dismissed) return null

  const missing = !user.occupation_type || !user.state_residence || !user.tax_year
  if (!missing) return null

  function dismiss() {
    setDismissed(true)
    try {
      sessionStorage.setItem(DISMISSED_KEY, '1')
    } catch {
      // sessionStorage unavailable — dismissal just won't persist across remounts this session
    }
  }

  return (
    <div className="mb-4 flex items-start gap-3 rounded-lg border border-accent/20 bg-accent/5 px-4 py-3">
      <span className="material-symbols-outlined mt-0.5 shrink-0 text-accent">info</span>
      <p className="flex-1 text-sm text-navy">
        Your profile is incomplete — add your occupation, state, and tax year so we can tailor your
        reliefs and filing guidance.{' '}
        <Link to="/settings" className="font-semibold text-accent underline">
          Complete profile
        </Link>
      </p>
      <button onClick={dismiss} aria-label="Dismiss" className="shrink-0 text-accent/70">
        <span className="material-symbols-outlined text-lg">close</span>
      </button>
    </div>
  )
}
