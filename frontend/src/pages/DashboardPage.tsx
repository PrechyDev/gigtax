import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { getDashboard } from '../api/tax'
import { useAuth } from '../context/AuthContext'
import { AppShell } from '../components/layout/AppShell'
import { PageSpinner } from '../components/ui/Spinner'
import { ErrorBanner } from '../components/ui/Banner'
import { YearSelector } from '../components/ui/YearSelector'
import { ApiError } from '../lib/apiClient'
import { formatNaira } from '../lib/formatters'

export function DashboardPage() {
  const { user } = useAuth()
  // Defaults to the real current year, not the profile's Tax Year field — that field
  // is a static setting nobody reliably remembers to bump every January, which is
  // exactly what made last year's data vanish from the dashboard once the calendar
  // rolled over. This selector is how you look at a prior year on purpose instead.
  const [taxYear, setTaxYear] = useState(() => String(new Date().getFullYear()))

  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: ['dashboard', taxYear],
    queryFn: () => getDashboard(taxYear),
  })

  return (
    <AppShell title="Dashboard">
      <div className="mb-6 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-2xl font-bold text-navy">Welcome back, {user?.name?.split(' ')[0]}</h2>
          <p className="text-on-surface-variant">Here is your financial overview for Fiscal Year {taxYear}</p>
        </div>
        <YearSelector value={taxYear} onChange={setTaxYear} />
      </div>

      {isLoading && <PageSpinner />}
      {isError && (
        <ErrorBanner
          message={error instanceof ApiError ? error.message : 'Could not load your dashboard.'}
          onRetry={() => refetch()}
        />
      )}

      {data && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
            <StatCard label="Gross Income (YTD)" value={formatNaira(data.total_income)} icon="payments" />
            <StatCard label="Allowable Deductions" value={formatNaira(data.total_deductions)} icon="receipt_long" />
            <StatCard
              label="Capital Allowances"
              value={formatNaira(data.total_capital_allowances)}
              icon="inventory_2"
            />
          </div>

          <div className="rounded-lg bg-navy p-6 text-white shadow-level-1">
            <p className="text-sm text-white/70">Estimated Tax Liability ({taxYear})</p>
            <p className="mt-1 text-3xl font-bold tabular-nums">{formatNaira(data.estimated_tax_owed)}</p>
          </div>

          <div className="rounded-lg border border-outline-variant bg-surface-container-lowest p-6 shadow-level-1">
            <h3 className="mb-3 font-semibold text-navy">Outstanding Actions</h3>
            {data.outstanding_actions.length > 0 ? (
              <ul className="space-y-2">
                {data.outstanding_actions.map((action) => (
                  <li key={action.href + action.message}>
                    <Link
                      to={action.href}
                      className="flex items-start gap-2 text-sm text-on-surface-variant hover:text-blue-dark hover:underline"
                    >
                      <span className="material-symbols-outlined text-lg text-blue">arrow_right</span>
                      {action.message}
                    </Link>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="flex items-center gap-2 text-sm text-emerald-dark">
                <span className="material-symbols-outlined text-lg">check_circle</span>
                You're all caught up — nothing outstanding.
              </p>
            )}
          </div>

          <p className="text-xs text-on-surface-variant">{data.filing_guidance}</p>
        </div>
      )}
    </AppShell>
  )
}

function StatCard({ label, value, icon }: { label: string; value: string; icon: string }) {
  return (
    <div className="rounded-lg bg-surface-container-lowest p-5 shadow-level-1">
      <div className="mb-2 flex items-center gap-2 text-on-surface-variant">
        <span className="material-symbols-outlined text-xl">{icon}</span>
        <span className="text-sm font-medium">{label}</span>
      </div>
      <p className="text-2xl font-bold tabular-nums text-navy">{value}</p>
    </div>
  )
}
