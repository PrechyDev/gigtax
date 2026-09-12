import { useEffect, useState, type FormEvent, type ReactNode } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import ReactMarkdown from 'react-markdown'
import { computeTax, downloadReport, getTaxComputation, type CategoryAmountItem } from '../api/tax'
import { getFilingGuidance } from '../api/filingGuidance'
import { getAnnualTaxProfile, updateAnnualTaxProfile, type AnnualTaxProfileInput } from '../api/annualTaxProfile'
import { useAuth } from '../context/AuthContext'
import { AppShell } from '../components/layout/AppShell'
import { Button } from '../components/ui/Button'
import { ErrorBanner, SuccessBanner } from '../components/ui/Banner'
import { PageSpinner } from '../components/ui/Spinner'
import { YearSelector } from '../components/ui/YearSelector'
import { ApiError } from '../lib/apiClient'
import { formatDateTime, formatNaira } from '../lib/formatters'

export function ReportsPage() {
  const { user } = useAuth()
  const queryClient = useQueryClient()
  // Defaults to the real current year, not the profile's Tax Year field — see the same
  // note on DashboardPage.tsx. The selector below is how a prior year's report is
  // reached on purpose instead.
  const [taxYear, setTaxYear] = useState(() => String(new Date().getFullYear()))
  const [error, setError] = useState<string | null>(null)
  const [isDownloading, setIsDownloading] = useState(false)

  const computationQuery = useQuery({
    queryKey: ['tax-computation', taxYear],
    queryFn: () => getTaxComputation(taxYear),
    retry: false,
  })

  const filingGuidanceQuery = useQuery({
    queryKey: ['filing-guidance', user?.state_residence],
    queryFn: () => getFilingGuidance(user?.state_residence ?? undefined),
  })

  // Shares its cache/network request with RentHomeOfficePanel below (same query key) —
  // fetched here too just to drive the "Paying rent?" hint on the Statutory Reliefs row.
  const annualProfileQuery = useQuery({
    queryKey: ['annual-tax-profile', taxYear],
    queryFn: () => getAnnualTaxProfile(taxYear),
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
        <div className="flex items-center gap-3">
          <p className="text-on-surface-variant">Fiscal Year {taxYear} — Self-Assessment Summary</p>
          <YearSelector value={taxYear} onChange={setTaxYear} />
        </div>
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

      <div className="mb-6">
        <RentHomeOfficePanel taxYear={taxYear} />
      </div>

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
            <div className="flex items-center gap-3 rounded-lg bg-emerald/10 p-4 text-emerald-dark">
              <span className="material-symbols-outlined shrink-0">verified</span>
              Total income is at or below the National Minimum Wage — fully exempt from tax this year.
            </div>
          )}

          <div className="overflow-hidden rounded-lg bg-surface-container-lowest shadow-level-1">
            <h3 className="border-b border-outline-variant bg-navy px-6 py-3 text-sm font-semibold text-white">
              Tax Summary
            </h3>
            <BreakdownRow label="Total Income" value={computationQuery.data.total_income} items={computationQuery.data.income_items} />
            <BreakdownRow
              label="Allowable Deductions"
              value={-computationQuery.data.total_deductions}
              items={computationQuery.data.deduction_items}
            />
            <BreakdownRow
              label="Capital Allowances"
              value={-computationQuery.data.total_capital_allowances}
              items={computationQuery.data.capital_allowance_items}
            />
            <BreakdownRow
              label="Statutory Reliefs"
              value={-computationQuery.data.total_reliefs}
              items={computationQuery.data.relief_items}
              emptyHint={
                !annualProfileQuery.data?.annual_rent_paid ? (
                  <>
                    Paying rent?{' '}
                    <a href="#rent-home-office" className="text-blue hover:underline">
                      Add it above
                    </a>{' '}
                    to claim rent relief automatically for {taxYear}.
                  </>
                ) : undefined
              }
            />
            <SummaryRow label="Taxable Income" value={computationQuery.data.taxable_income} bold />
            <SummaryRow label="Net Tax Payable" value={computationQuery.data.estimated_tax_owed} bold last highlight />
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

          <FilingGuidancePanel guidance={filingGuidanceQuery.data} isLoading={filingGuidanceQuery.isLoading} />

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

function RentHomeOfficePanel({ taxYear }: { taxYear: string }) {
  const queryClient = useQueryClient()
  const previousYear = String(Number(taxYear) - 1)

  const profileQuery = useQuery({
    queryKey: ['annual-tax-profile', taxYear],
    queryFn: () => getAnnualTaxProfile(taxYear),
  })
  // Fetched purely to power the "copy last year's numbers" shortcut below — cheap,
  // and avoids the user having to remember and retype the same rent figure every year.
  const previousProfileQuery = useQuery({
    queryKey: ['annual-tax-profile', previousYear],
    queryFn: () => getAnnualTaxProfile(previousYear),
  })

  const [form, setForm] = useState<{
    annual_rent_paid: number | ''
    has_home_office: boolean
    home_office_percentage: number
  }>({ annual_rent_paid: '', has_home_office: false, home_office_percentage: 0 })
  const [success, setSuccess] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (profileQuery.data) {
      setForm({
        annual_rent_paid: profileQuery.data.annual_rent_paid ?? '',
        has_home_office: profileQuery.data.has_home_office,
        home_office_percentage: profileQuery.data.home_office_percentage,
      })
      setSuccess(false)
      setError(null)
    }
  }, [profileQuery.data])

  const mutation = useMutation({
    mutationFn: (input: AnnualTaxProfileInput) => updateAnnualTaxProfile(taxYear, input),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['annual-tax-profile', taxYear] })
      setSuccess(true)
      setError(null)
    },
    onError: (err) => setError(err instanceof ApiError ? err.message : 'Could not save this.'),
  })

  function handleSave(e: FormEvent) {
    e.preventDefault()
    setSuccess(false)
    mutation.mutate({
      annual_rent_paid: form.annual_rent_paid === '' ? null : Number(form.annual_rent_paid),
      has_home_office: form.has_home_office,
      home_office_percentage: form.home_office_percentage,
    })
  }

  function copyFromPreviousYear() {
    if (!previousProfileQuery.data) return
    setForm({
      annual_rent_paid: previousProfileQuery.data.annual_rent_paid ?? '',
      has_home_office: previousProfileQuery.data.has_home_office,
      home_office_percentage: previousProfileQuery.data.home_office_percentage,
    })
  }

  if (profileQuery.isLoading) return null

  const isBlank =
    !!profileQuery.data && profileQuery.data.annual_rent_paid === null && !profileQuery.data.has_home_office
  const previousHasData =
    !!previousProfileQuery.data &&
    (previousProfileQuery.data.annual_rent_paid !== null || previousProfileQuery.data.has_home_office)

  return (
    <div id="rent-home-office" className="scroll-mt-6 rounded-lg bg-surface-container-lowest p-6 shadow-level-1">
      <div className="mb-1 flex flex-wrap items-center justify-between gap-2">
        <h3 className="font-semibold text-navy">Rent &amp; Home Office — {taxYear}</h3>
        {isBlank && previousHasData && (
          <button type="button" onClick={copyFromPreviousYear} className="text-sm text-blue hover:underline">
            Copy {previousYear}'s numbers
          </button>
        )}
      </div>
      <p className="mb-4 text-sm text-on-surface-variant">
        Rent, and how much of your home you use for work, can change year to year — this is set for {taxYear}{' '}
        specifically and won't affect any other year.
      </p>

      {error && (
        <div className="mb-3">
          <ErrorBanner message={error} onDismiss={() => setError(null)} />
        </div>
      )}
      {success && (
        <div className="mb-3">
          <SuccessBanner
            message={`Saved for ${taxYear} — click Recompute above to refresh your tax summary.`}
            onDismiss={() => setSuccess(false)}
          />
        </div>
      )}

      <form onSubmit={handleSave} className="space-y-4">
        <div>
          <label className="mb-1 block text-sm font-semibold text-on-surface-variant">Annual Rent Paid (NGN)</label>
          <input
            type="number"
            min={0}
            step="0.01"
            value={form.annual_rent_paid}
            onChange={(e) =>
              setForm({ ...form, annual_rent_paid: e.target.value === '' ? '' : Number(e.target.value) })
            }
            className="h-11 w-full max-w-xs rounded-lg border border-outline-variant px-3 text-sm focus:border-blue focus:outline-none focus:ring-1 focus:ring-blue"
          />
        </div>

        <div className="rounded-lg border border-outline-variant p-4">
          <label className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={form.has_home_office}
              onChange={(e) => setForm({ ...form, has_home_office: e.target.checked })}
            />
            <span className="text-sm font-semibold">Home Office Deduction</span>
          </label>
          {form.has_home_office && (
            <div className="mt-3">
              <label className="mb-1 block text-sm text-on-surface-variant">
                {form.home_office_percentage}% of your rent counts as a home-office business expense
              </label>
              <input
                type="range"
                min={0}
                max={100}
                value={form.home_office_percentage}
                onChange={(e) => setForm({ ...form, home_office_percentage: Number(e.target.value) })}
                className="w-full"
              />
              <p className="mt-1 text-xs text-emerald-dark">
                The rest of your rent still counts toward your rent relief (20%, capped at ₦500,000).
              </p>
            </div>
          )}
        </div>

        <Button type="submit" isLoading={mutation.isPending}>
          Save for {taxYear}
        </Button>
      </form>
    </div>
  )
}

