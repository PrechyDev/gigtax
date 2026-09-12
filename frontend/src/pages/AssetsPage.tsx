import { useState, type FormEvent } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { disposeAsset, listAssets } from '../api/assets'
import { AppShell } from '../components/layout/AppShell'
import { Button } from '../components/ui/Button'
import { ErrorBanner } from '../components/ui/Banner'
import { EmptyState } from '../components/ui/EmptyState'
import { Modal } from '../components/ui/Modal'
import { PageSpinner } from '../components/ui/Spinner'
import { StatusPill, assetStatusTone } from '../components/ui/StatusPill'
import { TextField } from '../components/ui/FormField'
import { ApiError } from '../lib/apiClient'
import { formatDate, formatNaira } from '../lib/formatters'

const ASSET_CLASS_LABELS: Record<string, string> = {
  class_1: 'Class 1 (10%/yr)',
  class_2: 'Class 2 (20%/yr)',
  class_3: 'Class 3 (25%/yr)',
}

export function AssetsPage() {
  const navigate = useNavigate()
  const currentYear = new Date().getFullYear()

  const assetsQuery = useQuery({ queryKey: ['assets', currentYear], queryFn: () => listAssets(currentYear) })
  const [disposeTarget, setDisposeTarget] = useState<{ id: string; description: string } | null>(null)

  const totalValue = assetsQuery.data?.reduce((sum, a) => sum + a.cost, 0) ?? 0
  const totalCurrentYearDeduction = assetsQuery.data?.reduce((sum, a) => sum + a.current_year_allowance, 0) ?? 0

  return (
    <AppShell title="Asset Register">
      <div className="mb-6 flex items-center justify-between">
        <p className="text-on-surface-variant">Track hardware depreciation and capital allowances for {currentYear}.</p>
        <Button onClick={() => navigate('/ingestion')}>New Asset</Button>
      </div>

      {assetsQuery.isLoading && <PageSpinner />}
      {assetsQuery.isError && (
        <ErrorBanner message="Could not load your assets." onRetry={() => assetsQuery.refetch()} />
      )}

      {assetsQuery.data && (
        <>
          <div className="mb-6 grid grid-cols-1 gap-4 md:grid-cols-2">
            <div className="rounded-lg bg-surface-container-lowest p-5 shadow-level-1">
              <p className="text-sm text-on-surface-variant">Total Asset Value</p>
              <p className="text-2xl font-bold tabular-nums text-navy">{formatNaira(totalValue)}</p>
            </div>
            <div className="rounded-lg bg-navy p-5 text-white shadow-level-1">
              <p className="text-sm text-white/70">{currentYear} Deductible Allowance</p>
              <p className="text-2xl font-bold tabular-nums">{formatNaira(totalCurrentYearDeduction)}</p>
            </div>
          </div>

          {assetsQuery.data.length === 0 && (
            <EmptyState
              icon="inventory_2"
              message="No assets yet — capital purchases (laptops, cameras, equipment) will show up here."
              action={{ label: 'Add one via Ingestion', onClick: () => navigate('/ingestion') }}
            />
          )}

          {assetsQuery.data.length > 0 && (
            <div className="overflow-x-auto rounded-lg bg-surface-container-lowest shadow-level-1">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-outline-variant text-left text-xs font-semibold uppercase text-on-surface-variant">
                    <th className="px-4 py-3">Asset</th>
                    <th className="px-4 py-3 tabular-nums">Purchase Value</th>
                    <th className="px-4 py-3">Rate</th>
                    <th className="px-4 py-3 tabular-nums">Current Year Ded.</th>
                    <th className="px-4 py-3 tabular-nums">Claimed to Date</th>
                    <th className="px-4 py-3 tabular-nums">Remaining to Deduct</th>
                    <th className="px-4 py-3">Status</th>
                    <th className="px-4 py-3" />
                  </tr>
                </thead>
                <tbody>
                  {assetsQuery.data.map((asset) => {
                    const isFullyDepreciated = !asset.disposed && asset.current_year_allowance === 0
                    return (
                      <tr
                        key={asset.asset_id}
                        className={`border-b border-outline-variant last:border-0 ${
                          asset.disposed || isFullyDepreciated ? 'opacity-60' : ''
                        }`}
                      >
                        <td className="px-4 py-3">
                          <p className={asset.disposed ? 'line-through' : ''}>{asset.description}</p>
                          <p className="text-xs text-on-surface-variant">Purchased: {formatDate(asset.purchase_date)}</p>
                        </td>
                        <td className="px-4 py-3 tabular-nums">{formatNaira(asset.cost)}</td>
                        <td className="px-4 py-3">{ASSET_CLASS_LABELS[asset.asset_class] ?? asset.asset_class}</td>
                        <td className="px-4 py-3 tabular-nums text-emerald-dark">
                          {formatNaira(asset.current_year_allowance)}
                        </td>
                        <td className="px-4 py-3 tabular-nums">{formatNaira(asset.cumulative_allowance_claimed)}</td>
                        <td className="px-4 py-3 tabular-nums">{formatNaira(asset.remaining_value)}</td>
                        <td className="px-4 py-3">
                          <StatusPill
                            label={asset.disposed ? 'Disposed' : isFullyDepreciated ? 'Fully Depreciated' : 'Active'}
                            tone={assetStatusTone(asset.disposed, asset.current_year_allowance)}
                          />
                        </td>
                        <td className="px-4 py-3">
                          {!asset.disposed && (
                            <button
                              className="text-sm text-error hover:underline"
                              onClick={() => setDisposeTarget({ id: asset.asset_id, description: asset.description })}
                            >
                              Dispose
                            </button>
                          )}
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}

      {disposeTarget && (
        <DisposeAssetModal target={disposeTarget} onClose={() => setDisposeTarget(null)} />
      )}
    </AppShell>
  )
}

function DisposeAssetModal({
  target,
  onClose,
}: {
  target: { id: string; description: string }
  onClose: () => void
}) {
  const queryClient = useQueryClient()
  const [date, setDate] = useState(new Date().toISOString().slice(0, 10))
  const [error, setError] = useState<string | null>(null)

  const disposeMutation = useMutation({
    mutationFn: () => disposeAsset(target.id, new Date(date).toISOString()),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['assets'] })
      queryClient.invalidateQueries({ queryKey: ['dashboard'] })
      onClose()
    },
    onError: (err) => setError(err instanceof ApiError ? err.message : 'Could not update this asset.'),
  })

  function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError(null)
    disposeMutation.mutate()
  }

  return (
    <Modal title={`Dispose "${target.description}"`} onClose={onClose}>
      {error && (
        <div className="mb-4">
          <ErrorBanner message={error} />
        </div>
      )}
      <form onSubmit={handleSubmit} className="space-y-4">
        <TextField label="Disposal Date" type="date" required value={date} onChange={(e) => setDate(e.target.value)} />
        <div className="flex justify-end gap-2 pt-2">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" isLoading={disposeMutation.isPending}>
            Confirm Disposal
          </Button>
        </div>
      </form>
    </Modal>
  )
}
