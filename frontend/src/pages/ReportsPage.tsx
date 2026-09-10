import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { computeTax, downloadReport, getTaxComputation } from '../api/tax'
import { useAuth } from '../context/AuthContext'
import { AppShell } from '../components/layout/AppShell'
import { Button } from '../components/ui/Button'
import { ErrorBanner } from '../components/ui/Banner'
import { PageSpinner } from '../components/ui/Spinner'
import { ApiError } from '../lib/apiClient'
import { formatDateTime, formatNaira } from '../lib/formatters'

const CURRENT_YEAR = String(new Date().getFullYear())

export function ReportsPage() {
  const { user } = useAuth()
  const queryClient = useQueryClient()
  const taxYear = user?.tax_year ?? CURRENT_YEAR
  const [error, setError] = useState<string | null>(null)
  const [isDownloading, setIsDownloading] = useState(false)

  const computationQuery = useQuery({
    queryKey: ['tax-computation', taxYear],
    queryFn: () => getTaxComputation(taxYear),
    retry: false,
  })

  const computeMutation = useMutation({
    mutationFn: () => computeTax(taxYear),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['tax-computation', taxYear] }),
    onError: (err) => setError(err instanceof ApiError ? err.message : 'Could not compute your tax liability.'),
  })

  async function handleDownload() {
    setError(null)
    setIsDownloading(true)
    try {
      const blob = await downloadReport(taxYear)
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = `GigTax-Report-${taxYear}.pdf`
      link.click()
      URL.revokeObjectURL(url)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not generate your report.')
    } finally {
      setIsDownloading(false)
    }
  }

  const notComputedYet = computationQuery.isError && computationQuery.error instanceof ApiError && computationQuery.error.status === 404

  return (
    <AppShell title="Annual Tax Report">
      <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
        <p className="text-on-surface-variant">Fiscal Year {taxYear} — Self-Assessment Summary</p>
        <div className="flex gap-2">
          <Button variant="secondary" isLoading={computeMutation.isPending} onClick={() => computeMutation.mutate()}>
            Recompute
          </Button>
          <Button
            isLoading={isDownloading}
            disabled={!computationQuery.data}
            onClick={handleDownload}
          >
            Download Report
          </Button>
        </div>
      </div>

      {error && (
        <div className="mb-4">
          <ErrorBanner message={error} />
        </div>
      )}

      {computationQuery.isLoading && <PageSpinner />}

      {notComputedYet && (
        <div className="rounded-lg bg-surface-container-lowest p-8 text-center shadow-level-1">
          <p className="mb-4 text-on-surface-variant">
            No computation yet for {taxYear} — run it against your currently approved transactions.
          </p>
          <Button isLoading={computeMutation.isPending} onClick={() => computeMutation.mutate()}>
            Compute Tax Now
          </Button>
        </div>
      )}

      {computationQuery.isError && !notComputedYet && (
        <ErrorBanner
          message={computationQuery.error instanceof ApiError ? computationQuery.error.message : 'Could not load your tax computation.'}
          onRetry={() => computationQuery.refetch()}
        />
      )}

      {computationQuery.data && (
        <div className="space-y-6">
          {computationQuery.data.minimum_wage_exempt && (
            <div className="rounded-lg bg-emerald/10 p-4 text-emerald-dark">
              Total income is at or below the National Minimum Wage — fully exempt under NTA 2025.
            </div>
          )}

          <div className="rounded-lg bg-surface-container-lowest shadow-level-1">
            <SummaryRow label="Total Income (s.28)" value={computationQuery.data.total_income} />
            <SummaryRow label="Allowable Deductions (ss.20-21)" value={-computationQuery.data.total_deductions} />
            <SummaryRow label="Capital Allowances (First Schedule)" value={-computationQuery.data.total_capital_allowances} />
            <SummaryRow label="Statutory Reliefs (s.30)" value={-computationQuery.data.total_reliefs} />
            <SummaryRow label="Chargeable Income" value={computationQuery.data.taxable_income} bold />
            <SummaryRow label="Net Tax Payable (Fourth Schedule)" value={computationQuery.data.estimated_tax_owed} bold last />
          </div>

          {computationQuery.data.band_breakdown.length > 0 && (
            <div className="rounded-lg bg-surface-container-lowest p-6 shadow-level-1">
              <h3 className="mb-4 font-semibold text-navy">Band-by-band computation</h3>
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-xs font-semibold uppercase text-on-surface-variant">
                    <th className="pb-2">Rate</th>
                    <th className="pb-2 tabular-nums">Amount in Band</th>
                    <th className="pb-2 tabular-nums">Tax</th>
                  </tr>
                </thead>
                <tbody>
                  {computationQuery.data.band_breakdown.map((band, i) => (
                    <tr key={i} className="border-t border-outline-variant">
                      <td className="py-2">{(band.rate * 100).toFixed(0)}%</td>
                      <td className="py-2 tabular-nums">{formatNaira(band.amount_in_band)}</td>
                      <td className="py-2 tabular-nums">{formatNaira(band.tax)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {computationQuery.data.last_updated && (
            <p className="text-xs text-on-surface-variant">
              Last computed: {formatDateTime(computationQuery.data.last_updated)}
            </p>
          )}
        </div>
      )}
    </AppShell>
  )
}

function SummaryRow({ label, value, bold, last }: { label: string; value: number; bold?: boolean; last?: boolean }) {
  return (
    <div className={`flex items-center justify-between px-6 py-4 ${!last ? 'border-b border-outline-variant' : ''}`}>
      <span className={bold ? 'font-semibold text-navy' : 'text-on-surface-variant'}>{label}</span>
      <span className={`tabular-nums ${bold ? 'text-lg font-bold text-navy' : ''}`}>{formatNaira(value)}</span>
    </div>
  )
}
