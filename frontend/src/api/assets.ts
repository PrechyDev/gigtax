import { apiFetch } from '../lib/apiClient'

export interface Asset {
  asset_id: string
  transaction_id: string | null
  description: string
  cost: number
  purchase_date: string
  asset_class: 'class_1' | 'class_2' | 'class_3'
  disposed: boolean
  disposed_date: string | null
  current_year_allowance: number
}

export function listAssets(taxYear?: number) {
  return apiFetch<Asset[]>('/assets', { query: { tax_year: taxYear } })
}

export function disposeAsset(assetId: string, disposedDate: string) {
  return apiFetch<Asset>(`/assets/${assetId}/dispose`, {
    method: 'PATCH',
    body: { disposed_date: disposedDate },
  })
}
