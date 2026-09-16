import { useEffect, useState, type FormEvent, type ReactNode } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import ReactMarkdown from 'react-markdown'
import { downloadReport, getTaxComputation, type CategoryAmountItem } from '../api/tax'
import { getFilingGuidance, type FilingGuidance } from '../api/filingGuidance'
import { getAnnualTaxProfile, updateAnnualTaxProfile, type AnnualTaxProfileInput } from '../api/annualTaxProfile'
import { useAuth } from '../context/AuthContext'
import { AppShell } from '../components/layout/AppShell'
import { Button } from '../components/ui/Button'
import { ErrorBanner, SuccessBanner } from '../components/ui/Banner'
import { PageSpinner } from '../components/ui/Spinner'
import { YearSelector } from '../components/ui/YearSelector'
import { ApiError } from '../lib/apiClient'
import { formatNaira } from '../lib/formatters'

export function ReportsPage() {
  const { user } = useAuth()
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

  const annualProfileQuery = useQuery({
    queryKey: ['annual-tax-profile', taxYear],
    queryFn: () => getAnnualTaxProfile(taxYear),
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


  return (
    <AppShell title="Self-assessment report">
      <div className="mx-auto flex max-w-[800px] flex-col gap-4">
        
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h3 className="m-0 mb-1 text-xl font-semibold text-navy">Self-assessment report</h3>
          </div>
          <div className="flex items-center gap-2">
            <YearSelector value={taxYear} onChange={setTaxYear} />
            <Button
              isLoading={isDownloading}
              disabled={!computationQuery.data}
              onClick={handleDownload}
            >
              <span className="material-symbols-outlined -ml-1 mr-1 text-[15px]">download</span>
              Download PDF
            </Button>
          </div>
        </div>

        {error && (
          <div className="mb-2">
            <ErrorBanner message={error} />
          </div>
        )}

        <RentHomeOfficePanel taxYear={taxYear} />

        {computationQuery.isLoading && <PageSpinner />}

        {computationQuery.isError && (
          <ErrorBanner
            message={computationQuery.error instanceof ApiError ? computationQuery.error.message : 'Could not load your tax computation.'}
            onRetry={() => computationQuery.refetch()}
          />
        )}

        {computationQuery.data && (
          <>
            {computationQuery.data.minimum_wage_exempt && (
              <div className="flex items-center gap-3 rounded-lg bg-emerald/10 p-4 text-sm text-emerald-dark border border-emerald/20">
                <span className="material-symbols-outlined shrink-0 text-lg">verified</span>
                Total income is at or below the National Minimum Wage — fully exempt from tax this year.
              </div>
            )}

            <div className="overflow-hidden rounded-lg border border-divider bg-surface shadow-sm">
              <div className="p-3">
                <span className="text-[15px] font-semibold text-navy">Summary</span>
                <p className="m-0 mt-1 text-[12px] text-on-surface-variant">Tap a line to see how it breaks down by category</p>
              </div>

              <div className="border-t border-divider">
                <BreakdownRow label="Total Income" section="Sixth Schedule" value={computationQuery.data.total_income} items={computationQuery.data.income_items} />
              </div>
              <div className="border-t border-divider">
                <BreakdownRow
                  label="Allowable Deductions"
                  section="S.20 PITA"
                  value={-computationQuery.data.total_deductions}
                  items={computationQuery.data.deduction_items}
                />
              </div>
              <div className="border-t border-divider">
                <BreakdownRow
                  label="Capital Allowances"
                  section="Fifth Schedule"
                  value={-computationQuery.data.total_capital_allowances}
                  items={computationQuery.data.capital_allowance_items}
                />
              </div>
              <div className="border-t border-divider">
                <BreakdownRow
                  label="Statutory Reliefs"
                  section="S.33 PITA"
                  value={-computationQuery.data.total_reliefs}
                  items={computationQuery.data.relief_items}
                  emptyHint={
                    !annualProfileQuery.data?.annual_rent_paid ? (
                      <>
                        Paying rent? Add it above to claim rent relief automatically for {taxYear}.
                      </>
                    ) : undefined
                  }
                />
              </div>

              <div className="flex justify-between border-t border-divider p-3 text-[13px]">
                <span>Chargeable income</span>
                <span className="tabular-nums font-semibold text-navy">{formatNaira(computationQuery.data.taxable_income)}</span>
              </div>
              <div className="flex justify-between border-t border-divider bg-accent/5 p-3 text-[14px]">
                <span className="font-semibold text-navy">Net tax payable</span>
                <span className="tabular-nums font-bold text-navy">{formatNaira(computationQuery.data.estimated_tax_owed)}</span>
              </div>
            </div>

            <FilingGuidancePanel guidance={filingGuidanceQuery.data} isLoading={filingGuidanceQuery.isLoading} state={user?.state_residence} />

            {computationQuery.data.band_breakdown.length > 0 && (
              <div className="overflow-hidden rounded-lg border border-divider bg-surface shadow-sm">
                <div className="p-3">
                  <span className="text-[15px] font-semibold text-navy">Tax bands</span>
                  <p className="m-0 mt-1 text-[12px] text-on-surface-variant">
                    How your chargeable income was taxed, band by band
                  </p>
                </div>
                <div className="border-t border-divider px-3 pb-3">
                  <table className="w-full text-left text-[13px]">
                    <thead>
                      <tr className="border-b border-divider">
                        <th className="py-2 font-medium text-on-surface-variant">Rate</th>
                        <th className="py-2 font-medium text-on-surface-variant tabular-nums text-right">Amount in band</th>
                        <th className="py-2 font-medium text-on-surface-variant tabular-nums text-right">Tax</th>
                      </tr>
                    </thead>
                    <tbody>
                      {computationQuery.data.band_breakdown.map((band, i) => (
                        <tr key={i} className="border-b border-divider/50 last:border-none">
                          <td className="py-2 text-on-surface-variant">{(band.rate * 100).toFixed(0)}%</td>
                          <td className="py-2 text-right text-on-surface-variant tabular-nums">{formatNaira(band.amount_in_band)}</td>
                          <td className="py-2 text-right text-on-surface-variant tabular-nums">{formatNaira(band.tax)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            <p className="m-0 text-[12px] text-on-surface-variant">
              This is a self-assessment estimate generated by GigTax based on the transactions you reviewed and
              approved. It is not a substitute for professional tax advice.
            </p>
          </>
        )}
      </div>
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
  const [isOpen, setIsOpen] = useState(false)

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
      queryClient.invalidateQueries({ queryKey: ['tax-computation', taxYear] })
      queryClient.invalidateQueries({ queryKey: ['dashboard'] })
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

  function copyFromPreviousYear(e: React.MouseEvent) {
    e.preventDefault()
    e.stopPropagation()
    if (!previousProfileQuery.data) return
    setForm({
      annual_rent_paid: previousProfileQuery.data.annual_rent_paid ?? '',
      has_home_office: previousProfileQuery.data.has_home_office,
      home_office_percentage: previousProfileQuery.data.home_office_percentage,
    })
    setIsOpen(true)
  }

  if (profileQuery.isLoading) return null

  const isBlank =
    !!profileQuery.data && profileQuery.data.annual_rent_paid === null && !profileQuery.data.has_home_office
  const previousHasData =
    !!previousProfileQuery.data &&
    (previousProfileQuery.data.annual_rent_paid !== null || previousProfileQuery.data.has_home_office)

  return (
    <div className="overflow-hidden rounded-lg border border-divider bg-surface shadow-sm">
      <button 
        onClick={() => setIsOpen(!isOpen)} 
        className="flex w-full cursor-pointer items-center gap-2 border-none bg-transparent p-3 text-left font-inherit text-inherit"
      >
        <span className="material-symbols-outlined shrink-0 text-base text-on-surface-variant transition-transform" style={{ transform: isOpen ? 'rotate(90deg)' : 'none' }}>
          chevron_right
        </span>
        <span className="flex-1 font-heading text-[15px] font-semibold">Rent and home office</span>
        {isBlank && previousHasData && (
          <span onClick={copyFromPreviousYear} className="text-xs text-accent hover:underline">
            Copy {previousYear}'s numbers
          </span>
        )}
      </button>

      {isOpen && (
        <div className="px-3 pb-3">
          <p className="m-0 mb-3 text-[12px] text-on-surface-variant">
            Rent, and how much of your home you use for work, can change year to year — this is set for {taxYear} specifically and won't affect any other year.
          </p>

          {error && (
            <div className="mb-2">
              <ErrorBanner message={error} onDismiss={() => setError(null)} />
            </div>
          )}
          {success && (
            <div className="mb-2">
              <SuccessBanner
                message={`Saved for ${taxYear} — your tax summary has been updated.`}
                onDismiss={() => setSuccess(false)}
              />
            </div>
          )}

          <form onSubmit={handleSave} className="flex flex-col gap-0">
            <div className="flex flex-col gap-1">
              <label className="text-sm font-medium">Annual rent paid (NGN)</label>
              <input
                type="number"
                min={0}
                step="0.01"
                value={form.annual_rent_paid}
                onChange={(e) =>
                  setForm({ ...form, annual_rent_paid: e.target.value === '' ? '' : Number(e.target.value) })
                }
                className="h-10 w-full max-w-[300px] rounded-md border border-outline-variant bg-transparent px-3 text-sm focus:border-accent focus:outline-none"
              />
            </div>

            <label className="mt-3 flex items-center gap-2 text-[13px]">
              <input
                type="checkbox"
                checked={form.has_home_office}
                onChange={(e) => setForm({ ...form, has_home_office: e.target.checked })}
              />
              I use part of my home for work
            </label>

            {form.has_home_office && (
              <div className="mt-2 flex flex-col gap-1">
                <label className="text-sm">Home office share ({form.home_office_percentage}%)</label>
                <input
                  type="range"
                  min={0}
                  max={100}
                  step={5}
                  value={form.home_office_percentage}
                  onChange={(e) => setForm({ ...form, home_office_percentage: Number(e.target.value) })}
                  className="w-full max-w-[300px]"
                />
              </div>
            )}
            
            {!form.has_home_office && (
              <p className="m-0 mt-2 text-[12px] text-on-surface-variant max-w-lg">
                If you work from home, this deducts the portion of your rent selected as business expenses and deducts that share of your utility bills as well.
              </p>
            )}

            <Button type="submit" isLoading={mutation.isPending} className="mt-3 self-start">
              Save for {taxYear}
            </Button>
          </form>
        </div>
      )}
    </div>
  )
}

function FilingGuidancePanel({
  guidance,
  isLoading,
  state,
}: {
  guidance?: FilingGuidance
  isLoading: boolean
  state: string | null | undefined
}) {
  const [guideOpen, setGuideOpen] = useState(false)

  if (isLoading) return null

  const displayState = guidance?.state || state || 'your state'
  const fallbackSearchUrl = `https://www.google.com/search?q=${encodeURIComponent(`${displayState} Internal Revenue Service tax filing portal`)}`
  const portalUrl = guidance?.portal_url || fallbackSearchUrl
  const portalLabel = guidance?.portal_name ? `Go to ${guidance.portal_name}` : `Go to ${displayState} portal`

  return (
    <div className="flex flex-col gap-3 rounded-xl border border-divider bg-surface p-5 shadow-sm mt-4">
      <span className="text-[15px] font-semibold text-on-surface">Filing guidance for {displayState}</span>
      <p className="m-0 text-[13px] text-on-surface-variant">
        {guidance?.note ??
          'GigTax does not file on your behalf. Once you are happy with this report, take it to your State Internal Revenue Service to complete your filing.'}
      </p>

      {guideOpen && (
        <div className="markdown-content filing-guide-content text-[13px] text-on-surface-variant leading-[1.6]">
          {guidance?.guide_markdown ? (
            <ReactMarkdown>{guidance.guide_markdown}</ReactMarkdown>
          ) : (
            <div className="flex flex-col gap-2">
              <p className="m-0"><strong>1. Register or confirm your Tax Identification Number (TIN).</strong> Most State Internal Revenue Services let you self-register online, or you can visit a tax office in person with a valid ID.</p>
              <p className="m-0"><strong>2. Download this self-assessment report.</strong> It shows your income, deductions, capital allowances, reliefs and the net tax payable, with the section of the Nigeria Tax Act 2025 behind each figure.</p>
              <p className="m-0"><strong>3. Submit it through your state's Direct Assessment filing channel.</strong> Some states accept this online, others ask you to bring a printed copy. Search below to find out which applies to {displayState}.</p>
              <p className="m-0"><strong>4. Pay before the deadline shown on your assessment.</strong> Keep the payment receipt together with this report as your record.</p>
              <p className="m-0 text-on-surface-variant/60">Portal addresses change from time to time, so we point you to search for the current one rather than link a fixed address that can go stale.</p>
            </div>
          )}
        </div>
      )}

      <div className="flex flex-wrap items-center gap-3">
        <button
          onClick={() => setGuideOpen((v) => !v)}
          className="rounded-md border border-outline-variant bg-transparent px-4 py-2 text-sm font-medium text-on-surface-variant transition-colors hover:bg-surface-container-low"
        >
          {guideOpen ? 'Hide full guide' : 'Read the full guide'}
        </button>
        <a
          href={portalUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center justify-center gap-2 rounded-md bg-accent px-4 py-2 text-sm font-semibold text-bg transition-colors hover:opacity-90"
        >
          <span className="material-symbols-outlined text-[15px]">open_in_new</span>
          {portalLabel}
        </a>
      </div>
    </div>
  )
}

function BreakdownRow({
  label,
  section,
  value,
  items,
  emptyHint,
}: {
  label: string
  section: string
  value: number
  items: CategoryAmountItem[]
  emptyHint?: ReactNode
}) {
  const [isOpen, setIsOpen] = useState(false)

  return (
    <div>
      <button 
        onClick={() => setIsOpen(!isOpen)} 
        className="flex w-full cursor-pointer items-center gap-2 border-none bg-transparent p-3 text-left font-inherit text-inherit"
      >
        <span className="material-symbols-outlined shrink-0 text-base text-on-surface-variant transition-transform" style={{ transform: isOpen ? 'rotate(90deg)' : 'none' }}>
          chevron_right
        </span>
        <span className="flex-1 text-[13px]">
          {label} <span className="text-[11px] text-on-surface-variant/70">{section}</span>
        </span>
        <span className="tabular-nums text-[13px] font-semibold">{formatNaira(value)}</span>
      </button>
      
      {isOpen && (
        <div className="px-3 pb-3">
          <table className="w-full text-left text-[13px]">
            <thead>
              <tr className="border-b border-divider">
                <th className="pb-1 font-medium text-on-surface-variant">Category</th>
                <th className="pb-1 font-medium text-on-surface-variant tabular-nums text-right">Amount</th>
              </tr>
            </thead>
            <tbody>
              {items.length > 0 ? (
                items.map((item) => (
                  <tr key={item.category_name} className="border-b border-divider/50 last:border-none">
                    <td className="py-2 text-on-surface-variant">
                      {item.category_name}
                      {item.rate != null && item.rate < 100 && (
                        <span className="ml-2 rounded bg-accent/10 px-1.5 py-0.5 text-[11px] font-medium text-accent">
                          {item.rate.toFixed(0)}% of {formatNaira(item.gross_amount ?? item.amount)}
                        </span>
                      )}
                    </td>
                    <td className="py-2 text-right text-on-surface-variant tabular-nums">{formatNaira(item.amount)}</td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={2} className="py-2 italic text-on-surface-variant">
                    {emptyHint ?? 'Nothing in this category.'}
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
