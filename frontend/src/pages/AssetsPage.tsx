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
import { TextField } from '../components/ui/FormField'
import { ApiError } from '../lib/apiClient'
import { formatNaira } from '../lib/formatters'
import type { Asset } from '../api/assets'

const ASSET_CLASS: Record<string, { tag: string; rate: string }> = {
  class_1: { tag: 'Class 1', rate: '10%/yr' },
  class_2: { tag: 'Class 2', rate: '20%/yr' },
  class_3: { tag: 'Class 3', rate: '25%/yr' },
}

/** No physical-category field exists on the asset record (asset_class is a
 * depreciation-rate tier, not a category) — derive an icon from the description as a
 * best-effort visual cue rather than a precise classification. */
function assetIcon(description: string): string {
  const d = description.toLowerCase()
  if (/laptop|macbook|computer|\bpc\b|desktop/.test(d)) return 'laptop_mac'
  if (/camera|lens|gopro/.test(d)) return 'photo_camera'
  if (/car|vehicle|bike|motorcycle|keke|bus/.test(d)) return 'directions_car'
  if (/chair|desk|table|cabinet|furniture/.test(d)) return 'chair'
  return 'inventory_2'
}

function assetStatusLine(asset: Asset): string {
  if (asset.disposed) return 'Disposed, no further allowance'
  if (asset.current_year_allowance === 0) return 'Fully written down'
  return 'Active, still being written down'
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
            <div className="rounded-lg bg-accent p-5 text-bg shadow-level-1">
              <p className="text-sm opacity-70">{currentYear} Deductible Allowance</p>
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
            <div className="grid gap-4" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))' }}>
              {assetsQuery.data.map((asset) => {
                const deemphasize = asset.disposed || asset.current_year_allowance === 0
                const cls = ASSET_CLASS[asset.asset_class] ?? { tag: asset.asset_class, rate: '—' }
                return (
                  <div
                    key={asset.asset_id}
                    className={`flex flex-col gap-3 rounded-lg bg-surface-container-lowest p-4 shadow-level-1 ${
                      deemphasize ? 'opacity-55' : ''
                    }`}
                  >
                    <div className="flex items-start justify-between">
                      <span className="material-symbols-outlined text-2xl text-accent">
                        {assetIcon(asset.description)}
                      </span>
                      <span className="rounded-full border border-outline-variant px-2 py-0.5 text-xs text-on-surface-variant">
                        {cls.tag}
                      </span>
                    </div>
                    <p className={`font-semibold ${asset.disposed ? 'line-through' : ''}`}>{asset.description}</p>
                    <div className="grid grid-cols-2 gap-2 text-xs">
                      <div>
                        <p className="text-on-surface-variant">Original cost</p>
                        <p className="tabular-nums font-medium">{formatNaira(asset.cost)}</p>
                      </div>
                      <div>
                        <p className="text-on-surface-variant">Rate</p>
                        <p className="font-medium">{cls.rate}</p>
                      </div>
                      <div>
                        <p className="text-on-surface-variant">This year's write-down</p>
                        <p className="tabular-nums font-medium text-emerald-dark">
                          {formatNaira(asset.current_year_allowance)}
                        </p>
                      </div>
                      <div>
                        <p className="text-on-surface-variant">Remaining value</p>
                        <p className="tabular-nums font-medium">{formatNaira(asset.remaining_value)}</p>
                      </div>
                    </div>
                    <p className="text-xs text-on-surface-variant">{assetStatusLine(asset)}</p>
                    {!asset.disposed && (
                      <button
                        className="self-start text-xs text-error hover:underline"
                        onClick={() => setDisposeTarget({ id: asset.asset_id, description: asset.description })}
                      >
                        Dispose
                      </button>
                    )}
                  </div>
                )
              })}
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
