type PillTone = 'positive' | 'warning' | 'neutral' | 'negative'

const TONE_CLASSES: Record<PillTone, string> = {
  positive: 'bg-emerald/10 text-emerald-dark',
  warning: 'bg-amber-100 text-amber-800',
  neutral: 'bg-surface-container text-on-surface-variant',
  negative: 'bg-error-container text-on-error-container',
}

export function StatusPill({ label, tone }: { label: string; tone: PillTone }) {
  return (
    <span className={`inline-block rounded-full px-3 py-1 text-xs font-semibold ${TONE_CLASSES[tone]}`}>
      {label}
    </span>
  )
}

/** Maps the backend's actual status strings to a pill so every page renders the
 * same enum consistently instead of ad hoc per-page color choices.
 */
export function reviewStatusTone(status: string): PillTone {
  if (status === 'APPROVED') return 'positive'
  if (status === 'REJECTED') return 'negative'
  return 'warning' // PENDING
}

export function parsingStatusTone(status: string): PillTone {
  if (status === 'COMPLETED') return 'positive'
  if (status === 'FAILED') return 'negative'
  if (status === 'LOCKED') return 'warning'
  return 'neutral' // PENDING / PROCESSING
}

export function assetStatusTone(disposed: boolean, currentYearAllowance: number): PillTone {
  if (disposed) return 'neutral'
  if (currentYearAllowance === 0) return 'neutral' // fully depreciated
  return 'positive'
}
