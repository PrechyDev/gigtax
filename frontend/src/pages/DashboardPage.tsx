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
      <div className="flex flex-col gap-6">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <h3 className="m-0 mb-1 text-xl font-semibold">Welcome back, {user?.name?.split(' ')[0]}</h3>
            <p className="m-0 text-sm text-on-surface-variant">Here is where things stand for tax year {taxYear}</p>
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
          <>
            <div>
              <h6 className="m-0 mb-2 text-sm font-medium text-on-surface-variant">What you owe, based on approved records</h6>
              <div className="rounded-xl bg-accent p-4 text-bg shadow-md">
                <p className="m-0 text-xs opacity-85">Estimated tax owed, {taxYear}</p>
                <p className="m-0 mt-1 font-heading text-3xl font-semibold tabular-nums">{formatNaira(data.estimated_tax_owed)}</p>
                <p className="m-0 mt-2 text-xs opacity-85">
                  From {data.approved_transactions_count} approved transactions. Approve more in the ledger to refine this number.
                </p>
              </div>
            </div>

            <div>
              <h6 className="m-0 mb-2 text-sm font-medium text-on-surface-variant">How that number was reached</h6>
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 md:grid-cols-3">
                <StatCard 
                  label="Gross Income (YTD)" 
                  value={formatNaira(data.total_income)} 
                  icon="payments" 
                  hint="Total incoming payments across all accounts" 
                />
                <StatCard 
                  label="Allowable Deductions" 
                  value={formatNaira(data.total_deductions)} 
                  icon="receipt_long" 
                  hint="Approved business expenses subtracted from your income" 
                />
                <StatCard
                  label="Capital Allowances"
                  value={formatNaira(data.total_capital_allowances)}
                  icon="inventory_2"
                  hint="Write-downs for large equipment (laptops, cameras, etc.)"
                />
              </div>
            </div>

            <div>
              <h6 className="m-0 mb-2 text-sm font-medium text-on-surface-variant">Needs your attention</h6>
              <div className="flex flex-col gap-2">
                {data.outstanding_actions.length > 0 ? (
                  data.outstanding_actions.map((action) => (
                    <Link
                      key={action.href + action.message}
                      to={action.href}
                      className="flex items-center gap-3 border border-outline-variant bg-surface p-3 no-underline text-on-surface hover:bg-surface-container-low transition-colors rounded-lg"
                    >
                      <span className="material-symbols-outlined shrink-0 text-lg text-accent">info</span>
                      <span className="flex-1 text-sm">{action.message}</span>
                      <span className="material-symbols-outlined text-lg text-on-surface-variant/60">chevron_right</span>
                    </Link>
                  ))
                ) : (
                  <div className="flex items-center gap-2 p-3 text-sm text-on-surface-variant">
                    <span className="material-symbols-outlined text-lg text-accent">check_circle</span>
                    You are all caught up, nothing outstanding.
                  </div>
                )}
              </div>
            </div>
            
            <p className="text-xs text-on-surface-variant mt-2">{data.filing_guidance}</p>
          </>
        )}
      </div>
    </AppShell>
  )
}

function StatCard({ label, value, icon, hint }: { label: string; value: string; icon: string; hint: string }) {
  return (
    <div className="flex flex-col gap-2 rounded-xl bg-surface-container-lowest border border-outline-variant p-4 shadow-sm">
      <div className="flex items-center gap-2 text-on-surface-variant">
        <span className="material-symbols-outlined text-base">{icon}</span>
        <span className="text-xs font-medium">{label}</span>
      </div>
      <p className="m-0 font-heading text-xl font-semibold tabular-nums">{value}</p>
      <p className="m-0 text-xs text-on-surface-variant">{hint}</p>
    </div>
  )
}