function FilingGuidancePanel({
  guidance,
  isLoading,
}: {
  guidance?: {
    state: string | null
    portal_name: string | null
    portal_url: string | null
    note: string
    guide_markdown: string | null
  }
  isLoading: boolean
}) {
  const [guideOpen, setGuideOpen] = useState(false)

  if (isLoading) return null
  if (!guidance) return null

  return (
    <div className="rounded-lg bg-surface-container-lowest p-6 shadow-level-1">
      <div className="mb-2 flex items-center gap-2">
        <span className="material-symbols-outlined text-blue">gavel</span>
        <h3 className="font-semibold text-navy">Filing Guidance{guidance.state ? ` — ${guidance.state}` : ''}</h3>
      </div>
      {guidance.portal_name && (
        <p className="mb-1 text-sm font-medium text-on-surface">{guidance.portal_name}</p>
      )}
      <p className="mb-3 text-sm text-on-surface-variant">{guidance.note}</p>
      {guidance.portal_url && (
        <a
          href={guidance.portal_url}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center justify-center gap-2 rounded-lg bg-blue px-4 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-blue-dark"
        >
          Go to {guidance.portal_name ?? 'portal'}
          <span className="material-symbols-outlined text-base">open_in_new</span>
        </a>
      )}
      {guidance.guide_markdown && (
        <div className="mt-4 border-t border-outline-variant pt-3">
          <button
            onClick={() => setGuideOpen((v) => !v)}
            className="flex w-full items-center justify-between text-sm font-semibold text-blue hover:underline"
          >
            {guideOpen ? 'Hide full filing walkthrough' : 'Show full filing walkthrough'}
            <span className="material-symbols-outlined text-base">{guideOpen ? 'expand_less' : 'expand_more'}</span>
          </button>
          {guideOpen && (
            <div className="markdown-content filing-guide-content mt-3 max-h-[32rem] overflow-y-auto text-sm">
              <ReactMarkdown>{guidance.guide_markdown}</ReactMarkdown>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

function SummaryRow({
  label,
  value,
  bold,
  last,
  highlight,
}: {
  label: string
  value: number
  bold?: boolean
  last?: boolean
  highlight?: boolean
}) {
  return (
    <div
      className={`flex items-center justify-between px-6 py-4 ${!last ? 'border-b border-outline-variant' : ''} ${
        highlight ? 'bg-blue/5' : ''
      }`}
    >
      <span className={bold ? 'font-semibold text-navy' : 'text-on-surface-variant'}>{label}</span>
      <span className={`tabular-nums ${bold ? 'text-lg font-bold text-navy' : ''}`}>{formatNaira(value)}</span>
    </div>
  )
}

function BreakdownRow({
  label,
  value,
  items,
  emptyHint,
}: {
  label: string
  value: number
  items: CategoryAmountItem[]
  emptyHint?: ReactNode
}) {
  return (
    <details className="group border-b border-outline-variant">
      <summary className="flex cursor-pointer list-none items-center justify-between px-6 py-4 [&::-webkit-details-marker]:hidden">
        <span className="flex items-center gap-2 text-on-surface-variant">
          <span className="material-symbols-outlined text-lg transition-transform group-open:rotate-90">
            chevron_right
          </span>
          {label}
        </span>
        <span className="tabular-nums">{formatNaira(value)}</span>
      </summary>
      <div className="px-6 pb-4 pl-11">
        {items.length > 0 ? (
          <ul className="space-y-1.5 text-sm text-on-surface-variant">
            {items.map((item) => (
              <li key={item.category_name} className="flex items-center justify-between gap-3">
                <span>
                  {item.category_name}
                  {item.rate != null && item.rate < 100 && (
                    <span className="ml-2 rounded bg-blue/10 px-1.5 py-0.5 text-xs font-medium text-blue">
                      {item.rate.toFixed(0)}% of {formatNaira(item.gross_amount ?? item.amount)}
                    </span>
                  )}
                </span>
                <span className="tabular-nums">{formatNaira(item.amount)}</span>
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-sm italic text-on-surface-variant">{emptyHint ?? 'Nothing in this category.'}</p>
        )}
      </div>
    </details>
  )
}
