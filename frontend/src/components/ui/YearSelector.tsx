/** A small inline tax-year picker shared by Dashboard and Reports — both default to
 * the current calendar year rather than a static profile setting (see
 * pages/DashboardPage.tsx and pages/ReportsPage.tsx), so this is how a user looks back
 * at a prior year's numbers without ever touching Settings.
 */
export function YearSelector({
  value,
  onChange,
  yearsBack = 5,
}: {
  value: string
  onChange: (year: string) => void
  yearsBack?: number
}) {
  const currentYear = new Date().getFullYear()
  const years = Array.from({ length: yearsBack + 1 }, (_, i) => String(currentYear - i))
  // The selected year might not be in the generated range (e.g. a profile-set year
  // from before this component existed) — keep it selectable rather than silently
  // snapping to something else the user didn't choose.
  const options = years.includes(value) ? years : [value, ...years]

  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value)}
      aria-label="Tax year"
      className="h-11 rounded-md border border-outline-variant bg-surface-container-lowest px-3 text-sm font-medium text-navy focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent"
    >
      {options.map((y) => (
        <option key={y} value={y}>
          {y}
        </option>
      ))}
    </select>
  )
}
