import { apiFetch } from '../lib/apiClient'

export interface Category {
  category_id: string
  classification: 'Income' | 'Expense' | 'Relief' | 'Asset' | 'Unknown'
  category_name: string
  developer_slug: string
  description: string | null
  tax_treatment: string | null
  asset_class: string | null
}

export function listCategories() {
  return apiFetch<Category[]>('/categories')
}
